"""Enums for the bids application."""

from enum import Enum


class BidStatus(str, Enum):
    ACTIVE = "ACTIVE"
    OUTBID = "OUTBID"
    WON = "WON"
    LOST = "LOST"
    RELEASED = "RELEASED"
