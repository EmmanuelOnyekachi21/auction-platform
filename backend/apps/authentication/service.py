"""Authentication service layer.

Provides ``AuthService``, the single entry-point for all authentication
business logic including registration, login, token refresh, email
verification, and password management.

Design notes:
    - All database mutations are flushed but **not committed** here;
      the transaction boundary is owned by the caller (e.g. the FastAPI
      dependency that provides the ``AsyncSession``).
    - Raw tokens are **never** stored; only their SHA-256 hashes are
      persisted via ``AuthRepository``.
    - Celery tasks for sending emails are stubbed with ``TODO`` comments
      and must be wired up before going to production.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.repository import AuthRepository
from apps.authentication.schemas import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    UserTokenResponse,
)
from apps.authentication.security import (
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)
from apps.notifications.tasks import send_password_reset_email, send_verification_email
from apps.users.enums import AccountStatus
from apps.users.models import User
from apps.users.repository import UserRepository
from common.exceptions import (
    AccountBannedException,
    AccountSuspendedException,
    AlreadyExistsException,
    InvalidCredentialsException,
    NotFoundException,
    TokenInvalidException,
)
from common.schemas import MessageResponse

from .jwt_service import create_access_token, create_token_pair, decode_token

logger = logging.getLogger(__name__)


class AuthService:
    """Orchestrates all authentication-related use cases.

    Depends on :class:`~apps.users.repository.UserRepository` and
    :class:`~apps.authentication.repository.AuthRepository` for
    database access, and on the ``jwt_service`` module for JWT
    creation and verification.

    Attributes:
        _db: The active ``AsyncSession`` shared with both repositories.
        _user_repo: Repository for ``User`` CRUD operations.
        _auth_repo: Repository for authentication token operations.

    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialise the service with a shared async database session.

        Args:
            db: An active ``AsyncSession`` used for all database
                operations within this service.

        """
        self._db = db
        self._user_repo = UserRepository(db)
        self._auth_repo = AuthRepository(db)

    async def register(self, data: RegisterRequest) -> AuthResponse:
        """Register a new user account and return an initial token pair.

        Validates that neither the email nor the phone number is already
        taken, hashes the supplied password, creates the user record,
        and queues an email-verification token.

        Args:
            data: Validated registration payload from the request body.

        Returns:
            An ``AuthResponse`` containing the new user's details and a
            freshly issued access / refresh token pair.

        Raises:
            AlreadyExistsException: If the email or phone number is
                already registered.

        """
        # Check email uniqueness
        email_already_exists = await self._user_repo.get_by_email(data.email)
        if email_already_exists:
            raise AlreadyExistsException("Email is already registered")

        # Check phone uniqueness
        phone_number_exist = await self._user_repo.get_by_phone_number(
            data.phone_number
        )
        if phone_number_exist:
            raise AlreadyExistsException("Phone number is already registered")

        # Hash the password and build user data
        user = await self._user_repo.create(
            {
                "first_name": data.first_name,
                "last_name": data.last_name,
                "email": data.email,
                "phone_number": data.phone_number,
                "password_hash": hash_password(data.password),
            }
        )
        logger.info(f"Created user: {user.first_name}")

        # Generate and store email verification token
        raw_token = generate_token()
        await self._auth_repo.create_email_verification_token(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        logger.info(f"Generated token:\nToken: {raw_token}")

        send_verification_email.delay(user.email, user.first_name, raw_token)

        # Explicit commit to save everything
        await self._db.commit()

        token_pair = create_token_pair(
            user_id=str(user.id),
            email=user.email,
            role=user.role.value,
        )

        return AuthResponse(
            user=UserTokenResponse(
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                role=user.role.value,
                is_email_verified=user.is_email_verified,
                account_status=user.account_status.value,
            ),
            access_token=token_pair["access_token"],
            refresh_token=token_pair["refresh_token"],
            token_type=token_pair["token_type"],
        )

    async def login(self, data: LoginRequest) -> AuthResponse:
        """Authenticate a user by email and password.

        Uses a constant-time bcrypt comparison so that bad-password and
        unknown-email errors return the same exception, preventing user
        enumeration.  Updates ``last_login_at`` on success.

        Args:
            data: Validated login payload containing email and password.

        Returns:
            An ``AuthResponse`` with the authenticated user's details
            and a fresh access / refresh token pair.

        Raises:
            InvalidCredentialsException: If the email is unknown or the
                password does not match.
            AccountSuspendedException: If the account is suspended.
            AccountBannedException: If the account is permanently banned.

        """
        user = await self._user_repo.get_by_email(data.email)

        if not user or not verify_password(data.password, user.password_hash):
            raise InvalidCredentialsException()

        if user.account_status == AccountStatus.SUSPENDED:
            raise AccountSuspendedException()

        if user.account_status == AccountStatus.BANNED:
            raise AccountBannedException()

        user.last_login_at = datetime.now(timezone.utc)

        # Explicit commit to save the last_login_time
        await self._db.commit()

        token_pair = create_token_pair(
            user_id=str(user.id),
            email=user.email,
            role=user.role.value,
        )

        return AuthResponse(
            user=UserTokenResponse(
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                role=user.role.value,
                is_email_verified=user.is_email_verified,
                account_status=user.account_status.value,
            ),
            access_token=token_pair["access_token"],
            refresh_token=token_pair["refresh_token"],
            token_type=token_pair["token_type"],
        )

    async def refresh_token(self, refresh_token: str) -> dict:
        """Issue a new access token from a valid refresh token.

        The refresh token itself is **not** rotated; only a new short-lived
        access token is returned.  ``decode_token`` raises
        ``TokenExpiredException`` or ``TokenInvalidException`` automatically
        if the JWT is malformed or expired.

        Args:
            refresh_token: The JWT refresh token string sent by the client.

        Returns:
            A dictionary with ``access_token`` and ``token_type`` keys.

        Raises:
            TokenInvalidException: If the token is not a refresh token, or
                the referenced user no longer exists.
            TokenExpiredException: If the token's ``exp`` claim is in the
                past (raised by ``decode_token``).

        """
        # decode_token raises TokenExpiredException / TokenInvalidException
        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise TokenInvalidException()

        user = await self._user_repo.get_by_id(payload["sub"])
        if not user:
            raise TokenInvalidException()

        # Issue a new access token only — refresh stays the same
        new_access_token = create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
                "role": user.role.value,
            }
        )

        return {
            "access_token": new_access_token,
            "token_type": "bearer",
        }

    async def verify_email(self, token: str) -> MessageResponse:
        """Mark a user's email address as verified.

        Looks up the hashed token in the database, validates that it has
        not expired or been used already, then sets ``is_email_verified``
        on the user and deletes the token record.

        Args:
            token: The raw (un-hashed) verification token from the link
                sent to the user's email address.

        Returns:
            A ``MessageResponse`` confirming successful verification.

        Raises:
            NotFoundException: If the token does not exist, has expired,
                or has already been consumed.

        """
        logger.info(f"Received token: {token}")
        hashed_token = hash_token(token)
        logger.info(f"Token hashed into: {hashed_token}")
        token_record = await self._auth_repo.get_valid_email_token(hashed_token)

        logger.info(f"Received Token record: {token_record}")

        if not token_record:
            raise NotFoundException(
                message="Verification token is invalid or has expired",
                code="TOKEN_INVALID",
            )

        # await self._user_repo.update(
        #     token_record.user_id, {"is_email_verified": True}
        # )
        # await self._auth_repo.delete_email_verification_token(token_record.id)
        # Update user status
        user = await self._user_repo.get_by_id(token_record.user_id)
        user.is_email_verified = True

        # Hash/Inactivate the token
        token_record.used_at = datetime.now(timezone.utc)

        # Explicit commit
        await self._db.commit()

        return MessageResponse(message="Email successfully verified")

    async def forgot_password(self, email: str) -> MessageResponse:
        """Initiate a password-reset flow for the given email address.

        Deliberately returns the same success message regardless of
        whether the email exists in the database, preventing user
        enumeration attacks.

        Args:
            email: The email address submitted by the user.

        Returns:
            A generic ``MessageResponse``; never reveals whether the
            email is registered.

        """
        user = await self._user_repo.get_by_email(email)

        # Silently succeed whether the email exists or not — never reveal
        # whether an address is registered in this system.
        if user:
            raw_token = generate_token()
            logger.info(f"Forgot password token generated: {raw_token}")
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            await self._auth_repo.create_password_reset_token(
                user.id, hash_token(raw_token), expires_at
            )
            send_password_reset_email.delay(user.email, user.first_name, raw_token)
            # Explicit commit to save the password reset token
            await self._db.commit()

        return MessageResponse(
            message="If that email is registered, a reset link has been sent"
        )

    async def reset_password(self, token: str, new_password: str) -> MessageResponse:
        """Reset a user's password using a valid reset token.

        Validates the token, updates the user's ``password_hash``, and
        deletes the consumed token so it cannot be reused.

        Args:
            token: The raw (un-hashed) reset token from the link sent
                to the user's email address.
            new_password: The new plain-text password chosen by the user.

        Returns:
            A ``MessageResponse`` confirming the password was changed.

        Raises:
            NotFoundException: If the token does not exist, has expired,
                or has already been consumed.

        """
        logger.info(f"Reset Password Endpoint called.\nReset Token Received: {token}")
        token_record = await self._auth_repo.get_valid_password_reset_token(
            hash_token(token)
        )

        if not token_record:
            raise NotFoundException(
                message="Reset token is invalid or has expired",
                code="TOKEN_INVALID",
            )

        user = await self._user_repo.get_by_id(token_record.user_id)
        user.password_hash = hash_password(new_password)

        # Burn the token so it can't be used again
        token_record.used_at = datetime.now(timezone.utc)

        # Explicit commit
        await self._db.commit()

        return MessageResponse(message="Password successfully reset")

    async def change_password(
        self, user: User, data: ChangePasswordRequest
    ) -> MessageResponse:
        """Change the password for an already-authenticated user.

        The caller must have already resolved the ``User`` object (e.g.
        from the JWT dependency), guaranteeing the user is logged in.

        Args:
            user: The authenticated ``User`` ORM instance.
            data: Validated payload containing ``old_password``,
                ``new_password``, and ``confirm_password``.

        Returns:
            A ``MessageResponse`` confirming the password was updated.

        Raises:
            InvalidCredentialsException: If ``old_password`` does not
                match the currently stored hash.

        """
        if not verify_password(data.old_password, user.password_hash):
            raise InvalidCredentialsException("Current password is incorrect")

        user.password_hash = hash_password(data.new_password)

        # Explicit commit
        await self._db.commit()

        return MessageResponse(message="Password successfully changed")
