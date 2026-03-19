"""Enums for the notifications application."""

from enum import Enum


class NotificationType(str, Enum):
    OUTBID = "outbid"
    AUCTION_WON = "auction_won"
    BID_PLACED = "bid_placed"
    ITEM_SHIPPED = "item_shipped"
    ESCROW_RELEASED = "escrow_released"
    DISPUTE_OPENED = "dispute_opened"
    DISPUTE_RESOLVED = "dispute_resolved"
    PAYMENT_RECEIVED = "payment_received"
    AUCTION_ENDED = "auction_ended"
    ORDER_CREATED = "order_created"
    ORDER_SHIPPED = "order_shipped"
    ORDER_DELIVERED = "order_delivered"
    WALLET_CREDITED = "wallet_credited"
    WALLET_DEBITED = "wallet_debited"
    ACCOUNT_VERIFIED = "account_verified"


class NotificationReferenceType(str, Enum):
    BID = "bid"
    AUCTION = "auction"
    ORDER = "order"
    DISPUTE = "dispute"
    ESCROW = "escrow"
    WALLET_TRANSACTION = "wallet_transaction"
