"""Enums for the escrow application."""

from enum import Enum


class EscrowStatus(str, Enum):
    """Lifecycle states for an escrow record."""

    HOLDING = "HOLDING"
    RELEASED = "RELEASED"
    REFUNDED = "REFUNDED"
    DISPUTED = "DISPUTED"
    FAILED = "FAILED"
    PROCESSING = "PROCESSING"
