"""Order router — endpoints for order management."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.orders.enums import OrderStatus
from apps.orders.schemas import ShipOrderRequest
from apps.orders.service import OrderService
from apps.users.models import User
from common.dependency import get_current_active_user, get_db

router = APIRouter()


@router.get("/orders/{order_id}")
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get full order detail. Only buyer or seller can view."""
    service = OrderService(db)
    return await service.get_order(
        order_id=order_id, requesting_user_id=current_user.id
    )


@router.get("/users/me/orders")
async def get_my_orders(
    role: str = Query("buyer", description="buyer or seller"),
    status: Optional[OrderStatus] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get current user's orders as buyer or seller."""
    service = OrderService(db)
    return await service.get_my_orders(
        user_id=current_user.id,
        role=role,
        status=status,
        page=page,
        limit=limit,
    )


@router.patch("/orders/{order_id}/ship")
async def ship_order(
    order_id: UUID,
    data: ShipOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Seller marks order as shipped."""
    service = OrderService(db)
    return await service.ship_order(
        seller_id=current_user.id,
        order_id=order_id,
        data=data,
    )


@router.patch("/orders/{order_id}/confirm-delivery")
async def confirm_delivery(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Buyer confirms delivery — releases escrow to seller."""
    service = OrderService(db)
    return await service.confirm_delivery(
        buyer_id=current_user.id,
        order_id=order_id,
    )


@router.patch("/orders/{order_id}/cancel")
async def cancel_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Buyer cancels order after seller missed shipping deadline."""
    service = OrderService(db)
    return await service.cancel_order(
        buyer_id=current_user.id,
        order_id=order_id,
    )
