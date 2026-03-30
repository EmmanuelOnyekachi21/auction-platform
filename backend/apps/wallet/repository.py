"""Data access layer for wallet operations."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.payments.models import Payment
from apps.users.models import User
from apps.wallet.enums import BalanceType, TransactionDirection, TransactionType
from apps.wallet.models import Wallet, WalletTransactions
from common.exceptions import WalletLockException, WalletNotFoundException
from common.pagination import PaginatedResponse, paginate


class WalletRepository:
    """Repository for wallet database operations."""

    def __init__(self, db: AsyncSession):
        """Initialize wallet repository.

        Args:
            db: Async database session

        """
        self._db = db

    async def get_by_user_id(self, user_id: UUID) -> Wallet | None:
        """Get wallet by user ID.

        Args:
            user_id: User UUID

        Returns:
            Wallet instance or None if not found

        """
        stmt = select(Wallet).where(Wallet.user_id == user_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id_with_lock(self, user_id: UUID) -> Wallet | None:
        """Get wallet by user ID with pessimistic lock.

        Args:
            user_id: User UUID

        Returns:
            Wallet instance or None if not found

        """
        stmt = select(Wallet).where(Wallet.user_id == user_id).with_for_update()
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_wallet(self, wallet_id: UUID):
        """Get wallet by ID without lock.

        Args:
            wallet_id: Wallet UUID

        Returns:
            Wallet instance or None if not found

        """
        stmt = select(Wallet).where(Wallet.id == wallet_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_balances(
        self,
        wallet_id: UUID,
        available_delta: Decimal,
        locked_delta: Decimal,
        escrow_delta: Decimal,
    ) -> Wallet:
        """Update wallet balances atomically.

        Args:
            wallet_id: Wallet UUID
            available_delta: Change in available funds
            locked_delta: Change in locked funds
            escrow_delta: Change in escrow funds

        Returns:
            Updated wallet instance

        Raises:
            WalletNotFoundException: If wallet not found
            WalletLockException: If balance would become negative

        """
        wallet = await self.get_wallet(wallet_id)

        if not wallet:
            raise WalletNotFoundException()

        # Compute new balances
        new_available = wallet.available_funds + available_delta
        new_locked = wallet.locked_funds + locked_delta
        new_escrow = wallet.escrow_funds + escrow_delta

        # Validate (NO NEGATIVES)
        if new_available < 0:
            raise WalletLockException("Insufficient available balance")

        if new_locked < 0:
            raise WalletLockException("Insufficient locked balance")

        if new_escrow < 0:
            raise WalletLockException("Insufficient escrow balance")

        # Apply updates
        wallet.available_funds = new_available
        wallet.locked_funds = new_locked
        wallet.escrow_funds = new_escrow

        self._db.add(wallet)
        await self._db.flush()
        await self._db.refresh(wallet)

        return wallet

    async def create_transaction(
        self, wallet_id: Wallet, data: dict
    ) -> WalletTransactions:
        """Create a new wallet transaction record.

        Args:
            wallet_id: Wallet UUID
            data: Transaction data dictionary

        Returns:
            Created transaction instance

        """
        transaction = WalletTransactions(wallet_id=wallet_id, **data)
        self._db.add(transaction)
        await self._db.flush()
        await self._db.refresh(transaction)

        return transaction

    async def get_transactions(
        self,
        wallet_id: UUID,
        filters: dict,
        page: int,
        limit: int,
    ) -> PaginatedResponse:
        """Get paginated transaction history for a wallet.

        Args:
            wallet_id: Wallet UUID
            filters: Filter dictionary (transaction_type, direction)
            page: Page number
            limit: Items per page

        Returns:
            Paginated response with transactions

        """
        stmt = (
            select(WalletTransactions)
            .where(WalletTransactions.wallet_id == wallet_id)
            .order_by(desc(WalletTransactions.created_at))
        )

        # apply filters
        if filters.get("transaction_type"):
            stmt = stmt.where(
                WalletTransactions.transaction_type == filters["transaction_type"]
            )

        if filters.get("direction"):
            stmt = stmt.where(WalletTransactions.direction == filters["direction"])

        return await paginate(stmt, page, limit, self._db)

    async def get_transaction_by_reference(
        self, reference: str
    ) -> WalletTransactions | None:
        """Get transaction by reference ID.

        Args:
            reference: Transaction reference ID

        Returns:
            Transaction instance or None if not found

        """
        stmt = select(WalletTransactions).where(
            WalletTransactions.reference_id == reference
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_transaction_by_id(
        self, transaction_id: UUID
    ) -> WalletTransactions | None:
        """Get transaction by ID with wallet relationship loaded.

        Args:
            transaction_id: Transaction UUID

        Returns:
            Transaction instance with wallet and user loaded

        """
        stmt = (
            select(WalletTransactions)
            .options(
                selectinload(WalletTransactions.wallet)
                .selectinload(Wallet.user)
                .selectinload(User.profile)
            )
            .where(WalletTransactions.id == transaction_id)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def credit_wallet(
        self, user_id: UUID, amount: Decimal, description: str = "Wallet credit"
    ) -> WalletTransactions:
        """Credit user's available wallet balance.

        Args:
            user_id: User ID
            amount: Amount to credit
            description: Transaction description

        Returns:
            Created transaction record

        """
        wallet = await self.get_by_user_id_with_lock(user_id)
        if not wallet:
            raise WalletNotFoundException()

        # Record balance before
        balance_before = wallet.available_funds

        # Update balance
        wallet.available_funds += amount
        balance_after = wallet.available_funds

        self._db.add(wallet)
        await self._db.flush()

        # Create transaction record
        transaction = await self.create_transaction(
            wallet_id=wallet.id,
            data={
                "amount": amount,
                "balance_before": balance_before,
                "balance_after": balance_after,
                "description": description,
                "transaction_type": TransactionType.REFUND,
                "direction": TransactionDirection.CREDIT,
                "balance_type": BalanceType.AVAILABLE,
            },
        )

        return transaction


class PaymentRepository:
    """Repository for payment operations."""

    def __init__(self, db: AsyncSession):
        """Initialize payment repository.

        Args:
            db: Async database session

        """
        self._db = db

    async def create_payment(self, data: dict):
        """Create a new payment record.

        Args:
            data: Payment data dictionary

        Returns:
            Created payment instance

        """
        payment = Payment(**data)
        self._db.add(payment)
        await self._db.flush()
        await self._db.refresh(payment)
        return payment

    async def get_payment_by_reference(self, transaction_reference: str):
        """Get payment by transaction reference (for idempotency).

        Args:
            transaction_reference: Transaction reference string

        Returns:
            Payment instance or None if not found

        """
        stmt = select(Payment).where(
            Payment.transaction_reference == transaction_reference
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_payment_status(
        self,
        payment_id: UUID,
        status: str,
        provider_reference: str | None = None,
        provider_response: str | None = None,
        webhook_received_at=None,
        verified_at=None,
        wallet_transaction_id: UUID | None = None,
    ):
        """Update payment status and related fields.

        Args:
            payment_id: Payment UUID
            status: New payment status
            provider_reference: Provider reference (optional)
            provider_response: Provider response JSON (optional)
            webhook_received_at: Webhook timestamp (optional)
            verified_at: Verification timestamp (optional)
            wallet_transaction_id: Linked transaction ID (optional)

        Returns:
            Updated payment instance or None if not found

        """
        stmt = select(Payment).where(Payment.id == payment_id)
        result = await self._db.execute(stmt)
        payment = result.scalar_one_or_none()

        if not payment:
            return None

        payment.status = status
        if provider_reference:
            payment.provider_reference = provider_reference
        if provider_response:
            payment.provider_response = provider_response
        if webhook_received_at:
            payment.webhook_received_at = webhook_received_at
        if verified_at:
            payment.verified_at = verified_at
        if wallet_transaction_id:
            payment.wallet_transaction_id = wallet_transaction_id

        self._db.add(payment)
        await self._db.flush()
        await self._db.refresh(payment)

        return payment
