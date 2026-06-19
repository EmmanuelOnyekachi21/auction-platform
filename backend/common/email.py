"""Email utilities using Resend.

Provides centralized email sending functionality via the Resend API.
The sender domain must be verified in the Resend dashboard.
"""

import asyncio
import logging
from typing import List

import resend

from config.settings import settings

logger = logging.getLogger(__name__)

resend.api_key = settings.resend_api_key

# Resend SDK is synchronous and exposes no timeout parameter.
# We run it in a thread pool and enforce a timeout via asyncio.wait_for.
_EMAIL_TIMEOUT_SECONDS = 10


async def send_email(
    subject: str,
    recipients: List[str],
    body: str,
) -> None:
    """Send a plain-text email via Resend.

    Runs the synchronous SDK call in a thread and enforces a 10-second
    timeout. Celery tasks that call this should re-raise on failure so
    they can retry.

    Args:
        subject: Email subject line.
        recipients: List of recipient email addresses.
        body: Plain text email body.

    """
    logger.info("Sending email | subject=%s recipients=%s", subject, recipients)

    def _send():
        resend.Emails.send(
            {
                "from": settings.mail_from,
                "to": recipients,
                "subject": subject,
                "text": body,
            }
        )

    try:
        await asyncio.wait_for(
            asyncio.to_thread(_send),
            timeout=_EMAIL_TIMEOUT_SECONDS,
        )
        logger.info("Email sent | subject=%s recipients=%s", subject, recipients)
    except asyncio.TimeoutError:
        logger.error(
            "Email timed out after %ds | subject=%s recipients=%s",
            _EMAIL_TIMEOUT_SECONDS,
            subject,
            recipients,
        )
        raise
    except Exception as exc:
        logger.error(
            "Email send failed | subject=%s recipients=%s error=%s",
            subject,
            recipients,
            exc,
        )
        raise


async def send_html_email(
    subject: str,
    recipients: List[str],
    html_body: str,
) -> None:
    """Send an HTML email via Resend.

    Args:
        subject: Email subject line.
        recipients: List of recipient email addresses.
        html_body: HTML email body.

    """
    logger.info("Sending HTML email | subject=%s recipients=%s", subject, recipients)

    def _send():
        resend.Emails.send(
            {
                "from": settings.mail_from,
                "to": recipients,
                "subject": subject,
                "html": html_body,
            }
        )

    try:
        await asyncio.wait_for(
            asyncio.to_thread(_send),
            timeout=_EMAIL_TIMEOUT_SECONDS,
        )
        logger.info("HTML email sent | subject=%s recipients=%s", subject, recipients)
    except asyncio.TimeoutError:
        logger.error(
            "HTML email timed out after %ds | subject=%s recipients=%s",
            _EMAIL_TIMEOUT_SECONDS,
            subject,
            recipients,
        )
        raise
    except Exception as exc:
        logger.error(
            "HTML email send failed | subject=%s recipients=%s error=%s",
            subject,
            recipients,
            exc,
        )
        raise
