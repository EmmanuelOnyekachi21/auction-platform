"""Enums for the escrow application."""

from enum import Enum


class EscrowStatus(str, Enum):
    HOLDING = "HOLDING"
    RELEASED = "RELEASED"
    REFUNDED = "REFUNDED"
    DISPUTED = "DISPUTED"
    FAILED = "FAILED"
