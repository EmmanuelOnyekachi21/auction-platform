"""Pydantic schemas for user-related API requests and responses.

Provides request validation models and response serialization models for
user profile, seller profile, and wallet operations.
"""

from datetime import date, datetime
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
    verified_by_id: UUID | None = None
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
    rating: Decimal = Decimal("0.0")
    total_sales: int = 0
    total_purchases: int = 0
    is_verified_seller: bool = False
    seller_type: str | None = None
    member_since: datetime | None = None

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Custom validation to map User model fields to schema fields."""
        if hasattr(obj, "__dict__") and not isinstance(obj, dict):
            data = {
                "id": obj.id,
                "first_name": getattr(obj, "first_name", None),
                "last_name": getattr(obj, "last_name", None),
                "rating": Decimal("0.0"),  # not stored on User yet
                "total_sales": 0,  # not stored on User yet
                "total_purchases": 0,  # not stored on User yet
                "is_verified_seller": (
                    obj.seller_profile.is_verified
                    if getattr(obj, "seller_profile", None)
                    else False
                ),
                "seller_type": (
                    obj.seller_profile.seller_type
                    if getattr(obj, "seller_profile", None)
                    else None
                ),
                "member_since": getattr(obj, "created_at", None),
            }
            return super().model_validate(data, **kwargs)
        return super().model_validate(obj, **kwargs)


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


# --- KYC Schema ---
class KYCLimitsResponse(BaseModel):
    """Transaction limits for a KYC tier."""

    max_bid: Decimal
    max_wallet_balance: Decimal
    max_daily_withdrawal: Decimal


class KYCStatusResponse(BaseModel):
    """Current KYC tier status and limits for a user."""

    model_config = ConfigDict(from_attributes=True)

    current_tier: str
    tier_1_complete: bool
    tier_2_complete: bool
    tier_3_complete: bool
    # 'none' | 'pending_review' | 'verified' | 'rejected'
    # In mock/dev mode this will be 'verified' immediately.
    # In production with async BVN webhooks it will be 'pending_review'
    # until the provider confirms.
    tier_2_verification_status: str
    limits: KYCLimitsResponse
    next_steps: list[str]


class BVNVerificationRequest(BaseModel):
    """Request body for BVN verification."""

    bvn: str
    date_of_birth: date

    @field_validator("bvn")
    @classmethod
    def validate_bvn(cls, v: str) -> str:
        """Validate BVN is exactly 11 numeric digits."""
        if not v.isdigit() or len(v) != 11:
            raise ValueError("BVN must be exactly 11 numeric digits.")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: date) -> date:
        """Validate user is at least 18 years old and DOB is in the past.

        Age calculation accounts for whether the birthday has occurred
        yet this year. For example, on April 10 2026, someone born
        May 15 2008 is still 17 (birthday hasn't happened yet this year),
        so they would be rejected.
        """
        from datetime import date as date_type

        today = date_type.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError("You must be at least 18 years old.")
        if v >= today:
            raise ValueError("Date of birth must be in the past.")
        return v
