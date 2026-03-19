"""Enumerations for wallet-related domain values.

Defines the allowed choices for transaction types, directions,
balance buckets, and reference entity types used across the wallet app.
"""

from enum import Enum


class TransactionType(str, Enum):
    """The nature of a wallet transaction."""

    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    BID_LOCK = "bid_lock"
    BID_UNLOCK = "bid_unlock"
    ESCROW_MOVE = "escrow_move"
    ESCROW_RELEASE = "escrow_release"
    COMMISION = "commission"
    REFUND = "refund"


class TransactionDirection(str, Enum):
    """Whether funds are moving into or out of the wallet."""

    CREDIT = "credit"
    DEBIT = "debit"


class BalanceType(str, Enum):
    """The balance bucket affected by a transaction."""

    AVAILABLE = "available"
    ESCROW = "escrow"
    LOCKED = "locked"


class ReferenceType(str, Enum):
    """The type of entity that triggered a wallet transaction."""

    BID = "bid"
    ORDER = "order"
    ESCROW = "escrow"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    REFUND = "refund"
    COMMISSION = "commission"
