"""Business logic layer for auction and item management.

Provides ``AuctionService``, the single entry-point for all auction-related
operations including item creation, image management, auction lifecycle,
and admin moderation workflows.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Sequence

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auctions.cloudinary_service import CloudinaryService
from apps.auctions.enums import AuctionStatus, ItemStatus
from apps.auctions.repository import (
    AuctionRepository,
    CategoryRepository,
    ItemRepository,
)
from apps.notifications.tasks import (
    send_item_approved_notification,
    send_item_rejected_notification,
)
from apps.users.repository import UserRepository
from common.exceptions import (
    AuctionNotFoundException,
    NotFoundException,
    ValidationException,
)
from common.schemas import MessageResponse, PaginatedResponse
from config.settings import settings

from .schemas import (
    AdminAuctionResponse,
    AttachItemRequest,
    AuctionResponse,
    CreateAuctionRequest,
    CreateItemRequest,
    ItemImageResponse,
    ItemResponse,
)

logger = logging.getLogger(__name__)


class AuctionService:
    """Service for auction-related business logic."""

    def __init__(self, db: AsyncSession):
        """Initialize auction service.

        Args:
            db: Async database session

        """
        self._db = db
        self._auction_repo = AuctionRepository(db)
        self._item_repo = ItemRepository(db)
        self._category_repo = CategoryRepository(db)
        self._user_repo = UserRepository(db)
        self._cloudinary = CloudinaryService()

    # ========================================================================
    # CATEGORY METHODS
    # ========================================================================

    async def get_all_categories(self) -> Sequence:
        """Get all categories ordered alphabetically.

        Returns:
            Sequence of all categories.

        """
        return await self._category_repo.get_all()

    async def get_category_by_id(self, category_id: uuid.UUID):
        """Get category by ID.

        Args:
            category_id: UUID of the category.

        Returns:
            Category instance.

        Raises:
            NotFoundException: If category not found.

        """
        category = await self._category_repo.get_by_id(category_id)
        if not category:
            raise NotFoundException(
                message="Category not found",
                code="CATEGORY_NOT_FOUND",
            )
        return category

    # ========================================================================
    # ITEM METHODS
    # ========================================================================

    async def create_item(
        self, seller_id: uuid.UUID, data: CreateItemRequest
    ) -> ItemResponse:
        """Create a new item for auction.

        Args:
            seller_id: UUID of the seller
            data: Item creation data

        Returns:
            Created item response

        Raises:
            ValidationException: If seller is not verified
            NotFoundException: If category doesn't exist

        """
        # Verify seller has verified SellerProfile
        user = await self._user_repo.get_with_profile(seller_id)

        # Admins and superusers bypass seller verification
        is_admin = user and user.role.value in ("ADMIN", "SUPERUSER")
        if not is_admin:
            if (
                not user
                or not user.seller_profile
                or not user.seller_profile.is_verified
            ):
                raise ValidationException(
                    message="You must be a verified seller to create items",
                )

        # Verify category exists
        category = await self._category_repo.get_by_id(data.category_id)
        if not category:
            raise NotFoundException(
                message="Category doesn't exist", code="CATEGORY_NOT_FOUND"
            )

        # Create item with status pending_review, then auto-approve for demo
        item = await self._item_repo.create(seller_id, data.model_dump())
        await self._item_repo.update_item_status(item.id, ItemStatus.APPROVED)
        await self._db.commit()

        # Reload with relationships for response
        item = await self._item_repo.get_by_id(item.id)
        return ItemResponse.model_validate(item)

    async def get_categories(self) -> Sequence:
        """Get all categories (alias for get_all_categories).

        Returns:
            Sequence of all categories.

        """
        return await self._category_repo.get_all()

    async def upload_item_image(
        self,
        seller_id: uuid.UUID,
        item_id: uuid.UUID,
        file: UploadFile,
        is_primary: bool,
    ) -> ItemImageResponse:
        """Upload an image for an item.

        Args:
            seller_id: UUID of the seller uploading the image.
            item_id: UUID of the item to attach the image to.
            file: The uploaded image file.
            is_primary: Whether this image should be the primary display image.

        Returns:
            The created ``ItemImageResponse``.

        Raises:
            NotFoundException: If the item does not exist.
            ValidationException: If not authorized or image limit reached.

        """
        item = await self._item_repo.get_by_id(item_id)
        if not item:
            raise NotFoundException(
                message="Item not found",
                code="ITEM_NOT_FOUND",
            )

        if item.seller_id != seller_id:
            raise ValidationException(
                message="Not authorized to modify this item",
            )

        if len(item.images) >= 8:
            raise ValidationException(
                message="Maximum 8 images per item allowed",
            )

        if is_primary:
            for img in item.images:
                img.is_primary = False
                self._db.add(img)

        # Upload to Cloudinary first
        result = await self._cloudinary.upload_image(file)
        public_id = result["public_id"]

        # save the reference to DB - if this fails, clean up cloudinary
        try:
            image = await self._item_repo.add_image(
                item_id=item_id,
                url=result["url"],
                public_id=result["public_id"],
                display_order=len(item.images),
                is_primary=is_primary,
            )

            await self._db.commit()
        except Exception:
            # DB save failed - remove the orphaned Cloudinary asset
            logger.warning(
                "DB save failed after Cloudinary upload — deleting orphan asset %s",
                public_id,
            )
            self._cloudinary.delete_image(public_id)
            raise ValidationException(message="Image upload failed. Please try again.")
        return ItemImageResponse.model_validate(image)

    async def delete_item_image(
        self, image_id: uuid.UUID, seller_id: uuid.UUID
    ) -> dict:
        """Delete an item image.

        Args:
            image_id: UUID of the image
            seller_id: UUID of the seller

        Returns:
            Success message

        Raises:
            NotFoundException: If image not found
            ValidationException: If not authorized

        """
        image = await self._item_repo.get_image_by_id(image_id)
        if not image:
            raise NotFoundException(message="Image not found", code="IMAGE_NOT_FOUND")

        item = await self._item_repo.get_by_id_with_seller(image.item_id)
        if item.seller_id != seller_id:
            raise ValidationException(
                message="Not authorized to delete this image",
            )

        # Delete from Cloudinary
        if image.public_id:
            self._cloudinary.delete_image(image.public_id)

        # Delete from database
        await self._item_repo.delete_image(image_id)
        await self._db.commit()

        return {"message": "Image deleted successfully"}

    async def get_item(self, item_id: uuid.UUID) -> ItemResponse:
        """Get item by ID.

        Args:
            item_id: UUID of the item.

        Returns:
            Item response with category and images.

        Raises:
            NotFoundException: If item not found.

        """
        item = await self._item_repo.get_by_id(item_id)
        if not item:
            raise NotFoundException(message="Item not found", code="ITEM_NOT_FOUND")
        return ItemResponse.model_validate(item)

    async def update_item(
        self,
        item_id: uuid.UUID,
        seller_id: uuid.UUID,
        data: dict,
    ) -> ItemResponse:
        """Update an existing item.

        Args:
            item_id: UUID of the item
            seller_id: UUID of the seller
            data: Dictionary of fields to update

        Returns:
            Updated item response

        Raises:
            NotFoundException: If item not found
            ValidationException: If not authorized or item in active auction

        """
        # Verify item exists and belongs to seller
        item = await self._item_repo.get_by_id_with_seller(item_id)
        if not item:
            raise NotFoundException(message="Item not found", code="ITEM_NOT_FOUND")

        if item.seller_id != seller_id:
            raise ValidationException(
                message="Not authorized to modify this item", code="FORBIDDEN"
            )

        # Cannot update item that's in an active auction
        if item.status == ItemStatus.IN_AUCTION:
            raise ValidationException(
                message="Cannot update item that is in an active auction",
            )

        # Update item with provided data
        item = await self._item_repo.update(item_id, data)
        await self._db.commit()

        # Reload with relationships
        item = await self._item_repo.get_by_id(item_id)
        return ItemResponse.model_validate(item)

    async def list_my_items(
        self, seller_id: uuid.UUID, status: ItemStatus | None, page: int, limit: int
    ) -> dict:
        """Get seller's items paginated.

        Args:
            seller_id: UUID of the seller
            status: Optional status filter
            page: Page number
            limit: Items per page

        Returns:
            Paginated response with seller's items.

        """
        result = await self._item_repo.get_seller_items(
            seller_id=seller_id,
            status=status,
            page=page,
            limit=limit,
        )
        result.data = [ItemResponse.model_validate(i) for i in result.data]
        return result

    async def delete_item(self, item_id: uuid.UUID, seller_id: uuid.UUID) -> dict:
        """Delete an item.

        Args:
            item_id: UUID of the item
            seller_id: UUID of the seller

        Returns:
            Success message

        Raises:
            NotFoundException: If item not found
            ValidationException: If not authorized or item in active auction

        """
        # Verify item exists and belongs to seller
        item = await self._item_repo.get_by_id(item_id)
        if not item:
            raise NotFoundException(
                message="Item not found",
                code="ITEM_NOT_FOUND",
            )

        if item.seller_id != seller_id:
            raise ValidationException(
                message="Not authorized to delete this item",
            )

        if item.status == ItemStatus.IN_AUCTION:
            raise ValidationException(
                message="Cannot delete item that is in an active auction",
            )

        # Delete all images from Cloudinary first
        for image in item.images:
            if image.public_id:
                self._cloudinary.delete_image(image.public_id)

        # Delete item (cascade will delete images from DB)
        await self._item_repo.delete(item_id)
        await self._db.commit()

        return {"message": "Item deleted successfully"}

    async def detach_item(
        self, auction_id: uuid.UUID, seller_id: uuid.UUID, item_id: uuid.UUID
    ) -> AuctionResponse:
        """Remove an item from a draft auction.

        Args:
            auction_id: UUID of the auction
            seller_id: UUID of the seller
            item_id: UUID of the item to detach

        Returns:
            Updated auction response

        Raises:
            AuctionNotFoundException: If auction not found
            ValidationException: If not authorized or auction not draft

        """
        auction = await self._auction_repo.get_by_id(auction_id)
        if not auction:
            raise AuctionNotFoundException()

        if auction.seller_id != seller_id:
            raise ValidationException(
                message="Not authorized to modify this auction",
            )

        if auction.status != AuctionStatus.DRAFT:
            raise ValidationException(
                message="Can only remove items from draft auctions",
            )

        success = await self._auction_repo.detach_item(auction_id, item_id)
        if not success:
            raise NotFoundException(
                message="Item not found in auction",
                code="ITEM_NOT_IN_AUCTION",
            )

        # Update item status back to approved
        await self._item_repo.update_item_status(item_id, ItemStatus.APPROVED)

        await self._db.commit()

        # Reload auction with relationships
        auction = await self._auction_repo.get_by_id(auction_id)
        return AuctionResponse.model_validate(auction)

    async def create_auction(
        self, seller_id: uuid.UUID, data: CreateAuctionRequest
    ) -> AuctionResponse:
        """Create a new draft auction.

        Args:
            seller_id: UUID of the seller
            data: Auction creation data

        Returns:
            Created auction response

        """
        duration = data.ends_at - data.starts_at
        if duration > timedelta(hours=settings.max_auction_duration_hours):
            raise ValidationException(
                message=(
                    f"Auction duration cannot exceed "
                    f"{settings.max_auction_duration_hours} hours"
                )
            )

        auction = await self._auction_repo.create_auction(
            seller_id=seller_id, data=data.model_dump()
        )
        await self._db.commit()

        # Reload with relationships
        auction = await self._auction_repo.get_by_id(auction.id)
        return AuctionResponse.model_validate(auction)

    async def attach_item_to_auction(
        self,
        seller_id: uuid.UUID,
        auction_id: uuid.UUID,
        data: AttachItemRequest,
    ) -> AuctionResponse:
        """Attach an item to a draft auction.

        Args:
            seller_id: UUID of the seller
            auction_id: UUID of the auction
            data: Item attachment data

        Returns:
            Updated auction response

        Raises:
            AuctionNotFoundException: If auction not found
            ValidationException: If not authorized, auction not draft, or item
                not approved.

        """
        # Verify auction exists and belongs to seller
        auction = await self._auction_repo.get_by_id(auction_id)
        if not auction:
            raise AuctionNotFoundException()

        if auction.seller_id != seller_id:
            raise ValidationException(
                message="Not authorized to modify this auction", code="FORBIDDEN"
            )

        if auction.status != AuctionStatus.DRAFT:
            raise ValidationException(
                message="Can only add items to draft auctions", code="AUCTION_NOT_DRAFT"
            )

        if auction.reserve_price:
            if auction.reserve_price <= data.starting_price:
                raise ValidationException(
                    message=(
                        "Starting price cannot equal or exceed reserve price. "
                        "Reserve price must be higher than starting price."
                    ),
                )

        # Verify item exists and belongs to seller
        item = await self._item_repo.get_by_id_with_seller(data.item_id)
        if not item:
            raise NotFoundException(message="Item not found", code="ITEM_NOT_FOUND")

        if item.seller_id != seller_id:
            raise ValidationException(
                message="Not authorized to add this item to auction", code="FORBIDDEN"
            )

        if item.status not in (ItemStatus.APPROVED, ItemStatus.PENDING_REVIEW):
            raise ValidationException(
                message="Item must be approved before listing",
            )

        # Attach item to auction
        await self._auction_repo.attach_item(
            auction_id=auction_id,
            item_id=data.item_id,
            starting_price=data.starting_price,
            quantity=data.quantity,
        )

        # Update item status to in_auction
        await self._item_repo.update_item_status(data.item_id, ItemStatus.IN_AUCTION)

        await self._db.commit()

        # Reload auction with relationships
        auction = await self._auction_repo.get_by_id(auction_id)
        return AuctionResponse.model_validate(auction)

    async def publish_auction(
        self, seller_id: uuid.UUID, auction_id: uuid.UUID
    ) -> AuctionResponse:
        """Publish a draft auction to make it active.

        Args:
            seller_id: UUID of the seller
            auction_id: UUID of the auction

        Returns:
            Published auction response

        Raises:
            AuctionNotFoundException: If auction not found
            ValidationException: If not authorized, not draft, no items, or
                ``starts_at`` is in the past.

        """
        # Verify auction exists and belongs to seller
        auction = await self._auction_repo.get_by_id(auction_id)
        if not auction:
            raise AuctionNotFoundException()

        if auction.seller_id != seller_id:
            raise ValidationException(
                message="Not authorized to modify this auction", code="FORBIDDEN"
            )

        if auction.status != AuctionStatus.DRAFT:
            raise ValidationException(
                message="Can only publish draft auctions", code="AUCTION_NOT_DRAFT"
            )

        # Verify auction has at least one item
        auction_items = await self._auction_repo.get_auction_items(auction_id)
        if len(auction_items) == 0:
            raise ValidationException(
                message="Auction must have at least one item to publish",
            )

        # Verify starts_at is still in the future
        now = datetime.now(timezone.utc)
        if auction.starts_at < now:
            raise ValidationException(
                message="Auction start time must be in the future",
            )

        # Verify duration is still valid
        duration = auction.ends_at - auction.starts_at
        if duration > timedelta(hours=settings.max_auction_duration_hours):
            raise ValidationException(
                message=(
                    f"Auction duration cannot exceed "
                    f"{settings.max_auction_duration_hours} hours"
                )
            )

        if auction.starts_at > now + timedelta(seconds=30):
            # Start time is far enough in the future — schedule it
            await self._auction_repo.update_status(auction_id, AuctionStatus.SCHEDULED)
        else:
            # Start time is imminent (≤ 30 s away) — activate immediately
            await self._auction_repo.update_status(auction_id, AuctionStatus.ACTIVE)
        await self._db.commit()

        # Reload auction with relationships
        auction = await self._auction_repo.get_by_id(auction_id)
        return AuctionResponse.model_validate(auction)

    async def get_auction(self, auction_id: uuid.UUID) -> AuctionResponse:
        """Get auction details with all relationships.

        Args:
            auction_id: UUID of the auction

        Returns:
            Auction response with calculated fields

        Raises:
            AuctionNotFoundException: If auction not found

        """
        auction = await self._auction_repo.get_by_id(auction_id)
        if not auction:
            raise AuctionNotFoundException()

        # Convert to response (time_remaining_seconds and reserve_price_met
        # are computed fields in the schema)
        return AuctionResponse.model_validate(auction)

    async def browse_auctions(
        self, filters: dict, page: int, limit: int
    ) -> PaginatedResponse:
        """Browse auctions with filters.

        Args:
            filters: Dictionary with category_id, min_price, max_price,
                     sort_by, view (all | active | scheduled)
            page: Page number
            limit: Items per page

        Returns:
            Paginated response with auctions

        """
        view = filters.get("view", "active")
        if view == "scheduled":
            statuses = [AuctionStatus.SCHEDULED]
        elif view == "all":
            statuses = [AuctionStatus.ACTIVE, AuctionStatus.SCHEDULED]
        else:
            statuses = [AuctionStatus.ACTIVE]

        result = await self._auction_repo.get_browsable_auctions(
            statuses=statuses,
            category_id=filters.get("category_id"),
            min_price=filters.get("min_price"),
            max_price=filters.get("max_price"),
            sort_by=filters.get("sort_by", "newest"),
            page=page,
            limit=limit,
        )
        result.data = [AuctionResponse.model_validate(a) for a in result.data]
        return result

    async def get_seller_auctions(
        self,
        seller_id: uuid.UUID,
        status: AuctionStatus | None,
        page: int,
        limit: int,
    ) -> dict:
        """Get paginated auctions for a seller.

        Args:
            seller_id: UUID of the seller
            status: Optional status filter
            page: Page number
            limit: Items per page

        Returns:
            Paginated response with seller's auctions

        """
        result = await self._auction_repo.get_seller_auctions(
            seller_id=seller_id, status=status, page=page, limit=limit
        )
        result.data = [AuctionResponse.model_validate(a) for a in result.data]
        return result

    async def cancel_auction(self, seller_id: uuid.UUID, auction_id: uuid.UUID) -> dict:
        """Cancel an auction with no bids.

        Args:
            seller_id: UUID of the seller
            auction_id: UUID of the auction

        Returns:
            Success message

        Raises:
            AuctionNotFoundException: If auction not found
            ValidationException: If not authorized or auction has bids

        """
        # Verify auction exists and belongs to seller
        auction = await self._auction_repo.get_by_id(auction_id)
        if not auction:
            raise AuctionNotFoundException()

        if auction.seller_id != seller_id:
            raise ValidationException(
                message="Not authorized to modify this auction", code="FORBIDDEN"
            )

        # Verify auction has zero bids
        if len(auction.bids) > 0:
            raise ValidationException(
                message="Cannot cancel auction with active bids",
            )

        # Update auction status to cancelled
        await self._auction_repo.update_status(auction_id, AuctionStatus.CANCELLED)

        # Update all attached items back to approved
        auction_items = await self._auction_repo.get_auction_items(auction_id)
        for auction_item in auction_items:
            await self._item_repo.update_item_status(
                auction_item.item_id, ItemStatus.APPROVED
            )

        await self._db.commit()

        return {"message": "Auction cancelled successfully"}

    async def update_auction(
        self,
        seller_id: uuid.UUID,
        auction_id: uuid.UUID,
        data: dict,
    ) -> AuctionResponse:
        """Update a draft auction.

        Args:
            seller_id: UUID of the seller
            auction_id: UUID of the auction
            data: Dictionary of fields to update

        Returns:
            Updated auction response

        Raises:
            AuctionNotFoundException: If auction not found
            ValidationException: If not authorized or auction not draft

        """
        # Verify auction exists and belongs to seller
        auction = await self._auction_repo.get_by_id(auction_id)
        if not auction:
            raise AuctionNotFoundException()

        if auction.seller_id != seller_id:
            raise ValidationException(
                message="Not authorized to modify this auction", code="FORBIDDEN"
            )

        if auction.status != AuctionStatus.DRAFT:
            raise ValidationException(
                message="Can only update draft auctions", code="AUCTION_NOT_DRAFT"
            )

        # Update provided fields only
        auction = await self._auction_repo.update_auction(auction_id, data)
        await self._db.commit()

        # Reload auction with relationships
        auction = await self._auction_repo.get_by_id(auction_id)
        return AuctionResponse.model_validate(auction)

    async def approve_item(
        self, admin_user_id: uuid.UUID, item_id: uuid.UUID
    ) -> ItemResponse:
        """Approve a pending item (admin only).

        Args:
            admin_user_id: UUID of the admin user
            item_id: UUID of the item to approve

        Returns:
            Approved item response

        Raises:
            NotFoundException: If item not found
            ValidationException: If caller is not admin

        """
        # Verify caller is admin
        admin_user = await self._user_repo.get_by_id(admin_user_id)
        if not admin_user or not admin_user.is_admin:
            raise ValidationException(
                message="Only admins can approve items", code="ADMIN_REQUIRED"
            )

        # Get item with seller for notification
        item = await self._item_repo.get_by_id_with_seller(item_id)
        if not item:
            raise NotFoundException(message="Item not found", code="ITEM_NOT_FOUND")

        # Update item status to approved
        await self._item_repo.update_item_status(item_id, ItemStatus.APPROVED)
        await self._db.commit()

        send_item_approved_notification.delay(
            seller_email=item.seller.email,
            seller_name=item.seller.full_name,
            item_name=item.title,
        )

        # Reload item with relationships
        item = await self._item_repo.get_by_id(item_id)
        return ItemResponse.model_validate(item)

    async def reject_item(
        self, admin_user_id: uuid.UUID, item_id: uuid.UUID, reason: str
    ) -> ItemResponse:
        """Reject a pending item (admin only).

        Args:
            admin_user_id: UUID of the admin user
            item_id: UUID of the item to reject
            reason: Reason for rejection

        Returns:
            Rejected item response

        Raises:
            NotFoundException: If item not found
            ValidationException: If caller is not admin

        """
        # Verify caller is admin
        admin_user = await self._user_repo.get_by_id(admin_user_id)
        if not admin_user or not admin_user.is_admin:
            raise ValidationException(
                message="Only admins can reject items",
            )

        # Get item with seller for notification
        item = await self._item_repo.get_by_id_with_seller(item_id)
        if not item:
            raise NotFoundException(message="Item not found", code="ITEM_NOT_FOUND")

        # Update item status to rejected
        await self._item_repo.update_item_status(item_id, ItemStatus.REJECTED)
        await self._db.commit()

        send_item_rejected_notification.delay(
            seller_email=item.seller.email,
            seller_name=item.seller.full_name,
            item_name=item.title,
            reason=reason,
        )

        # Reload item with relationships
        item = await self._item_repo.get_by_id(item_id)
        return ItemResponse.model_validate(item)

    async def get_pending_items(self, page: int, limit: int) -> dict:
        """Get paginated pending items for admin review.

        Args:
            page: Page number
            limit: Items per page

        Returns:
            Paginated response with pending items (oldest first)

        """
        result = await self._item_repo.get_items_by_status(
            status=ItemStatus.PENDING_REVIEW, page=page, limit=limit
        )
        result.data = [ItemResponse.model_validate(i) for i in result.data]
        return result

    async def get_all_auctions(
        self, status: AuctionStatus | None, page: int, limit: int
    ) -> PaginatedResponse:
        """Get all auctions for the admin dashboard.

        Args:
            status: Optional status filter.
            page: Page number.
            limit: Items per page.

        Returns:
            Paginated response with admin auction data.

        """
        result = await self._auction_repo.get_all(status, page, limit)
        result.data = [AdminAuctionResponse.model_validate(a) for a in result.data]
        return result

    async def cancel_auction_admin(self, auction_id: uuid.UUID) -> MessageResponse:
        """Cancel an auction as admin — bypasses seller ownership check.

        Args:
            auction_id: UUID of the auction to cancel.

        Returns:
            Message response confirming cancellation.

        """
        # Revert all attached items back to approved
        auction_items = await self._auction_repo.get_auction_items(auction_id)
        for auction_item in auction_items:
            await self._item_repo.update_item_status(
                auction_item.item_id, ItemStatus.APPROVED
            )
        # Cancel the auction in repo
        res = await self._auction_repo.cancel_auction_by_admin(auction_id)
        await self._db.commit()
        return res

    async def extend_auction(
        self,
        seller_id: uuid.UUID,
        auction_id: uuid.UUID,
        new_ends_at: datetime,
    ) -> AuctionResponse:
        """Extend the end time of an active or scheduled auction.

        Args:
            seller_id: UUID of the seller requesting the extension.
            auction_id: UUID of the auction to extend.
            new_ends_at: The new end datetime (must be later than current ends_at).

        Returns:
            Updated auction response.

        Raises:
            AuctionNotFoundException: If auction not found.
            ValidationException: If not authorized, wrong status, or invalid time.

        """
        auction = await self._auction_repo.get_by_id(auction_id)
        if not auction:
            raise AuctionNotFoundException()

        if auction.seller_id != seller_id:
            raise ValidationException(
                message="Not authorized to modify this auction", code="FORBIDDEN"
            )

        if auction.status not in (AuctionStatus.ACTIVE, AuctionStatus.SCHEDULED):
            raise ValidationException(
                message="Can only extend active or scheduled auctions",
            )

        now = datetime.now(timezone.utc)
        if new_ends_at <= now:
            raise ValidationException(
                message="New end time must be in the future",
            )

        if new_ends_at <= auction.ends_at:
            raise ValidationException(
                message="New end time must be later than the current end time",
            )

        max_ends_at = auction.starts_at + timedelta(
            hours=settings.max_auction_duration_hours
        )
        if new_ends_at > max_ends_at:
            raise ValidationException(
                message=(
                    f"Extended auction cannot exceed "
                    f"{settings.max_auction_duration_hours} hours total from start time"
                )
            )

        await self._auction_repo.update_auction(auction_id, {"ends_at": new_ends_at})
        await self._db.commit()

        auction = await self._auction_repo.get_by_id(auction_id)
        return AuctionResponse.model_validate(auction)
