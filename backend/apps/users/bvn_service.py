"""BVN (Bank Verification Number) verification service.

Handles BVN format validation, hashing, and verification against
the Paystack BVN API. When BVN_VERIFICATION_ENABLED=False (development),
returns a mock success response so the full KYC flow can be tested
without real credentials.

Security rules:
- BVN is NEVER logged in plain text
- BVN is NEVER stored in plain text
- Only the SHA256 hash is persisted
- Only the provider reference is logged
"""

import hashlib
import logging
import uuid

import httpx

from common.exceptions import ValidationException
from config.settings import settings

logger = logging.getLogger(__name__)


class BVNService:
    """Service for BVN format validation, hashing, and verification."""

    BVN_LENGTH = 11

    def hash_bvn(self, bvn: str) -> str:
        """Return SHA256 hex digest of the BVN.

        Args:
            bvn: Plain text BVN string.

        Returns:
            64-character hex string — safe to store in the database.

        """
        return hashlib.sha256(bvn.encode()).hexdigest()

    def validate_bvn_format(self, bvn: str) -> None:
        """Validate BVN is exactly 11 numeric digits.

        Args:
            bvn: BVN string to validate.

        Raises:
            ValidationException: If format is invalid.

        """
        if not bvn.isdigit() or len(bvn) != self.BVN_LENGTH:
            raise ValidationException(
                message="BVN must be exactly 11 numeric digits.",
            )

    async def verify_bvn(
        self,
        bvn: str,
        first_name: str,
        last_name: str,
        date_of_birth: str,
    ) -> dict:
        """Verify a BVN against the provider API.

        Validates format first, then either calls the real Paystack
        BVN API (when enabled) or returns a mock success (development).

        Args:
            bvn: 11-digit BVN string. Never logged.
            first_name: User's first name for identity matching.
            last_name: User's last name for identity matching.
            date_of_birth: Date of birth in YYYY-MM-DD format.

        Returns:
            dict with keys:
                is_match (bool): Whether BVN matches the provided details.
                reference (str): Provider reference for audit trail.
                message (str): Human-readable result message.

        Raises:
            ValidationException: If BVN format is invalid or verification fails.

        """
        self.validate_bvn_format(bvn)

        if not settings.bvn_verification_enabled:
            # Development mode — mock success without calling real API
            mock_reference = f"mock-{uuid.uuid4().hex[:12]}"
            logger.info(
                "BVN verification skipped (disabled). Mock reference: %s",
                mock_reference,
            )
            return {
                "is_match": True,
                "reference": mock_reference,
                "message": "BVN verified successfully (mock).",
            }

        # Production — call Paystack BVN verification API
        return await self._call_flutterwave_bvn_api(
            bvn, first_name, last_name, date_of_birth
        )

    async def _call_flutterwave_bvn_api(
        self,
        bvn: str,
        first_name: str,
        last_name: str,
        date_of_birth: str,
    ) -> dict:
        """Call Paystack BVN verification endpoint.

        Args:
            bvn: BVN to verify. Never logged.
            first_name: First name for matching.
            last_name: Last name for matching.
            date_of_birth: DOB in YYYY-MM-DD format.

        Returns:
            Verification result dict.

        Raises:
            ValidationException: If verification fails or API errors.

        """
        url = f"{settings.flutterwave_base_url}/kyc/bvns/{bvn}"
        headers = {
            "Authorization": f"Bearer {settings.flutterwave_secret_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

            if response.status_code != 200:
                logger.error("BVN API returned status %s", response.status_code)
                raise ValidationException(
                    message="BVN verification failed. Please try again later.",
                    code="BVN_API_ERROR",
                )

            data = response.json()
            reference = data.get("data", {}).get("reference", "unknown")
            logger.info("BVN verification completed. Reference: %s", reference)

            # Check name match from Paystack response
            bvn_data = data.get("data", {})
            provider_first = bvn_data.get("first_name", "").lower()
            provider_last = bvn_data.get("last_name", "").lower()

            first_name_match = first_name.lower() in provider_first
            last_name_match = last_name.lower() in provider_last
            is_match = first_name_match and last_name_match

            return {
                "is_match": is_match,
                "reference": reference,
                "message": "BVN verified." if is_match else "BVN details do not match.",
            }

        except httpx.RequestError as exc:
            logger.error("BVN API request failed: %s", type(exc).__name__)
            raise ValidationException(
                message="BVN verification service unavailable. Please try again later.",
                code="BVN_API_UNAVAILABLE",
            )
