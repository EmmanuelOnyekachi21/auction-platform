"""KYC verification endpoints.

Provides routes for checking KYC status, submitting BVN verification,
and viewing current tier limits. Also includes admin endpoints for
listing and manually managing user KYC tiers.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.enums import KYCTier
from apps.users.kyc_models import KYCProfile
from apps.users.kyc_service import KYCService
from apps.users.models import User
from apps.users.schemas import (
    BVNVerificationRequest,
    KYCLimitsResponse,
    KYCStatusResponse,
)
from common.dependency import get_current_active_user, get_db, require_admin
from common.rate_limiter import limiter

router = APIRouter()


@router.get("/status", response_model=KYCStatusResponse)
async def get_kyc_status(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> KYCStatusResponse:
    """Get the authenticated user's current KYC tier and limits."""
    service = KYCService(db)
    return await service.get_kyc_status(current_user.id)


@router.post("/verify-bvn", response_model=KYCStatusResponse)
@limiter.limit("3/day")
async def verify_bvn(
    request: Request,
    data: BVNVerificationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> KYCStatusResponse:
    """Submit BVN for Tier 2 verification.

    Rate limited to 3 attempts per day per user.
    BVN is never stored in plain text — only a SHA256 hash is persisted.
    """
    service = KYCService(db)
    return await service.verify_bvn(
        user_id=current_user.id,
        bvn=data.bvn,
        date_of_birth=str(data.date_of_birth),
    )


@router.get("/limits", response_model=KYCLimitsResponse)
async def get_kyc_limits(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> KYCLimitsResponse:
    """Get the current user's transaction limits based on their KYC tier."""
    service = KYCService(db)
    status = await service.get_kyc_status(current_user.id)
    return status.limits


# ── Admin endpoints ──────────────────────────────────────────────────────────


@router.get("/admin/users", response_model=list[dict])
async def list_users_kyc(
    tier: KYCTier | None = Query(None, description="Filter by KYC tier"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all users with their KYC tier and profile info (admin only).

    Optionally filter by tier to find users who need manual review.
    """
    stmt = (
        select(User, KYCProfile)
        .join(KYCProfile, KYCProfile.user_id == User.id, isouter=True)
        .order_by(User.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    if tier:
        stmt = stmt.where(User.kyc_tier == tier)

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "user_id": str(user.id),
            "email": user.email,
            "full_name": f"{user.first_name} {user.last_name}".strip(),
            "kyc_tier": user.kyc_tier.value if user.kyc_tier else "TIER_1",
            "bvn_verified": kyc.bvn_verified if kyc else False,
            "tier_1_completed_at": (
                kyc.tier_1_completed_at.isoformat()
                if kyc and kyc.tier_1_completed_at
                else None
            ),
            "tier_2_completed_at": (
                kyc.tier_2_completed_at.isoformat()
                if kyc and kyc.tier_2_completed_at
                else None
            ),
            "created_at": user.created_at.isoformat(),
        }
        for user, kyc in rows
    ]


@router.patch("/admin/users/{user_id}/upgrade-tier", response_model=dict)
async def admin_upgrade_tier(
    user_id: UUID,
    tier: KYCTier = Query(..., description="Target tier to upgrade user to"),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Manually upgrade a user's KYC tier (admin only).

    Used when document review is completed offline or for manual overrides.
    """
    from datetime import datetime, timezone

    # Fetch user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        from common.exceptions import NotFoundException

        raise NotFoundException(message="User not found", code="USER_NOT_FOUND")

    # Fetch or create KYC profile
    result = await db.execute(select(KYCProfile).where(KYCProfile.user_id == user_id))
    kyc = result.scalar_one_or_none()
    if not kyc:
        kyc = KYCProfile(user_id=user_id)
        db.add(kyc)

    now = datetime.now(timezone.utc)
    kyc.current_tier = tier
    user.kyc_tier = tier

    if tier == KYCTier.TIER_2 and not kyc.tier_2_completed_at:
        kyc.bvn_verified = True
        kyc.bvn_verified_at = now
        kyc.tier_2_completed_at = now

    if tier == KYCTier.TIER_3 and not kyc.tier_3_completed_at:
        kyc.address_verified = True
        kyc.bank_statement_verified = True
        kyc.tier_3_completed_at = now

    db.add(kyc)
    db.add(user)
    await db.commit()

    return {
        "message": f"User {user.email} upgraded to {tier.value}",
        "user_id": str(user_id),
        "new_tier": tier.value,
    }
