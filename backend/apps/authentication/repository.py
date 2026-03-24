"""Data access layer for authentication token database operations.

Provides ``AuthRepository``, a thin async wrapper around SQLAlchemy
for creating, querying, marking as used, and deleting
:class:`~apps.authentication.models.EmailVerificationToken` and
:class:`~apps.authentication.models.PasswordResetToken` records.

All methods flush changes to the current session but do **not** commit;
the transaction boundary is owned by the caller.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import EmailVerificationToken, PasswordResetToken


class AuthRepository:
    """Async repository for authentication token database operations.

    Encapsulates all SQLAlchemy queries for
    :class:`~apps.authentication.models.EmailVerificationToken` and
    :class:`~apps.authentication.models.PasswordResetToken` so that the
    service layer remains free of raw query concerns.

    Attributes:
        db: The active ``AsyncSession`` injected at construction time.

    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialise the repository with an async database session.

        Args:
            db: An active ``AsyncSession`` used for all queries.

        """
        self.db = db

    # --- Email verification ---

    async def create_email_verification_token(
        self, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> EmailVerificationToken:
        """Persist a new email verification token for the given user.

        Args:
            user_id: UUID of the user whose email is being verified.
            token_hash: SHA-256 hex digest of the raw token.
            expires_at: Timezone-aware UTC datetime after which the
                token should be considered expired.

        Returns:
            The newly created and flushed
            :class:`~apps.authentication.models.EmailVerificationToken`
            instance.

        """
        token = EmailVerificationToken(
            user_id=user_id,
            token=token_hash,
            expires_at=expires_at,
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def get_valid_email_token(
        self, token_hash: str
    ) -> EmailVerificationToken | None:
        """Retrieve an unexpired, unused email verification token.

        A token is considered valid when its ``used_at`` is ``None`` and
        its ``expires_at`` is in the future.

        Args:
            token_hash: SHA-256 hex digest of the raw token to look up.

        Returns:
            The matching
            :class:`~apps.authentication.models.EmailVerificationToken`,
            or ``None`` if no valid token is found.

        """
        stmt = select(EmailVerificationToken).where(
            EmailVerificationToken.token == token_hash,
            EmailVerificationToken.used_at.is_(None),
            EmailVerificationToken.expires_at > datetime.now(timezone.utc),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_email_token_used(self, token_id: UUID) -> None:
        """Stamp ``used_at`` on an email verification token.

        No-ops silently if the token ID does not exist.

        Args:
            token_id: Primary key of the token to mark as consumed.

        """
        token = await self.db.get(EmailVerificationToken, token_id)
        if token:
            token.used_at = datetime.now(timezone.utc)
            await self.db.flush()

    async def delete_email_verification_token(self, token_id: UUID) -> None:
        """Delete an email verification token record from the database.

        No-ops silently if the token ID does not exist.

        Args:
            token_id: Primary key of the token to delete.

        """
        token = await self.db.get(EmailVerificationToken, token_id)
        if token:
            await self.db.delete(token)
            await self.db.flush()

    # --- Password reset ---

    async def create_password_reset_token(
        self, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> PasswordResetToken:
        """Persist a new password reset token for the given user.

        Args:
            user_id: UUID of the user requesting the password reset.
            token_hash: SHA-256 hex digest of the raw token.
            expires_at: Timezone-aware UTC datetime after which the
                token should be considered expired.

        Returns:
            The newly created and flushed
            :class:`~apps.authentication.models.PasswordResetToken`
            instance.

        """
        token = PasswordResetToken(
            user_id=user_id,
            token=token_hash,
            expires_at=expires_at,
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def get_valid_password_reset_token(
        self, token_hash: str
    ) -> PasswordResetToken | None:
        """Retrieve an unexpired, unused password reset token.

        A token is considered valid when its ``used_at`` is ``None`` and
        its ``expires_at`` is in the future.

        Args:
            token_hash: SHA-256 hex digest of the raw token to look up.

        Returns:
            The matching
            :class:`~apps.authentication.models.PasswordResetToken`,
            or ``None`` if no valid token is found.

        """
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_password_reset_token_used(self, token_id: UUID) -> None:
        """Stamp ``used_at`` on a password reset token.

        No-ops silently if the token ID does not exist.

        Args:
            token_id: Primary key of the token to mark as consumed.

        """
        token = await self.db.get(PasswordResetToken, token_id)
        if token:
            token.used_at = datetime.now(timezone.utc)
            await self.db.flush()

    async def delete_password_reset_token(self, token_id: UUID) -> None:
        """Delete a password reset token record from the database.

        No-ops silently if the token ID does not exist.

        Args:
            token_id: Primary key of the token to delete.

        """
        token = await self.db.get(PasswordResetToken, token_id)
        if token:
            await self.db.delete(token)
            await self.db.flush()
