"""Enums for the auctions application."""

from enum import Enum


class ItemCondition(str, Enum):
    """Physical condition of an item being listed for auction."""

    NEW = "NEW"
    LIKE_NEW = "LIKE_NEW"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"


class ItemStatus(str, Enum):
    """Lifecycle state of an item from creation through to sale or archival."""

    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    LISTED = "LISTED"
    SOLD = "SOLD"
    IN_AUCTION = "IN_AUCTION"
    ARCHIVED = "ARCHIVED"


class AuctionStatus(str, Enum):
    """Lifecycle states for an auction from creation through settlement."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ENDED_WITH_WINNER = "ENDED_WITH_WINNER"
    ENDED_NO_BIDS = "ENDED_NO_BIDS"
    SETTLEMENT_IN_PROGRESS = "SETTLEMENT_IN_PROGRESS"
    SETTLED = "SETTLED"
    SCHEDULED = "SCHEDULED"
    CANCELLED = "CANCELLED"
    SETTLEMENT_FAILED = "SETTLEMENT_FAILED"
