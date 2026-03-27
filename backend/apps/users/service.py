"""User service layer for profile and seller management.

Provides business logic for user profile operations, seller registration,
and wallet management.
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from apps.notifications.tasks import (
    send_seller_verification_approved,
    send_seller_verification_rejected,
)
from apps.users.models import AccountStatus, VerificationDoc
from apps.users.repository import UserRepository
from apps.users.schemas import (
    PublicUserResponse,
    RegisterSellerRequest,
    SellerProfileResponse,
    UpdateProfileRequest,
    UserProfileResponse,
    VerifySellerRequest,
    WalletBalanceResponse,
)
from common.exceptions import (
    EmailNotVerifiedException,
    SellerProfileNotFoundException,
    SellerRequiredException,
    UserNotFoundException,
)


class UserService:
    """Orchestrates all user-related business logic.

    Manages user profiles, seller registration, verification documents,
    and wallet operations through the ``UserRepository``.

    Attributes:
        _db: The active ``AsyncSession`` for database operations.
        repo: Repository instance for user data access.

    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service with a database session.

        Args:
            db: An active ``AsyncSession`` for database operations.

        """
        self._db = db
        self.repo = UserRepository(db)

    async def get_my_profile(self, user_id: UUID) -> UserProfileResponse:
        """Get the authenticated user's full profile.

        Args:
            user_id: UUID of the user to retrieve.

        Returns:
            UserProfileResponse: Full user profile with nested data.

        Raises:
            UserNotFoundException: If user does not exist.

        """
        user = await self.repo.get_with_profile(user_id)
        if not user:
            raise UserNotFoundException()

        return UserProfileResponse.model_validate(user)

    async def update_my_profile(
        self, user_id: UUID, data: UpdateProfileRequest
    ) -> UserProfileResponse:
        """Update user profile with partial data.

        Args:
            user_id: UUID of the user to update.
            data: Validated profile update request.

        Returns:
            UserProfileResponse: Updated user profile.

        """
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}

        # Split data into User table fields and UserProfile table fields
        user_fields = {}
        profile_fields = {}

        for key, value in update_data.items():
            # REASONING: Only first_name and last_name are in User table
            # Everything else (bio, city, state, bank details, etc.) goes to UserProfile
            if key in ["first_name", "last_name"]:
                user_fields[key] = value
            else:
                profile_fields[key] = value

        # Update User table if there are user fields
        if user_fields:
            await self.repo.update(user_id, user_fields)

        # Update UserProfile table if there are profile fields
        if profile_fields:
            await self.repo.update_profile(user_id, profile_fields)

        await self._db.commit()

        user = await self.repo.get_with_profile(user_id)
        return UserProfileResponse.model_validate(user)

    async def register_as_seller(
        self, user_id: UUID, data: RegisterSellerRequest
    ) -> SellerProfileResponse:
        """Register user as a seller.

        Args:
            user_id: UUID of the user registering as seller.
            data: Validated seller registration request.

        Returns:
            SellerProfileResponse: Newly created seller profile.

        Raises:
            UserNotFoundException: If user does not exist.
            EmailNotVerifiedException: If email is not verified.

        """
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()

        if not user.is_email_verified:
            msg = "Email must be verified before registering as seller"
            raise EmailNotVerifiedException(msg)

        seller_data = data.model_dump()
        seller_profile = await self.repo.create_seller_profile(user_id, seller_data)
        await self._db.commit()

        return SellerProfileResponse.model_validate(seller_profile)

    async def get_public_profile(self, target_user_id: UUID) -> PublicUserResponse:
        """Get public profile without sensitive data.

        Args:
            target_user_id: UUID of the user to view.

        Returns:
            PublicUserResponse: Public user profile.

        Raises:
            UserNotFoundException: If user does not exist.

        """
        user = await self.repo.get_public_profile(target_user_id)
        if not user:
            raise UserNotFoundException()

        rating = Decimal("0.00")
        total_sales = 0
        total_purchases = 0

        if user.profile:
            rating = (
                user.profile.rating
                if user.profile.rating is not None
                else Decimal("0.00")
            )
            total_sales = (
                user.profile.total_sales if user.profile.total_sales is not None else 0
            )
            total_purchases = (
                user.profile.total_purchases
                if user.profile.total_purchases is not None
                else 0
            )

        return PublicUserResponse(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            rating=rating,
            total_sales=total_sales,
            total_purchases=total_purchases,
            is_verified_seller=(
                user.seller_profile.is_verified if user.seller_profile else False
            ),
            seller_type=(
                user.seller_profile.seller_type.value if user.seller_profile else None
            ),
            member_since=user.created_at,
        )

    async def verify_seller(
        self,
        target_user_id: UUID,
        data: VerifySellerRequest,
        admin_user_id: UUID,
    ) -> SellerProfileResponse:
        """Admin verification of seller profile.

        Args:
            target_user_id: UUID of user to verify.
            data: Verification request with status and optional reason.
            admin_user_id: UUID of admin performing verification.

        Returns:
            SellerProfileResponse: Updated seller profile.

        Raises:
            SellerProfileNotFoundException: If seller profile not found.

        """
        seller_profile = await self.repo.get_seller_profile(target_user_id)
        if not seller_profile:
            raise SellerProfileNotFoundException()

        user = await self.repo.get_by_id(target_user_id)

        updated_profile = await self.repo.update_seller_verification(
            target_user_id, data.is_verified, admin_user_id
        )
        await self._db.commit()

        if data.is_verified:
            send_seller_verification_approved.delay(user.email, user.first_name)
        else:
            send_seller_verification_rejected.delay(
                user.email, user.first_name, data.rejection_reason
            )

        return SellerProfileResponse.model_validate(updated_profile)

    async def upload_verification_document(
        self, user_id: UUID, url: str, doc_type: str
    ) -> VerificationDoc:
        """Upload verification document for seller.

        Args:
            user_id: UUID of the user uploading document.
            url: URL of the uploaded document.
            doc_type: Type of document (e.g., "National ID").

        Returns:
            VerificationDoc: Created verification document record.

        Raises:
            SellerRequiredException: If user is not registered as seller.

        """
        seller_profile = await self.repo.get_seller_profile(user_id)
        if not seller_profile:
            msg = "Must be registered as seller to upload documents"
            raise SellerRequiredException(msg)

        doc = VerificationDoc(
            title=doc_type,
            description=f"{doc_type} for seller verification",
            url=url,
            seller_id=seller_profile.id,
        )

        self._db.add(doc)
        await self._db.flush()
        await self._db.refresh(doc)
        await self._db.commit()

        return doc

    async def deactivate_account(self, user_id: UUID) -> dict:
        """Soft delete user account by deactivating it.

        Args:
            user_id: UUID of the user to deactivate.

        Returns:
            dict: Confirmation message.

        """
        from common.schemas import MessageResponse

        await self.repo.update(user_id, {"account_status": AccountStatus.DEACTIVATED})
        await self._db.commit()

        return MessageResponse(message="Account deactivated successfully")

    async def get_wallet_balance(self, user_id: UUID) -> WalletBalanceResponse | dict:
        """Get user's wallet balance.

        Args:
            user_id: UUID of the user.

        Returns:
            WalletBalanceResponse or dict: Wallet balance information.

        """
        wallet = await self.repo.get_wallet(user_id)

        if not wallet:
            return {"message": "Wallet not found"}

        return WalletBalanceResponse.model_validate(wallet)
