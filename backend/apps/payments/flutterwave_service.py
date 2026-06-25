"""Paystack payment gateway integration service."""

import logging
from decimal import Decimal

import httpx

from common.exceptions import (
    PaystackError,
    PaystackPaymentError,
    PaystackVerificationError,
)
from config.settings import settings

logger = logging.getLogger(__name__)


class PaystackService:
    """Service for interacting with Paystack payment gateway."""

    def __init__(self, base_url: str, secret_key: str):
        """Initialize Paystack service.

        Args:
            base_url: Paystack API base URL
            secret_key: Paystack secret key for authentication

        """
        self.base_url = base_url
        self.secret_key = secret_key
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    async def initiate_payment(
        self,
        transaction_reference: str,
        amount: Decimal,
        currency: str,
        user_email: str,
        user_name: str,
        redirect_url: str,
        description: str,
        metadata: dict,
    ) -> str:
        """Initiate payment with Paystack.

        Args:
            transaction_reference: Unique transaction reference
            amount: Payment amount
            currency: Currency code (e.g., "NGN")
            user_email: Customer email
            user_name: Customer name
            redirect_url: URL to redirect after payment
            description: Payment description
            metadata: Additional metadata

        Returns:
            Payment link URL

        Raises:
            PaystackPaymentError: If payment initiation fails

        """
        # Build payload
        payload = {
            "tx_ref": transaction_reference,
            "amount": amount,
            "currency": currency,
            "redirect_url": redirect_url,
            "customer": {"email": user_email, "name": user_name},
            "customizations": {
                "title": "Auction Platform Payment",
                "description": description,
                # "logo": "https://yourdomain.com/logo.png"
            },
            "meta": metadata,
        }

        logger.info(
            f"Initializing Paystack payment for transaction {transaction_reference}"
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/payments", json=payload, headers=self.headers
                )

                response.raise_for_status()

                data = response.json()

                # collect flutter payment link
                if data.get("status") == "success":
                    payment_link = data["data"]["link"]

                    return payment_link

                error_msg = data.get("message", "Unknown error")
                logger.error(f"Paystack payment initiation failed: {error_msg}")
                raise PaystackPaymentError(error_msg)
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error initiating payment for "
                f"{transaction_reference}: {e.response.text}"
            )
            raise PaystackPaymentError(f"Payment initiation failed: {e.response.text}")
        except httpx.HTTPError as e:
            logger.error(
                f"HTTP error initiating payment for {transaction_reference}: {e}"
            )
            raise PaystackPaymentError(f"Payment initiation failed: {str(e)}")

    async def verify_payment(self, transaction_reference: str) -> dict:
        """Verify payment with Paystack.

        Args:
            transaction_reference: Transaction reference to verify

        Returns:
            Payment data from Paystack

        Raises:
            PaystackVerificationError: If verification fails

        """
        logger.info(f"Verifying payment for transaction {transaction_reference}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Paystack verify endpoint uses tx_ref in URL
                response = await client.get(
                    f"{self.base_url}/transactions/verify_by_reference",
                    params={"tx_ref": transaction_reference},
                    headers=self.headers,
                )
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "success":
                    payment_data = data["data"]
                    logger.info(
                        f"Payment verified for {transaction_reference}: "
                        f"status={payment_data.get('status')}, "
                        f"amount={payment_data.get('amount')}"
                    )

                    return payment_data
                else:
                    error_msg = data.get("message", "Verification failed")
                    logger.error(
                        f"Payment verification failed for "
                        f"{transaction_reference}: {error_msg}"
                    )
                    raise PaystackVerificationError(error_msg)
        except httpx.HTTPError as e:
            logger.error(f"HTTP error verifying payment {transaction_reference}: {e}")
            raise PaystackVerificationError(f"Verification request failed: {str(e)}")

    async def initiate_transfer(
        self,
        account_number: str,
        account_bank: str,
        amount: Decimal,
        currency: str,
        narration: str,
        reference: str,
    ) -> dict:
        """Initiate bank transfer via Paystack.

        Args:
            account_bank: Bank code (e.g., "044" for Access Bank)
            account_number: Recipient's account number
            amount: Amount to transfer
            currency: Currency code (e.g., "NGN")
            narration: Transfer description (max 100 chars)
            reference: Unique transaction reference

        Returns:
            dict: Transfer response data from Paystack

        Raises:
            PaystackError: If transfer initiation fails

        """
        # Building Payload
        payload = {
            "account_bank": account_bank,
            "account_number": account_number,
            "amount": float(amount),  # flutterwave expects float
            "currency": currency,
            "narration": narration[:100],  # Max 100 chars
            "reference": reference,
            "callback_url": (f"{settings.app_url}/api/v1/wallets/webhooks/transfer"),
            "debit_currency": currency,  # Same as currency for NGN
        }

        # Making API call
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/transfers",
                    json=payload,
                    headers=self.headers,
                )

                response.raise_for_status()

                data = response.json()

                if data.get("status") == "success":
                    logger.info(f"Transfer initiated: {reference}")

                    return data["data"]

                else:
                    # Paystack returned error
                    error_msg = data.get("message", "Transfer failed")
                    logger.error(f"Transfer failed: {error_msg}")
                    raise PaystackError(error_msg)
        except httpx.HTTPStatusError as e:
            # HTTP error (4xx, 5xx)
            logger.error(f"Transfer HTTP error: {e.response.text}")
            raise PaystackError(f"Transfer request failed: {e.response.text}")
        except httpx.HTTPError as e:
            logger.error(f"Transfer HTTP error: {e}")
            raise PaystackError(f"Transfer request failed: {e}")
        except httpx.RequestError as e:
            # Network error
            logger.error(f"Transfer network error: {e}")
            raise PaystackError(f"Network error during transfer: {e}")
