"""ORM models for the bids application."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import BaseModel

from .enums import BidStatus

if TYPE_CHECKING:
    from apps.auctions.models import Auction
    from apps.users.models import User
    from apps.wallet.models import WalletTransactions


class Bid(BaseModel):
    """A single bid placed by a user on an auction.

    Attributes:
        auction_id: FK to the Auction being bid on.
        bidder_id: FK to the User placing the bid.
        amount: Bid amount, must be greater than zero.
        status: Current lifecycle state of the bid.
        wallet_transaction_id: FK to the WalletTransaction that locked funds.
        placed_at: Timestamp when the bid was placed.
    """

    __tablename__ = "bids"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_bid_amount"),)

    auction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auctions.id"),
        nullable=False,
        index=True,
    )
    bidder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[BidStatus] = mapped_column(
        nullable=False,
        default=BidStatus.ACTIVE,
    )
    wallet_transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wallet_transactions.id"),
        nullable=True,
    )
    placed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    auction: Mapped["Auction"] = relationship("Auction", back_populates="bids")
    bidder: Mapped["User"] = relationship("User", back_populates="bids")
    wallet_transaction: Mapped["WalletTransactions"] = relationship(
        "WalletTransactions"
    )
