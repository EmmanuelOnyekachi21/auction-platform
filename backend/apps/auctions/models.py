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
    arbitrarily deep (e.g. Electronics → Phones → Android).

    Attributes:
        name: Unique human-readable category name.
        slug: Unique URL-safe identifier, indexed for fast lookup.
        parent_id: Optional FK to the parent Category. Null means root.

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
        condition: Physical condition of the item.
        status: Lifecycle state of the item.
        weight_kg: Optional weight in kilograms.
        dimensions: Optional dimensions string e.g. '30x20x10cm'.

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
        url: URL pointing to the stored image.
        display_order: Controls the order images are shown.
        is_primary: Whether this is the main display image.

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

    # Relationships
    item: Mapped["Item"] = relationship("Item", back_populates="images")


class Auction(BaseModel):
    """An auction listing created by a seller.

    Attributes:
        seller_id: FK to the User running the auction.
        highest_bid_id: FK to the current highest Bid, nullable.
        status: Current lifecycle state of the auction.
        title: Short descriptive title.
        description: Full auction description.
        reserve_price: Minimum acceptable price, nullable.
        bid_increment: Minimum amount each new bid must exceed the last.
        starts_at: Scheduled start timestamp.
        ends_at: Scheduled end timestamp.
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
        ForeignKey("bids.id"),
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
    bid_increment: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Relationships
    seller: Mapped["User"] = relationship("User", back_populates="auctions")
    highest_bid: Mapped["Bid"] = relationship("Bid", foreign_keys=[highest_bid_id])
    bids: Mapped[list["Bid"]] = relationship(
        "Bid",
        back_populates="auction",
        foreign_keys="Bid.auction_id",
    )
    auction_items: Mapped[list["AuctionItem"]] = relationship(
        "AuctionItem", back_populates="auction"
    )


class AuctionItem(BaseModel):
    """Junction table linking an Auction to its Items.

    Attributes:
        auction_id: FK to the Auction.
        item_id: FK to the Item.
        starting_price: Opening price for this item in the auction.
        quantity: Number of units available, defaults to 1.
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
