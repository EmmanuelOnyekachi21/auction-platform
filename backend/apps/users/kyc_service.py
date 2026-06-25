import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.bvn_service import BVNService
from apps.users.enums import KYCTier
from apps.users.kyc_repository import KYCRepository
from apps.users.schemas import KYCLimitsResponse, KYCStatusResponse
from common.exceptions import PermissionDeniedException, ValidationException
from config.settings import settings


class KYCService:
    """Service for managing Know Your Customer (KYC) level-based limits.

    Handles verification and status checks.
    """

    def __init__(self, db: AsyncSession):
        """Initialize service with a database session."""
        self._db = db
        self._bvn = BVNService()
        self._kyc = KYCRepository(db)

    def _get_limits_for_tier(self, tier: KYCTier) -> KYCLimitsResponse:
        """Return transaction limits for the given KYC tier."""
        if tier == KYCTier.TIER_2:
            return KYCLimitsResponse(
                max_bid=settings.tier_2_max_bid,
                max_wallet_balance=settings.tier_2_max_wallet_balance,
                max_daily_withdrawal=settings.tier_2_max_daily_withdrawal,
            )
        if tier == KYCTier.TIER_3:
            return KYCLimitsResponse(
                max_bid=settings.tier_3_max_bid,
                max_wallet_balance=settings.tier_3_max_wallet_balance,
                max_daily_withdrawal=settings.tier_3_max_daily_withdrawal,
            )
        # Default: TIER_1
        return KYCLimitsResponse(
            max_bid=settings.tier_1_max_bid,
            max_wallet_balance=settings.tier_1_max_wallet_balance,
            max_daily_withdrawal=settings.tier_1_max_withdrawal,
        )

    def _get_next_steps(self, kyc_profile) -> list[str]:
        """Return human-readable next steps based on current KYC state."""
        if kyc_profile.current_tier == KYCTier.TIER_1:
            return [
                "Submit your BVN to unlock higher bid limits (up to ₦500,000)",
                "BVN verification enables wallet funding up to ₦2,000,000",
                "BVN verification enables withdrawals",
            ]
        if kyc_profile.current_tier == KYCTier.TIER_2:
            return [
                "Tier 3 verification (address + bank statement) coming soon",
            ]
        return []

    async def get_kyc_status(self, user_id: uuid.UUID) -> KYCStatusResponse:
        """Get the current KYC status and limits for a user.

        Creates a KYCProfile if one doesn't exist yet.
        """
        kyc_profile = await self._kyc.get_by_user_id(user_id)
        if kyc_profile is None:
            kyc_profile = await self._kyc.create_for_user(user_id)
            await self._db.commit()

        # Derive tier 2 verification status for the frontend
        if kyc_profile.tier_2_completed_at is not None:
            tier_2_status = "verified"
        elif kyc_profile.bvn_hash is not None:
            # BVN submitted but not yet confirmed (production async webhook flow)
            tier_2_status = "pending_review"
        elif kyc_profile.rejection_reason is not None:
            tier_2_status = "rejected"
        else:
            tier_2_status = "none"

        return KYCStatusResponse(
            current_tier=kyc_profile.current_tier.value,
            # Tier 1 is complete for any registered user — email verification
            # is enforced at login. tier_1_completed_at may be null for users
            # created before this field was added, so we treat existence as complete.
            tier_1_complete=True,
            tier_2_complete=kyc_profile.tier_2_completed_at is not None,
            tier_3_complete=kyc_profile.tier_3_completed_at is not None,
            tier_2_verification_status=tier_2_status,
            limits=self._get_limits_for_tier(kyc_profile.current_tier),
            next_steps=self._get_next_steps(kyc_profile),
        )

    async def verify_bvn(
        self,
        user_id: uuid.UUID,
        bvn: str,
        date_of_birth: str,
    ) -> KYCStatusResponse:
        """Verify a user's BVN and upgrade to Tier 2 on success."""
        from apps.users.repository import UserRepository

        user_repo = UserRepository(self._db)
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise ValidationException(message="User not found")

        # Rate limit check — increments attempt count
        await self._kyc.check_and_increment_bvn_attempts(user_id)

        # Hash BVN before any further processing
        bvn_hash = self._bvn.hash_bvn(bvn)

        # Prevent same BVN on two accounts
        already_registered = await self._kyc.check_bvn_already_registered(bvn_hash)
        if already_registered:
            raise ValidationException(
                message="This BVN is already associated with another account.",
            )

        # Call BVN verification (real or mock depending on settings)
        result = await self._bvn.verify_bvn(
            bvn=bvn,
            first_name=user.first_name,
            last_name=user.last_name,
            date_of_birth=date_of_birth,
        )

        if not result["is_match"]:
            await self._kyc.reject_verification(
                user_id, reason="BVN details do not match user records"
            )
            msg = "BVN verification failed. Ensure your details match your BVN records."
            raise ValidationException(message=msg)

        # Store verification proof
        await self._kyc.initiate_bvn_verification(
            user_id=user_id,
            bvn_hash=bvn_hash,
            reference=result["reference"],
        )

        # Upgrade tier
        await self._kyc.complete_tier_2(user_id)

        # Sync User.kyc_tier
        user.kyc_tier = KYCTier.TIER_2
        self._db.add(user)
        await self._db.flush()
        await self._db.commit()

        return await self.get_kyc_status(user_id)

    async def check_bid_limit(self, user_id: uuid.UUID, amount) -> None:
        """Raise PermissionDeniedException if bid exceeds tier limit."""
        from apps.users.repository import UserRepository

        user = await UserRepository(self._db).get_by_id(user_id)
        limits = self._get_limits_for_tier(user.kyc_tier)
        if amount > limits.max_bid:
            msg = (
                f"Your current KYC tier allows bids up to ₦{limits.max_bid:,.0f}. "
                "Complete BVN verification to increase your limit."
            )
            raise PermissionDeniedException(message=msg)

    async def check_withdrawal_limit(self, user_id: uuid.UUID, amount) -> None:
        """Raise PermissionDeniedException if withdrawal is not allowed."""
        from apps.users.repository import UserRepository

        user = await UserRepository(self._db).get_by_id(user_id)
        if user.kyc_tier == KYCTier.TIER_1:
            msg = (
                "Withdrawals require BVN verification. "
                "Please complete Tier 2 verification."
            )
            raise PermissionDeniedException(message=msg)
        today_total = await self._kyc.get_daily_withdrawal_total(user_id)
        limits = self._get_limits_for_tier(user.kyc_tier)
        if today_total + amount > limits.max_daily_withdrawal:
            msg = (
                f"Daily withdrawal limit of "
                f"₦{limits.max_daily_withdrawal:,.0f} reached. "
                "Resets at midnight."
            )
            raise PermissionDeniedException(message=msg)

    async def check_funding_limit(
        self, user_id: uuid.UUID, amount, current_balance
    ) -> None:
        """Raise PermissionDeniedException if funding would exceed wallet limit."""
        from apps.users.repository import UserRepository

        user = await UserRepository(self._db).get_by_id(user_id)
        limits = self._get_limits_for_tier(user.kyc_tier)
        if current_balance + amount > limits.max_wallet_balance:
            msg = (
                f"Funding would exceed your wallet limit of "
                f"₦{limits.max_wallet_balance:,.0f}. "
                "Complete KYC verification to increase your limit."
            )
            raise PermissionDeniedException(message=msg)
