"""Enums for the escrow application."""

from enum import Enum


class EscrowStatus(str, Enum):
    HOLDING = "holding"
    RELEASED = "released"
    REFUNDED = "refunded"
    DISPUTED = "disputed"
    FAILED = "failed"
