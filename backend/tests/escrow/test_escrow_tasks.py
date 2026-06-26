"""
Tests for escrow task logic.

The Celery tasks (process_auto_releases, release_single_escrow,
process_overdue_shipments) each spin up their own DB sessions via
asyncio.run() and are not directly testable through a shared fixture
session.  We test the underlying service/repository logic they delegate
to instead — this gives full coverage of the business rules without
fighting the task runner.

  test_auto_release_credits_seller   → OrderService._release_escrow_to_seller
  test_auto_release_idempotent       → EscrowRepository.claim_for_release
  test_overdue_shipment_refunds_buyer → OrderService.cancel_order
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import config.model_registry  # noqa: F401
from apps.auctions.enums import AuctionStatus, ItemCondition, ItemStatus
from apps.auctions.models import Auction, AuctionItem, Category, Item
from apps.escrow.enums import EscrowStatus
from apps.escrow.models import Escrow
from apps.escrow.repository import EscrowRepository
from apps.orders.enums import OrderStatus
from apps.orders.models import Order
from apps.orders.service import OrderService
from apps.users.models import User
from apps.wallet.models import Wallet
from config.settings import settings

test_engine = create_async_engine(settings.database_url, poolclass=NullPool)


@pytest_asyncio.fixture
async def db():
    """
    Wraps each test in a transaction that is always rolled back.
    commit() is replaced with flush() so service writes are visible
    within the test but never actually committed — the outer
    conn.rollback() cleans everything up after each test.
    """
    async with test_engine.connect() as conn:
        await conn.begin()
        async with AsyncSession(bind=conn, expire_on_commit=False) as session:

            async def _flush_instead_of_commit():
                await session.flush()

            session.commit = _flush_instead_of_commit  # type: ignore[method-assign]
            session.rollback = _flush_instead_of_commit  # type: ignore[method-assign]
            yield session
        await conn.rollback()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _user():
    uid = uuid4()
    return User(
        id=uid,
        email=f"{uid}@test.com",
        phone_number=f"+234{str(uid.int)[:10]}",
        first_name="Test",
        last_name="User",
        password_hash="x",
        is_email_verified=True,
    )


def _wallet(user_id, available=Decimal("0"), escrow=Decimal("0")):
    return Wallet(
        id=uuid4(),
        user_id=user_id,
        available_funds=available,
        locked_funds=Decimal("0"),
        escrow_funds=escrow,
        currency="NGN",
    )


def _auction(seller_id):
    now = datetime.now(timezone.utc)
    return Auction(
        id=uuid4(),
        seller_id=seller_id,
        status=AuctionStatus.SETTLED,
        starts_at=now - timedelta(hours=2),
        ends_at=now - timedelta(hours=1),
    )


def _category():
    uid = uuid4()
    return Category(id=uuid4(), name=f"Cat-{uid}", slug=f"cat-{uid}")


def _item(seller_id, category_id):
    return Item(
        id=uuid4(),
        seller_id=seller_id,
        category_id=category_id,
        title="Test Item",
        description="desc",
        condition=ItemCondition.GOOD,
        status=ItemStatus.SOLD,
    )


def _auction_item(auction_id, item_id):
    return AuctionItem(
        id=uuid4(),
        auction_id=auction_id,
        item_id=item_id,
        starting_price=Decimal("1000"),
        quantity=1,
    )


def _order(
    buyer_id,
    seller_id,
    auction_id,
    auction_item_id,
    status=OrderStatus.PENDING_SHIPMENT,
    deadline_hours=72,
    amount=Decimal("50000"),
):
    return Order(
        id=uuid4(),
        buyer_id=buyer_id,
        seller_id=seller_id,
        auction_id=auction_id,
        auction_item_id=auction_item_id,
        amount=amount,
        status=status,
        shipping_deadline_at=datetime.now(timezone.utc)
        + timedelta(hours=deadline_hours),
    )


def _escrow(
    order_id,
    auction_id,
    winner_id,
    seller_id,
    amount=Decimal("50000"),
    commission=Decimal("2500"),
    auto_release_offset_hours=-1,
):
    """Default auto_release_at is in the past so it's immediately eligible."""
    return Escrow(
        id=uuid4(),
        order_id=order_id,
        auction_id=auction_id,
        winner_id=winner_id,
        seller_id=seller_id,
        amount=amount,
        commission_amount=commission,
        status=EscrowStatus.HOLDING,
        auto_release_at=datetime.now(timezone.utc)
        + timedelta(hours=auto_release_offset_hours),
    )


async def _seed(db, *objects):
    for obj in objects:
        db.add(obj)
    await db.flush()


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("apps.notifications.tasks.notify_payment_released.delay")
@patch("apps.notifications.tasks.notify_transaction_completed.delay")
async def test_auto_release_credits_seller(mock_txn, mock_pay, db):
    """
    _release_escrow_to_seller (called by the auto-release task) deducts
    escrow from buyer's wallet and credits seller with amount minus commission.
    """
    buyer = _user()
    seller = _user()
    buyer_wallet = _wallet(buyer.id, escrow=Decimal("50000"))
    seller_wallet = _wallet(seller.id)
    category = _category()
    item = _item(seller.id, category.id)
    auction = _auction(seller.id)
    auction_item = _auction_item(auction.id, item.id)
    order = _order(
        buyer.id, seller.id, auction.id, auction_item.id, status=OrderStatus.SHIPPED
    )
    escrow = _escrow(
        order.id,
        auction.id,
        buyer.id,
        seller.id,
        amount=Decimal("50000"),
        commission=Decimal("2500"),
    )
    await _seed(
        db,
        buyer,
        seller,
        buyer_wallet,
        seller_wallet,
        category,
        item,
        auction,
        auction_item,
        order,
        escrow,
    )

    service = OrderService(db)
    await service._release_escrow_to_seller(escrow.id)

    await db.refresh(seller_wallet)
    await db.refresh(buyer_wallet)
    assert seller_wallet.available_funds == Decimal("47500")  # 50000 - 2500
    assert buyer_wallet.escrow_funds == Decimal("0")

    await db.refresh(escrow)
    assert escrow.status == EscrowStatus.RELEASED
    assert escrow.released_at is not None


@pytest.mark.asyncio
async def test_auto_release_idempotent(db):
    """
    claim_for_release returns True only once for a HOLDING escrow.
    A second call on the same escrow (now PROCESSING) returns False,
    preventing double-release by concurrent workers.
    """
    buyer = _user()
    seller = _user()
    category = _category()
    item = _item(seller.id, category.id)
    auction = _auction(seller.id)
    auction_item = _auction_item(auction.id, item.id)
    order = _order(buyer.id, seller.id, auction.id, auction_item.id)
    escrow = _escrow(order.id, auction.id, buyer.id, seller.id)
    await _seed(db, buyer, seller, category, item, auction, auction_item, order, escrow)

    repo = EscrowRepository(db)

    first = await repo.claim_for_release(escrow.id)
    second = await repo.claim_for_release(escrow.id)

    assert first is True
    assert second is False  # already PROCESSING — second worker is rejected


@pytest.mark.asyncio
@patch("apps.notifications.tasks.notify_order_cancelled_buyer.delay")
@patch("apps.notifications.tasks.notify_order_cancelled_seller.delay")
async def test_overdue_shipment_refunds_buyer(
    mock_seller_notify, mock_buyer_notify, db
):
    """
    cancel_order (called by process_overdue_shipments for each overdue order)
    refunds the buyer's escrow to available when the shipping deadline has passed.
    """
    buyer = _user()
    seller = _user()
    buyer_wallet = _wallet(buyer.id, escrow=Decimal("50000"))
    seller_wallet = _wallet(seller.id)
    category = _category()
    item = _item(seller.id, category.id)
    auction = _auction(seller.id)
    auction_item = _auction_item(auction.id, item.id)
    # deadline already passed — seller missed it
    order = _order(
        buyer.id,
        seller.id,
        auction.id,
        auction_item.id,
        status=OrderStatus.PENDING_SHIPMENT,
        deadline_hours=-1,
    )
    escrow = _escrow(order.id, auction.id, buyer.id, seller.id)
    await _seed(
        db,
        buyer,
        seller,
        buyer_wallet,
        seller_wallet,
        category,
        item,
        auction,
        auction_item,
        order,
        escrow,
    )

    service = OrderService(db)
    result = await service.cancel_order(buyer_id=buyer.id, order_id=order.id)

    assert result.status == OrderStatus.CANCELLED

    await db.refresh(buyer_wallet)
    assert buyer_wallet.available_funds == Decimal("50000")
    assert buyer_wallet.escrow_funds == Decimal("0")

    await db.refresh(escrow)
    assert escrow.status == EscrowStatus.REFUNDED
    assert escrow.refunded_at is not None
