"""ORM models for the orders application."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import BaseModel

from .enums import OrderStatus

if TYPE_CHECKING:
    from apps.auctions.models import Auction, AuctionItem
    from apps.disputes.models import Dispute
    from apps.users.models import User


class Order(BaseModel):
    """Represents a completed auction purchase between buyer and seller.

    Attributes:
        auction_id: FK to the Auction this order originated from.
        auction_item_id: FK to the specific AuctionItem sold.
        buyer_id: FK to the User who won the auction.
        seller_id: FK to the User who listed the item.
        dispute_id: FK to the associated Dispute record, nullable.
        amount: Final sale amount.
        status: Current lifecycle state of the order.
        shipping_deadline_at: Deadline by which seller must ship.
        shipped_at: Timestamp when seller marked as shipped.
        delivered_at: Timestamp when buyer confirmed delivery.
        dispute_raised_at: Timestamp when a dispute was opened.

    """

    __tablename__ = "orders"
    __table_args__ = (
        Index(
            "ix_orders_shipping_deadline",
            "shipping_deadline_at",
            postgresql_where=text("status = 'PENDING_SHIPMENT'"),
        ),
    )

    auction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auctions.id"), nullable=False, index=True
    )
    auction_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auction_items.id"), nullable=False
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    dispute_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("disputes.id", use_alter=True, name="fk_order_dispute_id"),
        nullable=True,
        unique=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        nullable=False, default=OrderStatus.PENDING_SHIPMENT, index=True
    )
    shipping_deadline_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    shipped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dispute_raised_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    buyer: Mapped[User] = relationship("User", foreign_keys=[buyer_id])
    seller: Mapped[User] = relationship("User", foreign_keys=[seller_id])
    auction: Mapped[Auction] = relationship("Auction")
    auction_item: Mapped[AuctionItem] = relationship("AuctionItem")
    dispute: Mapped[Dispute] = relationship("Dispute", foreign_keys=[dispute_id])
