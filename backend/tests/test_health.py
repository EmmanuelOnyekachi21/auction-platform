"""Tests for health check endpoints."""


async def test_health_returns_200(client):
    """GET /health should return HTTP 200."""
    response = await client.get("/health")
    assert response.status_code == 200


async def test_health_contains_app_name(client):
    """GET /health response body should include the app name."""
    response = await client.get("/health")
    data = response.json()
    assert data["app"] == "auction-platform"


async def test_health_contains_status(client):
    """GET /health response body should report status 'ok'."""
    response = await client.get("/health")
    data = response.json()
    assert data["status"] == "ok"


async def test_health_database_connected(client):
    """GET /health response body should include a database_connected field."""
    response = await client.get("/health")
    data = response.json()
    assert "database_connected" in data
