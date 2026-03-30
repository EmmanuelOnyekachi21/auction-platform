"""Bid router — endpoints for placing and viewing bids."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bids.enums import BidStatus
from apps.bids.schemas import PlaceBidRequest
from apps.bids.service import BidService
from apps.users.models import User
from common.dependency import get_current_active_user, get_db
from common.schemas import SuccessResponse

router = APIRouter()


@router.post("/auctions/{auction_id}/bids", status_code=201)
async def place_bid(
    auction_id: UUID,
    data: PlaceBidRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Place a bid on an active auction.

    Atomically locks the bid amount from the user's available wallet
    balance and refunds the previously outbid user in the same
    transaction.

    Args:
        auction_id: UUID of the auction to bid on.
        data: Validated bid request containing the amount.
        db: Injected async database session.
        current_user: The authenticated user placing the bid.

    Returns:
        A ``SuccessResponse`` containing the new bid and updated
        auction bid state.

    """
    service = BidService(db)
    bid = await service.place_bid(
        auction_id=auction_id,
        bidder_id=current_user.id,
        data=data,
    )
    auction_state = await service.get_auction_bid_state(
        auction_id=auction_id,
        user_id=current_user.id,
    )
    return SuccessResponse(
        message="Bid placed successfully",
        data={
            "bid": bid.model_dump(),
            "auction_state": auction_state.model_dump(),
        },
    )


@router.get("/auctions/{auction_id}/bids")
async def get_auction_bids(
    auction_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Return anonymised paginated bid history for an auction.

    Bidder identity is not exposed. No authentication required.

    Args:
        auction_id: UUID of the auction.
        page: Page number (default 1).
        limit: Items per page (default 20, max 100).
        db: Injected async database session.

    Returns:
        A paginated list of ``BidResponse`` objects.

    """
    service = BidService(db)
    return await service.get_auction_bids(auction_id, page, limit)


@router.get("/auctions/{auction_id}/bid-state")
async def get_bid_state(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return the current bidding state of an auction.

    Intended to be polled by the frontend every few seconds to keep
    the auction UI up to date. No authentication required.

    Args:
        auction_id: UUID of the auction.
        db: Injected async database session.

    Returns:
        An ``AuctionBidState`` with highest bid, minimum next bid,
        and total bid count.

    """
    service = BidService(db)
    return await service.get_auction_bid_state(
        auction_id=auction_id,
        user_id=None,
    )


@router.get("/users/me/bids")
async def get_my_bids(
    status: Optional[BidStatus] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return the authenticated user's paginated bid history.

    Args:
        status: Optional filter by ``BidStatus``.
        page: Page number (default 1).
        limit: Items per page (default 20, max 100).
        db: Injected async database session.
        current_user: The authenticated user.

    Returns:
        A paginated list of ``BidHistoryResponse`` objects.

    """
    service = BidService(db)
    return await service.get_my_bids(
        user_id=current_user.id,
        status=status,
        page=page,
        limit=limit,
    )
