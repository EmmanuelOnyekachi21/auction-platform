"""Tests for UserService business logic.

Tests the service layer for user profile management, seller registration,
and verification operations.
"""

from unittest.mock import patch
from uuid import uuid4

import pytest

from apps.users.models import SellerType
from apps.users.schemas import (
    RegisterSellerRequest,
    UpdateProfileRequest,
    VerifySellerRequest,
)
from apps.users.service import UserService
from common.exceptions import (
    AlreadyExistsException,
    EmailNotVerifiedException,
    NotFoundException,
    SellerRequiredException,
    UserNotFoundException,
)


@pytest.mark.asyncio
class TestUserService:
    """Test suite for UserService."""

    async def test_get_my_profile_returns_user_data(self, db_session, test_user):
        """Test get_my_profile returns full user profile."""
        service = UserService(db_session)

        profile = await service.get_my_profile(test_user.id)

        assert profile.id == test_user.id
        assert profile.email == test_user.email
        assert profile.profile is not None

    async def test_get_my_profile_raises_not_found(self, db_session):
        """Test get_my_profile raises UserNotFoundException for invalid user."""
        service = UserService(db_session)

        with pytest.raises(UserNotFoundException):
            await service.get_my_profile(uuid4())

    async def test_update_profile_updates_only_provided_fields(
        self, db_session, test_user
    ):
        """Test update_my_profile updates only provided fields."""
        service = UserService(db_session)

        data = UpdateProfileRequest(bio="New bio", city="Lagos")

        updated = await service.update_my_profile(test_user.id, data)

        assert updated.profile.bio == "New bio"
        assert updated.profile.city == "Lagos"

    async def test_update_profile_ignores_none_fields(self, db_session, test_user):
        """Test update_my_profile ignores None fields."""
        service = UserService(db_session)

        data1 = UpdateProfileRequest(bio="Original bio")
        await service.update_my_profile(test_user.id, data1)

        data2 = UpdateProfileRequest(city="Abuja")
        updated = await service.update_my_profile(test_user.id, data2)

        assert updated.profile.bio == "Original bio"
        assert updated.profile.city == "Abuja"

    async def test_register_as_seller_success(self, db_session, test_user):
        """Test register_as_seller creates seller profile."""
        service = UserService(db_session)

        data = RegisterSellerRequest(seller_type=SellerType.INDIVIDUAL)

        seller_profile = await service.register_as_seller(test_user.id, data)

        assert seller_profile.seller_type == SellerType.INDIVIDUAL
        assert seller_profile.is_verified is False

    async def test_register_as_seller_requires_verified_email(self, db_session):
        """Test register_as_seller requires email verification."""
        from apps.users.models import UserRole
        from apps.users.repository import UserRepository

        repo = UserRepository(db_session)
        unverified_user = await repo.create(
            {
                "email": "unverified@test.com",
                "first_name": "unverified",
                "last_name": "unverified",
                "phone_number": "09027346046",
                "password_hash": "hash",
                "role": UserRole.USER,
                "is_email_verified": False,
            }
        )
        await db_session.commit()

        service = UserService(db_session)
        data = RegisterSellerRequest(seller_type=SellerType.INDIVIDUAL)

        with pytest.raises(EmailNotVerifiedException):
            await service.register_as_seller(unverified_user.id, data)

    async def test_register_as_seller_duplicate_raises_error(
        self, db_session, test_user
    ):
        """Test register_as_seller raises error on duplicate."""
        service = UserService(db_session)

        data = RegisterSellerRequest(seller_type=SellerType.INDIVIDUAL)

        await service.register_as_seller(test_user.id, data)

        with pytest.raises(AlreadyExistsException):
            await service.register_as_seller(test_user.id, data)

    async def test_get_public_profile_excludes_sensitive_data(
        self, db_session, test_user
    ):
        """Test get_public_profile excludes email and phone."""
        service = UserService(db_session)

        public_profile = await service.get_public_profile(test_user.id)

        assert public_profile.id == test_user.id
        assert public_profile.first_name == test_user.first_name
        assert not hasattr(public_profile, "email")
        assert not hasattr(public_profile, "phone_number")

    async def test_get_public_profile_raises_not_found(self, db_session):
        """Test get_public_profile raises UserNotFoundException."""
        service = UserService(db_session)

        with pytest.raises(UserNotFoundException):
            await service.get_public_profile(uuid4())

    @patch("apps.notifications.tasks.send_seller_verification_approved.delay")
    async def test_verify_seller_success(
        self, mock_task, db_session, test_user, test_admin
    ):
        """Test verify_seller approves seller and sends notification."""
        service = UserService(db_session)

        data = RegisterSellerRequest(seller_type=SellerType.BUSINESS)
        await service.register_as_seller(test_user.id, data)

        verify_data = VerifySellerRequest(is_verified=True)
        result = await service.verify_seller(test_user.id, verify_data, test_admin.id)

        assert result.is_verified is True
        mock_task.assert_called_once_with(test_user.email, test_user.first_name)

    @patch("apps.notifications.tasks.send_seller_verification_rejected.delay")
    async def test_verify_seller_rejection_sends_notification(
        self, mock_task, db_session, test_user, test_admin
    ):
        """Test verify_seller rejection sends notification with reason."""
        service = UserService(db_session)

        data = RegisterSellerRequest(seller_type=SellerType.BUSINESS)
        await service.register_as_seller(test_user.id, data)

        verify_data = VerifySellerRequest(
            is_verified=False, rejection_reason="Incomplete documents"
        )
        result = await service.verify_seller(test_user.id, verify_data, test_admin.id)

        assert result.is_verified is False
        mock_task.assert_called_once_with(
            test_user.email, test_user.first_name, "Incomplete documents"
        )

    async def test_verify_seller_requires_seller_profile(
        self, db_session, test_user, test_admin
    ):
        """Test verify_seller requires existing seller profile."""
        service = UserService(db_session)

        verify_data = VerifySellerRequest(is_verified=True)

        with pytest.raises(NotFoundException):
            await service.verify_seller(test_user.id, verify_data, test_admin.id)

    @patch("apps.auctions.cloudinary_service.CloudinaryService.upload_document")
    async def test_upload_verification_document_success(
        self, mock_upload, db_session, test_user
    ):
        """Test upload_verification_document creates document."""
        mock_upload.return_value = {
            "url": "https://example.com/doc.pdf",
            "public_id": "test_doc",
        }
        service = UserService(db_session)

        data = RegisterSellerRequest(seller_type=SellerType.BUSINESS)
        await service.register_as_seller(test_user.id, data)

        from io import BytesIO

        from fastapi import UploadFile

        dummy_file = UploadFile(
            filename="doc.pdf",
            file=BytesIO(b"dummy pdf content"),
            headers={"content-type": "application/pdf"},
        )

        doc = await service.upload_verification_document(
            test_user.id, dummy_file, "National ID"
        )

        assert doc.title == "National ID"
        assert doc.url == "https://example.com/doc.pdf"

    async def test_upload_verification_document_requires_seller_profile(
        self, db_session, test_user
    ):
        """Test upload_verification_document requires seller profile."""
        service = UserService(db_session)

        with pytest.raises(SellerRequiredException):
            await service.upload_verification_document(
                test_user.id, "https://example.com/doc.pdf", "National ID"
            )

    async def test_deactivate_account_success(self, db_session, test_user):
        """Test deactivate_account sets account status to deactivated."""
        service = UserService(db_session)

        result = await service.deactivate_account(test_user.id)

        assert result.message == "Account deactivated successfully"

        from apps.users.models import AccountStatus
        from apps.users.repository import UserRepository

        repo = UserRepository(db_session)
        user = await repo.get_by_id(test_user.id)
        assert user.account_status == AccountStatus.DEACTIVATED

    async def test_get_wallet_balance_returns_balance(self, db_session, test_user):
        """Test get_wallet_balance returns wallet data."""
        service = UserService(db_session)

        wallet = await service.get_wallet_balance(test_user.id)

        assert "available_funds" in wallet.model_dump()
        assert "locked_funds" in wallet.model_dump()
        assert "escrow_funds" in wallet.model_dump()
        assert "currency" in wallet.model_dump()
