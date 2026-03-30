"""Tests for BidService.place_bid — no emails, no Celery, no external calls."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import config.model_registry  # noqa: F401
from apps.auctions.enums import AuctionStatus, ItemStatus
from apps.auctions.models import Auction, AuctionItem, Category, Item
from apps.bids.enums import BidStatus
from apps.bids.schemas import PlaceBidRequest
from apps.bids.service import BidService
from apps.users.models import User
from apps.wallet.models import Wallet
from common.exceptions import (
    AlreadyHighestBidderException,
    AuctionNotActiveException,
    InsufficientFundsException,
    InvalidBidAmountException,
    SellerCannotBidException,
)
from config.settings import settings

# ── Fixtures ──────────────────────────────────────────────────────────────────

test_engine = create_async_engine(settings.database_url, poolclass=NullPool)


@pytest_asyncio.fixture
async def db():
    async with test_engine.connect() as conn:
        await conn.begin()
        async with AsyncSession(bind=conn, expire_on_commit=False) as session:
            yield session
        await conn.rollback()


def make_user(role="USER"):
    u = User(
        id=uuid4(),
        email=f"{uuid4()}@test.com",
        phone_number=f"+234{str(uuid4().int)[:10]}",
        first_name="Test",
        last_name="User",
        password_hash="x",
        is_email_verified=True,
    )
    return u


def make_wallet(user_id, available=Decimal("100000")):
    return Wallet(
        id=uuid4(),
        user_id=user_id,
        available_funds=available,
        locked_funds=Decimal("0"),
        escrow_funds=Decimal("0"),
        currency="NGN",
    )


def make_auction(seller_id, status=AuctionStatus.ACTIVE, ends_in_minutes=60):
    now = datetime.now(timezone.utc)
    return Auction(
        id=uuid4(),
        seller_id=seller_id,
        status=status,
        bid_increment=Decimal("500"),
        starts_at=now - timedelta(minutes=5),
        ends_at=now + timedelta(minutes=ends_in_minutes),
    )


def make_category():
    return Category(id=uuid4(), name=f"Cat-{uuid4()}", slug=f"cat-{uuid4()}")


def make_item(seller_id, category_id):
    return Item(
        id=uuid4(),
        seller_id=seller_id,
        category_id=category_id,
        title="Test Item",
        description="A test item description that is long enough",
        condition="NEW",
        status=ItemStatus.IN_AUCTION,
    )


def make_auction_item(auction_id, item_id, starting_price=Decimal("1000")):
    return AuctionItem(
        id=uuid4(),
        auction_id=auction_id,
        item_id=item_id,
        starting_price=starting_price,
        quantity=1,
    )


async def seed(db, *objects):
    for obj in objects:
        db.add(obj)
    await db.flush()


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_place_bid_success(db):
    """Bid created, available funds reduced, locked funds increased."""
    seller = make_user()
    bidder = make_user()
    seller_wallet = make_wallet(seller.id)
    bidder_wallet = make_wallet(bidder.id, available=Decimal("50000"))
    auction = make_auction(seller.id)
    category = make_category()
    item = make_item(seller.id, category.id)
    auction_item = make_auction_item(
        auction.id, item.id, starting_price=Decimal("1000")
    )

    await seed(
        db,
        seller,
        bidder,
        seller_wallet,
        bidder_wallet,
        auction,
        category,
        item,
        auction_item,
    )

    service = BidService(db)
    result = await service.place_bid(
        auction_id=auction.id,
        bidder_id=bidder.id,
        data=PlaceBidRequest(amount=Decimal("1000")),
    )

    assert result.is_highest is True
    assert result.amount == Decimal("1000")
    assert result.status == BidStatus.ACTIVE

    await db.refresh(bidder_wallet)
    assert bidder_wallet.available_funds == Decimal("49000")
    assert bidder_wallet.locked_funds == Decimal("1000")


@pytest.mark.asyncio
async def test_place_bid_insufficient_funds(db):
    """Raises InsufficientFundsException, no bid created, no wallet changes."""
    seller = make_user()
    bidder = make_user()
    seller_wallet = make_wallet(seller.id)
    bidder_wallet = make_wallet(bidder.id, available=Decimal("500"))  # less than bid
    auction = make_auction(seller.id)
    category = make_category()
    item = make_item(seller.id, category.id)
    auction_item = make_auction_item(
        auction.id, item.id, starting_price=Decimal("1000")
    )

    await seed(
        db,
        seller,
        bidder,
        seller_wallet,
        bidder_wallet,
        auction,
        category,
        item,
        auction_item,
    )

    service = BidService(db)
    with pytest.raises(InsufficientFundsException):
        await service.place_bid(
            auction_id=auction.id,
            bidder_id=bidder.id,
            data=PlaceBidRequest(amount=Decimal("1000")),
        )

    await db.refresh(bidder_wallet)
    assert bidder_wallet.available_funds == Decimal("500")  # unchanged
    assert bidder_wallet.locked_funds == Decimal("0")


@pytest.mark.asyncio
async def test_place_bid_below_minimum(db):
    """Raises InvalidBidAmountException with minimum in message."""
    seller = make_user()
    bidder = make_user()
    seller_wallet = make_wallet(seller.id)
    bidder_wallet = make_wallet(bidder.id)
    auction = make_auction(seller.id)
    category = make_category()
    item = make_item(seller.id, category.id)
    auction_item = make_auction_item(
        auction.id, item.id, starting_price=Decimal("5000")
    )

    await seed(
        db,
        seller,
        bidder,
        seller_wallet,
        bidder_wallet,
        auction,
        category,
        item,
        auction_item,
    )

    service = BidService(db)
    with pytest.raises(InvalidBidAmountException) as exc_info:
        await service.place_bid(
            auction_id=auction.id,
            bidder_id=bidder.id,
            data=PlaceBidRequest(amount=Decimal("100")),  # below 5000 minimum
        )

    assert "5,000.00" in exc_info.value.message


@pytest.mark.asyncio
async def test_place_bid_seller_cannot_bid(db):
    """Seller cannot bid on their own auction."""
    seller = make_user()
    seller_wallet = make_wallet(seller.id)
    auction = make_auction(seller.id)
    category = make_category()
    item = make_item(seller.id, category.id)
    auction_item = make_auction_item(auction.id, item.id)

    await seed(db, seller, seller_wallet, auction, category, item, auction_item)

    service = BidService(db)
    with pytest.raises(SellerCannotBidException):
        await service.place_bid(
            auction_id=auction.id,
            bidder_id=seller.id,
            data=PlaceBidRequest(amount=Decimal("1000")),
        )


@pytest.mark.asyncio
async def test_place_bid_already_highest_bidder(db):
    """User cannot bid again when already the highest bidder."""
    from apps.bids.models import Bid

    seller = make_user()
    bidder = make_user()
    seller_wallet = make_wallet(seller.id)
    bidder_wallet = make_wallet(bidder.id)
    auction = make_auction(seller.id)
    category = make_category()
    item = make_item(seller.id, category.id)
    auction_item = make_auction_item(auction.id, item.id)

    # Existing highest bid by same bidder
    existing_bid = Bid(
        id=uuid4(),
        auction_id=auction.id,
        bidder_id=bidder.id,
        amount=Decimal("2000"),
        status=BidStatus.ACTIVE,
    )

    await seed(
        db,
        seller,
        bidder,
        seller_wallet,
        bidder_wallet,
        auction,
        category,
        item,
        auction_item,
        existing_bid,
    )
    # Set FK after both auction and bid are flushed
    auction.highest_bid_id = existing_bid.id
    await db.flush()

    service = BidService(db)
    with pytest.raises(AlreadyHighestBidderException):
        await service.place_bid(
            auction_id=auction.id,
            bidder_id=bidder.id,
            data=PlaceBidRequest(amount=Decimal("3000")),
        )


@pytest.mark.asyncio
async def test_place_bid_inactive_auction(db):
    """Raises AuctionNotActiveException for non-active auction."""
    seller = make_user()
    bidder = make_user()
    seller_wallet = make_wallet(seller.id)
    bidder_wallet = make_wallet(bidder.id)
    auction = make_auction(seller.id, status=AuctionStatus.DRAFT)
    category = make_category()
    item = make_item(seller.id, category.id)
    auction_item = make_auction_item(auction.id, item.id)

    await seed(
        db,
        seller,
        bidder,
        seller_wallet,
        bidder_wallet,
        auction,
        category,
        item,
        auction_item,
    )

    service = BidService(db)
    with pytest.raises(AuctionNotActiveException):
        await service.place_bid(
            auction_id=auction.id,
            bidder_id=bidder.id,
            data=PlaceBidRequest(amount=Decimal("1000")),
        )


@pytest.mark.asyncio
async def test_place_bid_outbids_previous_bidder(db):
    """Previous bidder funds unlocked, new bid is highest."""
    from apps.bids.models import Bid

    seller = make_user()
    bidder_a = make_user()
    bidder_b = make_user()
    seller_wallet = make_wallet(seller.id)
    wallet_a = make_wallet(bidder_a.id, available=Decimal("0"))  # already locked
    wallet_a.locked_funds = Decimal("2000")  # simulating locked bid
    wallet_b = make_wallet(bidder_b.id, available=Decimal("50000"))
    auction = make_auction(seller.id)
    category = make_category()
    item = make_item(seller.id, category.id)
    auction_item = make_auction_item(
        auction.id, item.id, starting_price=Decimal("1000")
    )

    existing_bid = Bid(
        id=uuid4(),
        auction_id=auction.id,
        bidder_id=bidder_a.id,
        amount=Decimal("2000"),
        status=BidStatus.ACTIVE,
    )

    await seed(
        db,
        seller,
        bidder_a,
        bidder_b,
        seller_wallet,
        wallet_a,
        wallet_b,
        auction,
        category,
        item,
        auction_item,
        existing_bid,
    )
    # Set FK after both auction and bid are flushed
    auction.highest_bid_id = existing_bid.id
    await db.flush()

    service = BidService(db)
    result = await service.place_bid(
        auction_id=auction.id,
        bidder_id=bidder_b.id,
        data=PlaceBidRequest(amount=Decimal("2500")),  # 2000 + 500 increment
    )

    assert result.is_highest is True

    # Bidder B funds locked
    await db.refresh(wallet_b)
    assert wallet_b.available_funds == Decimal("47500")
    assert wallet_b.locked_funds == Decimal("2500")

    # Bidder A funds returned
    await db.refresh(wallet_a)
    assert wallet_a.available_funds == Decimal("2000")
    assert wallet_a.locked_funds == Decimal("0")

    # Previous bid marked released
    await db.refresh(existing_bid)
    assert existing_bid.status == BidStatus.RELEASED
