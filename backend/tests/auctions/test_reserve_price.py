"""Tests for reserve price logic across schemas and service validation.

Covers:
- reserve_price_met computed field (None / False / True)
- reserve_progress_percent computed field (None / 0 / partial / 100)
- reserve_price excluded from API response serialisation
- starting price vs reserve price validation in attach_item_to_auction
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.auctions.enums import AuctionStatus, ItemStatus
from apps.auctions.schemas import AuctionResponse, BidSummary
from apps.auctions.service import AuctionService
from apps.users.schemas import PublicUserResponse
from common.exceptions import ValidationException

# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_seller() -> PublicUserResponse:
    return PublicUserResponse(
        id=uuid.uuid4(),
        first_name="Test",
        last_name="Seller",
        email="seller@test.com",
    )


def _make_bid(amount: Decimal) -> BidSummary:
    return BidSummary(
        id=uuid.uuid4(),
        bidder_id=uuid.uuid4(),
        amount=amount,
        created_at=datetime.now(timezone.utc),
    )


def _make_auction(
    reserve_price: Decimal | None = None,
    highest_bid_amount: Decimal | None = None,
) -> AuctionResponse:
    """Build a minimal AuctionResponse for computed field testing."""
    now = datetime.now(timezone.utc)
    return AuctionResponse(
        id=uuid.uuid4(),
        status=AuctionStatus.ACTIVE,
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=6),
        bid_increment=Decimal("500.00"),
        reserve_price=reserve_price,
        created_at=now,
        auction_items=[],
        seller=_make_seller(),
        highest_bid=_make_bid(highest_bid_amount) if highest_bid_amount else None,
        bids=[],
    )


# ─── reserve_price_met ───────────────────────────────────────────────────────


class TestReservePriceMet:
    """Tests for the reserve_price_met computed field."""

    def test_no_reserve_returns_none(self):
        """When no reserve is set, reserve_price_met should be None."""
        auction = _make_auction(reserve_price=None, highest_bid_amount=Decimal("10000"))
        assert auction.reserve_price_met is None

    def test_reserve_set_no_bids_returns_false(self):
        """Reserve set but no bids yet — not met."""
        auction = _make_auction(reserve_price=Decimal("50000"), highest_bid_amount=None)
        assert auction.reserve_price_met is False

    def test_bid_below_reserve_returns_false(self):
        """Highest bid below reserve — not met."""
        auction = _make_auction(
            reserve_price=Decimal("50000"),
            highest_bid_amount=Decimal("30000"),
        )
        assert auction.reserve_price_met is False

    def test_bid_exactly_at_reserve_returns_true(self):
        """Highest bid exactly equal to reserve — met."""
        auction = _make_auction(
            reserve_price=Decimal("50000"),
            highest_bid_amount=Decimal("50000"),
        )
        assert auction.reserve_price_met is True

    def test_bid_above_reserve_returns_true(self):
        """Highest bid exceeds reserve — met."""
        auction = _make_auction(
            reserve_price=Decimal("50000"),
            highest_bid_amount=Decimal("75000"),
        )
        assert auction.reserve_price_met is True


# ─── reserve_progress_percent ────────────────────────────────────────────────


class TestReserveProgressPercent:
    """Tests for the reserve_progress_percent computed field."""

    def test_no_reserve_returns_none(self):
        """No reserve set — progress is None (no bar to show)."""
        auction = _make_auction(reserve_price=None, highest_bid_amount=Decimal("10000"))
        assert auction.reserve_progress_percent is None

    def test_reserve_set_no_bids_returns_zero(self):
        """Reserve set but no bids — progress is 0."""
        auction = _make_auction(reserve_price=Decimal("50000"), highest_bid_amount=None)
        assert auction.reserve_progress_percent == 0

    def test_partial_progress_calculated_correctly(self):
        """30k bid on 50k reserve = 60%."""
        auction = _make_auction(
            reserve_price=Decimal("50000"),
            highest_bid_amount=Decimal("30000"),
        )
        assert auction.reserve_progress_percent == 60

    def test_progress_at_reserve_is_100(self):
        """Bid exactly at reserve = 100%."""
        auction = _make_auction(
            reserve_price=Decimal("50000"),
            highest_bid_amount=Decimal("50000"),
        )
        assert auction.reserve_progress_percent == 100

    def test_progress_capped_at_100_when_bid_exceeds_reserve(self):
        """Bid above reserve never returns more than 100."""
        auction = _make_auction(
            reserve_price=Decimal("50000"),
            highest_bid_amount=Decimal("80000"),
        )
        assert auction.reserve_progress_percent == 100

    def test_progress_rounds_down(self):
        """Integer truncation: 33333 / 50000 = 66.666 → 66."""
        auction = _make_auction(
            reserve_price=Decimal("50000"),
            highest_bid_amount=Decimal("33333"),
        )
        assert auction.reserve_progress_percent == 66


# ─── reserve_price not exposed in serialised output ──────────────────────────


class TestReservePriceNotExposed:
    """Ensures reserve_price never appears in the serialised API response."""

    def test_reserve_price_excluded_from_model_dump(self):
        """reserve_price must not appear in model_dump output."""
        auction = _make_auction(
            reserve_price=Decimal("50000"),
            highest_bid_amount=Decimal("30000"),
        )
        serialised = auction.model_dump()
        assert "reserve_price" not in serialised

    def test_reserve_progress_percent_present_in_output(self):
        """reserve_progress_percent must be present in model_dump output."""
        auction = _make_auction(
            reserve_price=Decimal("50000"),
            highest_bid_amount=Decimal("30000"),
        )
        serialised = auction.model_dump()
        assert "reserve_progress_percent" in serialised
        assert serialised["reserve_progress_percent"] == 60

    def test_reserve_price_met_present_in_output(self):
        """reserve_price_met must be present in model_dump output."""
        auction = _make_auction(
            reserve_price=Decimal("50000"),
            highest_bid_amount=Decimal("30000"),
        )
        serialised = auction.model_dump()
        assert "reserve_price_met" in serialised
        assert serialised["reserve_price_met"] is False


# ─── starting price vs reserve price validation ──────────────────────────────


class TestStartingPriceReserveValidation:
    """Tests for the reserve price vs starting price check in attach_item_to_auction."""

    def _make_service(self, auction_reserve: Decimal | None) -> AuctionService:
        """Build an AuctionService with a mocked auction repo."""
        db = MagicMock()
        service = AuctionService(db)

        mock_auction = MagicMock()
        mock_auction.seller_id = uuid.uuid4()
        mock_auction.status = AuctionStatus.DRAFT
        mock_auction.reserve_price = auction_reserve

        service._auction_repo = MagicMock()
        service._auction_repo.get_by_id = AsyncMock(return_value=mock_auction)

        mock_item = MagicMock()
        mock_item.seller_id = mock_auction.seller_id
        mock_item.status = ItemStatus.APPROVED

        service._item_repo = MagicMock()
        service._item_repo.get_by_id_with_seller = AsyncMock(return_value=mock_item)
        service._item_repo.update_item_status = AsyncMock()
        service._auction_repo.attach_item = AsyncMock()

        db.commit = AsyncMock()

        return service, mock_auction.seller_id

    @pytest.mark.asyncio
    async def test_starting_price_equal_to_reserve_raises(self):
        """Starting price equal to reserve must raise ValidationException."""
        from apps.auctions.schemas import AttachItemRequest

        service, seller_id = self._make_service(auction_reserve=Decimal("50000"))
        data = AttachItemRequest(
            item_id=uuid.uuid4(),
            starting_price=Decimal("50000"),
            quantity=1,
        )
        with pytest.raises(ValidationException, match="reserve price"):
            await service.attach_item_to_auction(seller_id, uuid.uuid4(), data)

    @pytest.mark.asyncio
    async def test_starting_price_above_reserve_raises(self):
        """Starting price above reserve must raise ValidationException."""
        from apps.auctions.schemas import AttachItemRequest

        service, seller_id = self._make_service(auction_reserve=Decimal("50000"))
        data = AttachItemRequest(
            item_id=uuid.uuid4(),
            starting_price=Decimal("60000"),
            quantity=1,
        )
        with pytest.raises(ValidationException, match="reserve price"):
            await service.attach_item_to_auction(seller_id, uuid.uuid4(), data)

    @pytest.mark.asyncio
    async def test_starting_price_below_reserve_passes(self):
        """Starting price below reserve must not raise ValidationException."""
        from apps.auctions.schemas import AttachItemRequest

        service, seller_id = self._make_service(auction_reserve=Decimal("50000"))

        # First call returns the auction for validation checks.
        # Second call (reload after attach) raises a generic RuntimeError —
        # this proves validation passed without needing a full ORM object.
        service._auction_repo.get_by_id = AsyncMock(
            side_effect=[
                _build_mock_auction(seller_id, Decimal("50000")),
                RuntimeError("reload not needed for this test"),
            ]
        )

        data = AttachItemRequest(
            item_id=uuid.uuid4(),
            starting_price=Decimal("10000"),
            quantity=1,
        )
        with pytest.raises(RuntimeError, match="reload not needed"):
            await service.attach_item_to_auction(seller_id, uuid.uuid4(), data)

    @pytest.mark.asyncio
    async def test_no_reserve_skips_validation(self):
        """When auction has no reserve price, starting price check is skipped."""
        from apps.auctions.schemas import AttachItemRequest

        service, seller_id = self._make_service(auction_reserve=None)

        service._auction_repo.get_by_id = AsyncMock(
            side_effect=[
                _build_mock_auction(seller_id, None),
                RuntimeError("reload not needed for this test"),
            ]
        )

        data = AttachItemRequest(
            item_id=uuid.uuid4(),
            starting_price=Decimal("99999"),
            quantity=1,
        )
        with pytest.raises(RuntimeError, match="reload not needed"):
            await service.attach_item_to_auction(seller_id, uuid.uuid4(), data)


def _build_mock_auction(seller_id: uuid.UUID, reserve_price: Decimal | None):
    """Build a mock auction ORM object for service tests."""
    mock = MagicMock()
    mock.seller_id = seller_id
    mock.status = AuctionStatus.DRAFT
    mock.reserve_price = reserve_price
    mock.auction_items = []
    mock.bids = []
    mock.highest_bid = None
    mock.seller = MagicMock()
    mock.seller.first_name = "Test"
    mock.seller.last_name = "Seller"
    mock.seller.email = "seller@test.com"
    return mock
