"""Enums for the bids application."""

from enum import Enum


class BidStatus(str, Enum):
    ACTIVE = "active"
    OUTBID = "outbid"
    WON = "won"
    LOST = "lost"
    RELEASED = "released"
