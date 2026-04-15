"""Tests for auction duration cap (Phase 6.10).

Covers schema validation and service-layer defence for the 24-hour
maximum auction duration rule.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.auctions.schemas import CreateAuctionRequest, UpdateAuctionRequest
from common.exceptions import ValidationException

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def future(hours: float = 1) -> datetime:
    """Return a UTC datetime `hours` from now."""
    return datetime.now(timezone.utc) + timedelta(hours=hours)


def make_create_payload(start_offset_hours=1, duration_hours=6) -> dict:
    """Build a valid ``CreateAuctionRequest`` payload dictionary.

    Args:
        start_offset_hours: Hours from now for ``starts_at``.
        duration_hours: Auction duration in hours.

    Returns:
        A dictionary suitable for ``CreateAuctionRequest(**payload)``.

    """
    start = future(start_offset_hours)
    return dict(
        starts_at=start,
        ends_at=start + timedelta(hours=duration_hours),
        bid_increment=Decimal("100.00"),
    )


# ---------------------------------------------------------------------------
# Schema — CreateAuctionRequest
# ---------------------------------------------------------------------------


class TestCreateAuctionRequestDurationValidation:
    """Schema validation tests for ``CreateAuctionRequest`` duration rules."""

    def test_24_hour_auction_is_accepted(self):
        """A 24-hour auction should pass schema validation."""
        data = make_create_payload(duration_hours=24)
        req = CreateAuctionRequest(**data)
        assert req.ends_at == data["ends_at"]

    def test_6_hour_auction_is_accepted(self):
        """A 6-hour auction should pass schema validation."""
        data = make_create_payload(duration_hours=6)
        req = CreateAuctionRequest(**data)
        assert req.ends_at == data["ends_at"]

    def test_1_hour_auction_is_accepted(self):
        """A 1-hour auction (minimum) should pass schema validation."""
        data = make_create_payload(duration_hours=1)
        req = CreateAuctionRequest(**data)
        assert req.ends_at == data["ends_at"]

    def test_25_hour_auction_is_rejected(self):
        """A 25-hour auction should be rejected for exceeding the cap."""
        data = make_create_payload(duration_hours=25)
        with pytest.raises(Exception, match="cannot exceed 24 hours"):
            CreateAuctionRequest(**data)

    def test_30_day_auction_is_rejected(self):
        """A 30-day auction should be rejected for exceeding the cap."""
        data = make_create_payload(duration_hours=24 * 30)
        with pytest.raises(Exception, match="cannot exceed 24 hours"):
            CreateAuctionRequest(**data)

    def test_30_minute_auction_is_rejected(self):
        """A 30-minute auction should be rejected for being below the minimum."""
        start = future(1)
        with pytest.raises(Exception, match="at least"):
            CreateAuctionRequest(
                starts_at=start,
                ends_at=start + timedelta(minutes=30),
                bid_increment=Decimal("100.00"),
            )

    def test_starts_at_in_past_is_rejected(self):
        """An auction starting in the past should be rejected."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        with pytest.raises(Exception, match="future"):
            CreateAuctionRequest(
                starts_at=past,
                ends_at=past + timedelta(hours=6),
                bid_increment=Decimal("100.00"),
            )

    def test_ends_at_before_starts_at_is_rejected(self):
        """An auction ending before it starts should be rejected."""
        start = future(2)
        with pytest.raises(Exception):
            CreateAuctionRequest(
                starts_at=start,
                ends_at=start - timedelta(hours=1),
                bid_increment=Decimal("100.00"),
            )


# ---------------------------------------------------------------------------
# Schema — UpdateAuctionRequest
# ---------------------------------------------------------------------------


class TestUpdateAuctionRequestDurationValidation:
    """Schema validation tests for ``UpdateAuctionRequest`` duration rules."""

    def test_valid_update_both_times(self):
        """Updating both times within the cap should pass."""
        start = future(1)
        req = UpdateAuctionRequest(
            starts_at=start,
            ends_at=start + timedelta(hours=12),
        )
        assert req.ends_at is not None

    def test_update_exceeding_24_hours_is_rejected(self):
        """Updating both times to exceed the cap should be rejected."""
        start = future(1)
        with pytest.raises(Exception, match="cannot exceed 24 hours"):
            UpdateAuctionRequest(
                starts_at=start,
                ends_at=start + timedelta(hours=25),
            )

    def test_update_with_only_starts_at_skips_duration_check(self):
        """Partial update with only starts_at should not raise."""
        req = UpdateAuctionRequest(starts_at=future(2))
        assert req.starts_at is not None

    def test_update_with_only_ends_at_skips_duration_check(self):
        """Partial update with only ends_at should not raise."""
        req = UpdateAuctionRequest(ends_at=future(10))
        assert req.ends_at is not None


# ---------------------------------------------------------------------------
# Service — create_auction second gate
# ---------------------------------------------------------------------------


class TestCreateAuctionServiceGate:
    """Service-layer second gate tests for the 24-hour duration cap.

    The service re-checks duration after schema validation as a defence-in-depth
    measure. We bypass the schema by passing a pre-validated object with a
    mutated ``ends_at`` to simulate a rogue call reaching the service directly.
    """

    @pytest.mark.asyncio
    async def test_service_rejects_duration_exceeding_24_hours(self):
        """Service should raise ValidationException for duration > 24 hours."""
        from apps.auctions.service import AuctionService

        db = AsyncMock()
        service = AuctionService(db)

        data = make_create_payload(duration_hours=24)
        req = CreateAuctionRequest(**data)
        req.ends_at = req.starts_at + timedelta(hours=25)

        with pytest.raises(ValidationException, match="cannot exceed 24 hours"):
            await service.create_auction(seller_id=MagicMock(), data=req)

    @pytest.mark.asyncio
    async def test_service_accepts_valid_24_hour_auction(self):
        """Service should accept a valid 24-hour auction."""
        from apps.auctions.service import AuctionService

        db = AsyncMock()
        service = AuctionService(db)

        data = make_create_payload(duration_hours=24)
        req = CreateAuctionRequest(**data)

        mock_auction = MagicMock()
        mock_auction.id = MagicMock()

        service._auction_repo.create_auction = AsyncMock(return_value=mock_auction)
        service._auction_repo.get_by_id = AsyncMock(return_value=mock_auction)

        with patch(
            "apps.auctions.service.AuctionResponse.model_validate",
            return_value=MagicMock(),
        ):
            result = await service.create_auction(seller_id=MagicMock(), data=req)

        assert result is not None
