"""Asynchronous Celery tasks for sending email notifications.

Uses centralized email utilities to send formatted emails for
verification, password resets, and other system alerts.
Also creates in-app Notification records for user-facing events.
"""

import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import config.model_registry  # noqa: F401
from apps.notifications.enums import NotificationReferenceType, NotificationType
from apps.notifications.models import Notification
from common.email import send_email
from config.celery_app import celery
from config.settings import settings

logger = logging.getLogger(__name__)


async def _create_notification(
    user_id: str,
    title: str,
    message: str,
    notification_type: str,
    reference_id: str | None = None,
    reference_type: str | None = None,
) -> None:
    """Create an in-app notification record in a fresh DB session.

    Called from synchronous Celery tasks via ``asyncio.run()``.
    Uses a dedicated session so it does not interfere with other task sessions.

    Args:
        user_id: UUID string of the recipient user.
        title: Short notification title.
        message: Full notification message body.
        notification_type: String value of the ``NotificationType`` enum.
        reference_id: Optional UUID string of the related entity.
        reference_type: Optional string value of the ``NotificationReferenceType`` enum.

    """
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with factory() as session:
            notification = Notification(
                user_id=UUID(user_id),
                title=title,
                message=message,
                notification_type=NotificationType(notification_type),
                reference_id=UUID(reference_id) if reference_id else None,
                reference_type=(
                    NotificationReferenceType(reference_type)
                    if reference_type
                    else None
                ),
            )
            session.add(notification)
            await session.commit()
    except Exception as exc:
        logger.error(
            "Failed to create in-app notification for user %s: %s", user_id, exc
        )
    finally:
        await engine.dispose()


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
            send_email(subject="Verify your email", recipients=[user_email], body=body)
        )
        logger.info("Verification email sent to %s", user_email)
    except Exception as exc:
        logger.error("Error sending verification email to %s: %s", user_email, exc)
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
                subject="Reset your password", recipients=[user_email], body=body
            )
        )
        logger.info("Password reset email sent to %s", user_email)
    except Exception as exc:
        logger.error("Error sending reset email to %s: %s", user_email, exc)
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
            "Error sending seller verification approved email to %s: %s",
            user_email,
            exc,
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
            "Error sending seller verification rejected email to %s: %s",
            user_email,
            exc,
        )
        raise exc


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_item_approved_notification(
    self, seller_email: str, seller_name: str, item_name: str
):
    """Send email notification when an item is approved by admin.

    Args:
        self: The Celery task instance (injected via bind=True).
        seller_email: The seller's email address.
        seller_name: The seller's name for personalization.
        item_name: The name of the approved item.

    Raises:
        Exception: If the email fails to send (triggered for retry).

    """
    body = (
        f"Hello {seller_name},\n\n"
        f"Great news! Your item '{item_name}' has been approved.\n\n"
        f"You can now add this item to an auction and start selling.\n\n"
        f"Create an auction: {settings.app_url}/seller/create-auction\n\n"
        f"Thank you for listing quality items on our platform!"
    )
    try:
        asyncio.run(
            send_email(
                subject="Item Approved - Ready to List",
                recipients=[seller_email],
                body=body,
            )
        )
        logger.info(
            "Item approved notification sent to %s for item: %s",
            seller_email,
            item_name,
        )
    except Exception as exc:
        logger.error(
            "Error sending item approved notification to %s: %s", seller_email, exc
        )
        raise exc


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_item_rejected_notification(
    self, seller_email: str, seller_name: str, item_name: str, reason: str
):
    """Send email notification when an item is rejected by admin.

    Args:
        self: The Celery task instance (injected via bind=True).
        seller_email: The seller's email address.
        seller_name: The seller's name for personalization.
        item_name: The name of the rejected item.
        reason: The reason for rejection provided by admin.

    Raises:
        Exception: If the email fails to send (triggered for retry).

    """
    body = (
        f"Hello {seller_name},\n\n"
        f"Unfortunately, your item '{item_name}' was not approved for listing.\n\n"
        f"Reason: {reason}\n\n"
        f"Please review our listing guidelines and make the necessary changes.\n\n"
        f"You can edit your item and resubmit it for review.\n\n"
        f"View your items: {settings.app_url}/seller/items\n\n"
        f"If you have questions, please contact our support team."
    )
    try:
        asyncio.run(
            send_email(
                subject="Item Not Approved - Action Required",
                recipients=[seller_email],
                body=body,
            )
        )
        logger.info(
            "Item rejected notification sent to %s for item: %s",
            seller_email,
            item_name,
        )
    except Exception as exc:
        logger.error(
            "Error sending item rejected notification to %s: %s", seller_email, exc
        )
        raise exc


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def notify_outbid_user(
    self,
    user_email: str,
    user_name: str,
    auction_id: str,
    new_highest_bid: str,
    user_id: str | None = None,
):
    """Send email notification when a user has been outbid.

    Args:
        self: The Celery task instance (injected via bind=True).
        user_email: The outbid user's email address.
        user_name: The outbid user's name for personalization.
        auction_id: UUID string of the auction.
        new_highest_bid: The new highest bid amount as string (Decimal-safe).
        user_id: UUID string of the user (for in-app notification).

    Raises:
        Exception: If the email fails to send (triggered for retry).

    """
    auction_url = f"{settings.app_url}/auctions/{auction_id}"
    body = (
        f"Hello {user_name},\n\n"
        f"You've been outbid! Someone placed a higher bid of ₦{new_highest_bid} "
        f"on an auction you were leading.\n\n"
        f"Your funds have been returned to your wallet.\n\n"
        f"Place a higher bid to get back in the lead:\n{auction_url}\n\n"
        f"Act fast — the auction may end soon!"
    )
    try:
        asyncio.run(
            send_email(
                subject="You've been outbid!", recipients=[user_email], body=body
            )
        )
        logger.info(
            "Outbid notification sent to %s for auction %s", user_email, auction_id
        )
    except Exception as exc:
        logger.error("Error sending outbid notification to %s: %s", user_email, exc)
        raise exc

    if user_id:
        asyncio.run(
            _create_notification(
                user_id=user_id,
                title="You've been outbid",
                message=(
                    f"Someone placed a higher bid of ₦{new_highest_bid}. "
                    f"Your funds have been returned."
                ),
                notification_type="OUTBID",
                reference_id=auction_id,
                reference_type="AUCTION",
            )
        )


# ── Order Notifications ───────────────────────────────────────────────────────


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def notify_item_shipped(
    self,
    buyer_email: str,
    buyer_name: str,
    order_id: str,
    tracking_number: str | None,
    user_id: str | None = None,
):
    """Notify buyer that their item has been shipped.

    Args:
        self: Celery task instance (injected via ``bind=True``).
        buyer_email: The buyer's email address.
        buyer_name: The buyer's name for personalisation.
        order_id: UUID string of the order.
        tracking_number: Optional carrier tracking number.
        user_id: Optional UUID string for in-app notification.

    """
    tracking_line = f"Tracking: {tracking_number}\n\n" if tracking_number else ""
    body = (
        f"Hello {buyer_name},\n\n"
        f"Great news! Your item has been shipped.\n\n"
        f"{tracking_line}"
        f"Once you receive your item, please confirm delivery in your orders page "
        f"to release payment to the seller.\n\n"
        f"View your order: {settings.app_url}/orders/{order_id}"
    )
    try:
        asyncio.run(
            send_email(
                subject="Your item has been shipped!",
                recipients=[buyer_email],
                body=body,
            )
        )
        logger.info("Item shipped notification sent to %s", buyer_email)
    except Exception as exc:
        logger.error(
            "Failed to send item shipped notification to %s: %s", buyer_email, exc
        )
        raise exc
    if user_id:
        asyncio.run(
            _create_notification(
                user_id=user_id,
                title="Your item has been shipped",
                message="Your item is on its way. Confirm delivery once received.",
                notification_type="ORDER_SHIPPED",
                reference_id=order_id,
                reference_type="ORDER",
            )
        )


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def notify_payment_released(
    self,
    seller_email: str,
    seller_name: str,
    order_id: str,
    amount: str,
    user_id: str | None = None,
):
    """Notify seller that escrow funds have been released to their wallet.

    Args:
        self: Celery task instance (injected via ``bind=True``).
        seller_email: The seller's email address.
        seller_name: The seller's name for personalisation.
        order_id: UUID string of the order.
        amount: Payout amount as a string.
        user_id: Optional UUID string for in-app notification.

    """
    body = (
        f"Hello {seller_name},\n\n"
        f"Payment of ₦{amount} has been released to your wallet.\n\n"
        f"The buyer has confirmed delivery of your item.\n\n"
        f"View your orders: {settings.app_url}/my-orders"
    )
    try:
        asyncio.run(
            send_email(
                subject="Payment released to your wallet",
                recipients=[seller_email],
                body=body,
            )
        )
        logger.info("Payment released notification sent to %s", seller_email)
    except Exception as exc:
        logger.error(
            "Failed to send payment released notification to %s: %s",
            seller_email,
            exc,
        )
        raise exc
    if user_id:
        asyncio.run(
            _create_notification(
                user_id=user_id,
                title="Payment released",
                message=f"₦{amount} has been released to your wallet.",
                notification_type="ESCROW_RELEASED",
                reference_id=order_id,
                reference_type="ORDER",
            )
        )


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def notify_transaction_completed(
    self,
    buyer_email: str,
    buyer_name: str,
    order_id: str,
    user_id: str | None = None,
):
    """Notify buyer that their transaction has been completed.

    Args:
        self: Celery task instance (injected via ``bind=True``).
        buyer_email: The buyer's email address.
        buyer_name: The buyer's name for personalisation.
        order_id: UUID string of the order.
        user_id: Optional UUID string for in-app notification.

    """
    body = (
        f"Hello {buyer_name},\n\n"
        f"Your transaction has been completed successfully.\n\n"
        f"Thank you for using KaraKaja!\n\n"
        f"View your order: {settings.app_url}/orders/{order_id}"
    )
    try:
        asyncio.run(
            send_email(
                subject="Transaction completed",
                recipients=[buyer_email],
                body=body,
            )
        )
        logger.info("Transaction completed notification sent to %s", buyer_email)
    except Exception as exc:
        logger.error(
            "Failed to send transaction completed notification to %s: %s",
            buyer_email,
            exc,
        )
        raise exc
    if user_id:
        asyncio.run(
            _create_notification(
                user_id=user_id,
                title="Transaction completed",
                message="Your order has been completed. Thank you for using KaraKaja!",
                notification_type="ORDER_DELIVERED",
                reference_id=order_id,
                reference_type="ORDER",
            )
        )


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def notify_order_cancelled_buyer(
    self,
    buyer_email: str,
    buyer_name: str,
    order_id: str,
    user_id: str | None = None,
):
    """Notify buyer that their order was cancelled and a refund issued.

    Args:
        self: Celery task instance (injected via ``bind=True``).
        buyer_email: The buyer's email address.
        buyer_name: The buyer's name for personalisation.
        order_id: UUID string of the order.
        user_id: Optional UUID string for in-app notification.

    """
    body = (
        f"Hello {buyer_name},\n\n"
        f"Your order has been cancelled because the seller did not ship "
        f"within the deadline.\n\n"
        f"A full refund has been issued to your wallet.\n\n"
        f"View your wallet: {settings.app_url}/wallet"
    )
    try:
        asyncio.run(
            send_email(
                subject="Order cancelled — refund issued",
                recipients=[buyer_email],
                body=body,
            )
        )
        logger.info("Order cancelled (buyer) notification sent to %s", buyer_email)
    except Exception as exc:
        logger.error(
            "Failed to send order cancelled notification to %s: %s", buyer_email, exc
        )
        raise exc
    if user_id:
        asyncio.run(
            _create_notification(
                user_id=user_id,
                title="Order cancelled — refund issued",
                message=(
                    "Your order was cancelled. "
                    "A full refund has been issued to your wallet."
                ),
                notification_type="ORDER_DELIVERED",
                reference_id=order_id,
                reference_type="ORDER",
            )
        )


# ── Dispute Notifications ─────────────────────────────────────────────────────


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def notify_dispute_raised_seller(
    self,
    seller_email: str,
    seller_name: str,
    order_id: str,
    dispute_id: str,
    user_id: str | None = None,
):
    """Notify seller that a dispute has been raised on their order.

    Args:
        self: Celery task instance (injected via ``bind=True``).
        seller_email: The seller's email address.
        seller_name: The seller's name for personalisation.
        order_id: UUID string of the order.
        dispute_id: UUID string of the dispute.
        user_id: Optional UUID string for in-app notification.

    """
    body = (
        f"Hello {seller_name},\n\n"
        f"A dispute has been raised on your order.\n\n"
        f"Please submit evidence to support your case.\n\n"
        f"View the dispute: {settings.app_url}/disputes/{dispute_id}"
    )
    try:
        asyncio.run(
            send_email(
                subject="A dispute has been raised on your order",
                recipients=[seller_email],
                body=body,
            )
        )
        logger.info("Dispute raised notification sent to seller %s", seller_email)
    except Exception as exc:
        logger.error(
            "Failed to send dispute raised notification to %s: %s", seller_email, exc
        )
        raise exc
    if user_id:
        asyncio.run(
            _create_notification(
                user_id=user_id,
                title="Dispute raised on your order",
                message="A buyer has raised a dispute. Please submit evidence.",
                notification_type="DISPUTE_OPENED",
                reference_id=dispute_id,
                reference_type="DISPUTE",
            )
        )


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def notify_dispute_resolved_buyer(
    self,
    buyer_email: str,
    buyer_name: str,
    dispute_id: str,
    in_favour: bool,
    user_id: str | None = None,
):
    """Notify buyer of the dispute resolution outcome.

    Args:
        self: Celery task instance (injected via ``bind=True``).
        buyer_email: The buyer's email address.
        buyer_name: The buyer's name for personalisation.
        dispute_id: UUID string of the dispute.
        in_favour: ``True`` if resolved in the buyer's favour.
        user_id: Optional UUID string for in-app notification.

    """
    outcome = "in your favour" if in_favour else "in the seller's favour"
    fund_msg = (
        "A refund has been issued to your wallet."
        if in_favour
        else "Payment has been released to the seller."
    )
    body = (
        f"Hello {buyer_name},\n\n"
        f"Your dispute has been resolved {outcome}.\n\n"
        f"{fund_msg}\n\n"
        f"View the dispute: {settings.app_url}/disputes/{dispute_id}"
    )
    subject = (
        "Dispute resolved in your favour"
        if in_favour
        else "Dispute resolved — payment released to seller"
    )
    try:
        asyncio.run(send_email(subject=subject, recipients=[buyer_email], body=body))
        logger.info("Dispute resolved notification sent to buyer %s", buyer_email)
    except Exception as exc:
        logger.error(
            "Failed to send dispute resolved notification to %s: %s", buyer_email, exc
        )
        raise exc
    if user_id:
        asyncio.run(
            _create_notification(
                user_id=user_id,
                title="Dispute resolved",
                message=f"Your dispute has been resolved {outcome}. {fund_msg}",
                notification_type="DISPUTE_RESOLVED",
                reference_id=dispute_id,
                reference_type="DISPUTE",
            )
        )


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def notify_dispute_resolved_seller(
    self,
    seller_email: str,
    seller_name: str,
    dispute_id: str,
    in_favour: bool,
    user_id: str | None = None,
):
    """Notify seller of the dispute resolution outcome.

    Args:
        self: Celery task instance (injected via ``bind=True``).
        seller_email: The seller's email address.
        seller_name: The seller's name for personalisation.
        dispute_id: UUID string of the dispute.
        in_favour: ``True`` if resolved in the seller's favour.
        user_id: Optional UUID string for in-app notification.

    """
    outcome = "in your favour" if in_favour else "in the buyer's favour"
    fund_msg = (
        "Payment has been released to your wallet."
        if in_favour
        else "A refund has been issued to the buyer."
    )
    body = (
        f"Hello {seller_name},\n\n"
        f"The dispute has been resolved {outcome}.\n\n"
        f"{fund_msg}\n\n"
        f"View the dispute: {settings.app_url}/disputes/{dispute_id}"
    )
    subject = (
        "Dispute resolved in your favour"
        if in_favour
        else "Dispute resolved — refund issued to buyer"
    )
    try:
        asyncio.run(send_email(subject=subject, recipients=[seller_email], body=body))
        logger.info("Dispute resolved notification sent to seller %s", seller_email)
    except Exception as exc:
        logger.error(
            "Failed to send dispute resolved notification to %s: %s",
            seller_email,
            exc,
        )
        raise exc
    if user_id:
        asyncio.run(
            _create_notification(
                user_id=user_id,
                title="Dispute resolved",
                message=f"The dispute has been resolved {outcome}. {fund_msg}",
                notification_type="DISPUTE_RESOLVED",
                reference_id=dispute_id,
                reference_type="DISPUTE",
            )
        )


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def notify_dispute_under_review(self, email: str, name: str, dispute_id: str):
    """Notify a dispute party that their dispute is now under admin review.

    Args:
        self: Celery task instance (injected via ``bind=True``).
        email: The recipient's email address.
        name: The recipient's name for personalisation.
        dispute_id: UUID string of the dispute.

    """
    body = (
        f"Hello {name},\n\n"
        f"Your dispute is now under review by our support team.\n\n"
        f"We will notify you once a decision has been made. "
        f"You may still submit additional evidence in the meantime.\n\n"
        f"View the dispute: {settings.app_url}/disputes/{dispute_id}"
    )
    try:
        asyncio.run(
            send_email(
                subject="Your dispute is under review",
                recipients=[email],
                body=body,
            )
        )
        logger.info("Under review notification sent to %s", email)
    except Exception as exc:
        logger.error("Failed to send under review notification to %s: %s", email, exc)
        raise exc
