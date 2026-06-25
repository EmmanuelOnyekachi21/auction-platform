"""Celery tasks for escrow auto-release and overdue shipment handling."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import config.model_registry  # noqa: F401
from apps.escrow.enums import EscrowStatus
from apps.escrow.models import Escrow as EscrowModel
from apps.escrow.repository import EscrowRepository
from apps.notifications.tasks import (
    notify_order_cancelled_buyer,
    notify_order_cancelled_seller,
    notify_payment_released,
    notify_transaction_completed,
)
from apps.orders.enums import OrderStatus
from apps.orders.repository import OrderRepository
from apps.users.models import User
from apps.wallet.enums import (
    BalanceType,
    ReferenceType,
    TransactionDirection,
    TransactionType,
)
from apps.wallet.repository import WalletRepository
from config.celery_app import celery
from config.settings import settings

logger = logging.getLogger(__name__)


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


# ── Auto-Release ──────────────────────────────────────────────────────────────


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_auto_releases(self):
    """Find escrows ready for auto-release and dispatch individual tasks.

    Runs every 5 minutes via Celery beat. Fetches IDs only, then processes
    each in its own session — same idempotency pattern as
    ``settle_ended_auctions``.

    Args:
        self: Celery task instance (injected via ``bind=True``).

    """

    async def _run():
        async with get_task_db_session() as db:
            repo = EscrowRepository(db)
            escrows = await repo.get_pending_auto_releases()
            escrow_ids = [str(e.id) for e in escrows]
            logger.info("Found %d escrows pending auto-release", len(escrow_ids))

        claimed = 0
        for escrow_id in escrow_ids:
            async with get_task_db_session() as db:
                repo = EscrowRepository(db)
                if await repo.claim_for_release(escrow_id):
                    logger.info("Claimed escrow %s for auto-release", escrow_id)
                    release_single_escrow.delay(escrow_id)
                    claimed += 1
                else:
                    logger.info(
                        "Escrow %s already claimed by another worker", escrow_id
                    )

        logger.info("Queued %d escrows for release", claimed)

    asyncio.run(_run())


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def release_single_escrow(self, escrow_id: str):
    """Release a single escrow to the seller.

    Called after ``claim_for_release`` succeeds. Wraps
    ``OrderService._release_escrow_to_seller`` — the shared method used
    by ``confirm_delivery`` and dispute resolution too.

    Args:
        self: Celery task instance (injected via ``bind=True``).
        escrow_id: String UUID of the escrow to release.

    """

    async def _run():
        from apps.orders.service import OrderService

        async with get_task_db_session() as db:
            escrow_repo = EscrowRepository(db)
            order_repo = OrderRepository(db)

            escrow = await escrow_repo.get_by_id(escrow_id)
            if not escrow:
                logger.error("Escrow %s not found for auto-release", escrow_id)
                return

            order = await order_repo.get_by_id(escrow.order_id)
            if not order:
                logger.error("Order not found for escrow %s", escrow_id)
                return

            try:
                order_service = OrderService(db)
                await order_service._release_escrow_to_seller(escrow_id)
                await order_repo.update_status(order.id, OrderStatus.COMPLETED)
                await db.commit()
                logger.info("Auto-released escrow %s to seller", escrow_id)
            except Exception as e:
                await db.rollback()
                logger.error("Failed to auto-release escrow %s: %s", escrow_id, e)
                raise

        async with get_task_db_session() as db:
            result = await db.execute(
                select(EscrowModel).where(EscrowModel.id == escrow_id)
            )
            escrow = result.scalar_one_or_none()
            if not escrow:
                return

            seller_result = await db.execute(
                select(User).where(User.id == escrow.seller_id)
            )
            winner_result = await db.execute(
                select(User).where(User.id == escrow.winner_id)
            )
            seller = seller_result.scalar_one_or_none()
            winner = winner_result.scalar_one_or_none()

        if seller:
            notify_payment_released.delay(
                seller_email=seller.email,
                seller_name=(
                    f"{seller.first_name or ''} " f"{seller.last_name or ''}".strip()
                ),
                order_id=str(escrow.order_id),
                amount=str(escrow.amount - escrow.commission_amount),
            )
        if winner:
            notify_transaction_completed.delay(
                buyer_email=winner.email,
                buyer_name=(
                    f"{winner.first_name or ''} " f"{winner.last_name or ''}".strip()
                ),
                order_id=str(escrow.order_id),
            )

    asyncio.run(_run())


# ── Overdue Shipments ─────────────────────────────────────────────────────────


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_overdue_shipments(self):
    """Auto-cancel orders where the seller missed the shipping deadline.

    Runs every 30 minutes via Celery beat. Refunds the buyer from escrow
    using the same logic as ``OrderService.cancel_order`` but triggered
    by the system rather than the buyer.

    Args:
        self: Celery task instance (injected via ``bind=True``).

    """

    async def _run():
        async with get_task_db_session() as db:
            order_repo = OrderRepository(db)
            overdue = await order_repo.get_overdue_shipments()
            order_ids = [str(o.id) for o in overdue]
            logger.info("Found %d overdue shipments", len(order_ids))

        for order_id in order_ids:
            async with get_task_db_session() as db:
                order_repo = OrderRepository(db)
                escrow_repo = EscrowRepository(db)
                wallet_repo = WalletRepository(db)

                order = await order_repo.get_by_id(order_id)
                if not order or order.status != OrderStatus.PENDING_SHIPMENT:
                    continue

                escrow = await escrow_repo.get_by_order_id(order_id)
                if not escrow:
                    continue

                try:
                    now = datetime.now(timezone.utc)
                    buyer_wallet = await wallet_repo.get_by_user_id_with_lock(
                        order.buyer_id
                    )
                    # available_funds before refund
                    balance_before = buyer_wallet.available_funds

                    buyer_wallet = await wallet_repo.update_balances(
                        wallet_id=buyer_wallet.id,
                        available_delta=escrow.amount,
                        locked_delta=Decimal("0"),
                        escrow_delta=-escrow.amount,
                    )
                    await wallet_repo.create_transaction(
                        wallet_id=buyer_wallet.id,
                        data={
                            "amount": escrow.amount,
                            "balance_before": balance_before,
                            "balance_after": buyer_wallet.available_funds,
                            "description": (
                                f"Auto-refund: seller failed to ship "
                                f"order {order_id}"
                            ),
                            "transaction_type": TransactionType.REFUND,
                            "direction": TransactionDirection.CREDIT,
                            "balance_type": BalanceType.AVAILABLE,
                            "reference_id": str(escrow.id),
                            "reference_type": ReferenceType.ESCROW,
                        },
                    )
                    await escrow_repo.update_status(
                        escrow_id=escrow.id,
                        status=EscrowStatus.REFUNDED,
                        extra_fields={"refunded_at": now},
                    )
                    await order_repo.update_status(order.id, OrderStatus.CANCELLED)
                    await db.commit()
                    logger.info(
                        "Auto-cancelled overdue order %s, buyer refunded",
                        order_id,
                    )

                    if order.buyer:
                        notify_order_cancelled_buyer.delay(
                            buyer_email=order.buyer.email,
                            buyer_name=(
                                f"{order.buyer.first_name or ''} "
                                f"{order.buyer.last_name or ''}".strip()
                            ),
                            order_id=order_id,
                        )
                    if order.seller:
                        notify_order_cancelled_seller.delay(
                            seller_email=order.seller.email,
                            seller_name=(
                                f"{order.seller.first_name or ''} "
                                f"{order.seller.last_name or ''}".strip()
                            ),
                            order_id=order_id,
                        )

                except Exception as e:
                    await db.rollback()
                    logger.error("Failed to auto-cancel order %s: %s", order_id, e)

    asyncio.run(_run())
