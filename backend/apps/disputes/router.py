"""Dispute router — endpoints for dispute management."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.disputes.models import Dispute, DisputeEvidence
from apps.disputes.schemas import (
    DisputeDetailResponse,
    RaiseDisputeRequest,
    ResolveDisputeRequest,
    SubmitEvidenceRequest,
)
from apps.disputes.service import DisputeService
from apps.users.models import User
from common.dependency import get_current_active_user, get_db, require_admin
from common.pagination import paginate

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


@router.get("/users/me/disputes")
async def get_my_disputes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all disputes where the current user is buyer or seller."""
    stmt = (
        select(Dispute)
        .where(
            or_(
                Dispute.raised_by_id == current_user.id,
                Dispute.against_id == current_user.id,
            )
        )
        .options(
            selectinload(Dispute.raised_by),
            selectinload(Dispute.against),
            selectinload(Dispute.order),
            selectinload(Dispute.evidence).selectinload(DisputeEvidence.uploaded_by),
        )
        .order_by(Dispute.created_at.desc())
    )
    result = await paginate(stmt, page, limit, db)
    result.data = [DisputeDetailResponse.model_validate(d) for d in result.data]
    return result


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


@router.post(
    "/disputes/{dispute_id}/evidence/upload",
    status_code=status.HTTP_201_CREATED,
)
async def upload_evidence_file(
    dispute_id: UUID,
    file: UploadFile = File(...),
    description: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Upload an image or video file as evidence for a dispute."""
    service = DisputeService(db)
    return await service.upload_evidence_file(
        dispute_id=dispute_id,
        file=file,
        description=description,
        user_id=current_user.id,
    )
