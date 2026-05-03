"""Pydantic schemas for wallet-related API requests and responses."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Input Schemas (Requests)


class InitiatePaymentRequest(BaseModel):
    """Request to initiate wallet funding."""

    amount: Decimal = Field(..., gt=0, description="Amount to fund (minimum ₦100)")
    currency: str = Field(default="NGN", max_length=3)
    # version: int

    @field_validator("amount")
    @classmethod
    def validate_minimum_amount(cls, v):
        """Ensure minimum funding amount is ₦100."""
        if v < Decimal("100.00"):
            raise ValueError("Minimum funding amount is ₦100.00")
        return v


class WebhookData(BaseModel):
    """Paystack webhook data structure."""

    id: int
    tx_ref: str
    flw_ref: str
    amount: Decimal
    charged_amount: Decimal
    currency: str
    payment_type: str
    status: str


class WebhookPayload(BaseModel):
    """Paystack webhook payload structure."""

    event: str
    data: WebhookData


class WithdrawalRequest(BaseModel):
    """Request to withdraw funds from wallet."""

    amount: Decimal = Field(..., gt=0, description="Amount to withdraw (minimum ₦100)")
    # version: int

    @field_validator("amount")
    @classmethod
    def validate_minimum_amount(cls, v):
        """Ensure minimum withdrawal amount is ₦100."""
        if v < Decimal("100.00"):
            raise ValueError("Minimum withdrawal amount is ₦100.00")
        return v


# Output Schemas (Responses)


class WalletResponse(BaseModel):
    """Wallet balance response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    available_funds: Decimal
    locked_funds: Decimal
    escrow_funds: Decimal
    currency: str
    # updated_at: datetime


class TransactionResponse(BaseModel):
    """Wallet transaction response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    description: str
    transaction_type: str
    direction: str
    balance_type: str
    status: str
    reference_id: UUID | None = None
    reference_type: str | None = None
    created_at: datetime


class PaymentInitiationResponse(BaseModel):
    """Response after initiating payment."""

    payment_link: str
    transaction_reference: str
    amount: Decimal
    expires_at: datetime
    # version: int


class PaymentResponse(BaseModel):
    """Payment details response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_reference: str
    provider: str
    provider_reference: str | None = None
    amount: Decimal
    currency: str
    status: str
    webhook_received_at: datetime | None = None
    verified_at: datetime | None = None
    created_at: datetime
    # version: int
