"""Middleware to inject standard security headers to all responses."""

import logging
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from config.settings import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleWare(BaseHTTPMiddleware):
    """Adds security headers to every HTTP response."""

    async def dispatch(self, request: Request, call_next: Callable):

        response = await call_next(request)

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
