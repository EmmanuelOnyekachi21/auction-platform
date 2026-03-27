"""Pydantic schemas for user-related API requests and responses.

Provides request validation models and response serialization models for
user profile, seller profile, and wallet operations.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from apps.users.models import AccountStatus, OnboardingIntent, SellerType, UserRole


class UpdateProfileRequest(BaseModel):
    """Request model for updating user profile.

    Attributes:
        first_name: User's first name (optional).
        last_name: User's last name (optional).
        bio: User biography or description (max 500 characters, optional).
        profile_picture_url: URL to user's profile picture (optional).
        city: User's city of residence (max 100 characters, optional).
        state: User's state of residence (max 100 characters, optional).
        onboarding_intent: User's intent during onboarding (optional).

    """

    first_name: str | None = None
    last_name: str | None = None
    bio: str | None = Field(None, max_length=500)
    profile_picture_url: HttpUrl | None = None
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    onboarding_intent: OnboardingIntent | None = None
    bank_code: str | None = None
    account_number: str | None = None
    account_name: str | None = None

    @field_validator("profile_picture_url", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        """Convert empty string to None for optional URL field."""
        if v == "" or v is None:
            return None
        return v


class RegisterSellerRequest(BaseModel):
    """Request model for registering as a seller.

    Attributes:
        seller_type: Classification of seller (casual, retail, wholesale).

    """

    seller_type: SellerType


class VerifySellerRequest(BaseModel):
    """Request model for admin verification of seller profile.

    Attributes:
        is_verified: Whether seller is approved (True) or rejected (False).
        rejection_reason: Reason for rejection if is_verified is False
            (required when rejecting).

    """

    is_verified: bool
    rejection_reason: str | None = None

    @model_validator(mode="after")
    def validate_rejection_reason(self) -> "VerifySellerRequest":
        """Validate that rejection reason is provided when rejecting.

        Raises:
            ValueError: If rejection is without a reason.

        """
        if not self.is_verified and not self.rejection_reason:
            msg = "rejection_reason is required when is_verified is False"
            raise ValueError(msg)
        return self


class ProfileData(BaseModel):
    """Nested response model for user profile details.

    Attributes:
        bio: User's biography or description.
        profile_picture_url: URL to profile picture.
        city: City of residence.
        state: State of residence.
        onboarding_intent: User's onboarding intent.

    """

    model_config = ConfigDict(from_attributes=True)

    bio: str | None = None
    profile_picture_url: str | None = None
    city: str | None = None
    state: str | None = None
    onboarding_intent: OnboardingIntent | None = None
    bank_code: str | None = None
    account_number: str | None = None
    account_name: str | None = None


class SellerData(BaseModel):
    """Nested response model for seller profile details.

    Attributes:
        seller_type: Type of seller (casual, retail, wholesale).
        is_verified: Whether seller is verified by admin.
        created_at: Timestamp when seller profile was created.
        verified_at: Timestamp of verification (None if not verified).

    """

    model_config = ConfigDict(from_attributes=True)

    seller_type: SellerType
    is_verified: bool
    verified_by_id: UUID
    created_at: datetime
    verified_at: datetime | None = None


class UserProfileResponse(BaseModel):
    """Full user profile response for authenticated user.

    Attributes:
        id: User's unique identifier (UUID).
        first_name: User's first name.
        last_name: User's last name.
        email: User's email address.
        phone_number: User's phone number.
        role: User's role (user, seller, admin).
        account_status: Current account status.
        is_email_verified: Whether email is verified.
        profile: Nested user profile data.
        seller_profile: Nested seller profile data if applicable.
        created_at: Account creation timestamp.

    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str | None = None
    last_name: str | None = None
    email: str
    phone_number: str | None = None
    role: UserRole
    account_status: AccountStatus
    is_email_verified: bool
    profile: ProfileData | None = None
    seller_profile: SellerData | None = None
    created_at: datetime


class PublicUserResponse(BaseModel):
    """Public user profile response without sensitive data.

    Attributes:
        id: User's unique identifier (UUID).
        first_name: User's first name.
        last_name: User's last name.
        rating: User's average rating as decimal.
        total_sales: Number of completed sales.
        total_purchases: Number of completed purchases.
        is_verified_seller: Whether user is a verified seller.
        seller_type: Type of seller if applicable.
        member_since: Account creation timestamp.

    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str | None = None
    last_name: str | None = None
    rating: Decimal
    total_sales: int
    total_purchases: int
    is_verified_seller: bool
    seller_type: str | None = None
    member_since: datetime


class SellerProfileResponse(BaseModel):
    """Seller profile response model.

    Attributes:
        seller_type: Type of seller (casual, retail, wholesale).
        is_verified: Whether seller is verified by admin.
        business_name: Name of seller's business if applicable.
        created_at: Profile creation timestamp.

    """

    model_config = ConfigDict(from_attributes=True)

    seller_type: SellerType
    is_verified: bool
    business_name: str | None = None
    created_at: datetime


class WalletBalanceResponse(BaseModel):
    """User wallet balance response model.

    Attributes:
        available_funds: Amount available for withdrawal.
        locked_funds: Amount locked in active bids or orders.
        escrow_funds: Amount held in escrow for completed orders.
        currency: Currency code (e.g., "NGN").

    """

    model_config = ConfigDict(from_attributes=True)

    available_funds: Decimal
    locked_funds: Decimal
    escrow_funds: Decimal
    currency: str
