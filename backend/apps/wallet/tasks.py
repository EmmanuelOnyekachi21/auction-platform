"""Celery tasks for wallet operations.

This module contains background tasks for:
- Sending wallet funding notification emails
- Sending withdrawal notification emails
- Processing withdrawal bank transfers
"""

import asyncio
import logging
from uuid import UUID

from common.dependency import get_async_db_session
from common.email import send_email
from config.celery_app import celery
from config.settings import settings

logger = logging.getLogger(__name__)


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_wallet_funded_email(
    self, user_email: str, user_name: str, amount: str, currency: str, new_balance: str
):
    """Send email notification after successful wallet funding.

    Args:
        self: Celery task instance
        user_email: User's email address
        user_name: User's name
        amount: Amount funded (as string to avoid Decimal serialization issues)
        currency: Currency code (e.g., "NGN")
        new_balance: New wallet balance (as string)

    """
    body = (
        f"Hello {user_name},\n\n"
        f"Your wallet has been funded successfully!\n\n"
        f"Amount: {currency} {amount}\n"
        f"New Balance: {currency} {new_balance}\n\n"
        f"Thank you for using Auction Platform.\n\n"
        f"View your wallet: {settings.frontend_url}/wallet"
    )

    try:
        asyncio.run(
            send_email(
                subject="Wallet Funded Successfully",
                recipients=[user_email],
                body=body,
            )
        )
        logger.info(f"Wallet funded email sent to {user_email}")
    except Exception as exc:
        logger.error(f"Error sending wallet funded email to {user_email}: {exc}")
        raise exc


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_withdrawal_notification(
    self,
    user_email: str,
    user_name: str,
    amount: str,
    currency: str,
    status: str,
    reason: str = None,
):
    """Send email notification about withdrawal outcome.

    Args:
        self: Celery task instance
        user_email: User's email address
        user_name: User's name
        amount: Withdrawal amount (as string)
        currency: Currency code (e.g., "NGN")
        status: "success" or "failed"
        reason: Failure reason (optional, only for failed withdrawals)

    """
    if status == "success":
        subject = "Withdrawal Processed Successfully"
        body = (
            f"Hello {user_name},\n\n"
            f"Your withdrawal has been processed successfully!\n\n"
            f"Amount: {currency} {amount}\n\n"
            f"The funds should arrive in your bank account within 24 hours.\n\n"
            f"Thank you for using Auction Platform.\n\n"
            f"View your wallet: {settings.frontend_url}/wallet"
        )
    else:
        subject = "Withdrawal Failed"
        body = (
            f"Hello {user_name},\n\n"
            f"Unfortunately, your withdrawal could not be processed.\n\n"
            f"Amount: {currency} {amount}\n"
            f"Reason: {reason or 'Unknown error'}\n\n"
            f"The amount has been refunded to your wallet.\n\n"
            f"Please try again or contact support if the issue persists.\n\n"
            f"View your wallet: {settings.frontend_url}/wallet"
        )

    try:
        asyncio.run(
            send_email(
                subject=subject,
                recipients=[user_email],
                body=body,
            )
        )
        logger.info(f"Withdrawal notification ({status}) sent to {user_email}")
    except Exception as exc:
        logger.error(f"Error sending withdrawal notification to {user_email}: {exc}")
        raise exc


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_withdrawal_transfer(self, transaction_id: str):
    """Process bank transfer for a pending withdrawal.

    This task runs in the background after wallet has been debited.
    It calls Paystack Transfer API and updates transaction status.

    Args:
        self: Celery task instance
        transaction_id: UUID of the withdrawal transaction (as string)

    """

    async def run():
        """Execute the withdrawal transfer and send the outcome notification."""
        from apps.payments.paystack_service import PaystackService
        from apps.wallet.repository import WalletRepository
        from apps.wallet.service import WalletService
        from common.exceptions import BankDetailsNotSetupException, PaystackError

        async with get_async_db_session() as db:
            # Initialize services
            flutterwave_service = PaystackService(
                base_url=settings.paystack_base_url,
                secret_key=settings.paystack_secret_key,
            )
            wallet_service = WalletService(db, flutterwave_service)
            wallet_repo = WalletRepository(db)

            # Get transaction with wallet AND user pre-loaded efficiently
            # This avoids secondary queries that might cause
            # 'operation in progress' errors
            transaction = await wallet_repo.get_transaction_by_id(UUID(transaction_id))
            if not transaction:
                logger.error(f"Transaction not found: {transaction_id}")
                return

            # REASONING: Relationships are already loaded via
            # selectinload in get_transaction_by_id
            user = transaction.wallet.user
            user_email = user.email
            user_name = f"{user.first_name} {user.last_name}"
            amount_str = str(transaction.amount)

            try:
                # Process the transfer (now passing the object directly)
                await wallet_service.process_withdrawal_transfer_direct(transaction)

                # Send success notification with 2s delay to avoid
                # Mailtrap 550 rate limits
                send_withdrawal_notification.apply_async(
                    kwargs={
                        "user_email": user_email,
                        "user_name": user_name,
                        "amount": amount_str,
                        "currency": "NGN",
                        "status": "success",
                    },
                    countdown=2,
                )

                logger.info(
                    f"Withdrawal transfer processed successfully: " f"{transaction_id}"
                )

            except BankDetailsNotSetupException:
                logger.error(
                    f"Bank details not set up for transaction " f"{transaction_id}"
                )
                # Send failure notification with 2s delay
                send_withdrawal_notification.apply_async(
                    kwargs={
                        "user_email": user_email,
                        "user_name": user_name,
                        "amount": amount_str,
                        "currency": "NGN",
                        "status": "failed",
                        "reason": "Bank details not set up",
                    },
                    countdown=2,
                )
                # Don't retry - user needs to set up bank details
                raise

            except PaystackError as e:
                logger.error(
                    f"Paystack error processing withdrawal " f"{transaction_id}: {e}"
                )

                # Send failure notification with 2s delay
                send_withdrawal_notification.apply_async(
                    kwargs={
                        "user_email": user_email,
                        "user_name": user_name,
                        "amount": amount_str,
                        "currency": "NGN",
                        "status": "failed",
                        "reason": str(e),
                    },
                    countdown=2,
                )

                raise

            except Exception as e:
                logger.error(
                    f"Unexpected error processing withdrawal " f"{transaction_id}: {e}"
                )
                # Send failure notification
                send_withdrawal_notification.delay(
                    user_email=user_email,
                    user_name=user_name,
                    amount=amount_str,
                    currency="NGN",
                    status="failed",
                    reason="System error",
                )
                raise

    try:
        asyncio.run(run())
    except Exception as exc:
        logger.error(f"Withdrawal processing task failed: {exc}")
        raise exc
