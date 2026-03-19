"""Enumerations for user-related domain values.

Defines the allowed choices for user roles, account statuses,
seller types, and onboarding intent used across the users app.
"""

from enum import Enum


class AccountStatus(str, Enum):
    """Possible lifecycle states for a user account."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    BANNED = "banned"
    DEACTIVATED = "deactivated"


class UserRole(str, Enum):
    """Permission roles assignable to a user."""

    ADMIN = "admin"
    USER = "user"
    STAFF = "staff"
    SUPERUSER = "superuser"


class SellerType(str, Enum):
    """Classification of a seller's trading scale."""

    CASUAL = "casual"
    RETAIL = "retail"
    WHOLESALE = "wholesale"


class OnboardingIntent(str, Enum):
    """Primary intent declared by the user during onboarding."""

    BUY = "buy"
    SELL = "sell"
    BOTH = "both"
