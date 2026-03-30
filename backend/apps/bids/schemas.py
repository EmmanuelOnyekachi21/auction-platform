"""Pydantic schemas for bid-related API requests and responses."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PlaceBidRequest(BaseModel):
    """Request schema for placing a bid on an auction.

    Attributes:
        amount: The bid amount, must be greater than zero with up to
            2 decimal places.

    """

    amount: Decimal = Field(..., gt=0, decimal_places=2)


class BidResponse(BaseModel):
    """Response schema for a single bid.

    Attributes:
        id: Bid UUID.
        auction_id: UUID of the auction this bid belongs to.
        amount: Bid amount.
        status: Current bid status string.
        placed_at: Timezone-aware timestamp when the bid was placed.
        is_highest: Whether this bid is currently the highest on the auction.

    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    auction_id: uuid.UUID
    amount: Decimal
    status: str
    placed_at: datetime
    is_highest: bool = False


class AuctionSummary(BaseModel):
    """Minimal auction info nested inside ``BidHistoryResponse``.

    Attributes:
        id: Auction UUID.
        status: Current auction status string.
        ends_at: Timezone-aware timestamp when the auction ends.

    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    ends_at: datetime


class BidHistoryResponse(BaseModel):
    """Response schema for a bid in a user's bid history.

    Attributes:
        id: Bid UUID.
        amount: Bid amount.
        placed_at: Timezone-aware timestamp when the bid was placed.
        status: Current bid status string.
        auction: Minimal auction summary for context.

    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: Decimal
    placed_at: datetime
    status: str
    auction: AuctionSummary


class AuctionBidState(BaseModel):
    """Current bidding state of an auction, polled by the frontend.

    Returned by the bid-state endpoint which the frontend polls every
    few seconds to keep the auction UI up to date without a WebSocket.

    Attributes:
        auction_id: UUID of the auction.
        highest_bid_amount: Current highest bid, or ``None`` if no bids yet.
        minimum_next_bid: Minimum amount required for the next valid bid.
        bid_count: Total number of bids placed on this auction.
        user_current_bid: The authenticated user's current bid, if any.

    """

    model_config = ConfigDict(from_attributes=True)

    auction_id: uuid.UUID
    highest_bid_amount: Optional[Decimal] = None
    minimum_next_bid: Decimal
    bid_count: int
    user_current_bid: Optional[BidResponse] = None
