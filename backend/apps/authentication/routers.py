"""FastAPI router for authentication endpoints.

Handles user registration, login, token refresh, email verification,
password management, and logout.
"""

import logging

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.schemas import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
)
from apps.authentication.service import AuthService
from apps.users.models import User
from common.dependency import get_current_active_user, get_current_user, get_db
from common.rate_limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("3/minute")
async def register(
    request: Request, payload: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> AuthResponse:
    """Register a new user account and return an initial token pair.

    Args:
        payload: Validated registration data (email, name, password, etc.).
        db: Injected async database session.

    Returns:
        An AuthResponse with user details and JWT access/refresh tokens.

    """
    auth_service = AuthService(db)
    return await auth_service.register(payload)


@router.post("/login", response_model=AuthResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def login(
    request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)
) -> AuthResponse:
    """Authenticate a user by email and password.

    Args:
        payload: Validated login credentials.
        db: Injected async database session.

    Returns:
        An AuthResponse with user details and JWT access/refresh tokens.

    """
    auth_service = AuthService(db)
    return await auth_service.login(payload)


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh(
    data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """Issue a new access token using a valid refresh token.

    Args:
        data: Payload containing the JWT refresh token.
        db: Injected async database session.

    Returns:
        A dictionary containing the new access token and token type.

    """
    auth_service = AuthService(db)
    return await auth_service.refresh_token(data.refresh_token)


@router.get("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    token: str, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """Mark a user's email address as verified using a verification token.

    Args:
        token: The raw verification token from the confirmation link.
        db: Injected async database session.

    Returns:
        A MessageResponse confirming successful verification.

    """
    logger.info(f"Received token: {token}")
    auth_service = AuthService(db)
    return await auth_service.verify_email(token)


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request, data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """Initiate a password reset flow by sending a reset link via email.

    Args:
        data: Payload containing the user's email address.
        db: Injected async database session.

    Returns:
        A MessageResponse confirming that the reset link was sent (if the email exists).

    """
    auth_service = AuthService(db)
    return await auth_service.forgot_password(data.email)


@router.post("/reset-password", status_code=status.HTTP_200_OK)
@limiter.limit("3/minute")
async def reset_password(
    request: Request, data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """Reset a user's password using a valid reset token.

    Args:
        data: Payload containing the reset token and the new password.
        db: Injected async database session.

    Returns:
        A MessageResponse confirming successful password reset.

    """
    auth_service = AuthService(db)
    return await auth_service.reset_password(data.token, data.new_password)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    data: RefreshTokenRequest, current_user: User = Depends(get_current_user)
) -> MessageResponse:
    """Acknowledge a logout request and invalidate the session client-side.

    Note: Server-side token blacklisting requires a cache like Redis.

    Args:
        data: Payload containing the refresh token to be logged out.
        current_user: The authenticated User requesting logout.

    Returns:
        A MessageResponse confirming logout.

    """
    return MessageResponse(message="Successfully logged out")


@router.patch("/password", status_code=status.HTTP_200_OK)
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MessageResponse:
    """Change the password for an authenticated and active user.

    Args:
        data: Payload containing old and new passwords.
        db: Injected async database session.
        current_user: The authenticated and active User.

    Returns:
        A MessageResponse confirming the password update.

    """
    auth_service = AuthService(db)
    return await auth_service.change_password(current_user, data)


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification(
    data: ResendVerificationRequest, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """Resend an email verification link to a user.

    Args:
        data: Payload containing the user's email address.
        db: Injected async database session.

    Returns:
        A MessageResponse confirming that the verification link was resent.

    """
    auth_service = AuthService(db)
    return await auth_service.resend_email_verification(data.email)
