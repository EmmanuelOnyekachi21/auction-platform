"""Pydantic schemas for payment-related API requests and responses."""

from uuid import UUID

from pydantic import BaseModel


class PaymentInitiationResponse(BaseModel):
    """Response schema when payment is initiated.

    Attributes:
        transaction_id: UUID of the transaction.
        payment_link: URL to payment checkout page.
        message: Status message for the user.

    """

    transaction_id: UUID
    payment_link: str
    message: str
