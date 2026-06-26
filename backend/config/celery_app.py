"""Celery application configuration for the auction platform.

This module initializes the Celery app instance and configures it with
Redis as both the message broker and result backend. It also sets
default task execution policies (timeouts, serialization, etc.).
"""

import logging

from celery import Celery
from celery.signals import task_failure

from config.settings import settings

logger = logging.getLogger(__name__)


def _redis_url_with_ssl(url: str) -> str:
    """Append ``ssl_cert_reqs=none`` to a ``rediss://`` URL if not already present.

    Celery requires this parameter when connecting to Redis over TLS so it
    does not reject self-signed certificates used by managed Redis services.

    Args:
        url: Raw Redis connection URL (``redis://`` or ``rediss://``).

    Returns:
        The URL unchanged for ``redis://`` URLs, or the URL with
        ``ssl_cert_reqs=none`` appended for ``rediss://`` URLs.

    """
    if url.startswith("rediss://") and "ssl_cert_reqs" not in url:
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}ssl_cert_reqs=none"
    return url


_broker_url = _redis_url_with_ssl(settings.redis_url)
_backend_url = _redis_url_with_ssl(settings.redis_url)

celery = Celery(
    "auction_platform",
    broker=_broker_url,
    backend=_backend_url,
    include=[
        "apps.notifications.tasks",
        "apps.wallet.tasks",
        "apps.auctions.tasks",
        "apps.escrow.tasks",
        "apps.core.tasks",  # health check task
    ],
)

# Celery configuration
celery.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Result backend
    result_expires=3600,
    # Task execution
    task_always_eager=False,  # Always run tasks in the worker, never inline
    task_track_started=True,
    task_time_limit=300,  # Hard kill after 5 minutes
    task_soft_time_limit=240,  # Warn after 4 minutes
    # Worker
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Beat schedule — periodic tasks
    beat_schedule={
        "settle-ended-auctions": {
            "task": "apps.auctions.tasks.settle_ended_auctions",
            "schedule": 60.0,
        },
        "auto-release-escrow": {
            "task": "apps.escrow.tasks.process_auto_releases",
            "schedule": 300.0,
        },
        "check-overdue-shipments": {
            "task": "apps.escrow.tasks.process_overdue_shipments",
            "schedule": 1800.0,
        },
        "activate-scheduled-tasks": {
            "task": "apps.auctions.tasks.activate_scheduled_auctions",
            "schedule": 60.0,
        },
        # Health check — if this stops appearing in results the worker is down
        # "celery-health-check": {
        #     "task": "apps.core.tasks.health_check",
        #     "schedule": 300.0,  # Every 5 minutes
        # },
    },
)


@task_failure.connect
def on_task_failure(
    sender=None,
    task_id=None,
    exception=None,
    args=None,
    kwargs=None,
    traceback=None,
    einfo=None,
    **kw,
):
    """Log structured error on any task failure.

    Sentry captures the exception automatically via CeleryIntegration.
    This handler adds a structured log entry so failures also appear in
    the application log pipeline (Railway logs, CloudWatch, etc.).

    Args:
        sender: The task class that failed.
        task_id: Celery task UUID.
        exception: The raised exception instance.
        args: Positional arguments the task was called with.
        kwargs: Keyword arguments the task was called with.
        einfo: Exception info object with traceback.

    """
    logger.error(
        "Celery task failed | task=%s id=%s exception=%s",
        sender.name if sender else "unknown",
        task_id,
        repr(exception),
        exc_info=einfo.exc_info if einfo else None,
    )
