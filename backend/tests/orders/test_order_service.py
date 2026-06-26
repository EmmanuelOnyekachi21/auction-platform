"""Tests for OrderService — no emails, no Celery, no external calls."""

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
from apps.orders.enums import OrderStatus
from apps.orders.models import Order
from apps.orders.service import OrderService
from apps.users.models import User
from apps.wallet.models import Wallet
from common.exceptions import PermissionDeniedException, ValidationException
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


def _item(seller_id, category_id):
    return Item(
        id=uuid4(),
        seller_id=seller_id,
        category_id=category_id,
        title="Test Item",
        description="A test item description",
        condition=ItemCondition.GOOD,
        status=ItemStatus.SOLD,
    )


def _category():
    uid = uuid4()
    return Category(id=uuid4(), name=f"Cat-{uid}", slug=f"cat-{uid}")


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


def _escrow(order_id, auction_id, winner_id, seller_id, amount=Decimal("50000")):
    commission = (amount * Decimal("0.05")).quantize(Decimal("0.01"))
    return Escrow(
        id=uuid4(),
        order_id=order_id,
        auction_id=auction_id,
        winner_id=winner_id,
        seller_id=seller_id,
        amount=amount,
        commission_amount=commission,
        status=EscrowStatus.HOLDING,
        auto_release_at=datetime.now(timezone.utc) + timedelta(hours=48),
    )


async def _seed(db, *objects):
    for obj in objects:
        db.add(obj)
    await db.flush()


# ── Shared fixture for a standard buyer/seller/order setup ────────────────────


@pytest_asyncio.fixture
async def order_setup(db):
    """Seed a complete buyer+seller+order graph, return a dict of objects."""
    buyer = _user()
    seller = _user()
    buyer_wallet = _wallet(buyer.id, escrow=Decimal("50000"))
    seller_wallet = _wallet(seller.id)
    category = _category()
    item = _item(seller.id, category.id)
    auction = _auction(seller.id)
    auction_item = _auction_item(auction.id, item.id)
    order = _order(
        buyer.id,
        seller.id,
        auction.id,
        auction_item.id,
        status=OrderStatus.PENDING_SHIPMENT,
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
    )
    return dict(
        buyer=buyer,
        seller=seller,
        buyer_wallet=buyer_wallet,
        seller_wallet=seller_wallet,
        auction=auction,
        auction_item=auction_item,
        order=order,
    )


@pytest_asyncio.fixture
async def shipped_setup(db):
    """Seed a SHIPPED order with escrow ready for delivery confirmation."""
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
    return dict(
        buyer=buyer,
        seller=seller,
        buyer_wallet=buyer_wallet,
        seller_wallet=seller_wallet,
        order=order,
        escrow=escrow,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ship_order_requires_seller(db, order_setup):
    """Non-seller cannot mark order as shipped."""
    stranger = _user()
    await _seed(db, stranger)

    from apps.orders.schemas import ShipOrderRequest

    service = OrderService(db)
    with pytest.raises(PermissionDeniedException):
        await service.ship_order(
            seller_id=stranger.id,
            order_id=order_setup["order"].id,
            data=ShipOrderRequest(tracking_number=None),
        )


@pytest.mark.asyncio
async def test_ship_order_wrong_status_fails(db, order_setup):
    """Cannot ship an order that is not PENDING_SHIPMENT."""
    order = order_setup["order"]
    order.status = OrderStatus.SHIPPED
    await db.flush()

    from apps.orders.schemas import ShipOrderRequest

    service = OrderService(db)
    with pytest.raises(ValidationException):
        await service.ship_order(
            seller_id=order_setup["seller"].id,
            order_id=order.id,
            data=ShipOrderRequest(tracking_number=None),
        )


@pytest.mark.asyncio
@patch("apps.notifications.tasks.notify_payment_released.delay")
@patch("apps.notifications.tasks.notify_transaction_completed.delay")
async def test_confirm_delivery_releases_escrow(mock_txn, mock_pay, db, shipped_setup):
    """Confirm delivery releases escrow and marks order COMPLETED."""
    s = shipped_setup
    service = OrderService(db)
    result = await service.confirm_delivery(
        buyer_id=s["buyer"].id, order_id=s["order"].id
    )

    assert result.status == OrderStatus.COMPLETED

    await db.refresh(s["seller_wallet"])
    commission = (Decimal("50000") * Decimal("0.05")).quantize(Decimal("0.01"))
    assert s["seller_wallet"].available_funds == Decimal("50000") - commission

    await db.refresh(s["buyer_wallet"])
    assert s["buyer_wallet"].escrow_funds == Decimal("0")


@pytest.mark.asyncio
@patch("apps.notifications.tasks.notify_payment_released.delay")
@patch("apps.notifications.tasks.notify_transaction_completed.delay")
async def test_confirm_delivery_credits_seller_wallet(mock_txn, mock_pay, db):
    """Seller receives payout minus commission after delivery confirmation."""
    buyer = _user()
    seller = _user()
    buyer_wallet = _wallet(buyer.id, escrow=Decimal("100000"))
    seller_wallet = _wallet(seller.id)
    category = _category()
    item = _item(seller.id, category.id)
    auction = _auction(seller.id)
    auction_item = _auction_item(auction.id, item.id)
    order = _order(
        buyer.id,
        seller.id,
        auction.id,
        auction_item.id,
        status=OrderStatus.SHIPPED,
        amount=Decimal("100000"),
    )
    escrow = Escrow(
        id=uuid4(),
        order_id=order.id,
        auction_id=auction.id,
        winner_id=buyer.id,
        seller_id=seller.id,
        amount=Decimal("100000"),
        commission_amount=Decimal("5000"),
        status=EscrowStatus.HOLDING,
        auto_release_at=datetime.now(timezone.utc) + timedelta(hours=48),
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
    await service.confirm_delivery(buyer_id=buyer.id, order_id=order.id)

    await db.refresh(seller_wallet)
    assert seller_wallet.available_funds == Decimal("95000")


@pytest.mark.asyncio
@patch("apps.notifications.tasks.notify_payment_released.delay")
@patch("apps.notifications.tasks.notify_transaction_completed.delay")
async def test_confirm_delivery_records_commission(
    mock_txn, mock_pay, db, shipped_setup
):
    """Commission WalletTransaction is created on every escrow release."""
    from sqlalchemy import select

    from apps.wallet.enums import TransactionType
    from apps.wallet.models import WalletTransactions

    s = shipped_setup
    service = OrderService(db)
    await service.confirm_delivery(buyer_id=s["buyer"].id, order_id=s["order"].id)

    result = await db.execute(
        select(WalletTransactions).where(
            WalletTransactions.wallet_id == s["seller_wallet"].id,
            WalletTransactions.transaction_type == TransactionType.COMMISION,
        )
    )
    commission_txn = result.scalar_one_or_none()
    assert commission_txn is not None
    assert commission_txn.amount == s["escrow"].commission_amount


@pytest.mark.asyncio
async def test_cancel_order_before_deadline_fails(db, order_setup):
    """Buyer cannot cancel before shipping deadline passes."""
    service = OrderService(db)
    with pytest.raises(ValidationException) as exc_info:
        await service.cancel_order(
            buyer_id=order_setup["buyer"].id,
            order_id=order_setup["order"].id,
        )
    assert "Seller still has time" in exc_info.value.message


@pytest.mark.asyncio
@patch("apps.notifications.tasks.notify_order_cancelled_buyer.delay")
@patch("apps.notifications.tasks.notify_order_cancelled_seller.delay")
async def test_cancel_order_after_deadline_refunds_buyer(mock_seller, mock_buyer, db):
    """Buyer refunded from escrow after deadline passes."""
    buyer = _user()
    seller = _user()
    buyer_wallet = _wallet(buyer.id, escrow=Decimal("50000"))
    seller_wallet = _wallet(seller.id)
    category = _category()
    item = _item(seller.id, category.id)
    auction = _auction(seller.id)
    auction_item = _auction_item(auction.id, item.id)
    # deadline already passed
    order = _order(buyer.id, seller.id, auction.id, auction_item.id, deadline_hours=-1)
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


@pytest.mark.asyncio
@patch("apps.notifications.tasks.notify_payment_released.delay")
@patch("apps.notifications.tasks.notify_transaction_completed.delay")
async def test_release_escrow_updates_total_sales(
    mock_txn, mock_pay, db, shipped_setup
):
    """Seller total_sales increments by 1 after escrow release."""

    from apps.users.models import UserProfile

    s = shipped_setup
    seller_profile = UserProfile(id=uuid4(), user_id=s["seller"].id, total_sales=5)
    await _seed(db, seller_profile)

    service = OrderService(db)
    await service.confirm_delivery(buyer_id=s["buyer"].id, order_id=s["order"].id)

    await db.refresh(seller_profile)
    assert seller_profile.total_sales == 6
