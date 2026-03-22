"""ORM models for the disputes application."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import BaseModel

from .enums import DisputeStatus, EvidenceFileType

if TYPE_CHECKING:
    from apps.orders.models import Order
    from apps.users.models import User


class Dispute(BaseModel):
    """A formal dispute raised by a buyer or seller over an order.

    Attributes:
        order_id: FK to the disputed Order.
        auction_id: FK to the originating Auction.
        raised_by_id: FK to the User who raised the dispute.
        against_id: FK to the User the dispute is against.
        title: Short summary of the dispute.
        description: Full description of the issue.
        status: Current state of the dispute.
        resolution: Admin resolution notes, nullable.
        resolved_by_id: FK to the admin User who resolved it.
        resolved_at: Timestamp when the dispute was resolved.

    """

    __tablename__ = "disputes"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True
    )
    auction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auctions.id"), nullable=False
    )
    raised_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    against_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DisputeStatus] = mapped_column(
        nullable=False, default=DisputeStatus.OPEN
    )
    resolution: Mapped[str] = mapped_column(Text, nullable=True)
    resolved_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    resolved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    order: Mapped[Order] = relationship("Order", foreign_keys=[order_id])
    raised_by: Mapped[User] = relationship("User", foreign_keys=[raised_by_id])
    against: Mapped[User] = relationship("User", foreign_keys=[against_id])
    resolved_by: Mapped[User] = relationship("User", foreign_keys=[resolved_by_id])
    evidence: Mapped[list[DisputeEvidence]] = relationship(
        "DisputeEvidence", back_populates="dispute"
    )


class DisputeEvidence(BaseModel):
    """Immutable evidence record submitted for a dispute.

    Once submitted, evidence cannot be modified — only new
    evidence can be added.

    Attributes:
        dispute_id: FK to the parent Dispute.
        uploaded_by_id: FK to the User who submitted the evidence.
        url: URL to the stored file.
        file_type: Type of file submitted.
        description: Optional description of the evidence.

    """

    __tablename__ = "dispute_evidence"

    updated_at = None  # immutable record

    dispute_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("disputes.id"), nullable=False, index=True
    )
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[EvidenceFileType] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)

    # Relationships
    dispute: Mapped[Dispute] = relationship("Dispute", back_populates="evidence")
    uploaded_by: Mapped[User] = relationship("User", foreign_keys=[uploaded_by_id])
