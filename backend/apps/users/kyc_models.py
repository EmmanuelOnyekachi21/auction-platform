import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import BaseModel

from .enums import KYCDocuments, KYCStatus, KYCTier

# from datetime import datetime, timezone

if TYPE_CHECKING:
    from apps.users.models import User


class KYCProfile(BaseModel):
    __tablename__ = "kyc_profiles"
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        index=True,
        nullable=False,
        unique=True,
    )
    current_tier: Mapped[KYCTier] = mapped_column(
        default=KYCTier.TIER_1, nullable=False
    )

    # Tier 1 fields
    email_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    phone_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    tier_1_completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Tier 2 fields
    bvn_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    bvn_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    # reference from BVN verification provider
    bvn_verification_reference: Mapped[str] = mapped_column(String, nullable=True)
    bvn_verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tier_2_completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Tier 3 fields
    address_verified: Mapped[bool] = mapped_column(
        default=False,
    )
    bank_statement_verified: Mapped[bool] = mapped_column(default=False)
    tier_3_completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # General fields
    bvn_attempt_count: Mapped[int] = mapped_column(default=0, nullable=False)
    bvn_attempt_reset_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_verification_attempt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[str] = mapped_column(Text, nullable=True)

    # Realtionships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="kyc_profile",
    )


class KYCDocumentModel(BaseModel):
    __tablename__ = "kyc_document"

    # Immutable record
    updated_at = None

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    document_type: Mapped[KYCDocuments] = mapped_column(nullable=False)
    document_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[KYCStatus] = mapped_column(default=KYCStatus.PENDING, nullable=False)
    verified_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[str] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship
    user: Mapped["User"] = relationship(
        "User", back_populates="kyc_documents", foreign_keys=[user_id]
    )
    verified_by: Mapped["User"] = relationship("User", foreign_keys=[verified_by_id])
