"""Pydantic schemas for auction-related API requests and responses."""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from apps.auctions.enums import AuctionStatus, ItemCondition, ItemStatus
from apps.users.schemas import PublicUserResponse

# --- Shared / Nested Helper Schemas ---


class CategoryResponse(BaseModel):
    """Response schema for category data."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    slug: str
    parent_id: Optional[uuid.UUID] = None


class ItemImageResponse(BaseModel):
    """Response schema for item image data."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    url: str
    display_order: int
    is_primary: bool


class BidSummary(BaseModel):
    """Summary of a bid for nested responses."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    bidder_id: uuid.UUID
    amount: Decimal
    created_at: datetime


# --- Item Request Schemas ---


class CreateItemRequest(BaseModel):
    """Request schema for creating a new auction item."""

    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=20, max_length=5000)
    condition: ItemCondition
    category_id: uuid.UUID
    weight_kg: Optional[Decimal] = Field(None, ge=0)
    dimensions: Optional[str] = Field(None, max_length=100)


class UpdateItemRequest(BaseModel):
    """Request schema for updating an existing auction item."""

    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=20, max_length=5000)
    condition: Optional[ItemCondition] = None
    category_id: Optional[uuid.UUID] = None
    weight_kg: Optional[Decimal] = Field(None, ge=0)
    dimensions: Optional[str] = Field(None, max_length=100)


# --- Auction Request Schemas ---


class CreateAuctionRequest(BaseModel):
    """Request schema for creating a new auction."""

    starts_at: datetime
    ends_at: datetime
    bid_increment: Decimal = Field(Decimal("100.00"), ge=100.00)
    reserve_price: Optional[Decimal] = Field(None, ge=0)

    @model_validator(mode="after")
    def validate_auction_times(self) -> "CreateAuctionRequest":
        """Validate auction start and end times.

        Raises:
            ValueError: If times are invalid

        """
        now = datetime.now(timezone.utc)
        if self.starts_at < now:
            raise ValueError("Starts_at must be in the future")
        if self.ends_at < self.starts_at + timedelta(minutes=5):
            raise ValueError("Auction must last at least 5 minutes")
        if self.ends_at > self.starts_at + timedelta(days=30):
            raise ValueError("Auction cannot last longer than 30 days")
        return self


class UpdateAuctionRequest(BaseModel):
    """Request schema for updating an existing auction."""

    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    bid_increment: Optional[Decimal] = Field(None, ge=100.00)
    reserve_price: Optional[Decimal] = Field(None, ge=0)


class AttachItemRequest(BaseModel):
    """Request schema for attaching an item to an auction."""

    item_id: uuid.UUID
    starting_price: Decimal = Field(..., ge=0)
    quantity: int = Field(default=1, ge=1)


class PublishAuctionRequest(BaseModel):
    """Empty body - action is implicit by endpoint."""

    pass


# --- Response Schemas ---


class ItemResponse(BaseModel):
    """Response schema for auction item details."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    description: str
    condition: ItemCondition
    status: ItemStatus
    category: CategoryResponse
    images: List[ItemImageResponse] | None = None
    # seller: PublicUserResponse
    weight_kg: Optional[Decimal] = None
    dimensions: Optional[str] = None
    created_at: datetime


class AuctionItemResponse(BaseModel):
    """Response schema for item attached to an auction."""

    model_config = ConfigDict(from_attributes=True)
    item: ItemResponse
    starting_price: Decimal
    quantity: int


class AuctionResponse(BaseModel):
    """Response schema for detailed auction information."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: uuid.UUID
    title: Optional[str] = None
    description: Optional[str] = None
    status: AuctionStatus
    starts_at: datetime
    ends_at: datetime
    bid_increment: Decimal
    reserve_price: Optional[Decimal] = None
    created_at: datetime

    # ORM attribute is auction_items, but we expose it as items in the API
    items: List[AuctionItemResponse] = Field(
        default_factory=list, validation_alias="auction_items"
    )
    seller: PublicUserResponse
    highest_bid: Optional[BidSummary] = None

    # Load bids from ORM to count them — excluded from API output
    bids: List[Any] = Field(default_factory=list, exclude=True)

    # Counters
    viewer_count: int = 0

    @computed_field
    @property
    def bid_count(self) -> int:
        """Count bids from loaded relationship."""
        return len(self.bids) if self.bids else 0

    @computed_field
    @property
    def time_remaining_seconds(self) -> int:
        """Calculate seconds remaining until auction ends."""
        now = datetime.now(timezone.utc)
        delta = self.ends_at - now
        return max(0, int(delta.total_seconds()))

    @computed_field
    @property
    def reserve_price_met(self) -> bool:
        """Check if reserve price has been met by highest bid."""
        if self.reserve_price is None:
            return True  # No reserve means always met
        if self.highest_bid is None:
            return False  # No bids yet
        return self.highest_bid.amount >= self.reserve_price


class AuctionListResponse(BaseModel):
    """Response schema for auction list items (summary view)."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    status: AuctionStatus
    ends_at: datetime
    bid_count: int
    current_highest_bid: Optional[Decimal] = None
    primary_image_url: Optional[str] = None
    condition: ItemCondition
    category: str  # Category name for quick display

    @computed_field
    @property
    def time_remaining_seconds(self) -> int:
        """Calculate seconds remaining until auction ends."""
        now = datetime.now(timezone.utc)
        delta = self.ends_at - now
        return max(0, int(delta.total_seconds()))


class RejectItemRequest(BaseModel):
    """Request schema for rejecting an item."""

    reason: str = Field(
        ..., min_length=10, max_length=500, description="Reason for rejection"
    )
