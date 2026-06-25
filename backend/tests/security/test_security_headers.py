"""Security headers middleware tests.

Tests SecurityHeadersMiddleWare directly with a minimal Starlette app.
The patch must be active during the request (dispatch time), not just
at app construction time, because the middleware reads settings.app_env
on every response.
"""

from unittest.mock import patch

from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route
from starlette.testclient import TestClient

from common.security_headers import SecurityHeadersMiddleWare


def _make_app() -> Starlette:
    """Build a minimal Starlette app with SecurityHeadersMiddleWare."""

    async def homepage(request):
        return Response("ok")

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(SecurityHeadersMiddleWare)
    return app


def test_security_headers_present_in_production():
    """All security headers including HSTS must be present in production."""
    with patch("common.security_headers.settings") as mock_settings:
        mock_settings.app_env = "production"
        response = TestClient(_make_app()).get("/")

    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "Content-Security-Policy" in response.headers
    assert "Referrer-Policy" in response.headers
    assert "Strict-Transport-Security" in response.headers
    assert "max-age=31536000" in response.headers["Strict-Transport-Security"]


def test_hsts_header_only_in_production():
    """HSTS must be absent in development and present in production."""
    with patch("common.security_headers.settings") as mock_settings:
        mock_settings.app_env = "development"
        dev_response = TestClient(_make_app()).get("/")
    assert "Strict-Transport-Security" not in dev_response.headers

    with patch("common.security_headers.settings") as mock_settings:
        mock_settings.app_env = "production"
        prod_response = TestClient(_make_app()).get("/")
    assert "Strict-Transport-Security" in prod_response.headers


def test_security_headers_present_in_development():
    """Non-HSTS headers must be present in development too."""
    with patch("common.security_headers.settings") as mock_settings:
        mock_settings.app_env = "development"
        response = TestClient(_make_app()).get("/")

    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "Content-Security-Policy" in response.headers
    assert "Referrer-Policy" in response.headers
