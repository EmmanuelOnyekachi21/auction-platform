"""FastAPI dependency functions for database sessions and authentication.

Provides reusable ``Depends``-compatible callables that handle:

- Database session lifecycle (``get_db``).
- JWT decoding and user resolution (``get_current_user``).
- Email-verification gate (``get_current_active_user``).
- Role-based access guards (``require_admin``, ``require_verified_seller``).
"""

import logging
from typing import AsyncGenerator

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.enums import AccountStatus, UserRole
from apps.users.models import User
from common.exceptions import (
    AccountBannedException,
    AccountSuspendedException,
    AdminRequiredException,
    EmailNotVerifiedException,
    SellerRequiredException,
    TokenExpiredException,
    TokenInvalidException,
    UserNotFoundException,
)
from config.database import AsyncSessionLocal
from config.settings import settings

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for the duration of a request.

    Opens a new ``AsyncSession`` from the session factory, yields it to
    the route handler, and ensures it is closed when the request completes
    regardless of whether an exception was raised.

    Yields:
        An active ``AsyncSession`` bound to the application's async engine.

    """
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    """Decode the bearer token and return the authenticated ``User``.

    Validates the JWT signature and expiry, extracts the ``sub`` claim as
    the user ID, fetches the corresponding ``User`` row, and checks that
    the account is neither suspended nor banned.

    Args:
        db: Injected async database session from ``get_db``.
        token: Raw JWT string extracted from the ``Authorization`` header
            by the ``OAuth2PasswordBearer`` scheme.

    Returns:
        The authenticated and active ``User`` ORM instance.

    Raises:
        TokenExpiredException: If the token's expiry time has passed.
        TokenInvalidException: If the token cannot be decoded, the
            signature is invalid, or the ``sub`` claim is missing.
        UserNotFoundException: If no user exists for the ID in the token.
        AccountSuspendedException: If the user's account is suspended.
        AccountBannedException: If the user's account is banned.

    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except ExpiredSignatureError:
        raise TokenExpiredException()
    except JWTError:
        raise TokenInvalidException()

    user_id = payload.get("sub")
    if not user_id:
        raise TokenInvalidException()

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise UserNotFoundException()

    if user.account_status == AccountStatus.SUSPENDED:
        raise AccountSuspendedException()

    if user.account_status == AccountStatus.BANNED:
        raise AccountBannedException()

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure the authenticated user has verified their email address.

    Args:
        current_user: Injected ``User`` instance from ``get_current_user``.

    Returns:
        The same ``User`` instance if their email is verified.

    Raises:
        EmailNotVerifiedException: If the user's email has not been
            confirmed.

    """
    if current_user.is_email_verified:
        return current_user
    raise EmailNotVerifiedException()


async def require_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Restrict access to users with an admin or superuser role.

    Args:
        current_user: Injected ``User`` instance from
            ``get_current_active_user``.

    Returns:
        The same ``User`` instance if they hold an admin role.

    Raises:
        AdminRequiredException: If the user's role is neither ``ADMIN``
            nor ``SUPERUSER``.

    """
    if current_user.role in (UserRole.ADMIN, UserRole.SUPERUSER):
        return current_user
    raise AdminRequiredException()


async def require_verified_seller(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Restrict access to users with a verified seller profile.

    Args:
        current_user: Injected ``User`` instance from
            ``get_current_active_user``.

    Returns:
        The same ``User`` instance if they have a verified seller profile.

    Raises:
        SellerRequiredException: If the user has no seller profile or
            their seller profile has not been verified.

    """
    if current_user.seller_profile and current_user.seller_profile.is_verified:
        return current_user
    raise SellerRequiredException()
