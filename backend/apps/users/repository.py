"""Data access layer for user-related database operations.

Provides ``UserRepository``, a thin async wrapper around SQLAlchemy
queries for ``User``, ``UserProfile``, and ``Wallet`` records.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.wallet.models import Wallet

from .models import User, UserProfile


class UserRepository:
    """Async repository for all user-related database operations.

    Encapsulates SQLAlchemy queries so that service and handler layers
    remain free of raw SQL concerns.  Every method flushes changes to
    the session but does not commit — the caller controls the transaction
    boundary.

    Attributes:
        db: The active ``AsyncSession`` injected at construction time.

    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialise the repository with an async database session.

        Args:
            db: An active ``AsyncSession`` to use for all queries.

        """
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Fetch a user by their UUID primary key.

        Args:
            user_id: The UUID of the user to retrieve.

        Returns:
            The matching ``User`` instance, or ``None`` if not found.

        """
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by email address, case-insensitively.

        Args:
            email: The email address to search for.

        Returns:
            The matching ``User`` instance, or ``None`` if not found.

        """
        stmt = select(User).where(func.lower(User.email) == email.lower())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_phone_number(self, phone_number: str) -> User | None:
        """Fetch a user by their phone number.

        Args:
            phone_number: The phone number string to search for.

        Returns:
            The matching ``User`` instance, or ``None`` if not found.

        """
        stmt = select(User).where(User.phone_number == phone_number)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> User:
        """Create a new user together with a blank profile and wallet.

        Flushes the user first so that ``user.id`` is populated by the
        database before creating the dependent ``UserProfile`` and
        ``Wallet`` records.

        Args:
            data: A dictionary of column values for the ``User`` model.

        Returns:
            The newly created and refreshed ``User`` instance.

        """
        user = User(**data)
        self.db.add(user)
        await self.db.flush()

        profile = UserProfile(user_id=user.id)
        wallet = Wallet(
            user_id=user.id,
            available_funds=0,
            locked_funds=0,
            escrow_funds=0,
            currency="NGN",
        )
        self.db.add(profile)
        self.db.add(wallet)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update(self, user_id: uuid.UUID, data: dict) -> User | None:
        """Apply a partial update to an existing user record.

        Args:
            user_id: The UUID of the user to update.
            data: A dictionary of field names and their new values.

        Returns:
            The updated ``User`` instance, or ``None`` if not found.

        """
        user = await self.get_by_id(user_id)
        for key, value in data.items():
            setattr(user, key, value)
        self.db.add(user)
        await self.db.flush()
        return user

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        """Stamp the user's ``last_login_at`` field with the current UTC time.

        Args:
            user_id: The UUID of the user whose login timestamp to update.

        """
        user = await self.get_by_id(user_id)
        user.last_login_at = datetime.now(timezone.utc)
        self.db.add(user)
        await self.db.flush()
