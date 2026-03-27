"""Tests for WalletRepository."""

from decimal import Decimal

import pytest

from apps.wallet.repository import PaymentRepository, WalletRepository
from common.exceptions import WalletLockException


@pytest.mark.asyncio
class TestWalletRepository:
    """Test suite for WalletRepository."""

    async def test_get_by_user_id_returns_wallet(self, db_session, test_wallet_user):
        """Test get_by_user_id returns user's wallet."""
        repo = WalletRepository(db_session)

        wallet = await repo.get_by_user_id(test_wallet_user.id)

        assert wallet is not None
        assert wallet.user_id == test_wallet_user.id
        assert wallet.currency == "NGN"

    async def test_get_by_user_id_with_lock_locks_row(
        self, db_session, test_wallet_user
    ):
        """Test get_by_user_id_with_lock uses SELECT FOR UPDATE."""
        repo = WalletRepository(db_session)

        wallet = await repo.get_by_user_id_with_lock(test_wallet_user.id)

        assert wallet is not None
        assert wallet.user_id == test_wallet_user.id

    async def test_update_balances_increases_available(self, db_session, test_wallet):
        """Test update_balances increases available funds."""
        repo = WalletRepository(db_session)
        initial_balance = test_wallet.available_funds

        updated_wallet = await repo.update_balances(
            test_wallet.id,
            available_delta=Decimal("500.00"),
            locked_delta=Decimal("0"),
            escrow_delta=Decimal("0"),
        )
        await db_session.commit()

        assert updated_wallet.available_funds == initial_balance + Decimal("500.00")

    async def test_update_balances_decreases_available(self, db_session, test_wallet):
        """Test update_balances decreases available funds."""
        repo = WalletRepository(db_session)
        initial_balance = test_wallet.available_funds

        updated_wallet = await repo.update_balances(
            test_wallet.id,
            available_delta=Decimal("-200.00"),
            locked_delta=Decimal("0"),
            escrow_delta=Decimal("0"),
        )
        await db_session.commit()

        assert updated_wallet.available_funds == initial_balance - Decimal("200.00")

    async def test_update_balances_raises_on_negative_balance(
        self, db_session, test_wallet
    ):
        """Test update_balances raises error if balance would go negative."""
        repo = WalletRepository(db_session)

        with pytest.raises(WalletLockException) as exc_info:
            await repo.update_balances(
                test_wallet.id,
                available_delta=Decimal("-2000.00"),  # More than available
                locked_delta=Decimal("0"),
                escrow_delta=Decimal("0"),
            )

        assert "insufficient" in str(exc_info.value).lower()

    async def test_update_balances_moves_to_locked(self, db_session, test_wallet):
        """Test moving funds from available to locked."""
        repo = WalletRepository(db_session)

        updated_wallet = await repo.update_balances(
            test_wallet.id,
            available_delta=Decimal("-100.00"),
            locked_delta=Decimal("100.00"),
            escrow_delta=Decimal("0"),
        )
        await db_session.commit()

        assert updated_wallet.available_funds == Decimal("900.00")
        assert updated_wallet.locked_funds == Decimal("100.00")

    async def test_create_transaction_creates_record(self, db_session, test_wallet):
        """Test create_transaction creates transaction record."""
        repo = WalletRepository(db_session)

        transaction = await repo.create_transaction(
            test_wallet.id,
            {
                "amount": Decimal("100.00"),
                "balance_before": Decimal("1000.00"),
                "balance_after": Decimal("1100.00"),
                "description": "Test deposit",
                "transaction_type": "DEPOSIT",
                "direction": "CREDIT",
                "balance_type": "AVAILABLE",
            },
        )
        await db_session.commit()

        assert transaction is not None
        assert transaction.wallet_id == test_wallet.id
        assert transaction.amount == Decimal("100.00")
        assert transaction.transaction_type == "DEPOSIT"

    async def test_get_transactions_returns_paginated(self, db_session, test_wallet):
        """Test get_transactions returns paginated results."""
        repo = WalletRepository(db_session)

        # Create multiple transactions
        for i in range(5):
            await repo.create_transaction(
                test_wallet.id,
                {
                    "amount": Decimal("10.00"),
                    "balance_before": Decimal("1000.00"),
                    "balance_after": Decimal("1010.00"),
                    "description": f"Transaction {i}",
                    "transaction_type": "DEPOSIT",
                    "direction": "CREDIT",
                    "balance_type": "AVAILABLE",
                },
            )
        await db_session.commit()

        result = await repo.get_transactions(
            test_wallet.id, filters={}, page=1, limit=3
        )

        assert result.pagination.total >= 5
        assert len(result.data) == 3

    async def test_get_transactions_filters_by_type(self, db_session, test_wallet):
        """Test get_transactions filters by transaction type."""
        repo = WalletRepository(db_session)

        # Create different transaction types
        await repo.create_transaction(
            test_wallet.id,
            {
                "amount": Decimal("100.00"),
                "balance_before": Decimal("1000.00"),
                "balance_after": Decimal("1100.00"),
                "description": "Deposit",
                "transaction_type": "DEPOSIT",
                "direction": "CREDIT",
                "balance_type": "AVAILABLE",
            },
        )
        await repo.create_transaction(
            test_wallet.id,
            {
                "amount": Decimal("50.00"),
                "balance_before": Decimal("1100.00"),
                "balance_after": Decimal("1050.00"),
                "description": "Withdrawal",
                "transaction_type": "WITHDRAWAL",
                "direction": "DEBIT",
                "balance_type": "AVAILABLE",
            },
        )
        await db_session.commit()

        result = await repo.get_transactions(
            test_wallet.id, filters={"transaction_type": "DEPOSIT"}, page=1, limit=10
        )

        assert all(tx.transaction_type == "DEPOSIT" for tx in result.data)


@pytest.mark.asyncio
class TestPaymentRepository:
    """Test suite for PaymentRepository."""

    async def test_create_payment_creates_record(self, db_session, test_wallet):
        """Test create_payment creates payment record."""
        repo = PaymentRepository(db_session)

        payment = await repo.create_payment(
            {
                "transaction_reference": "APF-TEST-123",
                "wallet_id": test_wallet.id,
                "amount": Decimal("1000.00"),
                "currency": "NGN",
                "provider": "FLUTTERWAVE",
                "status": "PENDING",
            }
        )
        await db_session.commit()

        assert payment is not None
        assert payment.transaction_reference == "APF-TEST-123"
        assert payment.status == "PENDING"

    async def test_get_payment_by_reference_returns_payment(
        self, db_session, test_wallet
    ):
        """Test get_payment_by_reference finds payment."""
        repo = PaymentRepository(db_session)

        created = await repo.create_payment(
            {
                "transaction_reference": "APF-TEST-456",
                "wallet_id": test_wallet.id,
                "amount": Decimal("500.00"),
                "currency": "NGN",
                "provider": "FLUTTERWAVE",
                "status": "PENDING",
            }
        )
        await db_session.commit()

        found = await repo.get_payment_by_reference("APF-TEST-456")

        assert found is not None
        assert found.id == created.id

    async def test_update_payment_status_updates_fields(self, db_session, test_wallet):
        """Test update_payment_status updates payment fields."""
        from datetime import datetime, timezone

        repo = PaymentRepository(db_session)

        payment = await repo.create_payment(
            {
                "transaction_reference": "APF-TEST-789",
                "wallet_id": test_wallet.id,
                "amount": Decimal("750.00"),
                "currency": "NGN",
                "provider": "FLUTTERWAVE",
                "status": "PENDING",
            }
        )
        await db_session.commit()

        now = datetime.now(timezone.utc)
        updated = await repo.update_payment_status(
            payment.id,
            status="COMPLETED",
            provider_reference="FLW-REF-123",
            verified_at=now,
        )
        await db_session.commit()

        assert updated.status == "COMPLETED"
        assert updated.provider_reference == "FLW-REF-123"
        assert updated.verified_at is not None
