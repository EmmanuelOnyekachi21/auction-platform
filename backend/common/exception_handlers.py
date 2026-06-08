"""Global exception handlers for the auction platform.

Registered in ``main.py``, these handlers intercept specific exception
types raised anywhere in the application and return consistently
formatted ``ErrorResponse`` JSON bodies.

Each handler follows the same contract:
- Accept a ``Request`` and the raised exception.
- Build an ``ErrorResponse`` payload.
- Return a ``JSONResponse`` with the appropriate HTTP status code.
"""

import logging

import sentry_sdk
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from common.exceptions import AuctionPlatformException
from common.schemas import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


async def handle_auction_platform_exception(
    request: Request,
    exc: AuctionPlatformException,
) -> JSONResponse:
    """Handle any ``AuctionPlatformException`` subclass.

    Serialises the exception's structured metadata directly into the
    ``ErrorResponse`` envelope and returns it with the exception's own
    HTTP status code.

    Args:
        request: The incoming FastAPI request (unused but required by
            the handler signature).
        exc: The caught ``AuctionPlatformException`` instance.

    Returns:
        A ``JSONResponse`` containing the serialised ``ErrorResponse``.

    """
    content = ErrorResponse(
        code=exc.code,
        status="error",
        message=exc.message,
        details=exc.details,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=content.model_dump(),
    )


async def handle_pydantic_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle Pydantic ``RequestValidationError`` raised by FastAPI.

    Flattens the list of Pydantic validation errors into ``ErrorDetail``
    objects, joining nested location parts with `` -> `` for readability.

    Args:
        request: The incoming FastAPI request (unused but required by
            the handler signature).
        exc: The caught ``RequestValidationError`` instance.

    Returns:
        A ``JSONResponse`` with HTTP 422 and a list of field-level errors.

    """
    error_details = []

    for error in exc.errors():
        loc = error["loc"]
        # loc[0] is always the input type ("body", "query", "path", etc.)
        # loc[1:] contains the field path. When the entire body is missing
        # or unparseable, loc is just ("body",) with nothing after it —
        # produce a readable label instead of an empty string.
        field_parts = loc[1:]
        if field_parts:
            field = " -> ".join(str(part) for part in field_parts)
        else:
            # Entire body missing or not valid JSON
            field = loc[0] if loc else "request"

        # Strip Pydantic's internal "Value error, " prefix from custom validators
        message = error["msg"].replace("Value error, ", "")
        error_details.append(ErrorDetail(field=field, message=message))

    content = ErrorResponse(
        code="VALIDATION_ERROR",
        status="error",
        message="Validation failed",
        details=error_details,
    )
    return JSONResponse(
        status_code=422,
        content=content.model_dump(),
    )


async def handle_not_found(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """Handle FastAPI ``HTTPException`` raised with any status.

    Respects the status code set in the exception (e.g. 401, 403, 404)
    rather than hardcoding to 404.

    Args:
        request: The incoming FastAPI request (unused but required by
            the handler signature).
        exc: The caught ``HTTPException`` instance.

    Returns:
        A ``JSONResponse`` with the exception's status code and an
        appropriate error response body.

    """
    code = "NOT_FOUND" if exc.status_code == 404 else "AUTHENTICATION_ERROR"
    content = ErrorResponse(
        code=code,
        status="error",
        message=exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=content.model_dump(),
    )


async def handle_generic_exception(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle any unhandled exception as an internal server error.

    Logs the full traceback at ERROR level so it is captured by the
    application's logging pipeline, then returns a generic 500 response
    without leaking internal details to the client.

    Args:
        request: The incoming FastAPI request (unused but required by
            the handler signature).
        exc: The unhandled exception instance.

    Returns:
        A ``JSONResponse`` with HTTP 500 and an ``INTERNAL_SERVER_ERROR``
        error code.

    """
    # Send to Sentry - this is a genuinely unexpected error
    sentry_sdk.capture_exception(exc)
    logger.error("Unhandled exception", exc_info=True)
    content = ErrorResponse(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred",
    )
    return JSONResponse(
        status_code=500,
        content=content.model_dump(),
    )


async def rate_limited_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    """Handle ``RateLimitExceeded`` raised by SlowAPI.

    Logs the offending request at WARNING level and returns a consistent
    429 response matching the platform's ``ErrorResponse`` envelope.

    Args:
        request: The incoming FastAPI request.
        exc: The ``RateLimitExceeded`` exception raised by SlowAPI.

    Returns:
        A ``JSONResponse`` with HTTP 429 and a ``RATE_LIMIT_EXCEEDED`` code.

    """
    logger.warning(
        "rate limit exceeded: %s %s from IP %s",
        request.method,
        request.url.path,
        request.client if request.client else "Unknown",
    )
    content = ErrorResponse(
        code="RATE_LIMIT_EXCEEDED",
        message="Too many requests. Please try again later.",
    )
    return JSONResponse(
        status_code=429,
        content=content.model_dump(),
    )
