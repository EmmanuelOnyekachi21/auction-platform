"""Asynchronous Celery tasks for sending email notifications.

Uses ``FastAPI-Mail`` to connect to an SMTP server and send formatted
emails for verification, password resets, and other system alerts.
"""

import asyncio
import logging

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from config.celery_app import celery
from config.settings import settings

logger = logging.getLogger(__name__)

# FastAPI-Mail configuration
mail_conf = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_FROM_NAME=settings.mail_from_name,
    MAIL_STARTTLS=settings.mail_starttls,
    MAIL_SSL_TLS=settings.mail_ssl_tls,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=False,
)


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
    message = MessageSchema(
        subject="Verify your email",
        recipients=[user_email],
        body=body,
        subtype=MessageType.plain,
    )

    fm = FastMail(mail_conf)
    logger.info(
        "Attempting to send verification email to %s via %s:%s (TLS=%s).",
        user_email,
        settings.mail_server,
        settings.mail_port,
        settings.mail_starttls,
    )

    try:
        asyncio.run(fm.send_message(message))
        logger.info("Verification email sent.")
    except Exception as exc:
        logger.error(f"Error sending verification email: {exc}")
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
    message = MessageSchema(
        subject="Reset your password",
        recipients=[user_email],
        body=body,
        subtype=MessageType.plain,
    )
    fm = FastMail(mail_conf)
    logger.info(
        "Attempting to send password reset email to %s via %s:%s (TLS=%s).",
        user_email,
        settings.mail_server,
        settings.mail_port,
        settings.mail_starttls,
    )
    try:
        asyncio.run(fm.send_message(message))
        logger.info("Password reset link sent.")
    except Exception as exc:
        logger.error(f"Error sending reset email: {exc}")
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
    message = MessageSchema(
        subject="Seller Account Verified",
        recipients=[user_email],
        body=body,
        subtype=MessageType.plain,
    )

    fm = FastMail(mail_conf)
    logger.info(
        "Attempting to send seller verification approved email to %s.", user_email
    )

    try:
        asyncio.run(fm.send_message(message))
        logger.info("Seller verification approved email sent to %s.", user_email)
    except Exception as exc:
        logger.error(f"Error sending seller verification approved email: {exc}")
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
    message = MessageSchema(
        subject="Seller Verification Unsuccessful",
        recipients=[user_email],
        body=body,
        subtype=MessageType.plain,
    )

    fm = FastMail(mail_conf)
    logger.info(
        "Attempting to send seller verification rejected email to %s.", user_email
    )

    try:
        asyncio.run(fm.send_message(message))
        logger.info("Seller verification rejected email sent to %s.", user_email)
    except Exception as exc:
        logger.error(f"Error sending seller verification rejected email: {exc}")
        raise exc
