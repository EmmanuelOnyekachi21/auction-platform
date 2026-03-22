"""Pydantic request and response schemas for the authentication app.

Request schemas validate and coerce inbound payloads for registration,
login, token refresh, email verification, and password management flows.

Response schemas define the outbound shapes for auth-related API responses.
"""

import re
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


def valid_password_strength(v: str) -> str:
    """Validate that a password meets the platform's strength requirements.

    Enforces a minimum length of 8 characters and requires at least one
    uppercase letter, one lowercase letter, one digit, and one special
    character.

    Args:
        v: The plain-text password string to validate.

    Returns:
        The original password string if all checks pass.

    Raises:
        ValueError: If any strength requirement is not met.

    """
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
        raise ValueError("Password must contain at least one special character")
    return v


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """Payload for creating a new user account.

    Attributes:
        first_name: User's given name, 2–100 characters.
        last_name: User's family name, 2–100 characters.
        email: Valid email address; used as the login identifier.
        phone_number: Nigerian mobile number in ``+234`` or ``0`` format.
        password: Plain-text password; must pass strength validation.
        confirm_password: Must match ``password`` exactly.

    """

    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone_number: str = Field(..., min_length=8, max_length=15)
    password: str = Field(..., min_length=8)
    confirm_password: str

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """Validate that the phone number is a valid Nigerian mobile number.

        Args:
            v: The raw phone number string.

        Returns:
            The phone number string if it matches the expected pattern.

        Raises:
            ValueError: If the number does not match the Nigerian format.

        """
        pattern = r"^(\+234|0)[789]\d{9}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid Nigerian phone number")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Delegate password strength validation to ``valid_password_strength``.

        Args:
            v: The plain-text password string.

        Returns:
            The validated password string.

        """
        return valid_password_strength(v)

    @model_validator(mode="after")
    def password_match(self) -> "RegisterRequest":
        """Ensure ``password`` and ``confirm_password`` are identical.

        Returns:
            The model instance if passwords match.

        Raises:
            ValueError: If the two password fields differ.

        """
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(BaseModel):
    """Payload for authenticating an existing user.

    Attributes:
        email: The user's registered email address.
        password: The user's plain-text password.

    """

    email: EmailStr
    password: str = Field(..., min_length=1)


class RefreshTokenRequest(BaseModel):
    """Payload for obtaining a new access token using a refresh token.

    Attributes:
        refresh_token: A valid, unexpired refresh JWT.

    """

    refresh_token: str


class VerifyEmailRequest(BaseModel):
    """Payload for confirming a user's email address.

    Attributes:
        token: The plain verification token sent to the user's email.

    """

    token: str


class ForgotPasswordRequest(BaseModel):
    """Payload for initiating a password-reset flow.

    Attributes:
        email: The email address associated with the account to reset.

    """

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Payload for completing a password reset using a reset token.

    Attributes:
        token: The plain reset token received via email.
        new_password: The desired new password; must pass strength validation.
        confirm_password: Must match ``new_password`` exactly.

    """

    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str

    @model_validator(mode="after")
    def password_match(self) -> "ResetPasswordRequest":
        """Ensure ``new_password`` and ``confirm_password`` are identical.

        Returns:
            The model instance if passwords match.

        Raises:
            ValueError: If the two password fields differ.

        """
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Delegate new password strength validation to ``valid_password_strength``.

        Args:
            v: The plain-text new password string.

        Returns:
            The validated password string.

        """
        return valid_password_strength(v)


class ChangePasswordRequest(BaseModel):
    """Payload for changing a password while authenticated.

    Attributes:
        old_password: The user's current password for verification.
        new_password: The desired new password; must pass strength validation.
        confirm_password: Must match ``new_password`` exactly.

    """

    old_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)
    confirm_password: str

    @model_validator(mode="after")
    def password_match(self) -> "ChangePasswordRequest":
        """Ensure ``new_password`` and ``confirm_password`` are identical.

        Returns:
            The model instance if passwords match.

        Raises:
            ValueError: If the two password fields differ.

        """
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Delegate new password strength validation to ``valid_password_strength``.

        Args:
            v: The plain-text new password string.

        Returns:
            The validated password string.

        """
        return valid_password_strength(v)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class UserTokenResponse(BaseModel):
    """User identity fields embedded in an authentication response.

    Attributes:
        id: The user's UUID primary key.
        first_name: User's given name.
        last_name: User's family name.
        email: User's email address.
        role: The user's permission role string.
        is_email_verified: Whether the user has confirmed their email.
        account_status: Current lifecycle state of the account.

    """

    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    role: str
    is_email_verified: bool
    account_status: str


class AuthResponse(BaseModel):
    """Response body returned after a successful login or token refresh.

    Attributes:
        user: Serialised identity fields for the authenticated user.
        access_token: Short-lived JWT for authenticating API requests.
        refresh_token: Long-lived JWT for obtaining new access tokens.
        token_type: Always ``"bearer"``.

    """

    user: UserTokenResponse
    access_token: str
    refresh_token: str
    token_type: str


class MessageResponse(BaseModel):
    """Generic single-message response for simple confirmation endpoints.

    Attributes:
        message: Human-readable confirmation or status message.

    """

    message: str
