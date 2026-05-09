"""Admin panel router for user management operations."""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.enums import AccountStatus, KYCTier
from apps.users.models import User
from apps.users.service import UserService
from common.dependency import get_db, require_admin

router = APIRouter()


class UpdateStatusRequest(BaseModel):
    """Request body for updating a user's account status.

    Attributes:
        account_status: The new account status to apply.

    """

    account_status: AccountStatus


@router.get("/verify-users", status_code=200)
async def get_unverified_sellers(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get a list of users with pending seller verification."""
    service = UserService(db)
    return await service.get_unverified_sellers(
        has_seller_profile=True,
        seller_verified=False,
        limit=limit,
    )


@router.get("/users", status_code=200)
async def get_all_users(
    search: str | None = None,
    account_status: AccountStatus | None = None,
    kyc_tier: KYCTier | None = None,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get paginated list of all users with optional filters."""
    service = UserService(db)
    return await service.get_all_users(
        search=search,
        account_status=account_status,
        kyc_tier=kyc_tier,
        page=page,
        limit=limit,
    )


@router.get("/users/{user_id}", status_code=200)
async def get_user_detail(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get full detail for a single user including all relationships."""
    service = UserService(db)
    return await service.get_user_detail(user_id)


@router.patch("/users/{user_id}/status", status_code=200)
async def update_user_status(
    user_id: UUID,
    data: UpdateStatusRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a user's account status (suspend, ban, reactivate)."""
    service = UserService(db)
    return await service.update_user_status(user_id, data.account_status)
