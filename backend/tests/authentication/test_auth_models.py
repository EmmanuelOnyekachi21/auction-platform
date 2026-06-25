"""Tests for authentication ORM models.

Verifies that ``EmailVerificationToken`` and ``PasswordResetToken`` are
correctly created, that their ``updated_at`` field remains ``None``
(immutable records), and that their SQLAlchemy ``user`` relationships
resolve to the expected ``User`` instance."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from apps.authentication.models import EmailVerificationToken, PasswordResetToken
from apps.users.enums import AccountStatus, UserRole
from apps.users.models import User


def make_users(**overrides) -> User:
    """Build an unsaved ``User`` ORM instance with sensible defaults.

    Args:
        **overrides: Column values that should replace the defaults.

    Returns:
        An un-persisted ``User`` object ready to be added to a session.

    """
    return User(
        first_name="Jane",
        last_name="Doe",
        email=f"jane_{uuid4().hex[:6]}@example.com",
        phone_number=f"0801{uuid4().int % 10**7:07d}",
        password_hash="hashed",
        account_status=AccountStatus.ACTIVE,
        role=UserRole.USER,
        is_email_verified=False,
        **overrides,
    )


def future(minutes: int = 30) -> datetime:
    """Return a timezone-aware UTC datetime ``minutes`` in the future.

    Args:
        minutes: Number of minutes from now. Defaults to 30.

    Returns:
        A timezone-aware UTC ``datetime``.

    """
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


async def test_email_verification_token_updated_at_is_none(db_session):
    user = make_users()
    db_session.add(user)

    await db_session.flush()

    token = EmailVerificationToken(
        user_id=user.id,
        token="hashed_token_xyz",
        expires_at=future(),
    )
    db_session.add(token)
    await db_session.flush()

    # updated_at column shouldn't exist as I set it to None
    assert not hasattr(token, "updated_at") or token.updated_at is None


async def test_password_reset_token_created(db_session):
    user = make_users()
    db_session.add(user)
    await db_session.flush()

    token = PasswordResetToken(
        user_id=user.id,
        token="hashed_reset_token",
        expires_at=future(minutes=60),
    )
    db_session.add(token)
    await db_session.flush()

    assert token.id is not None
    assert token.user_id == user.id
    assert token.used_at is None


async def test_email_token_user_relationship(db_session):
    user = make_users()
    db_session.add(user)
    await db_session.flush()

    token = EmailVerificationToken(
        user_id=user.id,
        token="hashed_rel_token",
        expires_at=future(),
    )
    db_session.add(token)
    await db_session.flush()
    await db_session.refresh(token)

    assert token.user is not None
    assert token.user.id == user.id


async def test_password_reset_token_updated_at_is_none(db_session):
    user = make_users()
    db_session.add(user)
    await db_session.flush()

    token = PasswordResetToken(
        user_id=user.id,
        token="hashed_reset_immutable",
        expires_at=future(minutes=60),
    )
    db_session.add(token)
    await db_session.flush()

    assert not hasattr(token, "updated_at") or token.updated_at is None


async def test_password_reset_token_user_relationship(db_session):
    user = make_users()
    db_session.add(user)
    await db_session.flush()

    token = PasswordResetToken(
        user_id=user.id,
        token="hashed_reset_rel",
        expires_at=future(minutes=60),
    )
    db_session.add(token)
    await db_session.flush()
    await db_session.refresh(token)

    assert token.user is not None
    assert token.user.id == user.id
