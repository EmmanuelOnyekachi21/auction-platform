"""Data access layer for bid database operations."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.bids.enums import BidStatus
from apps.bids.models import Bid
from common.pagination import PaginatedResponse, paginate


class BidRepository:
    """Repository for all bid-related database operations.

    Encapsulates SQLAlchemy queries for ``Bid`` records.  All methods
    flush but do not commit — the caller owns the transaction boundary.

    Attributes:
        _db: The active ``AsyncSession`` injected at construction time.

    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialise the repository with an async database session.

        Args:
            db: An active ``AsyncSession`` to use for all queries.

        """
        self._db = db

    async def create(self, auction_id: UUID, bidder_id: UUID, amount: Decimal) -> Bid:
        """Create a new bid record.

        Does not move wallet funds — that is the service's responsibility.
        Uses ``flush()`` rather than ``commit()`` so the caller controls
        the transaction boundary.

        Args:
            auction_id: UUID of the auction being bid on.
            bidder_id: UUID of the user placing the bid.
            amount: Bid amount.

        Returns:
            The newly created ``Bid`` instance with a populated ``id``.

        """
        new_bid = Bid(
            auction_id=auction_id,
            bidder_id=bidder_id,
            amount=amount,
            status=BidStatus.ACTIVE,
            wallet_transaction_id=None,
        )
        self._db.add(new_bid)
        await self._db.flush()
        return new_bid

    async def get_by_id(self, bid_id: UUID) -> Bid | None:
        """Fetch a bid by its UUID primary key.

        Args:
            bid_id: UUID of the bid to retrieve.

        Returns:
            The matching ``Bid`` instance, or ``None`` if not found.

        """
        stmt = select(Bid).where(Bid.id == bid_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_highest_bid(self, auction_id: UUID) -> Bid | None:
        """Return the current highest active or winning bid for an auction.

        Args:
            auction_id: UUID of the auction.

        Returns:
            The highest ``Bid`` instance, or ``None`` if no bids exist.

        """
        stmt = (
            select(Bid)
            .where(Bid.auction_id == auction_id)
            .where(Bid.status.in_([BidStatus.ACTIVE, BidStatus.WON]))
            .order_by(Bid.amount.desc(), Bid.placed_at.asc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        return result.scalars().first()

    async def get_user_bid_on_auction(
        self, auction_id: UUID, user_id: UUID
    ) -> Bid | None:
        """Return the most recent active or outbid bid by a user on an auction.

        Args:
            auction_id: UUID of the auction.
            user_id: UUID of the bidding user.

        Returns:
            The most recent matching ``Bid``, or ``None`` if not found.

        """
        stmt = (
            select(Bid)
            .where(Bid.auction_id == auction_id)
            .where(Bid.bidder_id == user_id)
            .where(Bid.status.in_([BidStatus.ACTIVE, BidStatus.OUTBID]))
            .order_by(Bid.placed_at.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        return result.scalars().first()

    async def get_auction_bids(
        self, auction_id: UUID, page: int, limit: int
    ) -> PaginatedResponse:
        """Return paginated bids for an auction, ordered by amount descending.

        Args:
            auction_id: UUID of the auction.
            page: Page number (1-indexed).
            limit: Maximum number of bids per page.

        Returns:
            A ``PaginatedResponse`` containing the bid records.

        """
        stmt = (
            select(Bid)
            .where(Bid.auction_id == auction_id)
            .order_by(Bid.amount.desc(), Bid.placed_at.asc())
        )
        return await paginate(stmt, page, limit, self._db)

    async def get_user_bid_history(
        self,
        user_id: UUID,
        status: BidStatus | None,
        page: int,
        limit: int,
    ) -> PaginatedResponse:
        """Return paginated bid history for a user, newest first.

        Args:
            user_id: UUID of the user.
            status: Optional status filter.
            page: Page number (1-indexed).
            limit: Maximum number of bids per page.

        Returns:
            A ``PaginatedResponse`` containing the bid records with
            their associated auction loaded.

        """
        stmt = (
            select(Bid)
            .where(Bid.bidder_id == user_id)
            .options(selectinload(Bid.auction))
            .order_by(Bid.placed_at.desc())
        )
        if status:
            stmt = stmt.where(Bid.status == status)
        return await paginate(stmt, page, limit, self._db)

    async def update_status(self, bid_id: UUID, status: BidStatus) -> Bid | None:
        """Update the status of a bid.

        Args:
            bid_id: UUID of the bid to update.
            status: The new ``BidStatus`` value.

        Returns:
            The updated ``Bid`` instance, or ``None`` if not found.

        """
        bid = await self.get_by_id(bid_id)
        if bid:
            bid.status = status
            await self._db.flush()
        return bid

    async def link_wallet_transaction(
        self, bid_id: UUID, wallet_transaction_id: UUID
    ) -> Bid | None:
        """Associate a wallet transaction with a bid.

        Args:
            bid_id: UUID of the bid.
            wallet_transaction_id: UUID of the wallet transaction that
                locked funds for this bid.

        Returns:
            The updated ``Bid`` instance, or ``None`` if not found.

        """
        bid = await self.get_by_id(bid_id)
        if bid:
            bid.wallet_transaction_id = wallet_transaction_id
            await self._db.flush()
        return bid

    async def get_active_bids_except(
        self, exclude_bid_id: UUID, auction_id: UUID
    ) -> list[Bid]:
        """Return all active bids on an auction excluding one specific bid.

        Used when a new highest bid is placed to identify the previously
        active bids that should be marked as ``OUTBID``.

        Args:
            exclude_bid_id: UUID of the bid to exclude from results.
            auction_id: UUID of the auction.

        Returns:
            A list of active ``Bid`` instances, excluding the specified bid.

        """
        stmt = (
            select(Bid)
            .where(Bid.id != exclude_bid_id)
            .where(Bid.auction_id == auction_id)
            .where(Bid.status == BidStatus.ACTIVE)
        )
        result = await self._db.execute(stmt)
        return result.scalars().all()
