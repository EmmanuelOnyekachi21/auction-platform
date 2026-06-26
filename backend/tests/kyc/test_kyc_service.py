"""Tests for KYC service — tier enforcement, BVN verification, limit checks."""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.users.enums import KYCTier
from apps.users.kyc_service import KYCService
from common.exceptions import PermissionDeniedException, ValidationException

# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_kyc_profile(
    tier: KYCTier = KYCTier.TIER_1,
    tier_1_completed_at=None,
    tier_2_completed_at=None,
    tier_3_completed_at=None,
    bvn_verified: bool = False,
    bvn_attempt_count: int = 0,
    bvn_attempt_reset_at=None,
):
    profile = MagicMock()
    profile.current_tier = tier
    profile.tier_1_completed_at = tier_1_completed_at
    profile.tier_2_completed_at = tier_2_completed_at
    profile.tier_3_completed_at = tier_3_completed_at
    profile.bvn_verified = bvn_verified
    profile.bvn_attempt_count = bvn_attempt_count
    profile.bvn_attempt_reset_at = bvn_attempt_reset_at
    return profile


def _make_user(kyc_tier: KYCTier = KYCTier.TIER_1):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.first_name = "Test"
    user.last_name = "User"
    user.email = "test@example.com"
    user.kyc_tier = kyc_tier
    return user


def _make_service(kyc_profile=None, user=None):
    """Build a KYCService with fully mocked dependencies."""
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    service = KYCService(db)

    service._kyc = MagicMock()
    service._kyc.get_by_user_id = AsyncMock(return_value=kyc_profile)
    service._kyc.create_for_user = AsyncMock(
        return_value=kyc_profile or _make_kyc_profile()
    )
    service._kyc.check_and_increment_bvn_attempts = AsyncMock()
    service._kyc.check_bvn_already_registered = AsyncMock(return_value=False)
    service._kyc.initiate_bvn_verification = AsyncMock()
    service._kyc.complete_tier_2 = AsyncMock()
    service._kyc.reject_verification = AsyncMock()
    service._kyc.get_daily_withdrawal_total = AsyncMock(return_value=Decimal("0"))

    service._bvn = MagicMock()
    service._bvn.hash_bvn = MagicMock(return_value="abc123hash")
    service._bvn.verify_bvn = AsyncMock(
        return_value={"is_match": True, "reference": "mock-ref-001", "message": "OK"}
    )

    # Patch UserRepository inside service
    mock_user_repo = MagicMock()
    mock_user_repo.get_by_id = AsyncMock(return_value=user or _make_user())
    service._user_repo_mock = mock_user_repo

    return service, mock_user_repo


# ─── get_kyc_status ──────────────────────────────────────────────────────────


class TestGetKYCStatus:

    @pytest.mark.asyncio
    async def test_returns_tier_1_status(self):
        from datetime import datetime, timezone

        profile = _make_kyc_profile(
            tier=KYCTier.TIER_1,
            tier_1_completed_at=datetime.now(timezone.utc),
        )
        service, _ = _make_service(kyc_profile=profile)

        result = await service.get_kyc_status(uuid.uuid4())

        assert result.current_tier == "TIER_1"
        assert result.tier_1_complete is True
        assert result.tier_2_complete is False
        assert result.tier_3_complete is False

    @pytest.mark.asyncio
    async def test_returns_tier_2_status(self):
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        profile = _make_kyc_profile(
            tier=KYCTier.TIER_2,
            tier_1_completed_at=now,
            tier_2_completed_at=now,
        )
        service, _ = _make_service(kyc_profile=profile)

        result = await service.get_kyc_status(uuid.uuid4())

        assert result.current_tier == "TIER_2"
        assert result.tier_2_complete is True

    @pytest.mark.asyncio
    async def test_creates_profile_if_missing(self):
        service, _ = _make_service(kyc_profile=None)
        service._kyc.get_by_user_id = AsyncMock(return_value=None)
        new_profile = _make_kyc_profile()
        service._kyc.create_for_user = AsyncMock(return_value=new_profile)

        result = await service.get_kyc_status(uuid.uuid4())

        service._kyc.create_for_user.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_tier_1_limits_returned(self):
        profile = _make_kyc_profile(tier=KYCTier.TIER_1)
        service, _ = _make_service(kyc_profile=profile)

        result = await service.get_kyc_status(uuid.uuid4())

        assert (
            result.limits.max_bid
            == service._get_limits_for_tier(KYCTier.TIER_1).max_bid
        )

    @pytest.mark.asyncio
    async def test_tier_2_limits_returned(self):
        from datetime import datetime, timezone

        profile = _make_kyc_profile(
            tier=KYCTier.TIER_2,
            tier_2_completed_at=datetime.now(timezone.utc),
        )
        service, _ = _make_service(kyc_profile=profile)

        result = await service.get_kyc_status(uuid.uuid4())

        assert (
            result.limits.max_bid
            == service._get_limits_for_tier(KYCTier.TIER_2).max_bid
        )

    @pytest.mark.asyncio
    async def test_tier_1_next_steps_not_empty(self):
        profile = _make_kyc_profile(tier=KYCTier.TIER_1)
        service, _ = _make_service(kyc_profile=profile)

        result = await service.get_kyc_status(uuid.uuid4())

        assert len(result.next_steps) > 0

    @pytest.mark.asyncio
    async def test_tier_3_next_steps_empty(self):
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        profile = _make_kyc_profile(
            tier=KYCTier.TIER_3,
            tier_1_completed_at=now,
            tier_2_completed_at=now,
            tier_3_completed_at=now,
        )
        service, _ = _make_service(kyc_profile=profile)

        result = await service.get_kyc_status(uuid.uuid4())

        assert result.next_steps == []


# ─── verify_bvn ──────────────────────────────────────────────────────────────


class TestVerifyBVN:

    @pytest.mark.asyncio
    async def test_successful_verification_upgrades_tier(self):
        profile = _make_kyc_profile(tier=KYCTier.TIER_1)
        user = _make_user(kyc_tier=KYCTier.TIER_1)
        service, mock_user_repo = _make_service(kyc_profile=profile, user=user)

        with patch("apps.users.repository.UserRepository", return_value=mock_user_repo):
            await service.verify_bvn(user.id, "12345678901", "1990-01-01")

        service._kyc.complete_tier_2.assert_called_once_with(user.id)

    @pytest.mark.asyncio
    async def test_bvn_already_registered_raises(self):
        profile = _make_kyc_profile()
        user = _make_user()
        service, mock_user_repo = _make_service(kyc_profile=profile, user=user)
        service._kyc.check_bvn_already_registered = AsyncMock(return_value=True)

        with patch("apps.users.repository.UserRepository", return_value=mock_user_repo):
            with pytest.raises(ValidationException, match="already associated"):
                await service.verify_bvn(user.id, "12345678901", "1990-01-01")

    @pytest.mark.asyncio
    async def test_bvn_mismatch_calls_reject_and_raises(self):
        profile = _make_kyc_profile()
        user = _make_user()
        service, mock_user_repo = _make_service(kyc_profile=profile, user=user)
        service._bvn.verify_bvn = AsyncMock(
            return_value={
                "is_match": False,
                "reference": "ref-fail",
                "message": "No match",
            }
        )

        with patch("apps.users.repository.UserRepository", return_value=mock_user_repo):
            with pytest.raises(ValidationException, match="verification failed"):
                await service.verify_bvn(user.id, "12345678901", "1990-01-01")

        service._kyc.reject_verification.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_checked_before_api_call(self):
        profile = _make_kyc_profile()
        user = _make_user()
        service, mock_user_repo = _make_service(kyc_profile=profile, user=user)
        service._kyc.check_and_increment_bvn_attempts = AsyncMock(
            side_effect=ValidationException(
                message="Maximum BVN verification attempts reached"
            )
        )

        with patch("apps.users.repository.UserRepository", return_value=mock_user_repo):
            with pytest.raises(ValidationException, match="attempts"):
                await service.verify_bvn(user.id, "12345678901", "1990-01-01")

        # BVN API should NOT have been called
        service._bvn.verify_bvn.assert_not_called()


# ─── check_bid_limit ─────────────────────────────────────────────────────────


class TestCheckBidLimit:

    @pytest.mark.asyncio
    async def test_tier_1_bid_within_limit_passes(self):
        user = _make_user(kyc_tier=KYCTier.TIER_1)
        service, mock_user_repo = _make_service(user=user)

        with patch("apps.users.repository.UserRepository", return_value=mock_user_repo):
            # Should not raise
            await service.check_bid_limit(user.id, Decimal("10000"))

    @pytest.mark.asyncio
    async def test_tier_1_bid_exceeds_limit_raises(self):
        user = _make_user(kyc_tier=KYCTier.TIER_1)
        service, mock_user_repo = _make_service(user=user)

        with patch("apps.users.repository.UserRepository", return_value=mock_user_repo):
            with pytest.raises(PermissionDeniedException, match="KYC tier"):
                await service.check_bid_limit(user.id, Decimal("60000"))

    @pytest.mark.asyncio
    async def test_tier_2_bid_above_tier_1_limit_passes(self):
        user = _make_user(kyc_tier=KYCTier.TIER_2)
        service, mock_user_repo = _make_service(user=user)

        with patch("apps.users.repository.UserRepository", return_value=mock_user_repo):
            # ₦60,000 exceeds Tier 1 but is within Tier 2
            await service.check_bid_limit(user.id, Decimal("60000"))


# ─── check_withdrawal_limit ──────────────────────────────────────────────────


class TestCheckWithdrawalLimit:

    @pytest.mark.asyncio
    async def test_tier_1_withdrawal_blocked(self):
        user = _make_user(kyc_tier=KYCTier.TIER_1)
        service, mock_user_repo = _make_service(user=user)

        with patch("apps.users.repository.UserRepository", return_value=mock_user_repo):
            with pytest.raises(PermissionDeniedException, match="BVN verification"):
                await service.check_withdrawal_limit(user.id, Decimal("1000"))

    @pytest.mark.asyncio
    async def test_tier_2_withdrawal_within_daily_limit_passes(self):
        user = _make_user(kyc_tier=KYCTier.TIER_2)
        service, mock_user_repo = _make_service(user=user)
        service._kyc.get_daily_withdrawal_total = AsyncMock(return_value=Decimal("0"))

        with patch("apps.users.repository.UserRepository", return_value=mock_user_repo):
            await service.check_withdrawal_limit(user.id, Decimal("100000"))

    @pytest.mark.asyncio
    async def test_tier_2_daily_limit_exceeded_raises(self):
        user = _make_user(kyc_tier=KYCTier.TIER_2)
        service, mock_user_repo = _make_service(user=user)
        # Already withdrawn ₦450,000 today, trying to withdraw ₦100,000 more
        service._kyc.get_daily_withdrawal_total = AsyncMock(
            return_value=Decimal("450000")
        )

        with patch("apps.users.repository.UserRepository", return_value=mock_user_repo):
            with pytest.raises(
                PermissionDeniedException, match="Daily withdrawal limit"
            ):
                await service.check_withdrawal_limit(user.id, Decimal("100000"))


# ─── check_funding_limit ─────────────────────────────────────────────────────


class TestCheckFundingLimit:

    @pytest.mark.asyncio
    async def test_tier_1_funding_within_limit_passes(self):
        user = _make_user(kyc_tier=KYCTier.TIER_1)
        service, mock_user_repo = _make_service(user=user)

        with patch("apps.users.repository.UserRepository", return_value=mock_user_repo):
            await service.check_funding_limit(user.id, Decimal("50000"), Decimal("0"))

    @pytest.mark.asyncio
    async def test_tier_1_funding_exceeds_wallet_limit_raises(self):
        user = _make_user(kyc_tier=KYCTier.TIER_1)
        service, mock_user_repo = _make_service(user=user)

        with patch("apps.users.repository.UserRepository", return_value=mock_user_repo):
            # Current balance ₦80,000 + deposit ₦50,000 = ₦130,000 > ₦100,000 limit
            with pytest.raises(PermissionDeniedException, match="wallet limit"):
                await service.check_funding_limit(
                    user.id, Decimal("50000"), Decimal("80000")
                )

    @pytest.mark.asyncio
    async def test_tier_2_higher_wallet_limit_passes(self):
        user = _make_user(kyc_tier=KYCTier.TIER_2)
        service, mock_user_repo = _make_service(user=user)

        with patch("apps.users.repository.UserRepository", return_value=mock_user_repo):
            # ₦80,000 + ₦50,000 = ₦130,000 — fine for Tier 2 (limit ₦2,000,000)
            await service.check_funding_limit(
                user.id, Decimal("50000"), Decimal("80000")
            )


# ─── BVNService unit tests ────────────────────────────────────────────────────


class TestBVNService:

    def test_hash_bvn_returns_64_char_hex(self):
        from apps.users.bvn_service import BVNService

        service = BVNService()
        result = service.hash_bvn("12345678901")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_same_bvn_always_produces_same_hash(self):
        from apps.users.bvn_service import BVNService

        service = BVNService()
        assert service.hash_bvn("12345678901") == service.hash_bvn("12345678901")

    def test_different_bvns_produce_different_hashes(self):
        from apps.users.bvn_service import BVNService

        service = BVNService()
        assert service.hash_bvn("12345678901") != service.hash_bvn("12345678902")

    def test_invalid_bvn_format_raises(self):
        from apps.users.bvn_service import BVNService

        service = BVNService()
        with pytest.raises(ValidationException, match="11 numeric"):
            service.validate_bvn_format("1234")

    def test_non_numeric_bvn_raises(self):
        from apps.users.bvn_service import BVNService

        service = BVNService()
        with pytest.raises(ValidationException, match="11 numeric"):
            service.validate_bvn_format("1234567890a")

    @pytest.mark.asyncio
    async def test_mock_mode_returns_success(self):
        from apps.users.bvn_service import BVNService

        with patch("apps.users.bvn_service.settings") as mock_settings:
            mock_settings.bvn_verification_enabled = False
            service = BVNService()
            result = await service.verify_bvn(
                "12345678901", "Test", "User", "1990-01-01"
            )
        assert result["is_match"] is True
        assert "reference" in result
