"""Tests for users router endpoints.

Integration tests for user profile management, seller registration, and
seller verification endpoints.
"""

from unittest.mock import patch
from uuid import uuid4

import pytest


@pytest.mark.asyncio
class TestUsersRouter:
    """Test suite for users router endpoints."""

    async def test_get_me_requires_auth(self, client):
        """Test GET /api/v1/users/me requires authentication."""
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401

    async def test_get_me_returns_profile(self, client, auth_headers):
        """Test GET /api/v1/users/me returns user profile."""
        response = await client.get("/api/v1/users/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "profile" in data

    async def test_patch_me_updates_profile(self, client, auth_headers):
        """Test PATCH /api/v1/users/me updates profile."""
        update_data = {"bio": "Updated bio", "city": "Lagos"}

        response = await client.patch(
            "/api/v1/users/me", json=update_data, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["profile"]["bio"] == "Updated bio"
        assert data["profile"]["city"] == "Lagos"

    async def test_patch_me_requires_auth(self, client):
        """Test PATCH /api/v1/users/me requires authentication."""
        response = await client.patch("/api/v1/users/me", json={"bio": "test"})
        assert response.status_code == 401

    async def test_delete_me_deactivates_account(self, client, auth_headers):
        """Test DELETE /api/v1/users/me deactivates account."""
        response = await client.delete("/api/v1/users/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "deactivated" in data["message"].lower()

    async def test_get_public_profile_no_auth_required(self, client, test_user):
        """Test GET /api/v1/users/{user_id} works without auth."""
        response = await client.get(f"/api/v1/users/{test_user.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user.id)

    async def test_public_profile_has_no_email(self, client, test_user):
        """Test public profile excludes sensitive data."""
        response = await client.get(f"/api/v1/users/{test_user.id}")

        assert response.status_code == 200
        data = response.json()
        assert "email" not in data
        assert "phone_number" not in data
        assert "password_hash" not in data

    async def test_get_public_profile_returns_404_for_invalid_user(self, client):
        """Test GET /api/v1/users/{user_id} returns 404 for invalid user."""
        response = await client.get(f"/api/v1/users/{uuid4()}")
        assert response.status_code == 404

    async def test_register_as_seller_success(self, client, auth_headers):
        """Test POST /api/v1/users/me/seller-profile creates seller."""
        seller_data = {"seller_type": "CASUAL", "bio": "Casual seller"}

        response = await client.post(
            "/api/v1/users/me/seller-profile",
            json=seller_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["seller_type"] == "CASUAL"
        assert data["is_verified"] is False

    async def test_register_as_seller_requires_auth(self, client):
        """Test POST /api/v1/users/me/seller-profile requires auth."""
        response = await client.post(
            "/api/v1/users/me/seller-profile", json={"seller_type": "CASUAL"}
        )
        assert response.status_code == 401

    async def test_upload_verification_document_success(
        self, client, auth_headers, test_user, db_session
    ):
        """Test POST /api/v1/users/me/seller-profile/documents uploads."""
        from apps.users.models import SellerType
        from apps.users.schemas import RegisterSellerRequest
        from apps.users.service import UserService

        service = UserService(db_session)
        await service.register_as_seller(
            test_user.id,
            RegisterSellerRequest(seller_type=SellerType.CASUAL),
        )

        response = await client.post(
            "/api/v1/users/me/seller-profile/documents",
            params={
                "url": "https://example.com/doc.pdf",
                "doc_type": "National ID",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "National ID"
        assert data["url"] == "https://example.com/doc.pdf"

    @patch("apps.notifications.tasks.send_seller_verification_approved.delay")
    async def test_verify_seller_requires_admin_role(
        self, mock_task, client, auth_headers, test_user
    ):
        """Test PATCH /api/v1/users/{user_id}/seller-profile/verify needs."""
        verify_data = {"is_verified": True}

        response = await client.patch(
            f"/api/v1/users/{test_user.id}/seller-profile/verify",
            json=verify_data,
            headers=auth_headers,
        )

        assert response.status_code == 403

    @patch("apps.notifications.tasks.send_seller_verification_approved.delay")
    async def test_verify_seller_success_as_admin(
        self,
        mock_task,
        client,
        admin_auth_headers,
        test_user,
        db_session,
    ):
        """Test admin can verify seller."""
        from apps.users.models import SellerType
        from apps.users.schemas import RegisterSellerRequest
        from apps.users.service import UserService

        service = UserService(db_session)
        await service.register_as_seller(
            test_user.id,
            RegisterSellerRequest(seller_type=SellerType.RETAIL),
        )

        verify_data = {"is_verified": True}
        response = await client.patch(
            f"/api/v1/users/{test_user.id}/seller-profile/verify",
            json=verify_data,
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_verified"] is True

    async def test_get_wallet_returns_balance(self, client, auth_headers):
        """Test GET /api/v1/users/me/wallet returns wallet balance."""
        response = await client.get("/api/v1/users/me/wallet", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "available_funds" in data
        assert "currency" in data

    async def test_get_wallet_requires_auth(self, client):
        """Test GET /api/v1/users/me/wallet requires authentication."""
        response = await client.get("/api/v1/users/me/wallet")
        assert response.status_code == 401
