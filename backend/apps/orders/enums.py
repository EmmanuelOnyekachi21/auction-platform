"""Enums for the orders application."""

from enum import Enum


class OrderStatus(str, Enum):
    PENDING_SHIPMENT = "PENDING_SHIPMENT"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    DISPUTED = "DISPUTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"
