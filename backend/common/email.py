"""Email utilities using FastAPI-Mail.

Provides centralized email configuration and sending functionality.
Supports both development (Mailtrap) and production SMTP servers.
"""

import logging
from typing import List

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from config.settings import settings

logger = logging.getLogger(__name__)


def get_mail_config() -> ConnectionConfig:
    """Create FastAPI-Mail connection configuration from settings."""
    validate_certs = not settings.mail_server.endswith("mailtrap.io")

    return ConnectionConfig(
        MAIL_USERNAME=settings.mail_username,
        MAIL_PASSWORD=settings.mail_password,
        MAIL_FROM=settings.mail_from,
        MAIL_PORT=settings.mail_port,
        MAIL_SERVER=settings.mail_server,
        MAIL_FROM_NAME=settings.mail_from_name,
        MAIL_STARTTLS=settings.mail_starttls,
        MAIL_SSL_TLS=settings.mail_ssl_tls,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=validate_certs,
    )


def get_mail_client() -> FastMail:
    """Get configured FastMail client instance."""
    return FastMail(get_mail_config())


async def send_email(
    subject: str,
    recipients: List[str],
    body: str,
    subtype: MessageType = MessageType.plain,
) -> None:
    """Send an email using configured SMTP settings."""
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=body,
        subtype=subtype,
    )

    fm = get_mail_client()

    logger.info(
        "Sending email to %s via %s:%s (subject: %s)",
        recipients,
        settings.mail_server,
        settings.mail_port,
        subject,
    )

    try:
        await fm.send_message(message)
        logger.info("Email sent successfully to %s", recipients)
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", recipients, exc)
        raise


async def send_html_email(
    subject: str,
    recipients: List[str],
    html_body: str,
) -> None:
    """Send an HTML email."""
    await send_email(
        subject=subject,
        recipients=recipients,
        body=html_body,
        subtype=MessageType.html,
    )
