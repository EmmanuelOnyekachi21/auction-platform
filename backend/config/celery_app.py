"""Celery application configuration for the auction platform.

This module initializes the Celery app instance and configures it with
Redis as both the message broker and result backend. It also sets
default task execution policies (timeouts, serialization, etc.).
"""

from celery import Celery

from config.settings import settings

celery = Celery(
    "auction_platform",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "apps.notifications.tasks",
        "apps.wallet.tasks",
        "apps.auctions.tasks",  # Auction settlement tasks
    ],
)

# Celery configuration
celery.conf.update(
    # Task settings
    task_serializer="json",  # How to serialize task arguments
    accept_content=["json"],  # Only accept JSON (security)
    result_serializer="json",  # How to serialize task results
    timezone="UTC",  # All times in UTC
    enable_utc=True,  # Enable UTC timezone
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    # Task execution settings
    task_track_started=True,  # Track when task starts
    task_time_limit=300,  # Kill task after 5 minutes
    task_soft_time_limit=240,  # Warn task after 4 minutes
    # Worker settings
    worker_prefetch_multiplier=1,  # Take 1 task at a time (fair distribution)
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    # Beat schedule - periodic tasks (cron jobs)
    beat_schedule={
        "settle-ended-auctions": {
            "task": "apps.auctions.tasks.settle_ended_auctions",
            "schedule": 60.0,  # Run every 60 seconds
        },
    },
)
