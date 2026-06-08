"""Pydantic schemas for auction-related API requests and responses."""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from apps.auctions.enums import AuctionStatus, ItemCondition, ItemStatus
from apps.users.schemas import PublicUserResponse
from common.sanitisation import sanitize_string
from config.settings import settings

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

    @field_validator("title", mode="after")
    @classmethod
    def sanitise_name(cls, v: str) -> str:
        """Sanitise title to prevent XSS injection."""
        return sanitize_string(v, max_length=100)

    @field_validator("description", mode="after")
    @classmethod
    def sanitise_description(cls, v: str) -> str:
        """Sanitise description to prevent XSS injection."""
        return sanitize_string(v, max_length=1000)  # Description limit


class UpdateItemRequest(BaseModel):
    """Request schema for updating an existing auction item."""

    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=20, max_length=5000)
    condition: Optional[ItemCondition] = None
    category_id: Optional[uuid.UUID] = None
    weight_kg: Optional[Decimal] = Field(None, ge=0)
    dimensions: Optional[str] = Field(None, max_length=100)

    @field_validator("title", mode="after")
    @classmethod
    def sanitise_name(cls, v: str) -> str:
        """Sanitise title to prevent XSS injection."""
        return sanitize_string(v, max_length=100)

    @field_validator("description", mode="after")
    @classmethod
    def sanitise_description(cls, v: str) -> str:
        """Sanitise description to prevent XSS injection."""
        return sanitize_string(v, max_length=1000)  # Description limit


# --- Auction Request Schemas ---


class CreateAuctionRequest(BaseModel):
    """Request schema for creating a new auction."""

    starts_at: datetime
    ends_at: datetime
    reserve_price: Optional[Decimal] = Field(None, ge=0)

    @model_validator(mode="after")
    def validate_auction_times(self) -> "CreateAuctionRequest":
        """Validate auction start and end times.

        Raises:
            ValueError: If times are invalid

        """
        now = datetime.now(timezone.utc)
        if self.starts_at < now:
            raise ValueError("Time for auction to begin must be in the future")
        if self.ends_at < self.starts_at + timedelta(
            # hours=settings.min_auction_duration_hours
            minutes=5
        ):
            raise ValueError(
                f"Auction must last at least "
                f"{settings.min_auction_duration_hours} hour(s)"
            )
        if self.ends_at > self.starts_at + timedelta(
            hours=settings.max_auction_duration_hours
        ):
            raise ValueError(
                f"Auction duration cannot exceed "
                f"{settings.max_auction_duration_hours} hours"
            )
        return self


class UpdateAuctionRequest(BaseModel):
    """Request schema for updating an existing auction."""

    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    reserve_price: Optional[Decimal] = Field(None, ge=0)

    @model_validator(mode="after")
    def validate_update_times(self) -> "UpdateAuctionRequest":
        """Validate duration constraints when both times are provided.

        Raises:
            ValueError: If the duration exceeds the maximum or is below minimum.

        """
        if self.starts_at and self.ends_at:
            if self.ends_at > self.starts_at + timedelta(
                hours=settings.max_auction_duration_hours
            ):
                raise ValueError(
                    f"Auction duration cannot exceed "
                    f"{settings.max_auction_duration_hours} hours"
                )
            if self.ends_at < self.starts_at + timedelta(
                # hours=settings.min_auction_duration_hours
                minutes=5
            ):
                raise ValueError(
                    f"Auction must last at least "
                    f"{settings.min_auction_duration_hours} hour(s)"
                )
        return self


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
    # reserve_price is intentionally excluded from API output to prevent
    # buyers from seeing the exact threshold. Use reserve_progress_percent
    # and reserve_price_met instead.
    reserve_price: Optional[Decimal] = Field(None, exclude=True)
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
    def reserve_price_met(self) -> Optional[bool]:
        """Check if reserve price has been met by highest bid."""
        if self.reserve_price is None:
            return None  # No reserve means always met
        if self.highest_bid is None:
            return False  # No bids yet
        return self.highest_bid.amount >= self.reserve_price

    @computed_field
    @property
    def reserve_progress_percent(self) -> Optional[int]:
        """Percentage progress toward reserve price.

        Returns:
            None if no reserve is set.
            0 if reserve is set but no bids yet.
            Integer 0-100 representing how close the highest bid is to reserve.
            Capped at 100 once reserve is met or exceeded.

        """
        if self.reserve_price is None:
            return None
        if self.highest_bid is None:
            return 0
        pct = int((self.highest_bid.amount / self.reserve_price) * 100)
        return min(pct, 100)


class AdminAuctionResponse(AuctionResponse):
    """AuctionResponse variant for admin endpoints.

    Identical to AuctionResponse but exposes reserve_price in plain text.
    Buyers never hit admin endpoints so hiding the reserve is unnecessary.
    """

    # Override the parent field — same type, no exclude
    reserve_price: Optional[Decimal] = Field(None)


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
