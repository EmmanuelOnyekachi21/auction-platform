"""Paystack payment gateway integration service."""

import logging
from decimal import Decimal

import httpx

from common.exceptions import (
    PaystackError,
    PaystackPaymentError,
    PaystackVerificationError,
)

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
        # Build payload — Paystack amount is in kobo (multiply NGN by 100)
        payload = {
            "reference": transaction_reference,
            "amount": int(amount * 100),
            "currency": currency,
            "callback_url": redirect_url,
            "email": user_email,
            "metadata": {
                "custom_fields": [
                    {
                        "display_name": "Customer Name",
                        "variable_name": "user_name",
                        "value": user_name,
                    }
                ],
                **metadata,
            },
        }

        logger.info(
            f"Initializing Paystack payment for transaction {transaction_reference}"
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/transaction/initialize",
                    json=payload,
                    headers=self.headers,
                )

                response.raise_for_status()

                data = response.json()

                # Paystack returns status as boolean True, not string "true"
                if data.get("status") is True:
                    payment_link = data["data"]["authorization_url"]
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
                # Paystack verify endpoint: GET /transaction/verify/:reference
                response = await client.get(
                    f"{self.base_url}/transaction/verify/{transaction_reference}",
                    headers=self.headers,
                )
                response.raise_for_status()
                data = response.json()

                if data.get("status") is True:
                    payment_data = data["data"]
                    # Convert amount from kobo to naira
                    if "amount" in payment_data:
                        payment_data["amount"] = (
                            Decimal(str(payment_data["amount"])) / 100
                        )
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

    async def resolve_account(self, account_number: str, bank_code: str) -> dict:
        """Resolve account name from account number and bank code.

        Args:
            account_number: 10-digit NUBAN account number
            bank_code: Bank code (e.g. "044" for Access, "999992" for OPay)

        Returns:
            dict with account_name and account_number

        Raises:
            PaystackError: If resolution fails or account not found

        """
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.base_url}/bank/resolve",
                    params={"account_number": account_number, "bank_code": bank_code},
                    headers=self.headers,
                )
                response.raise_for_status()
                data = response.json()

                if data.get("status") is True:
                    return {
                        "account_name": data["data"]["account_name"],
                        "account_number": data["data"]["account_number"],
                    }
                raise PaystackError(data.get("message", "Could not resolve account"))
        except httpx.HTTPStatusError as e:
            raise PaystackError(f"Account resolution failed: {e.response.text}")
        except httpx.HTTPError as e:
            raise PaystackError(f"Account resolution request failed: {str(e)}")

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

        Paystack requires two steps:
        1. Create a transfer recipient
        2. Initiate the transfer using the recipient code

        Args:
            account_bank: Bank code (e.g., "044" for Access Bank)
            account_number: Recipient's account number
            amount: Amount to transfer in naira
            currency: Currency code (e.g., "NGN")
            narration: Transfer description
            reference: Unique transaction reference

        Returns:
            dict: Transfer response data from Paystack

        Raises:
            PaystackError: If transfer initiation fails

        """
        # Step 1: Create transfer recipient
        recipient_payload = {
            "type": "nuban",
            "name": narration,
            "account_number": account_number,
            "bank_code": account_bank,
            "currency": currency,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                recipient_response = await client.post(
                    f"{self.base_url}/transferrecipient",
                    json=recipient_payload,
                    headers=self.headers,
                )
                recipient_response.raise_for_status()
                recipient_data = recipient_response.json()

                if not recipient_data.get("status"):
                    raise PaystackError(
                        recipient_data.get("message", "Failed to create recipient")
                    )

                recipient_code = recipient_data["data"]["recipient_code"]

            # Step 2: Initiate transfer — amount in kobo
            transfer_payload = {
                "source": "balance",
                "amount": int(amount * 100),
                "recipient": recipient_code,
                "reason": narration[:100],
                "reference": reference,
                "currency": currency,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/transfer",
                    json=transfer_payload,
                    headers=self.headers,
                )
                response.raise_for_status()
                data = response.json()

                if data.get("status") is True:
                    logger.info(f"Transfer initiated: {reference}")
                    return data["data"]
                else:
                    error_msg = data.get("message", "Transfer failed")
                    logger.error(f"Transfer failed: {error_msg}")
                    raise PaystackError(error_msg)

        except httpx.HTTPStatusError as e:
            logger.error(f"Transfer HTTP error: {e.response.text}")
            raise PaystackError(f"Transfer request failed: {e.response.text}")
        except httpx.HTTPError as e:
            logger.error(f"Transfer HTTP error: {e}")
            raise PaystackError(f"Transfer request failed: {e}")
        except httpx.RequestError as e:
            logger.error(f"Transfer network error: {e}")
            raise PaystackError(f"Network error during transfer: {e}")
