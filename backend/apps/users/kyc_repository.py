import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.enums import KYCTier
from apps.users.kyc_models import KYCProfile
from apps.wallet.enums import TransactionDirection, TransactionType
from apps.wallet.models import Wallet, WalletTransactions
from common.exceptions import ValidationException


class KYCRepository:
    """Repository for KYC-related database operations."""

    def __init__(self, db: AsyncSession):
        """Initialize repository with a database session."""
        self._db = db

    async def get_by_user_id(self, user_id: uuid.UUID) -> KYCProfile | None:
        """Get KYC profile for a specific user."""
        stmt = select(KYCProfile).where(KYCProfile.user_id == user_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_for_user(self, user_id: uuid.UUID) -> KYCProfile:
        """Create a new KYC profile for a user."""
        profile = KYCProfile(user_id=user_id)
        self._db.add(profile)
        await self._db.flush()
        await self._db.refresh(profile)
        return profile

    async def complete_tier_1(self, user_id: uuid.UUID) -> KYCProfile:
        """Mark Tier 1 KYC as completed (email/phone verified)."""
        kyc_profile = await self.get_by_user_id(user_id)
        kyc_profile.email_verified = True
        kyc_profile.phone_verified = True
        kyc_profile.tier_1_completed_at = datetime.now(timezone.utc)
        self._db.add(kyc_profile)
        await self._db.flush()
        await self._db.refresh(kyc_profile)
        return kyc_profile

    async def initiate_bvn_verification(
        self, user_id: uuid.UUID, bvn_hash: str, reference: str
    ) -> KYCProfile:
        """Store BVN hash and reference locally while verification is in progress."""
        kyc_profile = await self.get_by_user_id(user_id)
        kyc_profile.bvn_hash = bvn_hash
        kyc_profile.bvn_verification_reference = reference
        kyc_profile.last_verification_attempt = datetime.now(timezone.utc)
        self._db.add(kyc_profile)
        await self._db.flush()
        await self._db.refresh(kyc_profile)
        return kyc_profile

    async def complete_tier_2(self, user_id: uuid.UUID) -> KYCProfile:
        """Mark Tier 2 KYC as completed (BVN verified)."""
        kyc_profile = await self.get_by_user_id(user_id)
        kyc_profile.bvn_verified = True
        kyc_profile.bvn_verified_at = datetime.now(timezone.utc)
        kyc_profile.current_tier = KYCTier.TIER_2
        kyc_profile.tier_2_completed_at = datetime.now(timezone.utc)
        self._db.add(kyc_profile)
        await self._db.flush()
        await self._db.refresh(kyc_profile)
        return kyc_profile

    async def reject_verification(self, user_id: uuid.UUID, reason: str) -> KYCProfile:
        """Record the reason for a rejected KYC verification."""
        kyc_profile = await self.get_by_user_id(user_id)
        kyc_profile.rejection_reason = reason
        self._db.add(kyc_profile)
        await self._db.flush()
        await self._db.refresh(kyc_profile)
        return kyc_profile

    async def check_bvn_already_registered(self, bvn_hash: str) -> bool:
        """Check if a BVN hash already exists in the database."""
        stmt = select(KYCProfile).where(KYCProfile.bvn_hash == bvn_hash)
        result = await self._db.execute(stmt)
        existing = result.scalar_one_or_none()
        return existing is not None

    async def get_daily_withdrawal_total(self, user_id: uuid.UUID) -> Decimal:
        """Calculate the total amount withdrawn by a user today in UTC."""
        now = datetime.now(timezone.utc)
        today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = (
            select(func.coalesce(func.sum(WalletTransactions.amount), 0))
            .join(Wallet, WalletTransactions.wallet_id == Wallet.id)
            .where(Wallet.user_id == user_id)
            .where(WalletTransactions.transaction_type == TransactionType.WITHDRAWAL)
            .where(WalletTransactions.direction == TransactionDirection.DEBIT)
            .where(WalletTransactions.created_at >= today_midnight)
        )
        result = await self._db.execute(stmt)
        return Decimal(result.scalar())

    async def check_and_increment_bvn_attempts(self, user_id: uuid.UUID):
        """Enforce daily rate limit of 3 BVN verification attempts."""
        kyc_profile = await self.get_by_user_id(user_id)
        if kyc_profile is None:
            kyc_profile = await self.create_for_user(user_id)
        now = datetime.now(timezone.utc)

        # Reset counter if the daily window has expired or never been set
        has_expired = (
            kyc_profile.bvn_attempt_reset_at is None
            or kyc_profile.bvn_attempt_reset_at <= now
        )
        if has_expired:
            kyc_profile.bvn_attempt_count = 0
            tomorrow_midnight = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            kyc_profile.bvn_attempt_reset_at = tomorrow_midnight

        if kyc_profile.bvn_attempt_count >= 3:
            raise ValidationException(
                message=(
                    "Maximum BVN verification attempts reached for today. "
                    "Try again tomorrow."
                ),
            )

        kyc_profile.bvn_attempt_count += 1
        self._db.add(kyc_profile)
        await self._db.flush()
        await self._db.refresh(kyc_profile)
        return kyc_profile
