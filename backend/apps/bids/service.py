"""Bid service — handles bid placement with atomic wallet locking."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auctions.enums import AuctionStatus
from apps.auctions.repository import AuctionRepository
from apps.bids.enums import BidStatus
from apps.bids.models import Bid
from apps.bids.repository import BidRepository
from apps.bids.schemas import (
    AuctionBidState,
    AuctionSummary,
    BidHistoryResponse,
    BidResponse,
)
from apps.notifications.tasks import notify_outbid_user
from apps.users.kyc_service import KYCService
from apps.users.repository import UserRepository
from apps.wallet.enums import (
    BalanceType,
    ReferenceType,
    TransactionDirection,
    TransactionType,
)
from apps.wallet.repository import WalletRepository
from common.exceptions import (
    AlreadyHighestBidderException,
    AuctionEndedException,
    AuctionNotActiveException,
    AuctionNotFoundException,
    InsufficientFundsException,
    InvalidBidAmountException,
    SellerCannotBidException,
    ValidationException,
)


class BidService:
    """Service layer for bid placement and bid history operations.

    Orchestrates the atomic bid-placement flow: validation, wallet fund
    locking, bid record creation, outbid refund, and post-transaction
    notifications.

    Attributes:
        _db: The active ``AsyncSession`` shared across all repositories.
        _auction_repo: Repository for auction queries.
        _wallet_repo: Repository for wallet balance operations.
        _bid_repo: Repository for bid CRUD operations.

    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialise the service with a shared async database session.

        Args:
            db: An active ``AsyncSession`` used for all database operations.

        """
        self._db = db
        self._auction_repo = AuctionRepository(db)
        self._wallet_repo = WalletRepository(db)
        self._bid_repo = BidRepository(db)
        self._kyc = KYCService(db)

    async def place_bid(
        self, auction_id: UUID, bidder_id: UUID, data: BidResponse
    ) -> BidResponse:
        """Place a bid on an active auction with atomic wallet locking.

        Validates the auction state and bid amount, then within a single
        database transaction: locks the bidder's funds, creates the bid
        record, updates the auction's highest-bid pointer, and refunds
        the previously outbid user.

        Args:
            auction_id: UUID of the auction to bid on.
            bidder_id: UUID of the user placing the bid.
            data: Validated bid request containing the bid amount.

        Returns:
            A ``BidResponse`` for the newly placed bid.

        Raises:
            AuctionNotFoundException: If the auction does not exist.
            AuctionNotActiveException: If the auction is not in ACTIVE state.
            AuctionEndedException: If the auction's end time has passed.
            SellerCannotBidException: If the bidder is the auction's seller.
            AlreadyHighestBidderException: If the bidder already holds the
                highest bid.
            InvalidBidAmountException: If the amount is below the minimum.
            InsufficientFundsException: If the bidder's wallet balance is
                insufficient.

        """
        # ── VALIDATION PHASE ────────────────────────────────────────────────
        auction = await self._auction_repo.get_by_id(auction_id)
        if not auction:
            raise AuctionNotFoundException()

        if auction.status != AuctionStatus.ACTIVE:
            raise AuctionNotActiveException()

        if auction.ends_at <= datetime.now(timezone.utc):
            raise AuctionEndedException()

        if bidder_id == auction.seller_id:
            raise SellerCannotBidException()

        current_highest = await self._bid_repo.get_highest_bid(auction_id)

        if current_highest and current_highest.bidder_id == bidder_id:
            raise AlreadyHighestBidderException()

        if current_highest:
            increment = await self._auction_repo.get_increment_for_amount(
                current_highest.amount
            )
            minimum = current_highest.amount + increment
        else:
            auction_items = await self._auction_repo.get_auction_items(auction_id)
            if not auction_items:
                raise ValidationException(message="Auction has no items attached")
            minimum = auction_items[0].starting_price

        if data.amount < minimum:
            raise InvalidBidAmountException(message=f"Minimum bid is ₦{minimum:,.2f}")

        wallet = await self._wallet_repo.get_by_user_id(bidder_id)
        if not wallet or wallet.available_funds < data.amount:
            raise InsufficientFundsException()

        # ── KYC CHECK ─────────────────────────────────────────
        await self._kyc.check_bid_limit(bidder_id, data.amount)

        # ── ATOMIC TRANSACTION PHASE ─────────────────────────────────────────
        try:
            wallet = await self._wallet_repo.get_by_user_id_with_lock(bidder_id)
            if not wallet:
                raise InsufficientFundsException()

            if wallet.available_funds < data.amount:
                raise InsufficientFundsException()

            bid = await self._bid_repo.create(
                auction_id=auction_id,
                bidder_id=bidder_id,
                amount=data.amount,
            )

            # available_funds before bid lock
            balance_before = wallet.available_funds
            wallet = await self._wallet_repo.update_balances(
                wallet_id=wallet.id,
                available_delta=-data.amount,
                locked_delta=data.amount,
                escrow_delta=Decimal("0"),
            )
            # available_funds after bid lock — shows the deduction clearly
            wallet_txn = await self._wallet_repo.create_transaction(
                wallet_id=wallet.id,
                data={
                    "amount": data.amount,
                    "description": f"Bid placed on auction {auction_id}",
                    "reference_id": str(bid.id),
                    "reference_type": ReferenceType.BID,
                    "balance_before": balance_before,
                    "balance_after": wallet.available_funds,
                    "transaction_type": TransactionType.BID_LOCK,
                    "direction": TransactionDirection.DEBIT,
                    "balance_type": BalanceType.AVAILABLE,
                },
            )

            await self._bid_repo.link_wallet_transaction(
                bid_id=bid.id,
                wallet_transaction_id=wallet_txn.id,
            )

            await self._auction_repo.update_highest_bid(auction_id, bid.id)

            if current_highest:
                await self._bid_repo.update_status(current_highest.id, BidStatus.OUTBID)
                prev_wallet = await self._wallet_repo.get_by_user_id_with_lock(
                    current_highest.bidder_id
                )
                prev_balance_before = prev_wallet.available_funds
                prev_wallet = await self._wallet_repo.update_balances(
                    wallet_id=prev_wallet.id,
                    available_delta=current_highest.amount,
                    locked_delta=-current_highest.amount,
                    escrow_delta=Decimal("0"),
                )
                await self._wallet_repo.create_transaction(
                    wallet_id=prev_wallet.id,
                    data={
                        "amount": current_highest.amount,
                        "description": (f"Outbid refund on auction {auction_id}"),
                        "reference_id": str(current_highest.id),
                        "reference_type": ReferenceType.BID,
                        "balance_before": prev_balance_before,
                        "balance_after": prev_wallet.available_funds,
                        "transaction_type": TransactionType.BID_UNLOCK,
                        "direction": TransactionDirection.CREDIT,
                        "balance_type": BalanceType.AVAILABLE,
                    },
                )
                await self._bid_repo.update_status(
                    current_highest.id, BidStatus.RELEASED
                )

            await self._db.commit()

        except Exception:
            await self._db.rollback()
            raise

        # ── POST-TRANSACTION ─────────────────────────────────────────────────
        if current_highest:
            user_repo = UserRepository(self._db)
            prev_user = await user_repo.get_by_id(current_highest.bidder_id)
            if prev_user:
                notify_outbid_user.delay(
                    user_email=prev_user.email,
                    user_name=(
                        f"{prev_user.first_name or ''} "
                        f"{prev_user.last_name or ''}".strip()
                    ),
                    auction_id=str(auction_id),
                    new_highest_bid=str(data.amount),
                    user_id=str(prev_user.id),
                )

        return BidResponse(
            id=bid.id,
            auction_id=bid.auction_id,
            amount=bid.amount,
            status=bid.status,
            placed_at=bid.placed_at,
            is_highest=True,
        )

    async def get_auction_bid_state(
        self, auction_id: UUID, user_id: UUID | None
    ) -> AuctionBidState:
        """Get the current bidding state of an auction.

        Polled by the frontend to keep the auction UI up to date.

        Args:
            auction_id: UUID of the auction.
            user_id: UUID of the authenticated user, or ``None`` for
                anonymous requests.

        Returns:
            An ``AuctionBidState`` with the current highest bid, minimum
            next bid, total bid count, and the user's own bid if present.

        Raises:
            AuctionNotFoundException: If the auction does not exist.

        """
        auction = await self._auction_repo.get_by_id(auction_id)
        if not auction:
            raise AuctionNotFoundException()

        highest_bid = await self._bid_repo.get_highest_bid(auction_id)

        if highest_bid:
            increment = await self._auction_repo.get_increment_for_amount(
                highest_bid.amount
            )
            minimum_next_bid = highest_bid.amount + increment

        else:
            auction_items = await self._auction_repo.get_auction_items(auction_id)
            minimum_next_bid = (
                auction_items[0].starting_price if auction_items else Decimal("0")
            )

        result = await self._db.execute(
            select(func.count()).where(Bid.auction_id == auction_id)
        )
        bid_count = result.scalar() or 0

        user_current_bid = None
        if user_id:
            user_bid = await self._bid_repo.get_user_bid_on_auction(auction_id, user_id)
            if user_bid:
                user_current_bid = BidResponse(
                    id=user_bid.id,
                    auction_id=user_bid.auction_id,
                    amount=user_bid.amount,
                    status=user_bid.status,
                    placed_at=user_bid.placed_at,
                    is_highest=(
                        highest_bid is not None and highest_bid.id == user_bid.id
                    ),
                )

        return AuctionBidState(
            auction_id=auction_id,
            highest_bid_amount=highest_bid.amount if highest_bid else None,
            minimum_next_bid=minimum_next_bid,
            bid_count=bid_count,
            user_current_bid=user_current_bid,
        )

    async def get_auction_bids(self, auction_id: UUID, page: int, limit: int):
        """Get anonymised bid history for an auction.

        Bidder identity is not exposed in the response.

        Args:
            auction_id: UUID of the auction.
            page: Page number (1-indexed).
            limit: Maximum number of bids per page.

        Returns:
            A ``PaginatedResponse`` of ``BidResponse`` objects.

        """
        result = await self._bid_repo.get_auction_bids(auction_id, page, limit)
        result.data = [
            BidResponse(
                id=b.id,
                auction_id=b.auction_id,
                amount=b.amount,
                status=b.status,
                placed_at=b.placed_at,
                is_highest=False,
            )
            for b in result.data
        ]
        return result

    async def get_my_bids(
        self,
        user_id: UUID,
        status: BidStatus | None,
        page: int,
        limit: int,
    ):
        """Get the authenticated user's full bid history.

        Args:
            user_id: UUID of the user.
            status: Optional status filter.
            page: Page number (1-indexed).
            limit: Maximum number of bids per page.

        Returns:
            A ``PaginatedResponse`` of ``BidHistoryResponse`` objects.

        """
        result = await self._bid_repo.get_user_bid_history(user_id, status, page, limit)
        result.data = [
            BidHistoryResponse(
                id=b.id,
                amount=b.amount,
                placed_at=b.placed_at,
                status=b.status,
                auction=AuctionSummary(
                    id=b.auction.id,
                    status=b.auction.status,
                    ends_at=b.auction.ends_at,
                ),
            )
            for b in result.data
        ]
        return result
