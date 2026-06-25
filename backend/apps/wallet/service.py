"""Business logic layer for wallet operations."""

import json
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.payments.enums import PaymentProvider, PaymentStatus
from apps.payments.models import Payment
from apps.payments.paystack_service import PaystackService
from apps.users.kyc_service import KYCService
from apps.users.repository import UserRepository
from apps.wallet.enums import (
    BalanceType,
    ReferenceType,
    TransactionDirection,
    TransactionStatus,
    TransactionType,
)
from apps.wallet.models import WalletTransactions
from apps.wallet.repository import PaymentRepository, WalletRepository
from apps.wallet.schemas import (
    PaymentInitiationResponse,
    PaymentResponse,
    TransactionResponse,
    WalletResponse,
    WithdrawalRequest,
)
from common.exceptions import (
    InsufficientFundsException,
    PaymentVerificationException,
    PaystackError,
    PaystackPaymentError,
    PaystackVerificationError,
    UserNotFoundException,
    WalletNotFoundException,
)
from common.pagination import PaginatedResponse
from config.settings import settings

logger = logging.getLogger(__name__)


class WalletService:
    """Service layer for wallet operations.

    Handles business logic for:
    - Wallet funding (via Paystack)
    - Withdrawals
    - Transaction history
    - Balance queries
    """

    def __init__(self, db: AsyncSession, flutterwave_service: PaystackService):
        """Initialize wallet service.

        Args:
            db: Async database session
            flutterwave_service: Paystack service instance

        """
        self._db = db
        self._wallet_repo = WalletRepository(db)
        self._payment_repo = PaymentRepository(db)
        self._user_repo = UserRepository(db)
        self._flutterwave_service = flutterwave_service
        self._kyc = KYCService(db)

    async def get_wallet(self, user_id: UUID) -> WalletResponse:
        """Get user's wallet balance."""
        wallet = await self._wallet_repo.get_by_user_id(user_id)
        if not wallet:
            raise WalletNotFoundException()

        return WalletResponse.model_validate(wallet)

    async def generate_transaction_reference(self):
        """Generate unique transaction reference.

        Returns:
            Unique transaction reference string

        Raises:
            RuntimeError: If unable to generate unique reference

        """
        max_retries = 10

        for attempt in range(max_retries):
            date_part = datetime.now(timezone.utc).strftime("%Y%m%d")

            # Generate random chars
            random_part = secrets.token_hex(3).upper()
            reference = f"APF-{date_part}-{random_part}"

            stmt = select(Payment).where(Payment.transaction_reference == reference)
            results = await self._db.execute(stmt)
            if results.scalar_one_or_none() is None:
                return reference
        # If we get here, we failed to generate unique ref
        logger.error(
            "Failed to generate unique transaction reference", attempts=max_retries
        )
        raise RuntimeError("Reference generation failed")

    async def initiate_funding(
        self, user_id: UUID, amount: Decimal, currency: str = "NGN"
    ) -> PaymentInitiationResponse:
        """Initiate wallet funding via Paystack.

        Creates a Payment record and returns payment link.
        Does NOT create WalletTransaction yet (that happens in webhook).

        Args:
            user_id: User initiating the funding
            amount: Amount to fund (minimum ₦100)
            currency: Currency code (default: NGN)

        Returns:
            PaymentInitiationResponse with payment link and reference

        Raises:
            WalletNotFoundException: If user has no wallet

        """
        # Ensure wallet exists
        wallet = await self._wallet_repo.get_by_user_id(user_id)
        if not wallet:
            raise WalletNotFoundException()

        # Generate transaction reference
        try:
            transaction_reference = await self.generate_transaction_reference()
        except RuntimeError as e:
            raise HTTPException(
                status_code=500, detail="Could not generate transaction reference"
            ) from e

        # Check for duplicate (idempotency)
        existing_payment = await self._payment_repo.get_payment_by_reference(
            transaction_reference
        )
        if existing_payment:
            if (
                existing_payment.payment_link
                and existing_payment.payment_link_expires_at
            ):
                now = datetime.now(timezone.utc)
                if existing_payment.payment_link_expires_at > now:
                    return PaymentInitiationResponse(
                        payment_link=existing_payment.payment_link,
                        transaction_reference=transaction_reference,
                        amount=existing_payment.amount,
                        expires_at=existing_payment.created_at + timedelta(hours=1),
                        version=existing_payment.version,
                    )

        # Implementng KYC checks
        await self._kyc.check_funding_limit(user_id, amount, wallet.available_funds)

        # Create Payment record
        payment_data = {
            "transaction_reference": transaction_reference,
            "provider": PaymentProvider.PAYSTACK.value,
            "wallet_id": wallet.id,
            "amount": amount,
            "currency": currency,
        }

        payment = await self._payment_repo.create_payment(payment_data)
        await self._db.commit()
        await self._db.refresh(payment)  # Refresh to load version column

        # Get user
        user_repo = UserRepository(self._db)
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()

        # Call Paystack API to get actual payment link
        try:
            payment_link = await self._flutterwave_service.initiate_payment(
                transaction_reference=transaction_reference,
                amount=amount,
                currency=currency,
                user_email=wallet.user.email,
                user_name=f"{user.first_name} {user.last_name}",
                redirect_url=f"{settings.frontend_url}/payment/{payment.id}/confirm",
                metadata={
                    "user_id": str(user_id),
                    "wallet_id": str(wallet.id),
                    "payment_id": str(payment.id),
                },
            )

            logger.info(
                f"Payment initiated for transaction reference: {transaction_reference}"
            )
        except PaystackPaymentError as e:
            logger.error(f"Failed to initiate payment: {e}")
            raise  # Re-raise the original exception

        # Store payment link and expiry in database
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        payment.payment_link = payment_link
        payment.payment_link_expires_at = expires_at
        self._db.add(payment)
        await self._db.commit()

        return PaymentInitiationResponse(
            payment_link=payment_link,
            transaction_reference=transaction_reference,
            amount=amount,
            expires_at=payment.created_at + timedelta(hours=1),
            version=payment.version,
        )

    async def handle_webhook(
        self,
        transaction_reference: str,
        provider_reference: str,
        status: str,
        amount: Decimal,
        provider_response: dict,
    ) -> PaymentResponse:
        """Handle Paystack webhook for payment completion.

        Updates Payment status and creates WalletTransaction on success.

        Args:
            transaction_reference: Our transaction reference
            provider_reference: Paystack's reference
            status: Payment status from provider
            amount: Amount paid
            provider_response: Full webhook payload

        Returns:
            PaymentResponse with updated payment details

        Raises:
            PaymentVerificationException: If payment not found or verification fails

        """
        # Get payment record
        payment = await self._payment_repo.get_payment_by_reference(
            transaction_reference
        )
        if not payment:
            raise PaymentVerificationException("Payment not found")

        # Verify payment with Paystack API
        try:
            verified_data = await self._flutterwave_service.verify_payment(
                transaction_reference
            )
        except PaystackVerificationError as e:
            logger.error(
                f"Payment verification failed for {transaction_reference}: {e}"
            )
            raise PaymentVerificationException(f"Payment verification failed: {str(e)}")

        # Extract verified data
        verified_status = verified_data.get("status")
        verified_amount = Decimal(str(verified_data.get("amount")))
        verified_currency = verified_data.get("currency")
        verified_reference = verified_data.get("reference")

        # Validate amount matches
        if verified_amount != payment.amount:
            logger.error(
                f"Amount mismatch for {transaction_reference}: "
                f"expected {payment.amount}, got {verified_amount}"
            )
            raise PaymentVerificationException(
                f"Amount mismatch: expected {payment.amount}, got {verified_amount}"
            )

        # Validate currency matches
        if verified_currency != payment.currency:
            logger.error(
                f"Currency mismatch for {transaction_reference}: "
                f"expected {payment.currency}, got {verified_currency}"
            )
            raise PaymentVerificationException(
                f"Currency mismatch: expected {payment.currency}, "
                f"got {verified_currency}"
            )

        # Determine payment status — Paystack uses "success" for completed payments
        now = datetime.now(timezone.utc)
        payment_status = (
            PaymentStatus.COMPLETED.value
            if verified_status == "success"
            else PaymentStatus.FAILED.value
        )

        updated_payment = await self._payment_repo.update_payment_status(
            payment_id=payment.id,
            status=payment_status,
            provider_reference=verified_reference,
            provider_response=json.dumps(provider_response),
            webhook_received_at=now,
            verified_at=now,
        )

        # If successful, credit wallet and create transaction
        if payment_status == PaymentStatus.COMPLETED.value:
            # REASONING: Use payment.wallet_id (FK column) instead of
            # payment.wallet.user_id to avoid triggering lazy loading
            # of the wallet relationship
            wallet_id = payment.wallet_id

            # Get wallet by ID with lock, and eager load user relationship
            wallet = await self._wallet_repo.get_by_id_with_lock(wallet_id)
            if not wallet:
                raise WalletNotFoundException()

            # REASONING: Force load user relationship NOW while in async context
            # This prevents "greenlet_spawn" errors when accessing wallet.user later
            await self._db.refresh(wallet, ["user"])

            # Extract user data as primitives (not ORM objects) for Celery
            # REASONING: Celery tasks run in separate processes and
            # can't access ORM objects. We extract primitive values now
            # while we're in the async context
            user_email = wallet.user.email
            user_first_name = wallet.user.first_name
            user_last_name = wallet.user.last_name

            # Record balance before — available_funds only
            balance_before = wallet.available_funds

            # Update wallet balance (use verified amount, not webhook amount)
            await self._wallet_repo.update_balances(
                wallet_id=wallet.id,
                available_delta=verified_amount,
                locked_delta=Decimal("0.00"),
                escrow_delta=Decimal("0.00"),
            )

            # Refresh to get updated available_funds for balance_after
            await self._db.refresh(wallet)

            # Create wallet transaction (use verified amount)
            transaction_data = {
                "amount": verified_amount,
                "balance_before": balance_before,
                "balance_after": wallet.available_funds,
                "description": f"Wallet funding via {payment.provider}",
                "transaction_type": TransactionType.DEPOSIT.value,
                "direction": TransactionDirection.CREDIT.value,
                "balance_type": BalanceType.AVAILABLE.value,
                "reference_id": payment.id,
                "reference_type": ReferenceType.DEPOSIT.value,
            }

            wallet_transaction = await self._wallet_repo.create_transaction(
                wallet_id=wallet.id, data=transaction_data
            )

            # Link payment to wallet transaction
            await self._payment_repo.update_payment_status(
                payment_id=payment.id,
                status=payment_status,
                wallet_transaction_id=wallet_transaction.id,
            )

            # REASONING: Refresh wallet to get updated balance after commit
            await self._db.refresh(wallet)
            new_balance = wallet.available_funds

            # Send funding notification email
            # REASONING: Use primitives extracted earlier
            # (user_email, user_first_name, etc.) instead of accessing
            # ORM relationships. This prevents lazy loading errors and
            # ensures Celery task receives serializable data, not ORM
            # objects.
            from apps.wallet.tasks import send_wallet_funded_email  # noqa: F811

            send_wallet_funded_email.delay(
                user_email=user_email,
                user_name=f"{user_first_name} {user_last_name}",
                amount=str(verified_amount),
                currency=payment.currency,
                new_balance=str(new_balance),
            )

        await self._db.commit()

        return PaymentResponse.model_validate(updated_payment)

    async def get_transactions(
        self,
        user_id: UUID,
        transaction_type: Optional[str] = None,
        direction: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> PaginatedResponse:
        """Get user's transaction history with pagination.

        Args:
            user_id: User ID
            transaction_type: Filter by transaction type (optional)
            direction: Filter by direction (CREDIT/DEBIT) (optional)
            page: Page number (default: 1)
            limit: Items per page (default: 20)

        Returns:
            PaginatedResponse with TransactionResponse items

        Raises:
            WalletNotFoundException: If user has no wallet

        """
        wallet = await self._wallet_repo.get_by_user_id(user_id)
        if not wallet:
            raise WalletNotFoundException()

        filters = {}
        if transaction_type:
            filters["transaction_type"] = transaction_type
        if direction:
            filters["direction"] = direction

        result = await self._wallet_repo.get_transactions(
            wallet_id=wallet.id, filters=filters, page=page, limit=limit
        )

        # REASONING: Convert ORM objects to Pydantic schemas for serialization
        # The pagination helper returns raw WalletTransactions ORM objects
        # which FastAPI cannot serialize. We need TransactionResponse schemas.
        result.data = [
            TransactionResponse.model_validate(transaction)
            for transaction in result.data
        ]

        return result

    async def initiate_withdrawal(
        self, user_id: UUID, withdrawal_request: WithdrawalRequest
    ) -> TransactionResponse:
        """Initiate withdrawal from wallet to bank account.

        Debits wallet and creates pending withdrawal transaction.
        Actual bank transfer happens via Celery task.

        Args:
            user_id: User initiating withdrawal
            withdrawal_request: Withdrawal details (amount, version)

        Returns:
            TransactionResponse for the withdrawal

        Raises:
            WalletNotFoundException: If user has no wallet
            InsufficientFundsException: If insufficient available balance
            BankDetailsNotSetupException: If user hasn't set up bank details

        """
        # Verify user has bank details set up
        user = await self._user_repo.get_with_profile(user_id)
        if not user or not user.profile:
            raise UserNotFoundException()

        if not user.profile.bank_code or not user.profile.account_number:
            from common.exceptions import BankDetailsNotSetupException

            raise BankDetailsNotSetupException()

        # Implementng KYC checks
        await self._kyc.check_withdrawal_limit(user_id, withdrawal_request.amount)

        # Get wallet with lock
        wallet = await self._wallet_repo.get_by_user_id_with_lock(user_id)
        if not wallet:
            raise WalletNotFoundException()

        # Check sufficient balance
        if wallet.available_funds < withdrawal_request.amount:
            raise InsufficientFundsException(
                f"Insufficient balance. Available: "
                f"₦{wallet.available_funds}, Required: "
                f"₦{withdrawal_request.amount}"
            )

        # Record balance before — available_funds only
        balance_before = wallet.available_funds

        # Debit available funds
        await self._wallet_repo.update_balances(
            wallet_id=wallet.id,
            available_delta=-withdrawal_request.amount,
            locked_delta=Decimal("0.00"),
            escrow_delta=Decimal("0.00"),
        )

        # Refresh to get updated available_funds
        await self._db.refresh(wallet)

        # Create withdrawal transaction with PENDING status
        transaction_data = {
            "amount": withdrawal_request.amount,
            "balance_before": balance_before,
            "balance_after": wallet.available_funds,
            "description": (
                f"Withdrawal to {user.profile.bank_code} - "
                f"{user.profile.account_number}"
            ),
            "transaction_type": TransactionType.WITHDRAWAL.value,
            "direction": TransactionDirection.DEBIT.value,
            "balance_type": BalanceType.AVAILABLE.value,
            "status": TransactionStatus.PENDING.value,
            "reference_id": None,  # Will be updated when bank transfer completes
            "reference_type": ReferenceType.WITHDRAWAL.value,
        }

        transaction = await self._wallet_repo.create_transaction(
            wallet_id=wallet.id, data=transaction_data
        )

        await self._db.commit()

        # Trigger Celery task for bank transfer
        from apps.wallet.tasks import process_withdrawal_transfer  # noqa: F811

        process_withdrawal_transfer.delay(str(transaction.id))

        return TransactionResponse.model_validate(transaction)

    async def process_withdrawal_transfer(
        self,
        transaction_id: UUID,
    ) -> WalletTransactions:
        """Process bank transfer for a pending withdrawal by ID.

        Compatibility wrapper.

        Args:
            transaction_id: Transaction UUID

        Returns:
            Updated wallet transaction

        """
        transaction = await self._wallet_repo.get_transaction_by_id(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")

        return await self.process_withdrawal_transfer_direct(transaction)

    async def process_withdrawal_transfer_direct(
        self,
        transaction: WalletTransactions,
    ) -> WalletTransactions:
        """Process bank transfer for a pre-loaded withdrawal transaction.

        Called by Celery task after wallet has been debited.
        Assumes transaction.wallet and transaction.wallet.user are
        loaded (Eager loaded).

        Args:
            transaction: The pending withdrawal transaction object

        Returns:
            Updated WalletTransaction

        """
        transaction_id = transaction.id

        # Validate it is a withdrawal and pending
        if transaction.transaction_type != TransactionType.WITHDRAWAL:
            logger.error(f"Transaction {transaction_id} is not a withdrawal")
            raise ValueError(f"Transaction {transaction_id} is not a withdrawal")

        if transaction.status != TransactionStatus.PENDING:
            logger.error(
                f"Transaction {transaction_id} is not pending "
                f"(status: {transaction.status})"
            )
            raise ValueError(
                f"Transaction {transaction_id} is not pending "
                f"(status: {transaction.status})"
            )

        # Access pre-loaded user and bank details
        # REASONING: Wallet and user relations must be pre-loaded via
        # selectinload to avoid triggering lazy loading (which in async
        # context/concurrency causes errors)
        user = transaction.wallet.user
        profile = getattr(user, "profile", None)

        # Validate bank details exist
        if not profile or not profile.bank_code or not profile.account_number:
            await self._refund_failed_withdrawal(
                transaction, "Bank details not set up in profile"
            )
            from common.exceptions import BankDetailsNotSetupException

            raise BankDetailsNotSetupException()

        # Generate unique reference for Paystack transfer
        transfer_reference = (
            f"APW-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
        )

        # Call Paystack Transfer API
        logger.info(f"Initiating Paystack transfer for tx: {transaction_id}")
        try:
            transfer_data = await self._flutterwave_service.initiate_transfer(
                account_bank=profile.bank_code,
                account_number=profile.account_number,
                amount=transaction.amount,
                currency="NGN",
                narration="Withdrawal from Auction Platform",
                reference=transfer_reference,
            )

            # Success - update transaction status
            transaction.status = TransactionStatus.COMPLETED

            # Update description to include transfer details
            transaction.description = (
                f"{transaction.description} | "
                f"Transfer Ref: {transfer_reference} | "
                f"Transfer ID: {transfer_data.get('id')} | "
                f"Account: {profile.account_number}"
            )

            self._db.add(transaction)
            # REASONING: Removing manual commit/refresh here because
            # this method is called within the get_async_db_session()
            # context manager which handles the final commit
            # automatically. This prevents "another operation is in
            # progress" InterfaceErrors.

            logger.info(
                f"Withdrawal processed successfully: {transaction_id}, "
                f"transfer_ref: {transfer_reference}"
            )

            return transaction

        except PaystackError as e:
            # Failure - refund wallet and mark as failed
            logger.error(f"Withdrawal transfer failed for {transaction_id}: {e}")

            await self._refund_failed_withdrawal(transaction, str(e))

            raise

    async def _refund_failed_withdrawal(
        self, transaction: WalletTransactions, error_message: str = "Transfer failed"
    ) -> None:
        """Refund wallet for a failed withdrawal.

        Credits the wallet back and marks transaction as failed.

        Args:
            transaction: The failed withdrawal transaction
            error_message: Reason for failure

        """
        # Credit wallet back
        await self._wallet_repo.credit_wallet(
            user_id=transaction.wallet.user_id,
            amount=transaction.amount,
            description=f"Refund for failed withdrawal | Reason: {error_message}",
        )

        # Update transaction status to failed
        transaction.status = TransactionStatus.FAILED
        transaction.description = f"{transaction.description} | FAILED: {error_message}"

        self._db.add(transaction)
        # REASONING: Manual commit removed to avoid conflict with task context manager.

        logger.info(
            f"Refunded failed withdrawal: {transaction.id}, "
            f"amount: {transaction.amount}, "
            f"reason: {error_message}"
        )

    async def get_wallet_transactions_admin(
        self,
        page: int,
        limit: int,
        transaction_type: Optional[str] = None,
        direction: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse:
        """Get all wallet transactions for admin dashboard."""
        result = await self._wallet_repo.get_all_transactions(
            page, limit, transaction_type, direction, search
        )

        from apps.wallet.schemas import AdminTransactionResponse

        result.data = [
            AdminTransactionResponse.model_validate(tx) for tx in result.data
        ]
        return result

    async def get_payments_admin(
        self,
        page: int,
        limit: int,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse:
        """Get all payments for admin dashboard."""
        result = await self._payment_repo.get_all_payments(page, limit, status, search)

        result.data = [PaymentResponse.model_validate(p) for p in result.data]
        return result
