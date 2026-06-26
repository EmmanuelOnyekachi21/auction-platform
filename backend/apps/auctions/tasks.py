"""Celery tasks for auction settlement and lifecycle management.

Provides scheduled and on-demand tasks for:
- Detecting ended auctions and queuing them for settlement.
- Settling individual auctions: creating orders, escrow records,
  moving wallet funds, and updating bid/item statuses.

Design notes:
    Each task creates its own SQLAlchemy engine and session via
    ``get_task_db_session`` because asyncpg connections are bound to the
    event loop they were created on.  ``asyncio.run()`` creates a new loop
    per task invocation, so a fresh engine is required each time.
"""

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

import config.model_registry  # noqa: F401 — registers all ORM models before tasks run
from apps.auctions.enums import AuctionStatus, ItemStatus
from apps.auctions.models import Auction, AuctionItem
from apps.auctions.repository import AuctionRepository
from apps.bids.enums import BidStatus
from apps.bids.models import Bid
from apps.escrow.enums import EscrowStatus
from apps.escrow.models import Escrow
from apps.notifications.tasks import _create_notification
from apps.orders.enums import OrderStatus
from apps.orders.models import Order
from apps.users.models import User
from apps.wallet.enums import (
    BalanceType,
    ReferenceType,
    TransactionDirection,
    TransactionType,
)
from apps.wallet.repository import WalletRepository
from common.email import send_email
from config.celery_app import celery
from config.settings import settings

logger = logging.getLogger(__name__)

COMMISSION_RATE = Decimal("0.05")  # 5% platform commission


@asynccontextmanager
async def get_task_db_session():
    """Create a fresh async SQLAlchemy session for use inside a Celery task.

    Builds a new engine and session factory on every call so that the
    asyncpg connection is bound to the current event loop (created by
    ``asyncio.run()``).  The session is committed on clean exit and rolled
    back on any exception.

    Yields:
        An ``AsyncSession`` scoped to a single task invocation.

    """
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
            await engine.dispose()


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_reserve_not_met_seller(
    self,
    seller_email: str,
    seller_name: str,
    item_name: str,
    highest_bid: Decimal,
    reserve_price: Decimal,
):
    """Send an email to the seller when an auction ends without meeting the reserve
    price.

    Args:
        self: Celery task instance.
        seller_email: Seller's email address.
        seller_name: Seller's full name.
        item_name: Name of the auctioned item.
        highest_bid: The highest bid placed during the auction.
        reserve_price: The reserve price set by the seller.

    """
    body = (
        f"Hello {seller_name},\n\n"
        f"Your auction for {item_name} has ended.\n\n"
        f"Highest bid received: ₦{highest_bid:,.2f}\n"
        f"Your reserve price: ₦{reserve_price:,.2f}\n\n"
        f"The reserve price was not met, and the item has been returned "
        f"to your inventory.\n\n"
        f"Visit your dashboard: {settings.frontend_url}/seller/dashboard"
    )

    try:
        asyncio.run(
            send_email(
                subject="Reserve price not met on your auction",
                recipients=[seller_email],
                body=body,
            )
        )
        logger.info("Reserve not met email sent to seller %s", seller_email)
    except Exception as exc:
        logger.error(
            "Failed to send reserve not met email to seller %s: %s", seller_email, exc
        )
        raise exc


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_reserve_not_met_bidder(
    self, bidder_email: str, bidder_name: str, item_name: str, bid_amount: Decimal
):
    """Send an email to the highest bidder when the reserve price was not met.

    Args:
        self: Celery task instance.
        bidder_email: Bidder's email address.
        bidder_name: Bidder's full name.
        item_name: Name of the auctioned item.
        bid_amount: The highest bid placed by the bidder.

    """
    body = (
        f"Hello {bidder_name},\n\n"
        f"The auction for {item_name} has ended.\n\n"
        f"Your bid: ₦{bid_amount:,.2f}\n\n"
        f"The reserve price was not met, so the item was not sold.\n\n"
        f"Your funds have been returned to your wallet.\n\n"
        f"Visit your dashboard: {settings.frontend_url}/dashboard"
    )

    try:
        asyncio.run(
            send_email(
                subject="Auction ended — reserve price not met",
                recipients=[bidder_email],
                body=body,
            )
        )
        logger.info("Reserve not met email sent to bidder %s", bidder_email)
    except Exception as exc:
        logger.error(
            "Failed to send reserve not met email to bidder %s: %s", bidder_email, exc
        )
        raise exc


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def settle_ended_auctions(self):
    """Find and settle all ended auctions (runs every 60 seconds via Celery Beat).

    Queries for all ``ACTIVE`` auctions whose ``ends_at`` has passed, then
    attempts to atomically claim each one for settlement.  Claimed auctions
    are handed off to ``process_auction_settlement`` as individual tasks,
    ensuring idempotency across multiple workers.

    Args:
        self: Celery task instance (injected via ``bind=True``).

    """

    async def _settle():
        async with get_task_db_session() as db:
            auction_repo = AuctionRepository(db)
            auctions = await auction_repo.get_auctions_to_settle()
            auction_ids = [auction.id for auction in auctions]
            logger.info("Found %d auctions to settle", len(auction_ids))

        settled_count = 0
        for auction_id in auction_ids:
            async with get_task_db_session() as db:
                auction_repo = AuctionRepository(db)
                claimed = await auction_repo.claim_for_settlement(auction_id)
                if claimed:
                    logger.info("Claimed auction %s for settlement", auction_id)
                    process_auction_settlement.delay(str(auction_id))
                    settled_count += 1
                else:
                    logger.info(
                        "Auction %s already claimed by another worker", auction_id
                    )

        logger.info("Queued %d auctions for settlement", settled_count)

    asyncio.run(_settle())


async def _handle_reserve_not_met(
    auction_id: uuid.UUID, auction_seller_name: str, auction_seller_email: str
) -> None:
    """Handle auction end where reserve price was not met.

    Only the highest bidder still has locked funds at this point — all other
    bidders were already refunded when they were outbid during the auction.
    This function unlocks the highest bidder's funds, marks all bids as LOST,
    returns items to APPROVED, and sends notifications.
    """
    async with get_task_db_session() as db:
        auction_repo = AuctionRepository(db)
        auction = await auction_repo.get_for_reserve_settlement(auction_id)

        if not auction:
            logger.error("Auction %s not found for reserve settlement", auction_id)
            return

        # Idempotency guard — already handled on a previous attempt
        if auction.status == AuctionStatus.ENDED_RESERVE_NOT_MET:
            logger.warning(
                "Auction %s already marked ENDED_RESERVE_NOT_MET — skipping duplicate",
                auction_id,
            )
            return

        # Set status atomically with fund unlocks so both commit together
        auction.status = AuctionStatus.ENDED_RESERVE_NOT_MET

        # Return all items to available inventory
        for auction_item in auction.auction_items:
            auction_item.item.status = ItemStatus.APPROVED

        # Mark all bids as LOST
        for bid in auction.bids:
            bid.status = BidStatus.LOST

        # Only the highest bidder still has locked funds — everyone else was
        # already refunded when they were outbid during the auction.
        highest_bid = auction.highest_bid
        if not highest_bid:
            logger.warning(
                "Auction %s has no highest bid — nothing to unlock", auction_id
            )
            return

        wallet_repo = WalletRepository(db)
        winner_wallet = await wallet_repo.get_by_user_id_with_lock(
            highest_bid.bidder_id
        )
        if not winner_wallet:
            raise ValueError(
                f"Wallet not found for highest bidder {highest_bid.bidder_id}"
            )

        balance_before = winner_wallet.available_funds
        logger.info(
            "Attempting to unlock %s from wallet %s "
            "(locked_funds=%s available_funds=%s)",
            highest_bid.amount,
            winner_wallet.id,
            winner_wallet.locked_funds,
            winner_wallet.available_funds,
        )
        updated_wallet = await wallet_repo.update_balances(
            wallet_id=winner_wallet.id,
            available_delta=highest_bid.amount,
            locked_delta=-highest_bid.amount,
            escrow_delta=Decimal("0"),
        )

        # Total after unlock — locked decreased, available increased, total same
        await wallet_repo.create_transaction(
            wallet_id=winner_wallet.id,
            data={
                "amount": highest_bid.amount,
                "balance_before": balance_before,
                "balance_after": updated_wallet.available_funds,
                "description": (
                    f"Bid refund - reserve price not met on auction {auction.id}"
                ),
                "transaction_type": TransactionType.BID_UNLOCK,
                "direction": TransactionDirection.CREDIT,
                "balance_type": BalanceType.LOCKED,
                "reference_id": highest_bid.id,
                "reference_type": ReferenceType.BID,
            },
        )

        logger.info(
            "Unlocked %s for highest bidder %s - reserve not met on auction %s",
            highest_bid.amount,
            highest_bid.bidder_id,
            auction_id,
        )

        # Fetch highest bidder details for notification
        highest_bidder = highest_bid.bidder

    # Queue notifications outside the DB session
    item_title = (
        auction.auction_items[0].item.title if auction.auction_items else "your item"
    )

    logger.info(
        "Notifying seller %s (%s) - reserve not met",
        auction_seller_name,
        auction_seller_email,
    )
    send_reserve_not_met_seller.delay(
        auction_seller_email,
        auction_seller_name,
        item_title,
        highest_bid.amount,
        auction.reserve_price,
    )

    if highest_bidder:
        bidder_name = f"{highest_bidder.first_name} {highest_bidder.last_name}".strip()
        send_reserve_not_met_bidder.delay(
            highest_bidder.email,
            bidder_name,
            item_title,
            highest_bid.amount,
        )


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_auction_settlement(self, auction_id: str):
    """Settle a single auction by creating order, escrow, and moving funds.

    Args:
        self: Celery task instance (injected via ``bind=True``).
        auction_id: String UUID of the auction to settle.

    Business logic:
        - No bids: mark ``ENDED_NO_BIDS``, return items to ``APPROVED``.
        - Has bids:

          1. Calculate 5% platform commission.
          2. Create ``Order`` record.
          3. Create ``Escrow`` record.
          4. Move winner's funds: locked → escrow bucket.
          5. Update bid statuses (``WON`` / ``LOST``).
          6. Update item statuses to ``SOLD``.
          7. Update auction status to ``SETTLED``.
          8. Queue winner/seller notifications (TODO).

    """
    logger.info("Processing auction settlement for %s", auction_id)

    async def _process():
        async with get_task_db_session() as db:
            stmt = (
                select(Auction)
                .where(Auction.id == uuid.UUID(auction_id))
                .options(
                    selectinload(Auction.auction_items).selectinload(AuctionItem.item),
                    selectinload(Auction.bids).selectinload(Bid.bidder),
                    selectinload(Auction.highest_bid),
                    selectinload(Auction.seller),
                )
            )

            result = await db.execute(stmt)
            auction = result.scalar_one_or_none()

            if not auction:
                logger.error("Auction %s not found for settlement", auction_id)
                return

            # Idempotency guard — if already settled or in a terminal state,
            # this is a retry hitting an already-completed settlement. Skip.
            terminal_statuses = {
                AuctionStatus.SETTLED,
                AuctionStatus.ENDED_NO_BIDS,
                AuctionStatus.ENDED_RESERVE_NOT_MET,
                AuctionStatus.CANCELLED,
                AuctionStatus.SETTLEMENT_FAILED,
            }
            if auction.status in terminal_statuses:
                logger.warning(
                    "Auction %s already in terminal status %s "
                    "— skipping duplicate settlement",
                    auction_id,
                    auction.status,
                )
                return

            logger.info(
                "Auction %s loaded — status=%s reserve_price=%s highest_bid=%s",
                auction_id,
                auction.status,
                auction.reserve_price,
                auction.highest_bid.amount if auction.highest_bid else None,
            )

            auction_seller_id = auction.seller_id
            auction_seller_email = auction.seller.email
            auction_seller_name = (
                f"{auction.seller.first_name} {auction.seller.last_name}"
            )

            # ----------------------------------------------------------------
            # CASE A: No bids
            # ----------------------------------------------------------------
            if not auction.bids:
                logger.info("Auction %s ended with no bids", auction_id)
                auction.status = AuctionStatus.ENDED_NO_BIDS
                for auction_item in auction.auction_items:
                    auction_item.item.status = ItemStatus.APPROVED
                logger.info(
                    "Notifying seller %s (%s) — no bids received",
                    auction_seller_name,
                    auction_seller_email,
                )
                try:
                    await send_email(
                        subject="Your auction ended with no bids",
                        recipients=[auction_seller_email],
                        body=(
                            f"Hello {auction_seller_name},\n\n"
                            f"Your auction has ended but no bids were placed.\n\n"
                            f"Your items have been returned to your inventory "
                            f"and are available to relist.\n\n"
                            f"Visit your dashboard: "
                            f"{settings.frontend_url}/seller/dashboard"
                        ),
                    )
                except Exception:
                    logger.error(
                        "Failed to send no-bids email to seller %s — "
                        "settlement still completed",
                        auction_seller_email,
                        exc_info=True,
                    )
                return

            # ----------------------------------------------------------------
            # CASE B: Has bids — Reserve Price Not Met
            # ----------------------------------------------------------------
            if auction.reserve_price is not None:
                if auction.reserve_price > auction.highest_bid.amount:
                    logger.info(
                        "Auction %s ended with reserve not met "
                        "(reserve=%s highest_bid=%s)",
                        auction_id,
                        auction.reserve_price,
                        auction.highest_bid.amount,
                    )
                    # Status is set inside _handle_reserve_not_met atomically
                    # with the wallet unlocks in its own session. Do NOT set it
                    # here — that would commit to a different session and cause
                    # the idempotency guard in _handle to skip the unlocks.
                    await _handle_reserve_not_met(
                        auction_id, auction_seller_name, auction_seller_email
                    )
                    return

            # ----------------------------------------------------------------
            # CASE C: Has bids, meets Reserve price — full settlement
            # ----------------------------------------------------------------
            highest_bid = auction.highest_bid
            bid_amount = highest_bid.amount
            winner_id = highest_bid.bidder_id

            commission = (bid_amount * COMMISSION_RATE).quantize(Decimal("0.01"))
            seller_payout = bid_amount - commission

            logger.info(
                "Settling auction %s: amount=%s commission=%s seller_payout=%s",
                auction_id,
                bid_amount,
                commission,
                seller_payout,
            )

            now = datetime.now(timezone.utc)
            first_auction_item = auction.auction_items[0]

            order = Order(
                auction_id=auction.id,
                buyer_id=winner_id,
                seller_id=auction_seller_id,
                auction_item_id=first_auction_item.id,
                amount=bid_amount,
                status=OrderStatus.PENDING_SHIPMENT,
                shipping_deadline_at=now
                + timedelta(minutes=settings.shipping_deadline),
            )
            db.add(order)
            await db.flush()

            escrow = Escrow(
                order_id=order.id,
                auction_id=auction.id,
                winner_id=winner_id,
                seller_id=auction_seller_id,
                amount=bid_amount,
                commission_amount=commission,
                status=EscrowStatus.HOLDING,
                auto_release_at=now + timedelta(hours=48),
            )
            db.add(escrow)

            wallet_repo = WalletRepository(db)
            winner_wallet = await wallet_repo.get_by_user_id_with_lock(winner_id)
            # available_funds before escrow move (doesn't change during locked→escrow)
            balance_before = winner_wallet.available_funds

            updated_winner_wallet = await wallet_repo.update_balances(
                wallet_id=winner_wallet.id,
                available_delta=Decimal("0"),
                locked_delta=-bid_amount,
                escrow_delta=bid_amount,
            )

            # available_funds after — same as before since available wasn't touched
            balance_after = updated_winner_wallet.available_funds

            await wallet_repo.create_transaction(
                wallet_id=winner_wallet.id,
                data={
                    "amount": bid_amount,
                    "balance_before": balance_before,
                    "balance_after": balance_after,
                    "description": f"Escrow hold for auction {auction_id}",
                    "transaction_type": TransactionType.ESCROW_MOVE,
                    "direction": TransactionDirection.DEBIT,
                    "balance_type": BalanceType.LOCKED,
                    "reference_id": order.id,
                    "reference_type": ReferenceType.ORDER,
                },
            )

            for bid in auction.bids:
                bid.status = (
                    BidStatus.WON if bid.id == highest_bid.id else BidStatus.LOST
                )

            for auction_item in auction.auction_items:
                auction_item.item.status = ItemStatus.SOLD

            auction.status = AuctionStatus.SETTLED
            logger.info("Auction %s settled successfully", auction_id)

        # Fetch winner details for notification (outside DB session)
        async with get_task_db_session() as notify_db:
            result = await notify_db.execute(select(User).where(User.id == winner_id))
            winner_user = result.scalar_one_or_none()
            winner_email = winner_user.email if winner_user else None
            winner_name = (
                f"{winner_user.first_name} {winner_user.last_name}".strip()
                if winner_user
                else "Winner"
            )

        if winner_email:
            try:
                await send_email(
                    subject="Congratulations! You won the auction",
                    recipients=[winner_email],
                    body=(
                        f"Hello {winner_name},\n\n"
                        f"You won the auction with a bid of ₦{bid_amount:,.2f}!\n\n"
                        f"The seller has {settings.shipping_deadline} hours to ship"
                        f" your item.\n\n"
                        f"View your order: {settings.frontend_url}/orders"
                    ),
                )
            except Exception:
                logger.error(
                    "Failed to send auction won email to winner %s — "
                    "settlement still completed",
                    winner_email,
                    exc_info=True,
                )
            # In-app notification for winner
            await _create_notification(
                user_id=str(winner_id),
                title="You won the auction!",
                message=(
                    f"Congratulations! You won with a bid of "
                    f"₦{bid_amount:,.2f}. "
                    f"The seller has {settings.shipping_deadline} hours to ship."
                ),
                notification_type="AUCTION_WON",
                reference_id=str(auction_id),
                reference_type="AUCTION",
            )

        try:
            await send_email(
                subject="Your item has been sold!",
                recipients=[auction_seller_email],
                body=(
                    f"Hello {auction_seller_name},\n\n"
                    f"Your auction has settled! Your item sold for "
                    f"₦{bid_amount:,.2f}.\n\n"
                    f"Commission (5%): ₦{commission:,.2f}\n"
                    f"Your payout: ₦{seller_payout:,.2f}\n\n"
                    f"Please ship the item within {settings.shipping_deadline} "
                    f"hours.\n\n"
                    f"View your orders: {settings.frontend_url}/seller/dashboard"
                ),
            )
        except Exception:
            logger.error(
                "Failed to send auction settled email to seller %s — "
                "settlement still completed",
                auction_seller_email,
                exc_info=True,
            )
        # In-app notification for seller
        await _create_notification(
            user_id=str(auction_seller_id),
            title="Your item has been sold!",
            message=(
                f"Your auction settled at ₦{bid_amount:,.2f}. "
                f"Payout: ₦{seller_payout:,.2f}. "
                f"Ship within {settings.shipping_deadline} hours."
            ),
            notification_type="PAYMENT_RECEIVED",
            reference_id=str(auction_id),
            reference_type="AUCTION",
        )

    asyncio.run(_process())


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def activate_scheduled_auctions(self):
    """Activate scheduled auctions whose start time has arrived.

    Runs every 60 seconds via Celery Beat. Finds all SCHEDULED auctions
    where starts_at <= now and transitions them to ACTIVE.

    Args:
        self: Celery task instance (injected via ``bind=True``).

    """

    async def _activate():
        async with get_task_db_session() as db:
            auction_repo = AuctionRepository(db)
            auctions = await auction_repo.get_scheduled_auctions()
            logger.info("Found %d scheduled auctions to activate", len(auctions))
            for auction in auctions:
                auction.status = AuctionStatus.ACTIVE
                logger.info("Activated scheduled auction %s", auction.id)

    asyncio.run(_activate())
