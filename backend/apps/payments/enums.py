"""Enumerations for payment-related domain values."""

from enum import Enum


class PaymentProvider(str, Enum):
    """External payment provider for wallet funding."""

    FLUTTERWAVE = "FLUTTERWAVE"
    PAYSTACK = "PAYSTACK"
    BANK_TRANSFER = "BANK_TRANSFER"
    MICROFINANCE = "MICROFINANCE"
    MANUAL = "MANUAL"


class PaymentStatus(str, Enum):
    """Lifecycle status of an external payment record."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
