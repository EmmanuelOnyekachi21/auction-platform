"""Pydantic schemas for dispute-related API requests and responses."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from apps.disputes.enums import DisputeStatus, EvidenceFileType

# ── Input Schemas ─────────────────────────────────────────────────────────────


class RaiseDisputeRequest(BaseModel):
    """Buyer submits this to open a dispute on an order."""

    title: str = Field(..., min_length=10, max_length=255)
    description: str = Field(..., min_length=50, max_length=5000)


class SubmitEvidenceRequest(BaseModel):
    """Either party submits evidence to support their case.

    url must be a valid HTTPS URL — we don't store files ourselves,
    the user uploads to their own storage and provides the link.
    """

    url: HttpUrl
    file_type: EvidenceFileType
    description: Optional[str] = Field(None, max_length=255)


class ResolveDisputeRequest(BaseModel):
    """Admin-only. Resolves a dispute in favour of one party.

    resolution_notes is required — admin must explain their decision.
    This creates an audit trail and gives both parties context.
    """

    resolution: str = Field(
        ...,
        description="in_favour_of_buyer or in_favour_of_seller",
        pattern="^(in_favour_of_buyer|in_favour_of_seller)$",
    )
    resolution_notes: str = Field(..., min_length=20)


# ── Output Schemas ────────────────────────────────────────────────────────────


class EvidenceResponse(BaseModel):
    """A single piece of evidence submitted to a dispute."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str  # stored as string — HttpUrl doesn't round-trip cleanly from ORM
    file_type: EvidenceFileType
    description: Optional[str] = None
    uploaded_by_id: UUID
    created_at: datetime


class DisputeParty(BaseModel):
    """Minimal user info shown on a dispute."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str | None = None
    last_name: str | None = None


class DisputePartyDetail(BaseModel):
    """Full party info for admin — includes contact details."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone_number: str | None = None


class DisputeSummary(BaseModel):
    """Minimal dispute info shown inside an order response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    status: DisputeStatus
    raised_by_id: UUID
    created_at: datetime
    raised_by: Optional[DisputeParty] = None
    against: Optional[DisputeParty] = None


class DisputeOrderSummary(BaseModel):
    """Minimal order info embedded in a dispute response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: Optional[float] = None
    status: Optional[str] = None


class DisputeDetailResponse(BaseModel):
    """Full dispute detail including evidence and resolution."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    status: DisputeStatus
    raised_by_id: UUID
    against_id: UUID
    created_at: datetime
    description: str
    raised_by: Optional[DisputePartyDetail] = None
    against: Optional[DisputePartyDetail] = None
    order: Optional[DisputeOrderSummary] = None
    evidence: list[EvidenceResponse] = []
    resolution: Optional[str] = None
    resolved_by_id: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
