"""Data access layer for user-related database operations.

Provides ``UserRepository``, a thin async wrapper around SQLAlchemy
queries for ``User``, ``UserProfile``, and ``Wallet`` records.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.users.enums import AccountStatus, KYCTier, SellerVerificationStatus
from apps.users.kyc_models import KYCProfile
from apps.wallet.models import Wallet
from common.exceptions import AlreadyExistsException
from common.pagination import paginate
from common.schemas import PaginatedResponse

from .models import SellerProfile, User, UserProfile, VerificationDoc


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
        self._db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Fetch a user by their UUID primary key.

        Args:
            user_id: The UUID of the user to retrieve.

        Returns:
            The matching ``User`` instance, or ``None`` if not found.

        """
        stmt = select(User).where(User.id == user_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by email address, case-insensitively.

        Args:
            email: The email address to search for.

        Returns:
            The matching ``User`` instance, or ``None`` if not found.

        """
        stmt = select(User).where(func.lower(User.email) == email.lower())
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_phone_number(self, phone_number: str) -> User | None:
        """Fetch a user by their phone number.

        Args:
            phone_number: The phone number string to search for.

        Returns:
            The matching ``User`` instance, or ``None`` if not found.

        """
        stmt = select(User).where(User.phone_number == phone_number)
        result = await self._db.execute(stmt)
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
        self._db.add(user)
        await self._db.flush()

        profile = UserProfile(user_id=user.id)
        wallet = Wallet(
            user_id=user.id,
            available_funds=0,
            locked_funds=0,
            escrow_funds=0,
            currency="NGN",
        )
        kyc_profile = KYCProfile(user_id=user.id)
        self._db.add(profile)
        self._db.add(wallet)
        self._db.add(kyc_profile)
        await self._db.flush()
        await self._db.refresh(user)

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
        self._db.add(user)
        await self._db.flush()
        return user

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        """Stamp the user's ``last_login_at`` field with the current UTC time.

        Args:
            user_id: The UUID of the user whose login timestamp to update.

        """
        user = await self.get_by_id(user_id)
        user.last_login_at = datetime.now(timezone.utc)
        self._db.add(user)
        await self._db.flush()

    async def get_with_profile(self, user_id: uuid.UUID) -> User | None:
        """Fetch user with profile eagerly loaded (no N+1 query).

        Args:
            user_id: The UUID of the user to retrieve.

        Returns:
            The matching ``User`` instance with profile relationships loaded,
            or ``None`` if not found.

        """
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.profile), selectinload(User.seller_profile))
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_profile(self, user_id: uuid.UUID, data: dict) -> "UserProfile":
        """Update or create user profile with partial data.

        Args:
            user_id: The UUID of the user whose profile to update.
            data: Dictionary of field names and values to update.

        Returns:
            The updated or newly created ``UserProfile`` instance.

        """
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await self._db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            profile = UserProfile(user_id=user_id)
            self._db.add(profile)

        for key, value in data.items():
            if value is not None:
                setattr(profile, key, value)

        await self._db.flush()
        await self._db.refresh(profile)
        return profile

    async def create_seller_profile(
        self, user_id: uuid.UUID, data: dict
    ) -> "SellerProfile":
        """Create seller profile, or reset it if previously rejected.

        A rejected seller is allowed to reapply. Their existing profile
        is reset to PENDING with the new data rather than creating a
        duplicate row (which would violate the unique constraint).

        Args:
            user_id: The UUID of the user creating the seller profile.
            data: Dictionary of seller profile field values.

        Returns:
            The newly created or reset ``SellerProfile`` instance.

        Raises:
            AlreadyExistsException: If a non-rejected profile already exists.

        """
        stmt = select(SellerProfile).where(SellerProfile.user_id == user_id)
        result = await self._db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            if existing.verification_status != SellerVerificationStatus.REJECTED:
                msg = "Seller profile already exists for this user"
                raise AlreadyExistsException(msg)

            # Rejected — delete old documents so the new submission starts clean
            await self._db.execute(
                delete(VerificationDoc).where(VerificationDoc.seller_id == existing.id)
            )
            # Reset the existing profile with the new submission data
            for key, value in data.items():
                setattr(existing, key, value)
            existing.verification_status = SellerVerificationStatus.PENDING
            existing.is_verified = False
            existing.verified_at = None
            existing.verified_by_id = None
            existing.rejection_reason = None
            await self._db.flush()
            await self._db.refresh(existing)
            return existing  # return here — do NOT create a new row

        seller_profile = SellerProfile(user_id=user_id, **data)
        self._db.add(seller_profile)
        await self._db.flush()
        await self._db.refresh(seller_profile)
        return seller_profile

    async def get_seller_profile(self, user_id: uuid.UUID) -> "SellerProfile | None":
        """Fetch seller profile for a user.

        Args:
            user_id: The UUID of the user.

        Returns:
            The ``SellerProfile`` instance, or ``None`` if not found.

        """
        stmt = select(SellerProfile).where(SellerProfile.user_id == user_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_seller_verification(
        self,
        user_id: uuid.UUID,
        is_verified: bool,
        verified_by_id: uuid.UUID,
        reason: str,
    ) -> "SellerProfile":
        """Update seller verification status.

        Args:
            user_id: The UUID of the user to verify.
            is_verified: Boolean indicating verification status.
            verified_by_id: The UUID of the admin who performed verification.

        Returns:
            The updated ``SellerProfile`` instance.

        """
        seller_profile = await self.get_seller_profile(user_id)
        seller_profile.is_verified = is_verified
        seller_profile.verified_by_id = verified_by_id
        seller_profile.verification_status = (
            SellerVerificationStatus.APPROVED
            if is_verified
            else SellerVerificationStatus.REJECTED
        )
        seller_profile.rejection_reason = reason if not is_verified else None

        if is_verified:
            seller_profile.verified_at = datetime.now(timezone.utc)

        self._db.add(seller_profile)
        await self._db.flush()
        await self._db.refresh(seller_profile)
        return seller_profile

    async def get_public_profile(self, user_id: uuid.UUID) -> User | None:
        """Fetch user with profile and seller profile for public view.

        Args:
            user_id: The UUID of the user to retrieve.

        Returns:
            The ``User`` instance with profile relationships loaded,
            or ``None`` if not found.

        """
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.profile), selectinload(User.seller_profile))
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_wallet(self, user_id: uuid.UUID) -> Wallet | None:
        """Fetch wallet for a user.

        Args:
            user_id: The UUID of the user.

        Returns:
            The ``Wallet`` instance, or ``None`` if not found.

        """
        stmt = select(Wallet).where(Wallet.user_id == user_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def increment_total_sales(self, user_id: uuid.UUID) -> None:
        """Increment the ``total_sales`` counter on ``UserProfile`` by 1.

        Called after escrow is released to the seller on order completion.
        Creates the profile row if it does not exist yet.

        Args:
            user_id: The UUID of the seller whose counter to increment.

        """
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await self._db.execute(stmt)
        profile = result.scalar_one_or_none()

        if profile:
            profile.total_sales = (profile.total_sales or 0) + 1
            await self._db.flush()

    async def get_unverified_sellers(
        self,
        has_seller_profile: bool,
        seller_verified: bool,
        limit: int,
    ):
        """Fetch sellers with a pending verification status.

        Args:
            has_seller_profile: Unused filter flag (kept for API compatibility).
            seller_verified: Unused filter flag (kept for API compatibility).
            limit: Maximum number of results to return.

        Returns:
            A list of ``User`` instances with pending seller profiles loaded.

        """
        stmt = (
            select(User)
            .join(SellerProfile, User.id == SellerProfile.user_id)
            .where(
                SellerProfile.verification_status == SellerVerificationStatus.PENDING
            )
            .options(
                selectinload(User.seller_profile).selectinload(
                    SellerProfile.verification_docs
                ),
                selectinload(User.profile),
            )
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def get_all_users(
        self,
        search: str | None,
        account_status: AccountStatus | None,
        kyc_tier: KYCTier | None,
        page: int = 1,
        limit: int = 20,
    ) -> PaginatedResponse:
        """Fetch a paginated list of users, with optional filters.

        Args:
            search: A string to search for in users' first name, last name, or email.
            account_status: Filter by account status.
            kyc_tier: Filter by KYC tier.
            page: The page number to retrieve (1-indexed).
            limit: The maximum number of users per page.

        Returns:
            A ``PaginatedResponse`` containing the list of users and pagination info.

        """
        stmt = select(User)
        if search:
            stmt = stmt.where(
                func.lower(User.first_name).contains(search.lower())
                | func.lower(User.last_name).contains(search.lower())
                | func.lower(User.email).contains(search.lower())
            )

        if account_status:
            stmt = stmt.where(User.account_status == account_status)

        if kyc_tier:
            stmt = stmt.where(User.kyc_tier == kyc_tier)

        stmt = stmt.options(
            selectinload(User.profile),
            selectinload(User.seller_profile),
        )

        return await paginate(stmt, page, limit, self._db)

    async def get_user_detail(self, user_id: uuid.UUID) -> User | None:
        """Fetch a single user with all relationships for admin detail view."""
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.profile),
                selectinload(User.seller_profile).selectinload(
                    SellerProfile.verification_docs
                ),
                selectinload(User.kyc_profile),
                selectinload(User.kyc_documents),
                selectinload(User.wallet),
                selectinload(User.bids),
            )
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()
