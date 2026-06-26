"""Tests for UserRepository profile and seller methods.

Tests the data access layer for user profiles, seller profiles, and
related database operations.
"""

from uuid import uuid4

import pytest

from apps.users.enums import SellerType
from apps.users.repository import UserRepository
from common.exceptions import AlreadyExistsException


@pytest.mark.asyncio
class TestUserRepository:
    """Test suite for UserRepository profile and seller methods."""

    async def test_get_with_profile_returns_user_with_profile(
        self, db_session, test_user
    ):
        """Test get_with_profile loads user and profile in single query."""
        repo = UserRepository(db_session)

        user = await repo.get_with_profile(test_user.id)
        await db_session.commit()

        assert user is not None
        assert user.id == test_user.id
        assert user.profile is not None
        assert user.profile.user_id == test_user.id

    async def test_get_with_profile_returns_none_for_nonexistent_user(self, db_session):
        """Test get_with_profile returns None for invalid user_id."""
        repo = UserRepository(db_session)

        user = await repo.get_with_profile(uuid4())

        assert user is None

    async def test_update_profile_updates_only_provided_fields(
        self, db_session, test_user
    ):
        """Test update_profile updates only fields in data dict."""
        repo = UserRepository(db_session)

        updated_profile = await repo.update_profile(
            test_user.id, {"bio": "New bio", "city": "Lagos"}
        )
        await db_session.commit()

        assert updated_profile.bio == "New bio"
        assert updated_profile.city == "Lagos"
        assert updated_profile.state is None

    async def test_update_profile_ignores_none_values(self, db_session, test_user):
        """Test update_profile ignores None values in data dict."""
        repo = UserRepository(db_session)

        await repo.update_profile(test_user.id, {"bio": "Original bio"})
        await db_session.commit()

        updated_profile = await repo.update_profile(
            test_user.id, {"bio": None, "city": "Abuja"}
        )
        await db_session.commit()

        assert updated_profile.bio == "Original bio"
        assert updated_profile.city == "Abuja"

    async def test_create_seller_profile_success(self, db_session, test_user):
        """Test create_seller_profile creates new seller profile."""
        repo = UserRepository(db_session)

        seller_profile = await repo.create_seller_profile(
            test_user.id, {"seller_type": SellerType.INDIVIDUAL}
        )
        await db_session.commit()

        assert seller_profile is not None
        assert seller_profile.user_id == test_user.id
        assert seller_profile.seller_type == SellerType.INDIVIDUAL
        assert seller_profile.is_verified is False

    async def test_create_seller_profile_raises_on_duplicate(
        self, db_session, test_user
    ):
        """Test create_seller_profile raises error if profile exists."""
        repo = UserRepository(db_session)

        await repo.create_seller_profile(
            test_user.id, {"seller_type": SellerType.INDIVIDUAL}
        )
        await db_session.commit()

        with pytest.raises(AlreadyExistsException) as exc_info:
            await repo.create_seller_profile(
                test_user.id, {"seller_type": SellerType.BUSINESS}
            )

        assert "already exists" in str(exc_info.value).lower()

    async def test_get_seller_profile_returns_profile(self, db_session, test_user):
        """Test get_seller_profile returns existing seller profile."""
        repo = UserRepository(db_session)

        created = await repo.create_seller_profile(
            test_user.id, {"seller_type": SellerType.BUSINESS}
        )
        await db_session.commit()

        fetched = await repo.get_seller_profile(test_user.id)

        assert fetched is not None
        assert fetched.id == created.id

    async def test_get_seller_profile_returns_none_if_not_exists(
        self, db_session, test_user
    ):
        """Test get_seller_profile returns None if no seller profile."""
        repo = UserRepository(db_session)

        seller_profile = await repo.get_seller_profile(test_user.id)

        assert seller_profile is None

    async def test_update_seller_verification_sets_verified_true(
        self, db_session, test_user, test_admin
    ):
        """Test update_seller_verification sets is_verified to True."""
        repo = UserRepository(db_session)

        await repo.create_seller_profile(
            test_user.id, {"seller_type": SellerType.BUSINESS}
        )
        await db_session.commit()

        updated = await repo.update_seller_verification(
            test_user.id, is_verified=True, verified_by_id=test_admin.id
        )
        await db_session.commit()

        assert updated.is_verified is True
        assert updated.verified_by_id == test_admin.id
        assert updated.verified_at is not None

    async def test_update_seller_verification_sets_verified_false(
        self, db_session, test_user, test_admin
    ):
        """Test update_seller_verification can set is_verified to False."""
        repo = UserRepository(db_session)

        await repo.create_seller_profile(
            test_user.id, {"seller_type": SellerType.INDIVIDUAL}
        )
        await db_session.commit()

        updated = await repo.update_seller_verification(
            test_user.id, is_verified=False, verified_by_id=test_admin.id
        )
        await db_session.commit()

        assert updated.is_verified is False
        assert updated.verified_at is None

    async def test_get_public_profile_loads_relationships(self, db_session, test_user):
        """Test get_public_profile loads profile and seller_profile."""
        repo = UserRepository(db_session)

        await repo.update_profile(test_user.id, {"bio": "Public bio"})
        await db_session.commit()

        await repo.create_seller_profile(
            test_user.id, {"seller_type": SellerType.BUSINESS}
        )
        await db_session.commit()

        user = await repo.get_public_profile(test_user.id)

        assert user is not None
        assert user.profile is not None
        assert user.profile.bio == "Public bio"
        assert user.seller_profile is not None

    async def test_get_public_profile_returns_none_for_invalid_user(self, db_session):
        """Test get_public_profile returns None for nonexistent user."""
        repo = UserRepository(db_session)

        user = await repo.get_public_profile(uuid4())

        assert user is None
