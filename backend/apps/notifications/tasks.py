"""Asynchronous Celery tasks for sending email notifications.

Uses centralized email utilities to send formatted emails for
verification, password resets, and other system alerts.
"""

import asyncio
import logging

from common.email import send_email
from config.celery_app import celery
from config.settings import settings

logger = logging.getLogger(__name__)


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_verification_email(self, user_email: str, user_name: str, token: str):
    """Send an email verification link to a newly registered user.

    Args:
        self: The Celery task instance (injected via bind=True).
        user_email: The recipient's email address.
        user_name: The recipient's name for personalization.
        token: The raw verification token to include in the link.

    Raises:
        Exception: If the email fails to send (triggered for retry).

    """
    verify_url = f"{settings.app_url}/verify-email?token={token}"

    body = (
        f"Hello {user_name},\n\n"
        f"Thank you for joining! Verify your email here: {verify_url}"
    )

    try:
        asyncio.run(
            send_email(
                subject="Verify your email",
                recipients=[user_email],
                body=body,
            )
        )
        logger.info("Verification email sent to %s", user_email)
    except Exception as exc:
        logger.error(f"Error sending verification email to {user_email}: {exc}")
        raise exc


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_password_reset_email(self, user_email: str, user_name: str, token: str):
    """Send a password reset link to a user who requested a reset.

    Args:
        self: The Celery task instance (injected via bind=True).
        user_email: The recipient's email address.
        user_name: The recipient's name for personalization.
        token: The raw reset token to include in the link.

    Raises:
        Exception: If the email fails to send (triggered for retry).

    """
    reset_url = f"{settings.app_url}/reset-password?token={token}"

    body = f"Hello {user_name},\n\nReset your password here: {reset_url}"

    try:
        asyncio.run(
            send_email(
                subject="Reset your password",
                recipients=[user_email],
                body=body,
            )
        )
        logger.info("Password reset email sent to %s", user_email)
    except Exception as exc:
        logger.error(f"Error sending reset email to {user_email}: {exc}")
        raise exc


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_seller_verification_approved(self, user_email: str, user_name: str):
    """Send email notification when seller account is verified.

    Args:
        self: The Celery task instance (injected via bind=True).
        user_email: The recipient's email address.
        user_name: The recipient's name for personalization.

    Raises:
        Exception: If the email fails to send (triggered for retry).

    """
    body = (
        f"Hello {user_name},\n\n"
        f"Congratulations! Your seller account has been verified.\n\n"
        f"You can now start listing items and creating auctions on our platform.\n\n"
        f"Visit your dashboard: {settings.app_url}/dashboard\n\n"
        f"Thank you for being part of our community!"
    )

    try:
        asyncio.run(
            send_email(
                subject="Seller Account Verified",
                recipients=[user_email],
                body=body,
            )
        )
        logger.info("Seller verification approved email sent to %s", user_email)
    except Exception as exc:
        logger.error(
            f"Error sending seller verification approved email to {user_email}: {exc}"
        )
        raise exc


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_seller_verification_rejected(
    self, user_email: str, user_name: str, reason: str
):
    """Send email notification when seller verification is rejected.

    Args:
        self: The Celery task instance (injected via bind=True).
        user_email: The recipient's email address.
        user_name: The recipient's name for personalization.
        reason: The reason for rejection provided by admin.

    Raises:
        Exception: If the email fails to send (triggered for retry).

    """
    body = (
        f"Hello {user_name},\n\n"
        f"Unfortunately, your seller verification was unsuccessful.\n\n"
        f"Reason: {reason}\n\n"
        f"Please review the requirements and resubmit your verification documents.\n\n"
        f"If you have questions, please contact our support team.\n\n"
        f"Visit your profile: {settings.app_url}/profile"
    )

    try:
        asyncio.run(
            send_email(
                subject="Seller Verification Unsuccessful",
                recipients=[user_email],
                body=body,
            )
        )
        logger.info("Seller verification rejected email sent to %s", user_email)
    except Exception as exc:
        logger.error(
            f"Error sending seller verification rejected email to {user_email}: {exc}"
        )
        raise exc
