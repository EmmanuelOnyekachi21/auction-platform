"""Tests for DisputeService — no emails, no Celery."""

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
from apps.disputes.enums import DisputeStatus
from apps.disputes.models import Dispute
from apps.disputes.schemas import RaiseDisputeRequest, ResolveDisputeRequest
from apps.disputes.service import DisputeService
from apps.escrow.enums import EscrowStatus
from apps.escrow.models import Escrow
from apps.orders.enums import OrderStatus
from apps.orders.models import Order
from apps.users.enums import UserRole
from apps.users.models import User
from apps.wallet.models import Wallet
from common.exceptions import AlreadyExistsException, PermissionDeniedException
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


def _user(role=UserRole.USER):
    uid = uuid4()
    return User(
        id=uid,
        email=f"{uid}@test.com",
        phone_number=f"+234{str(uid.int)[:10]}",
        first_name="Test",
        last_name="User",
        password_hash="x",
        is_email_verified=True,
        role=role,
    )


def _wallet(user_id, escrow=Decimal("50000")):
    return Wallet(
        id=uuid4(),
        user_id=user_id,
        available_funds=Decimal("0"),
        locked_funds=Decimal("0"),
        escrow_funds=escrow,
        currency="NGN",
    )


async def _seed(db, *objects):
    for obj in objects:
        db.add(obj)
    await db.flush()


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def shipped(db):
    """Buyer + seller + SHIPPED order + escrow, all flushed."""
    buyer = _user()
    seller = _user()
    buyer_wallet = _wallet(buyer.id, escrow=Decimal("50000"))
    seller_wallet = _wallet(seller.id, escrow=Decimal("0"))

    uid = uuid4()
    category = Category(id=uuid4(), name=f"Cat-{uid}", slug=f"cat-{uid}")
    item = Item(
        id=uuid4(),
        seller_id=seller.id,
        category_id=category.id,
        title="Test Item",
        description="desc",
        condition=ItemCondition.GOOD,
        status=ItemStatus.SOLD,
    )
    now = datetime.now(timezone.utc)
    auction = Auction(
        id=uuid4(),
        seller_id=seller.id,
        status=AuctionStatus.SETTLED,
        starts_at=now - timedelta(hours=2),
        ends_at=now - timedelta(hours=1),
    )
    auction_item = AuctionItem(
        id=uuid4(),
        auction_id=auction.id,
        item_id=item.id,
        starting_price=Decimal("1000"),
        quantity=1,
    )
    order = Order(
        id=uuid4(),
        buyer_id=buyer.id,
        seller_id=seller.id,
        auction_id=auction.id,
        auction_item_id=auction_item.id,
        amount=Decimal("50000"),
        status=OrderStatus.SHIPPED,
        shipping_deadline_at=now + timedelta(hours=72),
    )
    escrow = Escrow(
        id=uuid4(),
        order_id=order.id,
        auction_id=auction.id,
        winner_id=buyer.id,
        seller_id=seller.id,
        amount=Decimal("50000"),
        commission_amount=Decimal("2500"),
        status=EscrowStatus.HOLDING,
        auto_release_at=now + timedelta(hours=48),
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
    return dict(
        buyer=buyer,
        seller=seller,
        buyer_wallet=buyer_wallet,
        seller_wallet=seller_wallet,
        auction=auction,
        order=order,
        escrow=escrow,
    )


@pytest_asyncio.fixture
async def disputed(db, shipped):
    """
    Extends `shipped`: seeds a Dispute first, then links it to the order.
    Dispute must exist in DB before order.dispute_id FK is set.
    """
    s = shipped
    dispute = Dispute(
        id=uuid4(),
        order_id=s["order"].id,
        auction_id=s["auction"].id,
        raised_by_id=s["buyer"].id,
        against_id=s["seller"].id,
        title="Test dispute",
        description="A" * 50,
        status=DisputeStatus.OPEN,
    )
    await _seed(db, dispute)
    # Keep order as SHIPPED so raise_dispute's status check passes;
    # the existing dispute record is what triggers AlreadyExistsException
    s["order"].dispute_id = dispute.id
    await db.flush()
    return {**s, "dispute": dispute}


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("apps.notifications.tasks.notify_dispute_raised_seller.delay")
async def test_raise_dispute_requires_buyer(mock_notify, db, shipped):
    """Seller cannot raise a dispute on their own order."""
    s = shipped
    service = DisputeService(db)
    with pytest.raises(PermissionDeniedException):
        await service.raise_dispute(
            buyer_id=s["seller"].id,  # seller trying to raise — should be rejected
            order_id=s["order"].id,
            data=RaiseDisputeRequest(
                title="Test dispute title here", description="A" * 50
            ),
        )


@pytest.mark.asyncio
@patch("apps.notifications.tasks.notify_dispute_raised_seller.delay")
async def test_raise_dispute_duplicate_rejected(mock_notify, db, disputed):
    """Cannot raise a second dispute on the same order."""
    s = disputed
    service = DisputeService(db)
    with pytest.raises(AlreadyExistsException):
        await service.raise_dispute(
            buyer_id=s["buyer"].id,
            order_id=s["order"].id,
            data=RaiseDisputeRequest(
                title="Second dispute title", description="B" * 50
            ),
        )


@pytest.mark.asyncio
@patch("apps.notifications.tasks.notify_dispute_resolved_buyer.delay")
@patch("apps.notifications.tasks.notify_dispute_resolved_seller.delay")
async def test_resolve_dispute_buyer_favour_refunds(
    mock_seller, mock_buyer, db, disputed
):
    """Resolving in buyer's favour refunds escrow to buyer's available balance."""
    s = disputed
    admin = _user(role=UserRole.ADMIN)
    await _seed(db, admin)

    service = DisputeService(db)
    result = await service.resolve_dispute(
        admin_id=admin.id,
        dispute_id=s["dispute"].id,
        data=ResolveDisputeRequest(
            resolution="in_favour_of_buyer",
            resolution_notes="Buyer provided sufficient evidence of non-delivery",
        ),
    )

    assert result.status == DisputeStatus.RESOLVED
    await db.refresh(s["buyer_wallet"])
    assert s["buyer_wallet"].available_funds == Decimal("50000")
    assert s["buyer_wallet"].escrow_funds == Decimal("0")


@pytest.mark.asyncio
@patch("apps.notifications.tasks.notify_dispute_resolved_buyer.delay")
@patch("apps.notifications.tasks.notify_dispute_resolved_seller.delay")
async def test_resolve_dispute_seller_favour_releases(
    mock_seller, mock_buyer, db, disputed
):
    """Resolving in seller's favour releases escrow minus commission to seller."""
    s = disputed
    admin = _user(role=UserRole.ADMIN)
    await _seed(db, admin)

    service = DisputeService(db)
    await service.resolve_dispute(
        admin_id=admin.id,
        dispute_id=s["dispute"].id,
        data=ResolveDisputeRequest(
            resolution="in_favour_of_seller",
            resolution_notes="Seller provided proof of delivery with tracking",
        ),
    )

    await db.refresh(s["seller_wallet"])
    assert s["seller_wallet"].available_funds == Decimal(
        "47500"
    )  # 50000 - 2500 commission


@pytest.mark.asyncio
@patch("apps.notifications.tasks.notify_dispute_raised_seller.delay")
async def test_submit_evidence_requires_party(mock_notify, db, disputed):
    """A user not party to the dispute cannot submit evidence."""
    from apps.disputes.enums import EvidenceFileType
    from apps.disputes.schemas import SubmitEvidenceRequest

    s = disputed
    stranger = _user()
    await _seed(db, stranger)

    service = DisputeService(db)
    with pytest.raises(PermissionDeniedException):
        await service.submit_evidence(
            user_id=stranger.id,
            dispute_id=s["dispute"].id,
            data=SubmitEvidenceRequest(
                url="https://example.com/evidence.jpg",
                file_type=EvidenceFileType.IMAGE,
            ),
        )


@pytest.mark.asyncio
async def test_resolve_requires_admin(db, disputed):
    """Non-admin user cannot resolve a dispute."""
    s = disputed
    service = DisputeService(db)
    with pytest.raises(PermissionDeniedException):
        await service.resolve_dispute(
            admin_id=s["buyer"].id,  # regular user, not admin
            dispute_id=s["dispute"].id,
            data=ResolveDisputeRequest(
                resolution="in_favour_of_buyer",
                resolution_notes="This should not work at all",
            ),
        )
