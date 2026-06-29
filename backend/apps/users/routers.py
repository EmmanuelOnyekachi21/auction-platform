"""Users router module providing user profile management endpoints.

Provides endpoints for retrieving, updating, and managing user profiles,
seller registration, and wallet operations.
"""

from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.payments.paystack_service import PaystackService
from apps.users.models import User
from apps.users.schemas import (
    PublicUserResponse,
    RegisterSellerRequest,
    SellerProfileResponse,
    UpdateProfileRequest,
    UserProfileResponse,
    VerifySellerRequest,
)
from apps.users.service import UserService
from apps.wallet.service import WalletService
from common.dependency import get_current_active_user, get_db, require_admin
from common.schemas import MessageResponse
from config.settings import settings

router = APIRouter()


@router.get("/me/resolve-account")
async def resolve_bank_account(
    account_number: str,
    bank_code: str,
    current_user: User = Depends(get_current_active_user),
):
    """Resolve account name from Paystack given account number + bank code.

    Used by the frontend to auto-fill account name when user sets up
    bank withdrawal details.
    """
    from fastapi import HTTPException

    from apps.payments.paystack_service import PaystackService
    from common.exceptions import PaystackError

    paystack = PaystackService(
        base_url=settings.paystack_base_url,
        secret_key=settings.paystack_secret_key,
    )
    try:
        result = await paystack.resolve_account(account_number, bank_code)
        return result
    except PaystackError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Get the authenticated user's full profile.

    Args:
        current_user: The currently authenticated user.
        db: The database session dependency.

    Returns:
        UserProfileResponse: Full user profile with nested data.

    """
    service = UserService(db)
    return await service.get_my_profile(current_user.id)


@router.patch("/me", response_model=UserProfileResponse)
async def update_my_profile(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Update the authenticated user's profile.

    Args:
        data: Validated profile update request data.
        current_user: The currently authenticated user.
        db: The database session dependency.

    Returns:
        UserProfileResponse: Updated user profile.

    """
    service = UserService(db)
    return await service.update_my_profile(current_user.id, data)


@router.delete("/me", response_model=MessageResponse)
async def delete_my_account(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Soft delete (deactivate) the authenticated user's account.

    Args:
        current_user: The currently authenticated user.
        db: The database session dependency.

    Returns:
        MessageResponse: Confirmation of account deactivation.

    """
    service = UserService(db)
    return await service.deactivate_account(current_user.id)


@router.get("/{user_id}", response_model=PublicUserResponse)
async def get_public_profile(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PublicUserResponse:
    """Get the public profile of any user (no authentication required).

    Args:
        user_id: UUID of the user to retrieve.
        db: The database session dependency.

    Returns:
        PublicUserResponse: Public user profile without sensitive data.

    """
    service = UserService(db)
    return await service.get_public_profile(user_id)


@router.post(
    "/me/seller-profile",
    response_model=SellerProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_as_seller(
    data: RegisterSellerRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SellerProfileResponse:
    """Register the authenticated user as a seller.

    Args:
        data: Validated seller registration request data.
        current_user: The currently authenticated user.
        db: The database session dependency.

    Returns:
        SellerProfileResponse: Newly created seller profile.

    """
    service = UserService(db)
    return await service.register_as_seller(current_user.id, data)


@router.post(
    "/me/seller-profile/documents",
    status_code=status.HTTP_201_CREATED,
)
async def upload_verification_document(
    file: UploadFile = File(...),
    doc_type: str = Form(default="Verification Document"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload a verification document for seller profile.

    Args:
        file: The uploaded document file (multipart/form-data).
        doc_type: Type of verification document (e.g., "National ID").
        current_user: The currently authenticated user.
        db: The database session dependency.

    Returns:
        dict: Document metadata including id, title, url, and created_at.

    """
    service = UserService(db)
    doc = await service.upload_verification_document(current_user.id, file, doc_type)
    return {
        "id": str(doc.id),
        "title": doc.title,
        "url": doc.url,
        "created_at": doc.created_at,
    }


@router.patch(
    "/{user_id}/seller-profile/verify",
    response_model=SellerProfileResponse,
)
async def verify_seller(
    user_id: UUID,
    data: VerifySellerRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> SellerProfileResponse:
    """Verify or reject a seller's profile (admin only).

    Args:
        user_id: UUID of the user to verify.
        data: Verification request with is_verified and optional reason.
        current_user: The currently authenticated admin user.
        db: The database session dependency.

    Returns:
        SellerProfileResponse: Updated seller profile with verification status.

    """
    service = UserService(db)
    return await service.verify_seller(user_id, data, current_user.id)


@router.get("/me/wallet")
async def get_my_wallet(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the authenticated user's wallet balance.

    Args:
        current_user: The currently authenticated user.
        db: The database session dependency.

    Returns:
        dict: Wallet balance information.

    """
    flutterwave_service = PaystackService(
        base_url=settings.paystack_base_url,
        secret_key=settings.paystack_secret_key,
    )
    service = WalletService(db, flutterwave_service)
    return await service.get_wallet(current_user.id)


@router.get("/documents/proxy")
async def proxy_document(
    url: str = Query(..., description="Cloudinary document URL to proxy"),
):
    """Proxy a Cloudinary document and serve it inline.

    Cloudinary raw files are served with Content-Disposition: attachment,
    which forces a download. This endpoint fetches the file and re-serves
    it with Content-Disposition: inline so the browser renders it in place.

    No auth required — the URL itself is the access token (only admins
    can obtain document URLs through the sellers endpoint).
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        response = await client.get(url)
        response.raise_for_status()

    content_type = response.headers.get("content-type", "application/octet-stream")

    return StreamingResponse(
        iter([response.content]),
        media_type=content_type,
        headers={"Content-Disposition": "inline"},
    )


@router.get("", status_code=200)
async def list_users_for_admin_dashboard(
    page: int = 1,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Retrieve all users paginated (admin only)."""
    service = UserService(db)
    return await service.get_all_users(
        search=None,
        account_status=None,
        kyc_tier=None,
        page=page,
        limit=limit,
    )
