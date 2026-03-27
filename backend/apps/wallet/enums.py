"""Enumerations for wallet-related domain values.

Defines the allowed choices for transaction types, directions,
balance buckets, and reference entity types used across the wallet app.
"""

from enum import Enum


class TransactionType(str, Enum):
    """The nature of a wallet transaction."""

    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    BID_LOCK = "BID_LOCK"
    BID_UNLOCK = "BID_UNLOCK"
    ESCROW_MOVE = "ESCROW_MOVE"
    ESCROW_RELEASE = "ESCROW_RELEASE"
    COMMISION = "COMMISION"
    REFUND = "REFUND"


class TransactionDirection(str, Enum):
    """Whether funds are moving into or out of the wallet."""

    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class BalanceType(str, Enum):
    """The balance bucket affected by a transaction."""

    AVAILABLE = "AVAILABLE"
    ESCROW = "ESCROW"
    LOCKED = "LOCKED"


class ReferenceType(str, Enum):
    """The type of entity that triggered a wallet transaction."""

    BID = "BID"
    ORDER = "ORDER"
    ESCROW = "ESCROW"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    REFUND = "REFUND"
    COMMISSION = "COMMISSION"


class TransactionStatus(str, Enum):
    """The current status of a wallet transaction."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
