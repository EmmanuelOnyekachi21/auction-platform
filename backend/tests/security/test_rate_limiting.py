"""Rate limiting integration tests.

Verifies that slowapi enforces the limits declared on each endpoint and
that the 429 response matches the platform error envelope.

Each test flushes the Redis rate-limit keys before running so limits from
previous tests (or previous runs) don't bleed in.
"""

from unittest.mock import patch

import redis
from httpx import AsyncClient

from config.settings import settings


def _flush_rate_limit_keys():
    """Delete all slowapi rate-limit keys from Redis before a test."""
    r = redis.from_url(settings.redis_url)
    # slowapi stores keys with the prefix "LIMITER/"
    keys = r.keys("LIMITER/*")
    if keys:
        r.delete(*keys)
    r.close()


# ---------------------------------------------------------------------------
# Login — 5/minute
# ---------------------------------------------------------------------------


async def test_login_rate_limit_enforced(client: AsyncClient):
    """6th login attempt within a minute must return 429.

    Limit is 5/minute. We send 5 requests (all fail with 401 — wrong
    password, but that's fine) then verify the 6th gets 429.
    """
    _flush_rate_limit_keys()

    payload = {"email": "nonexistent@example.com", "password": "wrong"}

    for _ in range(5):
        await client.post("/api/v1/auth/login", json=payload)

    response = await client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 429
    data = response.json()
    assert data["code"] == "RATE_LIMIT_EXCEEDED"
    assert data["status"] == "error"


# ---------------------------------------------------------------------------
# Register — 3/minute
# ---------------------------------------------------------------------------


async def test_register_rate_limit_enforced(client: AsyncClient):
    """4th register attempt within a minute must return 429.

    Limit is 3/minute. First 3 may succeed or fail (duplicate email) —
    we only care that the 4th is blocked at the rate-limit layer.
    """
    _flush_rate_limit_keys()

    base_payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "ratelimit_reg@example.com",
        "phone_number": "08099990001",
        "password": "SecurePass1!",
        "confirm_password": "SecurePass1!",
    }

    with patch("apps.notifications.tasks.send_verification_email.delay"):
        for _ in range(3):
            await client.post("/api/v1/auth/register", json=base_payload)

        response = await client.post("/api/v1/auth/register", json=base_payload)

    assert response.status_code == 429
    data = response.json()
    assert data["code"] == "RATE_LIMIT_EXCEEDED"


# ---------------------------------------------------------------------------
# Forgot password — 3/minute
# ---------------------------------------------------------------------------


async def test_forgot_password_rate_limit_enforced(client: AsyncClient):
    """4th forgot-password request within a minute must return 429."""
    _flush_rate_limit_keys()

    payload = {"email": "anyone@example.com"}

    for _ in range(3):
        await client.post("/api/v1/auth/forgot-password", json=payload)

    response = await client.post("/api/v1/auth/forgot-password", json=payload)

    assert response.status_code == 429
    assert response.json()["code"] == "RATE_LIMIT_EXCEEDED"


# ---------------------------------------------------------------------------
# Webhook — 100/minute (should not block legitimate traffic)
# ---------------------------------------------------------------------------


async def test_webhook_not_overly_restricted(client: AsyncClient):
    """Paystack webhook allows at least 10 rapid requests without 429.

    We don't send 100 requests (slow), but verify the limit is high
    enough that normal webhook bursts are not blocked.
    """
    _flush_rate_limit_keys()

    # Send 10 requests — all will fail auth (no valid signature) with 401,
    # but none should be rate-limited at this volume.
    for i in range(10):
        response = await client.post(
            "/api/v1/wallets/webhooks/paystack",
            content=b"{}",
            headers={"content-type": "application/json"},
        )
        assert (
            response.status_code != 429
        ), f"Webhook was rate-limited on request {i + 1} — limit is too low"
