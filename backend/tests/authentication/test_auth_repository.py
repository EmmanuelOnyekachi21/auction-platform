"""Integration tests for ``AuthRepository`` token operations.

Verifies that email verification and password reset tokens can be
created, retrieved when valid, rejected when expired or used, marked
as used, and deleted.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from apps.authentication.repository import AuthRepository
from apps.users.enums import AccountStatus, UserRole
from apps.users.repository import UserRepository


def make_user_data(**overrides) -> dict:
    """Generate a dictionary of user data for testing.

    Args:
        **overrides: Optional column overrides for the user.

    Returns:
        dict: A user data dictionary.

    """
    return {
        "first_name": "John",
        "last_name": "Doe",
        "email": f"john_{uuid4().hex[:6]}@example.com",
        "phone_number": f"0801{uuid4().int % 10**7:07d}",
        "password_hash": "hashed_password_placeholder",
        "account_status": AccountStatus.ACTIVE,
        "role": UserRole.USER,
        "is_email_verified": False,
        **overrides,
    }


def future(minutes: int = 30) -> datetime:
    """Return a UTC timestamp in the future.

    Args:
        minutes: Minutes from now. Defaults to 30.

    Returns:
        datetime: A timezone-aware future timestamp.

    """
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def past(minutes: int = 30) -> datetime:
    """Return a UTC timestamp in the past.

    Args:
        minutes: Minutes ago. Defaults to 30.

    Returns:
        datetime: A timezone-aware past timestamp.

    """
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)


# ---------------------------------------------------------------------------
# Email verification token tests
# ---------------------------------------------------------------------------


async def test_create_email_verification_token(db_session):
    user = await UserRepository(db_session).create(make_user_data())
    repo = AuthRepository(db_session)

    token = await repo.create_email_verification_token(
        user_id=user.id,
        token_hash="hashed_email_token_abc",
        expires_at=future(),
    )

    assert token.id is not None
    assert token.user_id == user.id
    assert token.used_at is None
    assert token.updated_at is None  # immutable record


async def test_get_valid_email_token_returns_token(db_session):
    user = await UserRepository(db_session).create(make_user_data())
    repo = AuthRepository(db_session)

    await repo.create_email_verification_token(
        user_id=user.id,
        token_hash="valid_email_token",
        expires_at=future(),
    )

    found = await repo.get_valid_email_token("valid_email_token")
    assert found is not None
    assert found.user_id == user.id


async def test_get_valid_email_token_returns_none_if_expired(db_session):
    user = await UserRepository(db_session).create(make_user_data())
    repo = AuthRepository(db_session)

    await repo.create_email_verification_token(
        user_id=user.id,
        token_hash="expired_email_token",
        expires_at=past(),  # already expired
    )

    found = await repo.get_valid_email_token("expired_email_token")
    assert found is None


async def test_get_valid_email_token_returns_none_if_used(db_session):
    user = await UserRepository(db_session).create(make_user_data())
    repo = AuthRepository(db_session)

    token = await repo.create_email_verification_token(
        user_id=user.id,
        token_hash="used_email_token",
        expires_at=future(),
    )
    await repo.mark_email_token_used(token.id)

    found = await repo.get_valid_email_token("used_email_token")
    assert found is None


async def test_mark_email_token_used(db_session):
    user = await UserRepository(db_session).create(make_user_data())
    repo = AuthRepository(db_session)

    token = await repo.create_email_verification_token(
        user_id=user.id,
        token_hash="mark_used_email_token",
        expires_at=future(),
    )
    assert token.used_at is None

    await repo.mark_email_token_used(token.id)
    assert token.used_at is not None


async def test_delete_email_verification_token(db_session):
    user = await UserRepository(db_session).create(make_user_data())
    repo = AuthRepository(db_session)

    token = await repo.create_email_verification_token(
        user_id=user.id,
        token_hash="delete_email_token",
        expires_at=future(),
    )
    token_id = token.id

    await repo.delete_email_verification_token(token_id)

    # Should no longer be findable
    found = await repo.get_valid_email_token("delete_email_token")
    assert found is None


# ---------------------------------------------------------------------------
# Password reset token tests
# ---------------------------------------------------------------------------


async def test_create_password_reset_token(db_session):
    user = await UserRepository(db_session).create(make_user_data())
    repo = AuthRepository(db_session)

    token = await repo.create_password_reset_token(
        user_id=user.id,
        token_hash="hashed_reset_token_abc",
        expires_at=future(minutes=60),
    )

    assert token.id is not None
    assert token.user_id == user.id
    assert token.used_at is None
    assert token.updated_at is None  # immutable record


async def test_get_valid_password_reset_token_returns_token(db_session):
    user = await UserRepository(db_session).create(make_user_data())
    repo = AuthRepository(db_session)

    await repo.create_password_reset_token(
        user_id=user.id,
        token_hash="valid_reset_token",
        expires_at=future(minutes=60),
    )

    found = await repo.get_valid_password_reset_token("valid_reset_token")
    assert found is not None
    assert found.user_id == user.id


async def test_get_valid_password_reset_token_returns_none_if_expired(db_session):
    user = await UserRepository(db_session).create(make_user_data())
    repo = AuthRepository(db_session)

    await repo.create_password_reset_token(
        user_id=user.id,
        token_hash="expired_reset_token",
        expires_at=past(),
    )

    found = await repo.get_valid_password_reset_token("expired_reset_token")
    assert found is None


async def test_get_valid_password_reset_token_returns_none_if_used(db_session):
    user = await UserRepository(db_session).create(make_user_data())
    repo = AuthRepository(db_session)

    token = await repo.create_password_reset_token(
        user_id=user.id,
        token_hash="used_reset_token",
        expires_at=future(minutes=60),
    )
    await repo.mark_password_reset_token_used(token.id)

    found = await repo.get_valid_password_reset_token("used_reset_token")
    assert found is None


async def test_mark_password_reset_token_used(db_session):
    user = await UserRepository(db_session).create(make_user_data())
    repo = AuthRepository(db_session)

    token = await repo.create_password_reset_token(
        user_id=user.id,
        token_hash="mark_used_reset_token",
        expires_at=future(minutes=60),
    )
    assert token.used_at is None

    await repo.mark_password_reset_token_used(token.id)
    assert token.used_at is not None


async def test_delete_password_reset_token(db_session):
    user = await UserRepository(db_session).create(make_user_data())
    repo = AuthRepository(db_session)

    token = await repo.create_password_reset_token(
        user_id=user.id,
        token_hash="delete_reset_token",
        expires_at=future(minutes=60),
    )

    await repo.delete_password_reset_token(token.id)

    found = await repo.get_valid_password_reset_token("delete_reset_token")
    assert found is None
