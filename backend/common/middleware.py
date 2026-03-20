"""Custom Starlette middleware for the auction platform.

Currently provides:
- ``RequestLoggingMiddleware``: logs every inbound request and its
  completed response, attaching a unique ``X-Request-ID`` header for
  distributed tracing.
"""

import logging
import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs request/response details and injects a request ID.

    For every HTTP request the middleware:

    1. Reads the ``X-Request-ID`` header if present, or generates a new
       UUID4 to use as the request identifier.
    2. Logs the incoming request (method, path, client IP, request ID).
    3. Delegates to the next handler via ``call_next``.
    4. Attaches the request ID to the response as ``X-Request-ID``.
    5. Logs the completed response (status code, duration in ms).
    """

    async def dispatch(self, request: Request, call_next: Callable):
        """Process a single request, adding logging and a request ID.

        Args:
            request: The incoming Starlette ``Request`` object.
            call_next: Callable that forwards the request to the next
                middleware or route handler and returns the response.

        Returns:
            The ``Response`` returned by the downstream handler, with the
            ``X-Request-ID`` header added.

        """
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        logger.info(
            "Request started | request_id=%s method=%s path=%s client_ip=%s",
            request_id,
            request.method,
            request.url.path,
            request.client.host,
        )

        start_time = time.time()
        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        process_time = (time.time() - start_time) * 1000
        logger.info(
            "Request completed | request_id=%s status_code=%s duration_ms=%.2f",
            request_id,
            response.status_code,
            process_time,
        )

        return response
