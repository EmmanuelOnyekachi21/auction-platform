"""Enums for the auctions application."""

from enum import Enum


class ItemCondition(str, Enum):
    """Physical condition of an item being listed for auction."""

    NEW = "new"
    LIKE_NEW = "like_new"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class ItemStatus(str, Enum):
    """Lifecycle state of an item from creation through to sale or archival."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    LISTED = "listed"
    SOLD = "sold"
    IN_AUCTION = "in_auction"
    ARCHIVED = "archived"
