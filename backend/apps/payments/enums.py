from enum import Enum


class PaymentProvider(str, Enum):
    """External payment provider for wallet funding."""

    FLUTTERWAVE = "FLUTTERWAVE"
    BANK_TRANSFER = "BANK_TRANSFER"
    MICROFINANCE = "MICROFINANCE"
    MANUAL = "MANUAL"


class PaymentStatus(str, Enum):
    """Status of external system"""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
