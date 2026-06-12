"""Middleware to inject standard security headers to all responses."""

import logging
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from config.settings import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleWare(BaseHTTPMiddleware):
    """Adds security headers to every HTTP response.

    Also handles Chrome's Private Network Access (PNA) preflight requests
    so that public origins (e.g. the Vercel frontend) are permitted to call
    the API when it is served via an ngrok tunnel or any other gateway that
    Chrome classifies as a ``local`` address space.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        # --- Private Network Access preflight ---
        # Chrome sends OPTIONS + ``Access-Control-Request-Private-Network: true``
        # before the real request.  We must reply with the allow header; if we
        # let it fall through to the route layer it may 405 or miss the header.
        if (
            request.method == "OPTIONS"
            and request.headers.get("Access-Control-Request-Private-Network") == "true"
        ):
            return Response(
                status_code=200,
                headers={"Access-Control-Allow-Private-Network": "true"},
            )

        response = await call_next(request)

        # Allow Chrome PNA on every response so real (non-preflight) requests
        # also satisfy the policy.
        response.headers["Access-Control-Allow-Private-Network"] = "true"

        # Prevent MIME Type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # Enable XSS protection filter in older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Restrict loading resources (CSP)
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        # Control how much referrer info is shared
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Restrict unused browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        # Force HTTPS in production (Strict-Transport-Security)
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response
