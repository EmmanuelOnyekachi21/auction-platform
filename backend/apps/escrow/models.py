"""ORM models for the escrow application."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import BaseModel

from .enums import EscrowStatus

if TYPE_CHECKING:
    from apps.orders.models import Order
    from apps.users.models import User


class Escrow(BaseModel):
    """Holds funds between auction win and order completion.

    Funds are locked here until the buyer confirms delivery or
    a dispute is resolved. Protects both buyer and seller.

    Attributes:
        order_id: FK to the associated Order, unique one-to-one.
        auction_id: FK to the originating Auction.
        winner_id: FK to the User who won the auction.
        seller_id: FK to the User who listed the item.
        amount: Total amount held in escrow.
        commission_amount: Platform commission deducted on release.
        status: Current state of the escrow.
        auto_release_at: Timestamp when funds auto-release if no dispute.
        released_at: Timestamp when funds were released to seller.
        refunded_at: Timestamp when funds were refunded to buyer.
    """

    __tablename__ = "escrows"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_escrow_amount"),)

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, unique=True
    )
    auction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auctions.id"), nullable=False
    )
    winner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    status: Mapped[EscrowStatus] = mapped_column(
        nullable=False, default=EscrowStatus.HOLDING
    )
    auto_release_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    released_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    refunded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    order: Mapped[Order] = relationship("Order", back_populates="escrow")
    winner: Mapped[User] = relationship("User", foreign_keys=[winner_id])
    seller: Mapped[User] = relationship("User", foreign_keys=[seller_id])
