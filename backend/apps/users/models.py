"""ORM models for the users application.

Defines the core user-related database tables:
- User: authentication and identity record.
- UserProfile: extended public-facing profile data.
- SellerProfile: seller-specific details and verification state.
- VerificationDoc: supporting documents uploaded for seller verification.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import BaseModel

from .enums import (
    AccountStatus,
    KYCTier,
    OnboardingIntent,
    SellerType,
    SellerVerificationStatus,
    UserRole,
)

if TYPE_CHECKING:
    from apps.auctions.models import Auction, Bid, Item
    from apps.authentication.models import EmailVerificationToken, PasswordResetToken
    from apps.notifications.models import Notification
    from apps.users.kyc_models import KYCDocumentModel, KYCProfile
    from apps.wallet.models import Wallet


class User(BaseModel):
    """Core user record storing authentication and identity data.

    Attributes:
        first_name: User's given name, max 100 characters.
        last_name: User's family name, max 100 characters.
        email: Unique, indexed email address used for login.
        phone_number: Unique contact number, max 15 characters.
        password_hash: Bcrypt or equivalent hash of the user's password.
        account_status: Current lifecycle state of the account.
        role: Permission role assigned to the user.
        is_email_verified: Whether the user has confirmed their email.
        last_login_at: Timezone-aware timestamp of the most recent login.

    """

    __tablename__ = "users"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    phone_number: Mapped[str] = mapped_column(String(15), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    account_status: Mapped[AccountStatus] = mapped_column(
        nullable=False, default=AccountStatus.ACTIVE, index=True
    )
    role: Mapped[UserRole] = mapped_column(
        nullable=False, default=UserRole.USER, index=True
    )
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    last_login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    kyc_tier: Mapped[KYCTier] = mapped_column(
        nullable=False, default=KYCTier.TIER_1, index=True
    )

    # Relationships
    profile: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="user", uselist=False
    )
    seller_profile: Mapped["SellerProfile"] = relationship(
        "SellerProfile",
        back_populates="user",
        uselist=False,
        foreign_keys="SellerProfile.user_id",
    )
    wallet: Mapped["Wallet"] = relationship(
        "Wallet", back_populates="user", uselist=False
    )
    auctions: Mapped[list["Auction"]] = relationship("Auction", back_populates="seller")
    bids: Mapped[list["Bid"]] = relationship("Bid", back_populates="bidder")
    items: Mapped[list["Item"]] = relationship("Item", back_populates="seller")
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user"
    )
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        "PasswordResetToken", back_populates="user"
    )
    email_verification: Mapped[list["EmailVerificationToken"]] = relationship(
        "EmailVerificationToken", back_populates="user"
    )

    kyc_profile: Mapped["KYCProfile"] = relationship(
        "KYCProfile", uselist=False, back_populates="user"
    )
    kyc_documents: Mapped[list["KYCDocumentModel"]] = relationship(
        "KYCDocumentModel",
        back_populates="user",
        foreign_keys="KYCDocumentModel.user_id",
    )


class UserProfile(BaseModel):
    """Extended public-facing profile data for a user.

    Holds optional biographical and location information, onboarding
    intent, and aggregated activity statistics.

    Attributes:
        user_id: Foreign key referencing the owning ``User``.
        bio: Short free-text biography.
        avatar_url: URL to the user's profile picture.
        city: City of residence.
        state: State or province of residence.
        onboarding_intent: Primary intent declared during onboarding.
        rating: Aggregate rating score, stored as a 3-digit decimal.
        total_sales: Cumulative number of completed sales.
        total_purchases: Cumulative number of completed purchases.

    """

    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    bio: Mapped[str] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str] = mapped_column(String(500), nullable=True)
    city: Mapped[str] = mapped_column(String(255), nullable=True)
    state: Mapped[str] = mapped_column(String(255), nullable=True)
    onboarding_intent: Mapped[OnboardingIntent] = mapped_column(nullable=True)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), nullable=True)
    total_sales: Mapped[int] = mapped_column(nullable=True)
    total_purchases: Mapped[int] = mapped_column(nullable=True)

    # Bank details for withdrawals
    bank_code: Mapped[str] = mapped_column(String(10), nullable=True)
    account_number: Mapped[str] = mapped_column(String(10), nullable=True)
    account_name: Mapped[str] = mapped_column(String(255), nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="profile")


class SellerProfile(BaseModel):
    """Seller-specific details and verification state for a user.

    A ``SellerProfile`` is created when a user registers as a seller.
    It tracks their seller classification, bank payout details, and
    the admin-driven verification workflow.

    Attributes:
        user_id: Foreign key referencing the owning ``User``.
        seller_type: Classification of the seller's trading scale.
        is_verified: Whether the seller has passed identity verification.
        bank_acct_number: Bank account number for payouts.
        bank_name: Name of the bank holding the payout account.
        verified_at: Timezone-aware timestamp of when verification was granted.
        verified_by_id: Foreign key referencing the admin ``User`` who
            approved the verification.

    """

    __tablename__ = "seller_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )
    seller_type: Mapped[SellerType] = mapped_column(nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_status: Mapped[SellerVerificationStatus] = mapped_column(
        nullable=False, default=SellerVerificationStatus.PENDING, index=True
    )
    bank_acct_number: Mapped[str] = mapped_column(String(50), nullable=True)
    bank_name: Mapped[str] = mapped_column(String(50), nullable=True)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], back_populates="seller_profile"
    )
    verification_docs: Mapped[list["VerificationDoc"]] = relationship(
        "VerificationDoc", back_populates="seller_profile"
    )
    verified_by: Mapped["User"] = relationship("User", foreign_keys=[verified_by_id])


class VerificationDoc(BaseModel):
    """A document uploaded by a seller to support identity verification.

    Attributes:
        title: Short descriptive title of the document.
        description: Detailed explanation of what the document proves.
        url: Publicly accessible or signed URL pointing to the stored file.
        seller_id: Foreign key referencing the owning ``SellerProfile``.

    """

    __tablename__ = "verification_docs"

    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("seller_profiles.id"),
        nullable=False,
    )

    # Relationships
    seller_profile: Mapped["SellerProfile"] = relationship(
        "SellerProfile", back_populates="verification_docs"
    )
