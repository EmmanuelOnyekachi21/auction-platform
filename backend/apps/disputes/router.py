"""Dispute router — endpoints for dispute management."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.disputes.schemas import (
    RaiseDisputeRequest,
    ResolveDisputeRequest,
    SubmitEvidenceRequest,
)
from apps.disputes.service import DisputeService
from apps.users.models import User
from common.dependency import get_current_active_user, get_db, require_admin

router = APIRouter()


@router.post("/orders/{order_id}/dispute", status_code=status.HTTP_201_CREATED)
async def raise_dispute(
    order_id: UUID,
    data: RaiseDisputeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Buyer raises a dispute on an order."""
    service = DisputeService(db)
    return await service.raise_dispute(
        buyer_id=current_user.id,
        order_id=order_id,
        data=data,
    )


@router.post("/disputes/{dispute_id}/evidence", status_code=status.HTTP_201_CREATED)
async def submit_evidence(
    dispute_id: UUID,
    data: SubmitEvidenceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Buyer or seller submits evidence for a dispute."""
    service = DisputeService(db)
    return await service.submit_evidence(
        user_id=current_user.id,
        dispute_id=dispute_id,
        data=data,
    )


@router.get("/disputes/{dispute_id}")
async def get_dispute(
    dispute_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get dispute detail. Accessible by buyer, seller, or admin."""
    service = DisputeService(db)
    return await service.get_dispute(
        user_id=current_user.id,
        dispute_id=dispute_id,
    )


@router.patch("/disputes/{dispute_id}/mark-under-review")
async def mark_under_review(
    dispute_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Admin marks dispute as under review."""
    service = DisputeService(db)
    return await service.mark_under_review(
        admin_id=admin_user.id,
        dispute_id=dispute_id,
    )


@router.patch("/disputes/{dispute_id}/resolve")
async def resolve_dispute(
    dispute_id: UUID,
    data: ResolveDisputeRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Admin resolves a dispute."""
    service = DisputeService(db)
    return await service.resolve_dispute(
        admin_id=admin_user.id,
        dispute_id=dispute_id,
        data=data,
    )


@router.get("/admin/disputes")
async def get_open_disputes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Admin — paginated list of open disputes."""
    service = DisputeService(db)
    return await service.get_open_disputes(page=page, limit=limit)
