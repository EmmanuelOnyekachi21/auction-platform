"""Pydantic schemas for escrow-related API responses."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field

from apps.escrow.enums import EscrowStatus


class EscrowResponse(BaseModel):
    """Escrow state shown inside an order detail response.

    seller_payout is computed here (amount - commission_amount) so the
    frontend never has to do the math itself.

    Note: we never expose winner_id or seller_id directly — the order
    already carries buyer/seller info. Escrow just shows the money state.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: Decimal
    commission_amount: Decimal
    status: EscrowStatus
    auto_release_at: datetime
    released_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None

    @computed_field
    @property
    def seller_payout(self) -> Decimal:
        """What the seller actually receives after commission."""
        return self.amount - self.commission_amount
