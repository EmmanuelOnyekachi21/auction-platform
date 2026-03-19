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


class OnboardingIntent(str, Enum):
    """Primary intent declared by the user during onboarding."""

    BUY = "BUY"
    SELL = "SELL"
    BOTH = "BOTH"
