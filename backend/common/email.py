"""Email utilities using Resend HTTP API.

Provides centralized email sending functionality via Resend,
which works on platforms that block outbound SMTP (e.g. Railway).
"""

import logging
from typing import List

import resend

from config.settings import settings

logger = logging.getLogger(__name__)


def _init_resend() -> None:
    resend.api_key = settings.resend_api_key


async def send_email(
    subject: str,
    recipients: List[str],
    body: str,
    subtype: str = "plain",
) -> None:
    """Send an email via Resend HTTP API.

    Args:
        subject: Email subject line
        recipients: List of recipient email addresses
        body: Email body content
        subtype: 'plain' or 'html'

    Raises:
        Exception: If email sending fails

    """
    _init_resend()

    logger.info("Sending email to %s (subject: %s)", recipients, subject)

    try:
        params = {
            "from": f"{settings.mail_from_name} <{settings.mail_from}>",
            "to": recipients,
            "subject": subject,
        }
        if subtype == "html":
            params["html"] = body
        else:
            params["text"] = body

        resend.Emails.send(params)
        logger.info("Email sent successfully to %s", recipients)
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", recipients, exc)
        raise


async def send_html_email(
    subject: str,
    recipients: List[str],
    html_body: str,
) -> None:
    """Send an HTML email via Resend."""
    await send_email(
        subject=subject,
        recipients=recipients,
        body=html_body,
        subtype="html",
    )
