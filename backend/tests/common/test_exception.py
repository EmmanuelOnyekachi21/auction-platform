"""Tests for global exception handlers.

Registers temporary routes on the live ``app`` instance that deliberately
raise specific exceptions, then asserts that the global handlers return
the correct HTTP status codes and ``ErrorResponse`` payloads.
"""

from fastapi import APIRouter

from common.exceptions import AuctionNotFoundException, InsufficientFundsException
from main import app

# Temporary router used only within this test module to trigger exceptions.
test_router = APIRouter()


@test_router.get("/test/auction-not-found")
async def raise_auction_not_found():
    """Raise ``AuctionNotFoundException`` to exercise the 404 handler."""
    raise AuctionNotFoundException()


@test_router.get("/test/insufficient-funds")
async def raise_insufficient_funds():
    """Raise ``InsufficientFundsException`` to exercise the 422 handler."""
    raise InsufficientFundsException()


@test_router.get("/test/unhandled")
async def raise_unhandled():
    """Raise a bare ``RuntimeError`` to exercise the generic 500 handler."""
    raise RuntimeError("something broke internally")


app.include_router(test_router)


async def test_auction_not_found_returns_404(client):
    """AuctionNotFoundException should produce a 404 with AUCTION_NOT_FOUND code."""
    response = await client.get("/test/auction-not-found")
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["code"] == "AUCTION_NOT_FOUND"


async def test_insufficient_funds_returns_422(client):
    """InsufficientFundsException should produce a 422 with INSUFFICIENT_FUNDS code."""
    response = await client.get("/test/insufficient-funds")
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == "error"
    assert data["code"] == "INSUFFICIENT_FUNDS"


async def test_unhandled_exception_returns_500(client):
    """Unhandled exceptions should produce a 500 without leaking internal details."""
    response = await client.get("/test/unhandled")
    assert response.status_code == 500
    data = response.json()
    assert data["status"] == "error"
    assert data["code"] == "INTERNAL_SERVER_ERROR"
    assert "something broke internally" not in data["message"]
