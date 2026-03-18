"""Celery application configuration for the auction platform."""

from celery import Celery

celery = Celery("auction_platform")
