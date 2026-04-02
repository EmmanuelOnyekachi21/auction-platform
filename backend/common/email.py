"""Email utilities using Brevo (Sendinblue) HTTP API.

Sends email via Brevo's transactional API over HTTPS,
avoiding SMTP port restrictions on platforms like Railway.
"""

import logging
from typing import List

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


async def send_email(
    subject: str,
    recipients: List[str],
    body: str,
    subtype: str = "plain",
) -> None:
    """Send an email via Brevo HTTP API.

    Args:
        subject: Email subject line
        recipients: List of recipient email addresses
        body: Email body content
        subtype: 'plain' or 'html'

    Raises:
        Exception: If email sending fails

    """
    logger.info("Sending email to %s (subject: %s)", recipients, subject)

    payload = {
        "sender": {"name": settings.mail_from_name, "email": settings.mail_from},
        "to": [{"email": r} for r in recipients],
        "subject": subject,
    }
    if subtype == "html":
        payload["htmlContent"] = body
    else:
        payload["textContent"] = body

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                BREVO_API_URL,
                json=payload,
                headers={
                    "api-key": settings.brevo_api_key,
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            response.raise_for_status()
        logger.info("Email sent successfully to %s", recipients)
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", recipients, exc)
        raise


async def send_html_email(
    subject: str,
    recipients: List[str],
    html_body: str,
) -> None:
    """Send an HTML email via Brevo."""
    await send_email(
        subject=subject,
        recipients=recipients,
        body=html_body,
        subtype="html",
    )
