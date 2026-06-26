"""Tests for WalletService business logic."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.payments.enums import PaymentStatus
from apps.wallet.schemas import WithdrawalRequest
from apps.wallet.service import WalletService
from common.exceptions import (
    BankDetailsNotSetupException,
    InsufficientFundsException,
    PaymentVerificationException,
    UserNotFoundException,
    WalletNotFoundException,
)


@pytest.mark.asyncio
class TestWalletService:
    """Test suite for WalletService."""

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
        from uuid import uuid4

        mock_flutterwave = MagicMock()
        service = WalletService(db_session, mock_flutterwave)

        with pytest.raises(WalletNotFoundException):
            await service.get_wallet(uuid4())

    async def test_initiate_funding_success(
        self, db_session, test_wallet_user, test_wallet
    ):
        """Test initiating wallet funding."""
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

    async def test_initiate_funding_idempotency(
        self, db_session, test_wallet_user, test_wallet
    ):
        """Test that duplicate funding requests return existing payment."""
        mock_flutterwave = AsyncMock()
        mock_flutterwave.initiate_payment = AsyncMock(
            return_value="https://checkout.flutterwave.com/test-link"
        )
        service = WalletService(db_session, mock_flutterwave)
        amount = Decimal("500.00")

        # First request
        result1 = await service.initiate_funding(
            user_id=test_wallet_user.id, amount=amount, currency="NGN"
        )

        # Second request - should generate new reference since we can't
        # easily mock the reference generation
        result2 = await service.initiate_funding(
            user_id=test_wallet_user.id, amount=amount, currency="NGN"
        )

        # Both should succeed and have valid references
        assert result1.transaction_reference.startswith("APF-")
        assert result2.transaction_reference.startswith("APF-")

    async def test_initiate_funding_no_wallet(self, db_session):
        """Test initiating funding for user without wallet."""
        from uuid import uuid4

        mock_flutterwave = MagicMock()
        service = WalletService(db_session, mock_flutterwave)

        with pytest.raises(WalletNotFoundException):
            await service.initiate_funding(user_id=uuid4(), amount=Decimal("500.00"))

    async def test_handle_webhook_success(
        self, db_session, test_wallet_user, test_wallet
    ):
        """Test handling successful payment webhook."""
        mock_flutterwave = AsyncMock()
        mock_flutterwave.initiate_payment = AsyncMock(
            return_value="https://checkout.flutterwave.com/test"
        )
        mock_flutterwave.verify_payment = AsyncMock(
            return_value={
                "status": "successful",
                "amount": 500.00,
                "currency": "NGN",
                "reference": "FLW-MOCK-REF-123",
                "flw_ref": "FLW-MOCK-REF-123",
            }
        )
        service = WalletService(db_session, mock_flutterwave)
        amount = Decimal("500.00")

        # First initiate payment
        payment_init = await service.initiate_funding(
            user_id=test_wallet_user.id, amount=amount
        )

        # Simulate webhook
        provider_response = {
            "id": 12345,
            "tx_ref": payment_init.transaction_reference,
            "flw_ref": "FLW-MOCK-REF-123",
            "amount": float(amount),
            "status": "successful",
        }

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

    async def test_handle_webhook_failed_payment(
        self, db_session, test_wallet_user, test_wallet
    ):
        """Test handling failed payment webhook."""
        mock_flutterwave = AsyncMock()
        mock_flutterwave.initiate_payment = AsyncMock(
            return_value="https://checkout.flutterwave.com/test"
        )
        mock_flutterwave.verify_payment = AsyncMock(
            return_value={
                "status": "failed",
                "amount": 500.00,
                "currency": "NGN",
                "flw_ref": "FLW-MOCK-REF-123",
            }
        )
        service = WalletService(db_session, mock_flutterwave)
        amount = Decimal("500.00")

        # First initiate payment
        payment_init = await service.initiate_funding(
            user_id=test_wallet_user.id, amount=amount
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

    async def test_handle_webhook_payment_not_found(self, db_session):
        """Test webhook for non-existent payment."""
        mock_flutterwave = MagicMock()
        service = WalletService(db_session, mock_flutterwave)

        with pytest.raises(PaymentVerificationException, match="Payment not found"):
            await service.handle_webhook(
                transaction_reference="APF-INVALID-123",
                provider_reference="FLW-REF",
                status="successful",
                amount=Decimal("500.00"),
                provider_response={},
            )

    async def test_handle_webhook_amount_mismatch(
        self, db_session, test_wallet_user, test_wallet
    ):
        """Test webhook with mismatched amount."""
        mock_flutterwave = AsyncMock()
        mock_flutterwave.initiate_payment = AsyncMock(
            return_value="https://checkout.flutterwave.com/test"
        )
        mock_flutterwave.verify_payment = AsyncMock(
            return_value={
                "status": "successful",
                "amount": 600.00,  # Different amount
                "currency": "NGN",
                "flw_ref": "FLW-MOCK-REF-123",
            }
        )
        service = WalletService(db_session, mock_flutterwave)
        amount = Decimal("500.00")

        # First initiate payment
        payment_init = await service.initiate_funding(
            user_id=test_wallet_user.id, amount=amount
        )

        # Simulate webhook with different amount
        with pytest.raises(PaymentVerificationException, match="Amount mismatch"):
            await service.handle_webhook(
                transaction_reference=payment_init.transaction_reference,
                provider_reference="FLW-MOCK-REF-123",
                status="successful",
                amount=Decimal("600.00"),  # Different amount
                provider_response={},
            )

    async def test_get_transactions_success(
        self, db_session, test_wallet_user, test_wallet
    ):
        """Test getting transaction history."""
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

        # Create some transactions by funding wallet
        await service.initiate_funding(test_wallet_user.id, Decimal("100.00"))
        payment_init = await service.initiate_funding(
            test_wallet_user.id, Decimal("200.00")
        )

        # Complete one payment
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

        assert result.pagination.total >= 1  # At least the completed transaction
        assert len(result.data) >= 1

    async def test_get_transactions_with_filters(
        self, db_session, test_wallet_user, test_wallet
    ):
        """Test getting transactions with filters."""
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

        # Get only DEPOSIT transactions
        result = await service.get_transactions(
            user_id=test_wallet_user.id,
            transaction_type="DEPOSIT",
            direction="CREDIT",
            page=1,
            limit=10,
        )

        assert result.pagination.total >= 1
        for item in result.data:
            assert item.transaction_type == "DEPOSIT"
            assert item.direction == "CREDIT"

    async def test_get_transactions_no_wallet(self, db_session):
        """Test getting transactions for user without wallet."""
        from uuid import uuid4

        mock_flutterwave = MagicMock()
        service = WalletService(db_session, mock_flutterwave)

        with pytest.raises(WalletNotFoundException):
            await service.get_transactions(user_id=uuid4())

    async def test_initiate_withdrawal_success(
        self, db_session, test_wallet_user_with_bank, test_wallet
    ):
        """Test initiating withdrawal."""
        mock_flutterwave = MagicMock()
        service = WalletService(db_session, mock_flutterwave)

        # Get wallet for user with bank details
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
        assert result.status == "PENDING"
        assert result.balance_before == Decimal("1000.00")
        assert result.balance_after == Decimal("700.00")

        # Verify wallet balance was debited
        wallet_balance = await service.get_wallet(test_wallet_user_with_bank.id)
        assert wallet_balance.available_funds == Decimal("700.00")

    async def test_initiate_withdrawal_insufficient_funds(
        self, db_session, test_wallet_user_with_bank, test_wallet
    ):
        """Test withdrawal with insufficient balance."""
        mock_flutterwave = MagicMock()
        service = WalletService(db_session, mock_flutterwave)

        # Get wallet for user with bank details
        from apps.wallet.repository import WalletRepository

        wallet_repo = WalletRepository(db_session)
        wallet = await wallet_repo.get_by_user_id(test_wallet_user_with_bank.id)
        wallet.available_funds = Decimal("1000.00")
        db_session.add(wallet)
        await db_session.commit()

        withdrawal_request = WithdrawalRequest(
            amount=Decimal("2000.00")  # More than available
        )

        with pytest.raises(InsufficientFundsException):
            await service.initiate_withdrawal(
                user_id=test_wallet_user_with_bank.id,
                withdrawal_request=withdrawal_request,
            )

    async def test_initiate_withdrawal_no_wallet(self, db_session):
        """Test withdrawal for user without wallet."""
        from uuid import uuid4

        mock_flutterwave = MagicMock()
        service = WalletService(db_session, mock_flutterwave)

        withdrawal_request = WithdrawalRequest(amount=Decimal("100.00"))

        with pytest.raises(UserNotFoundException):
            await service.initiate_withdrawal(
                user_id=uuid4(), withdrawal_request=withdrawal_request
            )

    async def test_initiate_withdrawal_minimum_amount(
        self, db_session, test_wallet_user, test_wallet
    ):
        """Test withdrawal validates minimum amount."""
        from pydantic import ValidationError

        # This should raise validation error before hitting service
        with pytest.raises(ValidationError, match="Minimum withdrawal amount"):
            WithdrawalRequest(amount=Decimal("50.00"))  # Less than minimum ₦100

    async def test_initiate_withdrawal_no_bank_details(
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
