"""Fixtures for wallet tests."""

from decimal import Decimal

import pytest_asyncio

from apps.users.models import UserRole
from apps.users.repository import UserRepository
from apps.wallet.enums import (
    BalanceType,
    TransactionDirection,
    TransactionStatus,
    TransactionType,
)
from apps.wallet.repository import WalletRepository


@pytest_asyncio.fixture
async def test_wallet_user(db_session):
    """Create a test user with wallet (no bank details)."""
    repo = UserRepository(db_session)
    user = await repo.create(
        {
            "email": "walletuser@example.com",
            "password_hash": "hashed_password",
            "phone_number": "+2348012345680",
            "first_name": "Wallet",
            "last_name": "User",
            "role": UserRole.USER,
            "is_email_verified": True,
        }
    )
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def test_wallet_user_with_bank(db_session):
    """Create a test user with wallet and bank details set up."""
    from sqlalchemy import select

    from apps.users.models import UserProfile

    repo = UserRepository(db_session)
    user = await repo.create(
        {
            "email": "walletuser_bank@example.com",
            "password_hash": "hashed_password",
            "phone_number": "+2348012345681",
            "first_name": "Wallet",
            "last_name": "UserBank",
            "role": UserRole.USER,
            "is_email_verified": True,
        }
    )
    await db_session.commit()

    # Eagerly load profile to avoid lazy loading issues
    stmt = select(UserProfile).where(UserProfile.user_id == user.id)
    result = await db_session.execute(stmt)
    profile = result.scalar_one_or_none()

    # Add bank details to profile
    if profile:
        profile.bank_code = "044"  # Access Bank
        profile.account_number = "1234567890"
        profile.account_name = "Wallet UserBank"
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def test_wallet(db_session, test_wallet_user):
    """Get the wallet for test user with initial balance."""
    wallet_repo = WalletRepository(db_session)
    wallet = await wallet_repo.get_by_user_id(test_wallet_user.id)

    # Fund wallet with initial balance
    wallet.available_funds = Decimal("1000.00")
    db_session.add(wallet)
    await db_session.commit()

    return wallet


@pytest_asyncio.fixture
async def pending_withdrawal_transaction(db_session, test_wallet_user_with_bank):
    """Create a pending withdrawal transaction."""
    from sqlalchemy import select

    from apps.wallet.models import Wallet, WalletTransactions

    # Get wallet
    stmt = select(Wallet).where(Wallet.user_id == test_wallet_user_with_bank.id)
    result = await db_session.execute(stmt)
    wallet = result.scalar_one()

    # Set initial balance
    wallet.available_funds = Decimal("1000.00")
    db_session.add(wallet)

    # Create pending withdrawal transaction
    transaction = WalletTransactions(
        wallet_id=wallet.id,
        amount=Decimal("300.00"),
        balance_before=Decimal("1000.00"),
        balance_after=Decimal("700.00"),
        description="Withdrawal to 044 - 1234567890",
        transaction_type=TransactionType.WITHDRAWAL,
        direction=TransactionDirection.DEBIT,
        balance_type=BalanceType.AVAILABLE,
        status=TransactionStatus.PENDING,
    )
    db_session.add(transaction)

    # Debit wallet
    wallet.available_funds = Decimal("700.00")
    db_session.add(wallet)

    await db_session.commit()
    await db_session.refresh(transaction)

    return transaction
