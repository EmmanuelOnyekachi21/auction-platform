"""Enums for the orders application."""

from enum import Enum


class OrderStatus(str, Enum):
    PENDING_SHIPMENT = "pending_shipment"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    DISPUTED = "disputed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
