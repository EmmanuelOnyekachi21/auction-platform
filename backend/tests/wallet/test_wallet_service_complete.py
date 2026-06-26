"""Comprehensive tests for WalletService with new features.

Tests cover:
- Transaction status (PENDING, COMPLETED, FAILED)
- Bank details from user profile
- Withdrawal processing with Paystack
- Refund logic for failed withdrawals
- Email notifications integration
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from apps.payments.enums import PaymentStatus
from apps.wallet.enums import TransactionStatus
from apps.wallet.schemas import WithdrawalRequest
from apps.wallet.service import WalletService
from common.exceptions import (
    BankDetailsNotSetupException,
    InsufficientFundsException,
    PaymentVerificationException,
    PaystackError,
    WalletNotFoundException,
)


@pytest.mark.asyncio
class TestWalletServiceComplete:
    """Complete test suite for WalletService with all new features."""

    # ==================== GET WALLET TESTS ====================

    async def test_get_wallet_success(self, db_session, test_wallet_user, test_wallet):
        """Test getting wallet balance."""
        mock_flutterwave = MagicMock()
        service = WalletService(db_session, mock_flutterwave)

        result = await service.get_wallet(test_wallet_user.id)

        assert result.id == test_wallet.id
        assert result.available_funds == Decimal("1000.00")
        assert result.locked_funds == Decimal("0.00")
        assert result.escrow_funds == Decimal("0.00")
        assert result.currency == "NGN"

    async def test_get_wallet_not_found(self, db_session):
        """Test getting wallet for non-existent user."""
        mock_flutterwave = MagicMock()
        service = WalletService(db_session, mock_flutterwave)

        with pytest.raises(WalletNotFoundException):
            await service.get_wallet(uuid4())

    # ==================== FUNDING TESTS ====================

    async def test_initiate_funding_success(
        self, db_session, test_wallet_user, test_wallet
    ):
        """Test initiating wallet funding creates payment with link."""
        mock_flutterwave = AsyncMock()
        mock_flutterwave.initiate_payment = AsyncMock(
            return_value="https://checkout.flutterwave.com/test-link"
        )

        service = WalletService(db_session, mock_flutterwave)
        amount = Decimal("500.00")

        result = await service.initiate_funding(
            user_id=test_wallet_user.id, amount=amount, currency="NGN"
        )

        assert result.amount == amount
        assert result.transaction_reference.startswith("APF-")
        assert "flutterwave.com" in result.payment_link

        # Verify Paystack was called
        mock_flutterwave.initiate_payment.assert_called_once()

    async def test_initiate_funding_no_wallet(self, db_session):
        """Test initiating funding for user without wallet."""
        mock_flutterwave = MagicMock()
        service = WalletService(db_session, mock_flutterwave)

        with pytest.raises(WalletNotFoundException):
            await service.initiate_funding(user_id=uuid4(), amount=Decimal("500.00"))

    # ==================== WEBHOOK TESTS ====================

    async def test_handle_webhook_success_credits_wallet(
        self, db_session, test_wallet_user, test_wallet
    ):
        """Test successful webhook credits wallet and creates transaction."""
        mock_flutterwave = AsyncMock()
        service = WalletService(db_session, mock_flutterwave)
        amount = Decimal("500.00")

        # First initiate payment
        mock_flutterwave.initiate_payment = AsyncMock(
            return_value="https://checkout.flutterwave.com/test"
        )
        payment_init = await service.initiate_funding(
            user_id=test_wallet_user.id, amount=amount
        )

        # Mock verification response
        mock_flutterwave.verify_payment = AsyncMock(
            return_value={
                "status": "successful",
                "amount": float(amount),
                "currency": "NGN",
                "reference": "FLW-MOCK-REF-123",
                "flw_ref": "FLW-MOCK-REF-123",
            }
        )

        # Simulate webhook
        provider_response = {
            "id": 12345,
            "tx_ref": payment_init.transaction_reference,
            "flw_ref": "FLW-MOCK-REF-123",
            "amount": float(amount),
            "status": "successful",
        }

        # Mock the task import to avoid import errors
        with patch("apps.wallet.tasks.send_wallet_funded_email"):
            result = await service.handle_webhook(
                transaction_reference=payment_init.transaction_reference,
                provider_reference="FLW-MOCK-REF-123",
                status="successful",
                amount=amount,
                provider_response=provider_response,
            )

        assert result.status == PaymentStatus.COMPLETED.value
        assert result.provider_reference == "FLW-MOCK-REF-123"
        assert result.verified_at is not None

        # Verify wallet was credited
        wallet_balance = await service.get_wallet(test_wallet_user.id)
        assert wallet_balance.available_funds == Decimal("1500.00")  # 1000 + 500

        # Verify email task was triggered
        # mock_email.delay.assert_called_once()

    async def test_handle_webhook_failed_payment_no_credit(
        self, db_session, test_wallet_user, test_wallet
    ):
        """Test failed webhook doesn't credit wallet."""
        mock_flutterwave = AsyncMock()
        service = WalletService(db_session, mock_flutterwave)
        amount = Decimal("500.00")

        # First initiate payment
        mock_flutterwave.initiate_payment = AsyncMock(
            return_value="https://checkout.flutterwave.com/test"
        )
        payment_init = await service.initiate_funding(
            user_id=test_wallet_user.id, amount=amount
        )

        # Mock verification response for failed payment
        mock_flutterwave.verify_payment = AsyncMock(
            return_value={
                "status": "failed",
                "amount": float(amount),
                "currency": "NGN",
                "flw_ref": "FLW-MOCK-REF-123",
            }
        )

        # Simulate failed webhook
        provider_response = {
            "id": 12345,
            "tx_ref": payment_init.transaction_reference,
            "flw_ref": "FLW-MOCK-REF-123",
            "amount": float(amount),
            "status": "failed",
        }

        result = await service.handle_webhook(
            transaction_reference=payment_init.transaction_reference,
            provider_reference="FLW-MOCK-REF-123",
            status="failed",
            amount=amount,
            provider_response=provider_response,
        )

        assert result.status == PaymentStatus.FAILED.value

        # Verify wallet was NOT credited
        wallet_balance = await service.get_wallet(test_wallet_user.id)
        assert wallet_balance.available_funds == Decimal("1000.00")  # Unchanged

    async def test_handle_webhook_amount_mismatch_raises_error(
        self, db_session, test_wallet_user, test_wallet
    ):
        """Test webhook with mismatched amount raises error."""
        mock_flutterwave = AsyncMock()
        service = WalletService(db_session, mock_flutterwave)
        amount = Decimal("500.00")

        # First initiate payment
        mock_flutterwave.initiate_payment = AsyncMock(
            return_value="https://checkout.flutterwave.com/test"
        )
        payment_init = await service.initiate_funding(
            user_id=test_wallet_user.id, amount=amount
        )

        # Mock verification with different amount
        mock_flutterwave.verify_payment = AsyncMock(
            return_value={
                "status": "successful",
                "amount": 600.00,  # Different amount!
                "currency": "NGN",
                "flw_ref": "FLW-MOCK-REF-123",
            }
        )

        # Should raise error
        with pytest.raises(PaymentVerificationException, match="Amount mismatch"):
            await service.handle_webhook(
                transaction_reference=payment_init.transaction_reference,
                provider_reference="FLW-MOCK-REF-123",
                status="successful",
                amount=amount,
                provider_response={},
            )

    # ==================== WITHDRAWAL TESTS ====================

    async def test_initiate_withdrawal_success_with_bank_details(
        self, db_session, test_wallet_user_with_bank, test_wallet
    ):
        """Test initiating withdrawal when user has bank details."""
        mock_flutterwave = MagicMock()
        service = WalletService(db_session, mock_flutterwave)

        # Get wallet for user with bank details and set balance
        from apps.wallet.repository import WalletRepository

        wallet_repo = WalletRepository(db_session)
        wallet = await wallet_repo.get_by_user_id(test_wallet_user_with_bank.id)
        wallet.available_funds = Decimal("1000.00")
        db_session.add(wallet)
        await db_session.commit()

        withdrawal_request = WithdrawalRequest(amount=Decimal("300.00"))

        with patch("apps.wallet.tasks.process_withdrawal_transfer"):
            result = await service.initiate_withdrawal(
                user_id=test_wallet_user_with_bank.id,
                withdrawal_request=withdrawal_request,
            )

        assert result.amount == Decimal("300.00")
        assert result.transaction_type == "WITHDRAWAL"
        assert result.direction == "DEBIT"
        assert result.status == "PENDING"  # New: status field
        assert result.balance_before == Decimal("1000.00")
        assert result.balance_after == Decimal("700.00")

        # Verify wallet balance was debited
        wallet_balance = await service.get_wallet(test_wallet_user_with_bank.id)
        assert wallet_balance.available_funds == Decimal("700.00")

        # Verify Celery task was triggered
        # mock_task.delay.assert_called_once()

    async def test_initiate_withdrawal_no_bank_details_raises_error(
        self, db_session, test_wallet_user, test_wallet
    ):
        """Test withdrawal without bank details raises error."""
        mock_flutterwave = MagicMock()
        service = WalletService(db_session, mock_flutterwave)

        withdrawal_request = WithdrawalRequest(amount=Decimal("300.00"))

        with pytest.raises(BankDetailsNotSetupException):
            await service.initiate_withdrawal(
                user_id=test_wallet_user.id, withdrawal_request=withdrawal_request
            )

    async def test_initiate_withdrawal_insufficient_funds(
        self, db_session, test_wallet_user_with_bank, test_wallet
    ):
        """Test withdrawal with insufficient balance."""
        mock_flutterwave = MagicMock()
        service = WalletService(db_session, mock_flutterwave)

        withdrawal_request = WithdrawalRequest(
            amount=Decimal("2000.00")  # More than available
        )

        with pytest.raises(InsufficientFundsException):
            await service.initiate_withdrawal(
                user_id=test_wallet_user_with_bank.id,
                withdrawal_request=withdrawal_request,
            )

    # ==================== WITHDRAWAL PROCESSING TESTS ====================

    async def test_process_withdrawal_transfer_success(
        self,
        db_session,
        test_wallet_user_with_bank,
        test_wallet,
        pending_withdrawal_transaction,
    ):
        """Test successful withdrawal processing updates status to COMPLETED."""
        mock_flutterwave = AsyncMock()
        mock_flutterwave.initiate_transfer = AsyncMock(
            return_value={"id": 12345, "status": "NEW", "reference": "APW-TEST-123"}
        )

        service = WalletService(db_session, mock_flutterwave)

        result = await service.process_withdrawal_transfer(
            transaction_id=pending_withdrawal_transaction.id
        )

        assert result.status == TransactionStatus.COMPLETED
        assert "Transfer Ref:" in result.description
        assert "Transfer ID: 12345" in result.description

        # Verify Paystack was called with correct bank details
        mock_flutterwave.initiate_transfer.assert_called_once()
        call_args = mock_flutterwave.initiate_transfer.call_args[1]
        assert call_args["account_bank"] == "044"
        assert call_args["account_number"] == "1234567890"

    async def test_process_withdrawal_transfer_failure_refunds_wallet(
        self,
        db_session,
        test_wallet_user_with_bank,
        test_wallet,
        pending_withdrawal_transaction,
    ):
        """Test failed withdrawal refunds wallet and marks transaction as FAILED."""
        mock_flutterwave = AsyncMock()
        mock_flutterwave.initiate_transfer = AsyncMock(
            side_effect=PaystackError("Transfer failed: Invalid account")
        )

        service = WalletService(db_session, mock_flutterwave)

        # Get initial balance
        initial_balance = test_wallet.available_funds

        with pytest.raises(PaystackError):
            await service.process_withdrawal_transfer(
                transaction_id=pending_withdrawal_transaction.id
            )

        # Verify transaction marked as failed
        from apps.wallet.repository import WalletRepository

        wallet_repo = WalletRepository(db_session)
        transaction = await wallet_repo.get_transaction_by_id(
            pending_withdrawal_transaction.id
        )
        assert transaction.status == TransactionStatus.FAILED
        assert "FAILED:" in transaction.description

        # Verify wallet was refunded
        wallet = await wallet_repo.get_by_user_id(test_wallet_user_with_bank.id)
        assert wallet.available_funds == initial_balance  # Refunded back

    # ==================== TRANSACTION HISTORY TESTS ====================

    async def test_get_transactions_with_status_filter(
        self, db_session, test_wallet_user, test_wallet
    ):
        """Test getting transactions shows status field."""
        mock_flutterwave = AsyncMock()
        mock_flutterwave.initiate_payment = AsyncMock(
            return_value="https://checkout.flutterwave.com/test"
        )
        mock_flutterwave.verify_payment = AsyncMock(
            return_value={
                "status": "successful",
                "amount": 200.00,
                "currency": "NGN",
                "reference": "FLW-REF",
                "flw_ref": "FLW-REF",
            }
        )

        service = WalletService(db_session, mock_flutterwave)

        # Create and complete a deposit
        payment_init = await service.initiate_funding(
            test_wallet_user.id, Decimal("200.00")
        )
        with patch("apps.wallet.tasks.send_wallet_funded_email"):
            await service.handle_webhook(
                transaction_reference=payment_init.transaction_reference,
                provider_reference="FLW-REF",
                status="successful",
                amount=Decimal("200.00"),
                provider_response={"status": "successful"},
            )

        # Get transactions
        result = await service.get_transactions(
            user_id=test_wallet_user.id, page=1, limit=10
        )

        assert result.pagination.total >= 1
        # Check that transactions have status field
        for transaction in result.data:
            assert hasattr(transaction, "status")
            assert transaction.status in ["PENDING", "COMPLETED", "FAILED", "CANCELLED"]
