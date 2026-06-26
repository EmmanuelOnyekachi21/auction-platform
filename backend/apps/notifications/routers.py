"""Router for in-app notification endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.models import User
from common.dependency import get_current_active_user, get_db
from common.schemas import PaginatedResponse

from .schemas import NotificationResponse, UnreadCountResponse
from .service import NotificationService

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def get_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get paginated notifications for the current user."""
    service = NotificationService(db)
    result = await service.get_notifications(current_user.id, page, limit, unread_only)
    result.data = [NotificationResponse.model_validate(n) for n in result.data]
    return result


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get count of unread notifications for the current user."""
    service = NotificationService(db)
    count = await service.get_unread_count(current_user.id)
    return UnreadCountResponse(count=count)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark a single notification as read."""
    service = NotificationService(db)
    notification = await service.mark_read(notification_id, current_user.id)
    return NotificationResponse.model_validate(notification)


@router.patch("/read-all", status_code=204, response_class=Response)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark all notifications as read for the current user."""
    service = NotificationService(db)
    await service.mark_all_read(current_user.id)
