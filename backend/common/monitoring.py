"""Sentry initialization and sensitive data scrubbing.

Call initialise_sentry() once at application startup (in main.py lifespan).
If SENTRY_DSN is empty the function returns immediately - safe for local dev.
"""

import logging

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from config.settings import settings

logger = logging.getLogger(__name__)


# Fields whose values must never appear in Sentry reports.
# Covers with tokens, credentials, and Nigerian-specific PII (BVN).
_SENSITIVE_FIELDS = frozenset(
    {
        "password",
        "password_hash",
        "bvn",
        "bvn_hash",
        "token",
        "access_token",
        "refresh_token",
        "card_number",
        "cvv",
        "secret_key",
        "api_key",
        "authorization",
    }
)


def initialise_sentry() -> None:
    """Initialize the sentry SDK.

    Skips silently if SENTRY_DSN is empty - allows local development
    without a Sentry account.

    In Production, DSN must be set via environment variable.
    """
    if not settings.sentry_dsn:
        logger.info("Sentry DSN not set - skipping Sentry initialization")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[
            # Captures FastAPI request context on errors (URL, method, headers)
            FastApiIntegration(),
            # Captures slow/failing SQLAlchemy queries as performance spans
            SqlalchemyIntegration(),
            # Captures Celery task failures automatically
            CeleryIntegration(),
        ],
        # Never attach user IP or inferred PII automatically
        send_default_pii=False,
        # Redact potentially sensitive fields from Sentry reports
        # https://docs.sentry.io/platforms/python/configuration/filtering/
        # Our custom scrubber runs before every event leaves the process
        before_send=scrub_sensitive_data,
    )
    logger.info(
        "Sentry initialised [env=%s, traces=%.0f%%]",
        settings.sentry_environment,
        settings.sentry_traces_sample_rate * 100,
    )


def _scrub_dict(data: dict) -> dict:
    """Recursively replace sensitive field values with '[Filtered]'."""
    scrubbed = {}

    for key, value in data.items():
        if key.lower() in _SENSITIVE_FIELDS:
            scrubbed[key] = "[Filtered]"
        elif isinstance(value, dict):
            scrubbed[key] = _scrub_dict(value)
        elif isinstance(value, list):
            scrubbed[key] = [
                _scrub_dict(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            scrubbed[key] = value

    return scrubbed  # must be outside the loop


def scrub_sensitive_data(event: dict, hint: dict) -> dict | None:
    """Sentry before_send hook — strips sensitive fields before upload.

    Called by the Sentry SDK for every event before it leaves the process.
    Scrubs request bodies, extra context, and breadcrumb data so passwords,
    tokens, and BVN values never appear in the Sentry dashboard.

    Args:
        event: The Sentry event dict (mutated in place).
        hint: Additional context from the SDK (unused).

    Returns:
        The scrubbed event dict.
    """
    # Scrub HTTP request body
    request_data = event.get("request", {})
    if "data" in request_data:
        request_data["data"] = _scrub_dict(request_data["data"])

    # Scrub request headers (Authorization header contains bearer token)
    if "headers" in request_data:
        if isinstance(request_data["headers"], dict):
            request_data["headers"] = _scrub_dict(request_data["headers"])

    # Scrub any extra context attached manually via sentry_sdk.set_context()
    for key, context in event.get("contexts", {}).items():
        if isinstance(context, dict):
            event["contexts"][key] = _scrub_dict(context)

    # Scrub breadcrumb data (action trail leading up to the error)
    for breadcrumb in event.get("breadcrumbs", {}).get("values", []):
        if isinstance(breadcrumb.get("data"), dict):
            breadcrumb["data"] = _scrub_dict(breadcrumb["data"])

    return event
