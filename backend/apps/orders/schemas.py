"""Pydantic schemas for order-related API requests and responses."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from apps.auctions.enums import AuctionStatus, ItemCondition
from apps.disputes.schemas import DisputeSummary
from apps.escrow.schemas import EscrowResponse
from apps.orders.enums import OrderStatus
from apps.users.schemas import PublicUserResponse


class AuctionSummary(BaseModel):
    """Minimal auction context shown on an order."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: AuctionStatus
    ends_at: datetime


class ItemSummary(BaseModel):
    """Minimal item info shown on an order card."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    condition: ItemCondition  # ItemCondition not ItemStatus
    primary_image_url: Optional[str] = None  # computed by service, not on model


class OrderSummaryResponse(BaseModel):
    """Lightweight order response for list pages."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: OrderStatus
    amount: Decimal
    commission_amount: Optional[Decimal] = None
    seller_payout: Optional[Decimal] = None
    created_at: datetime
    auction: Optional[AuctionSummary] = None
    item: Optional[ItemSummary] = None
    buyer: Optional[PublicUserResponse] = None
    seller: Optional[PublicUserResponse] = None


class OrderDetailResponse(BaseModel):
    """Full order response for detail page."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: OrderStatus
    amount: Decimal
    created_at: datetime
    auction: Optional[AuctionSummary] = None
    item: Optional[ItemSummary] = (
        None  # populated manually by service from auction_item.item
    )
    buyer: Optional[PublicUserResponse] = None
    seller: Optional[PublicUserResponse] = None
    escrow: Optional[EscrowResponse] = None
    dispute: Optional[DisputeSummary] = None
    shipping_deadline_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    dispute_raised_at: Optional[datetime] = None
    tracking_number: Optional[str] = None

    @computed_field
    @property
    def commission_amount(self) -> Decimal:
        """Commission taken by platform — lives on escrow, not order."""
        if self.escrow and self.escrow.commission_amount is not None:
            return self.escrow.commission_amount
        return Decimal("0")

    @computed_field
    @property
    def seller_payout(self) -> Decimal:
        """What seller receives after commission deducted."""
        if self.escrow and self.escrow.commission_amount is not None:
            return self.amount - self.escrow.commission_amount
        return self.amount


class ShipOrderRequest(BaseModel):
    """Request body for marking an order as shipped."""

    tracking_number: Optional[str] = Field(None, max_length=100)
