"""Enumerations for user-related domain values.

Defines the allowed choices for user roles, account statuses,
seller types, and onboarding intent used across the users app.
"""

from enum import Enum


class AccountStatus(str, Enum):
    """Possible lifecycle states for a user account."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    BANNED = "BANNED"
    DEACTIVATED = "DEACTIVATED"


class UserRole(str, Enum):
    """Permission roles assignable to a user."""

    ADMIN = "ADMIN"
    USER = "USER"
    STAFF = "STAFF"
    SUPERUSER = "SUPERUSER"


class SellerType(str, Enum):
    """Classification of a seller's trading scale."""

    CASUAL = "CASUAL"
    RETAIL = "RETAIL"
    WHOLESALE = "WHOLESALE"


class SellerVerificationStatus(str, Enum):
    """Verification workflow state for a seller profile."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class OnboardingIntent(str, Enum):
    """Primary intent declared by the user during onboarding."""

    BUY = "BUY"
    SELL = "SELL"
    BOTH = "BOTH"


class KYCTier(str, Enum):
    """Tier of Know Your Customer verification."""

    TIER_1 = "TIER_1"  # Email + Phone verified
    TIER_2 = "TIER_2"  # BVN verified
    TIER_3 = "TIER_3"  # address + bank statement


class KYCStatus(str, Enum):
    """Verification status of a KYC document or profile."""

    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class KYCDocuments(str, Enum):
    """Accepted document types for KYC verification."""

    NATIONAL_ID = "NATIONAL_ID"
    DRIVERS_LICENSE = "DRIVERS_LICENSE"
    PASSPORT = "PASSPORT"
    BANK_STATEMENT = "BANK_STATEMENT"
    UTILITY_BILL = "UTILITY_BILL"
    SELFIE = "SELFIE"
