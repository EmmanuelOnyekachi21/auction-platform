"""Tests for ``UserRepository`` data access methods."""

from uuid import uuid4

from sqlalchemy import select

from apps.users.enums import AccountStatus, UserRole
from apps.users.models import UserProfile
from apps.users.repository import UserRepository
from apps.wallet.models import Wallet


def make_user_data(**overrides) -> dict:
    """Build a valid user data dictionary with sensible defaults.

    Generates a unique email on each call so tests do not collide on the
    unique constraint.

    Args:
        **overrides: Any field values that should replace the defaults.

    Returns:
        A dictionary suitable for passing to ``UserRepository.create``.

    """
    return {
        "first_name": "John",
        "last_name": "Doe",
        "email": f"john_{uuid4().hex[:6]}@example.com",
        "phone_number": "09075897427",
        "password_hash": "hashed_password_placeholder",
        "account_status": AccountStatus.ACTIVE,
        "role": UserRole.USER,
        "is_email_verified": False,
        **overrides,
    }


async def test_create_user_creates_profile_and_wallets(db_session):
    """Creating a user should also create a linked profile and wallet."""
    repo = UserRepository(db_session)
    user = await repo.create(make_user_data())

    assert user.id is not None
    assert user.first_name == "John"
    assert user.account_status == AccountStatus.ACTIVE

    profile = await db_session.scalar(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    assert profile is not None

    wallet = await db_session.scalar(select(Wallet).where(Wallet.user_id == user.id))
    assert wallet is not None
    assert wallet.available_funds == 0
    assert wallet.currency == "NGN"


async def test_get_by_id_returns_user(db_session):
    """get_by_id should return the user matching the given UUID."""
    repo = UserRepository(db_session)
    created = await repo.create(make_user_data())

    found = await repo.get_by_id(created.id)
    assert found is not None
    assert found.id == created.id


async def test_get_by_id_returns_none_for_missing(db_session):
    """get_by_id should return None when no user exists for the UUID."""
    repo = UserRepository(db_session)
    result = await repo.get_by_id(uuid4())
    assert result is None


async def test_get_by_email_returns_user(db_session):
    """get_by_email should return the user with the matching email."""
    repo = UserRepository(db_session)
    await repo.create(make_user_data(email="test@example.com"))

    found = await repo.get_by_email("test@example.com")
    assert found is not None
    assert found.email == "test@example.com"


async def test_get_by_email_is_case_insensitive(db_session):
    """get_by_email should match regardless of email casing."""
    repo = UserRepository(db_session)
    await repo.create(make_user_data(email="Test@Example.com"))

    found = await repo.get_by_email("test@example.com")
    assert found is not None


async def test_get_by_email_returns_none_for_missing(db_session):
    """get_by_email should return None when no user has the given email."""
    repo = UserRepository(db_session)
    result = await repo.get_by_email("nobody@example.com")
    assert result is None


async def test_update_last_login(db_session):
    """update_last_login should stamp last_login_at with the current time."""
    repo = UserRepository(db_session)
    user = await repo.create(make_user_data())
    assert user.last_login_at is None

    await repo.update_last_login(user.id)
    updated = await repo.get_by_id(user.id)
    assert updated.last_login_at is not None
