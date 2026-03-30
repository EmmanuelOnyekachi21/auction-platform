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
from apps.escrow.enums import EscrowStatus
from apps.escrow.models import Escrow
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
                    selectinload(Auction.bids),
                    selectinload(Auction.highest_bid),
                    selectinload(Auction.seller),
                )
            )

            result = await db.execute(stmt)
            auction = result.scalar_one_or_none()

            if not auction:
                logger.error("Auction %s not found for settlement", auction_id)
                return

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
                await send_email(
                    subject="Your auction ended with no bids",
                    recipients=[auction_seller_email],
                    body=(
                        f"Hello {auction_seller_name},\n\n"
                        f"Your auction has ended but no bids were placed.\n\n"
                        f"Your items have been returned to your inventory and "
                        f"are available to relist.\n\n"
                        f"Visit your dashboard: {settings.app_url}/seller/dashboard"
                    ),
                )
                return

            # ----------------------------------------------------------------
            # CASE B: Has bids — full settlement
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
                shipping_deadline_at=now + timedelta(hours=72),
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
            balance_before = winner_wallet.locked_funds

            await wallet_repo.update_balances(
                wallet_id=winner_wallet.id,
                available_delta=Decimal("0"),
                locked_delta=-bid_amount,
                escrow_delta=bid_amount,
            )

            balance_after = winner_wallet.locked_funds - bid_amount

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
            await send_email(
                subject="Congratulations! You won the auction",
                recipients=[winner_email],
                body=(
                    f"Hello {winner_name},\n\n"
                    f"You won the auction with a bid of ₦{bid_amount:,.2f}!\n\n"
                    f"The seller has 72 hours to ship your item.\n\n"
                    f"View your order: {settings.app_url}/orders"
                ),
            )

        await send_email(
            subject="Your item has been sold!",
            recipients=[auction_seller_email],
            body=(
                f"Hello {auction_seller_name},\n\n"
                f"Your auction has settled! Your item sold for ₦{bid_amount:,.2f}.\n\n"
                f"Commission (5%): ₦{commission:,.2f}\n"
                f"Your payout: ₦{seller_payout:,.2f}\n\n"
                f"Please ship the item within 72 hours.\n\n"
                f"View your orders: {settings.app_url}/seller/dashboard"
            ),
        )

    asyncio.run(_process())
