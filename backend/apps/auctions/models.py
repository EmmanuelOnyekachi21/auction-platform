"""ORM models for the auctions application.

Defines Category, Item, and ItemImage models.
Auction and AuctionItem models are added in a later task.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import BaseModel

from .enums import AuctionStatus, ItemCondition, ItemStatus

if TYPE_CHECKING:
    from apps.bids.models import Bid
    from apps.users.models import User


class Category(BaseModel):
    """Product category with optional self-referencing parent.

    Supports a tree structure where categories can be nested
    arbitrarily deep (e.g. Electronics -> Phones -> Android).

    Attributes:
        name: Unique human-readable category name.
        slug: Unique URL-safe identifier, indexed for fast lookup.
        parent_id: Optional UUID FK to the parent Category. Null means root.
        parent: Relationship to the parent Category instance.
        children: Relationship to a list of sub-categories.
        items: Relationship to the items belonging to this category.

    """

    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    parent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id"),
        nullable=True,
    )

    # Self-referencing relationships
    parent: Mapped["Category"] = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="children",
    )
    children: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="parent",
    )
    items: Mapped[list["Item"]] = relationship("Item", back_populates="category")


class Item(BaseModel):
    """A physical item listed by a seller for auction.

    Attributes:
        seller_id: FK to the User who owns this item.
        category_id: FK to the Category this item belongs to.
        title: Short descriptive title.
        description: Full item description.
        condition: Physical condition (NEW, USED, etc.).
        status: Lifecycle state (DRAFT, LISTED, SOLD, etc.).
        weight_kg: Weight in kilograms for shipping calculation.
        dimensions: Dimensions string (e.g., '30x20x10cm').
        seller: Relationship to the owning User.
        category: Relationship to the assigned Category.
        images: Relationship to the list of associated images.
        auction_items: Relationship to the junction entries connecting to auctions.

    """

    __tablename__ = "items"

    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    condition: Mapped[ItemCondition] = mapped_column(nullable=False)
    status: Mapped[ItemStatus] = mapped_column(
        nullable=False,
        default=ItemStatus.DRAFT,
        index=True,
    )
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=True)
    dimensions: Mapped[str] = mapped_column(String(100), nullable=True)

    # Relationships
    seller: Mapped["User"] = relationship("User", back_populates="items")
    category: Mapped["Category"] = relationship("Category", back_populates="items")
    images: Mapped[list["ItemImage"]] = relationship("ItemImage", back_populates="item")
    auction_items: Mapped[list["AuctionItem"]] = relationship(
        "AuctionItem", back_populates="item"
    )


class ItemImage(BaseModel):
    """An image associated with an Item.

    Attributes:
        item_id: FK to the owning Item.
        url: URL pointing to the stored image (e.g., S3 URL).
        display_order: Controls the sequence images appear in (ascending).
        is_primary: Whether this is the thumbnail/main image.
        item: Relationship back to the Item.

    """

    __tablename__ = "item_images"

    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("items.id"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    public_id: Mapped[str] = mapped_column(String(255), nullable=True)

    # Relationships
    item: Mapped["Item"] = relationship("Item", back_populates="images")


class Auction(BaseModel):
    """An auction listing created by a seller.

    Attributes:
        seller_id: FK to the User running the auction.
        highest_bid_id: FK to the current highest Bid, nullable.
        status: Lifecycle state (DRAFT, ACTIVE, COMPLETED, etc.).
        title: Short descriptive title.
        description: Detailed auction description.
        reserve_price: Minimum price required for a sale.
        starts_at: Starting timestamp (UTC).
        ends_at: Ending timestamp (UTC).
        seller: Relationship to the host User.
        highest_bid: Relationship to the current winning Bid instance.
        bids: Relationship to all Bids made on this auction.
        auction_items: Relationship to the junction table linking items.

    """

    __tablename__ = "auctions"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="check_ends_after_starts"),
        CheckConstraint("reserve_price >= 0", name="check_reserve_price_non_negative"),
        Index("ix_auctions_status_ends_at", "status", "ends_at"),
    )

    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    highest_bid_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bids.id", use_alter=True, name="fk_auction_highest_bud_id"),
        nullable=True,
    )
    status: Mapped[AuctionStatus] = mapped_column(
        nullable=False,
        default=AuctionStatus.DRAFT,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    reserve_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Relationships
    seller: Mapped["User"] = relationship("User", back_populates="auctions")
    highest_bid: Mapped["Bid"] = relationship(
        "Bid", foreign_keys=[highest_bid_id], post_update=True
    )
    bids: Mapped[list["Bid"]] = relationship(
        "Bid",
        back_populates="auction",
        foreign_keys="Bid.auction_id",
    )
    auction_items: Mapped[list["AuctionItem"]] = relationship(
        "AuctionItem", back_populates="auction"
    )


class AuctionItem(BaseModel):
    """Junction table linking an Auction to its constituent Items.

    Enables multi-item auctions (lots) where a single auction listing
    can contain multiple physical items.

    Attributes:
        auction_id: FK to the Auction.
        item_id: FK to the Item.
        starting_price: Opening price for this specific item.
        quantity: Number of units available in this lot.
        auction: Relationship back to the Auction.
        item: Relationship back to the Item.

    """

    __tablename__ = "auction_items"
    __table_args__ = (
        UniqueConstraint("auction_id", "item_id", name="uq_auction_item"),
        CheckConstraint("quantity > 0", name="check_quantity_positive"),
        CheckConstraint(
            "starting_price >= 0", name="check_starting_price_non_negative"
        ),
    )

    auction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auctions.id"),
        nullable=False,
        index=True,
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("items.id"),
        nullable=False,
        index=True,
    )
    starting_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    auction: Mapped["Auction"] = relationship("Auction", back_populates="auction_items")
    item: Mapped["Item"] = relationship("Item", back_populates="auction_items")


class BidIncrementTier(BaseModel):
    """Platform-controlled bid increment tiers based on current bid amount.

    Attributes:
        min_value: Lower bound of the price range (inclusive).
        max_value: Upper bound of the price range. NULL means no upper limit.
        increment: Minimum amount each new bid must exceed the current highest.
        is_active: Whether this tier is currently in use.

    """

    __tablename__ = "bid_increment_tiers"
    __table_args__ = (
        CheckConstraint("min_value >= 0", name="ck_bid_tier_min_value_non_negative"),
        CheckConstraint("increment > 0", name="ck_bid_tier_increment_positive"),
    )

    min_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    max_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    increment: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
