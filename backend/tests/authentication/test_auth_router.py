"""Integration tests for authentication API endpoints.

Exercises the FastAPI router, dependency injection, and service layer
by making asynchronous HTTP requests using ``httpx.AsyncClient``.
"""

from unittest.mock import patch

from httpx import AsyncClient

from apps.users.repository import UserRepository

# ---------------------------------------------------------------------------
# register()
# ---------------------------------------------------------------------------


async def test_register_endpoint_returns_201(client: AsyncClient):
    """Test that a valid registration request returns 201 Created and tokens.

    Args:
        client: Injected httpx AsyncClient for making requests.

    """
    payload = {
        "first_name": "Alice",
        "last_name": "Smith",
        "email": "alice_router@example.com",
        "phone_number": "08011112222",
        "password": "SecurePass1!",
        "confirm_password": "SecurePass1!",
    }

    with patch("apps.notifications.tasks.send_verification_email.delay") as mock_mail:
        response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "alice_router@example.com"
    mock_mail.assert_called_once()


# ---------------------------------------------------------------------------
# login()
# ---------------------------------------------------------------------------


async def test_login_endpoint_returns_200(client: AsyncClient):
    """Test that valid credentials return a 200 OK and access token.

    Args:
        client: Injected httpx AsyncClient for making requests.

    """
    reg_payload = {
        "first_name": "Bob",
        "last_name": "Jones",
        "email": "bob_router@example.com",
        "phone_number": "08022223333",
        "password": "SecurePass1!",
        "confirm_password": "SecurePass1!",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {"email": "bob_router@example.com", "password": "SecurePass1!"}
    response = await client.post("/api/v1/auth/login", json=login_payload)

    assert response.status_code == 200
    assert "access_token" in response.json()


# ---------------------------------------------------------------------------
# Security / Protected Routes
# ---------------------------------------------------------------------------


async def test_protected_endpoint_without_token_returns_401(client: AsyncClient):
    """Test that protected endpoints reject requests without Authorization header.

    Args:
        client: Injected httpx AsyncClient for making requests.

    """
    # This should return 401 because no Authorization header is provided
    response = await client.patch("/api/v1/auth/password", json={})
    assert response.status_code == 401


async def test_protected_endpoint_with_valid_token_returns_200(
    client: AsyncClient, db_session
):
    """Test that protected endpoints accept requests with a valid Bearer token.

    Verifies the user, creates a token, and attempts to change their password.

    Args:
        client: Injected httpx AsyncClient for making requests.
        db_session: Injected async database session for manual state updates.

    """
    # 1. Register a user
    reg_payload = {
        "first_name": "Secure",
        "last_name": "User",
        "email": "secure_router@example.com",
        "phone_number": "09012345675",
        "password": "SecurePass1!",
        "confirm_password": "SecurePass1!",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=reg_payload)
    print(f"Register Response: {reg_resp.json()}")
    user_id = reg_resp.json()["user"]["id"]
    token = reg_resp.json()["access_token"]

    # Manually verify the user in the DB to satisfy get_current_active_user
    user_repo = UserRepository(db_session)
    await user_repo.update(user_id, {"is_email_verified": True})
    await db_session.commit()

    # 2. Hit protected route with token
    headers = {"Authorization": f"Bearer {token}"}
    change_payload = {
        "old_password": "SecurePass1!",
        "new_password": "NewSecurePass1!",
        "confirm_password": "NewSecurePass1!",
    }

    response = await client.patch(
        "/api/v1/auth/password", json=change_payload, headers=headers
    )

    assert response.status_code == 200
