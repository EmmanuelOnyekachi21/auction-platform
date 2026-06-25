"""Email utilities using Resend.

Provides centralized email sending functionality via the Resend API.
The sender domain must be verified in the Resend dashboard.
"""

import logging
from typing import List

import resend

from config.settings import settings

logger = logging.getLogger(__name__)

resend.api_key = settings.resend_api_key


async def send_email(
    subject: str,
    recipients: List[str],
    body: str,
) -> None:
    """Send a plain-text email via Resend.

    Args:
        subject: Email subject line.
        recipients: List of recipient email addresses.
        body: Plain text email body.

    Raises:
        Exception: If the Resend API call fails.

    """
    logger.info("Sending email to %s (subject: %s)", recipients, subject)

    try:
        # resend.Emails.send is synchronous — do not await
        resend.Emails.send(
            {
                "from": settings.mail_from,
                "to": recipients,
                "subject": subject,
                "text": body,
            }
        )
        logger.info("Email sent successfully to %s", recipients)
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", recipients, exc)
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
    logger.info("Sending HTML email to %s (subject: %s)", recipients, subject)

    try:
        resend.Emails.send(
            {
                "from": settings.mail_from,
                "to": recipients,
                "subject": subject,
                "html": html_body,
            }
        )
        logger.info("HTML email sent successfully to %s", recipients)
    except Exception as exc:
        logger.error("Failed to send HTML email to %s: %s", recipients, exc)
        raise
