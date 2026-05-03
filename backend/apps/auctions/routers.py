"""API router for auction and item endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auctions.enums import AuctionStatus, ItemStatus
from apps.auctions.service import AuctionService
from apps.users.models import User
from common.dependency import get_current_active_user, get_db, require_admin
from common.schemas import MessageResponse, PaginatedResponse

from .schemas import (
    AttachItemRequest,
    AuctionResponse,
    CategoryResponse,
    CreateAuctionRequest,
    CreateItemRequest,
    ItemImageResponse,
    ItemResponse,
    RejectItemRequest,
    UpdateAuctionRequest,
    UpdateItemRequest,
)

router = APIRouter()

# ============================================================================
# CATEGORY ENDPOINTS (Public)
# ============================================================================


@router.get("/categories", response_model=list[CategoryResponse], status_code=200)
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Get all categories.

    Public endpoint - no authentication required.
    Returns all categories ordered alphabetically.
    """
    service = AuctionService(db)
    # Service should have a method to get all categories
    categories = await service.get_all_categories()
    return [CategoryResponse.model_validate(cat) for cat in categories]


@router.get(
    "/categories/{category_id}",
    response_model=CategoryResponse,
    status_code=200,
)
async def get_category_by_id(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get category by ID with subcategories.

    Public endpoint - no authentication required.
    Returns category details including child categories.
    """
    service = AuctionService(db)
    category = await service.get_category_by_id(category_id)
    return CategoryResponse.model_validate(category)


# ============================================================================
# ITEM ENDPOINTS
# ============================================================================


@router.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    data: CreateItemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new item for auction.

    Requires: Verified seller account

    Business rules:
    - User must have verified SellerProfile
    - Category must exist
    - Item starts with status PENDING_REVIEW (awaiting admin approval)
    """
    service = AuctionService(db)
    return await service.create_item(seller_id=current_user.id, data=data)


@router.get("/items/{item_id}", response_model=ItemResponse, status_code=200)
async def get_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get item details.

    Public endpoint - no authentication required.
    Returns item with category, images, and seller info.
    """
    service = AuctionService(db)
    return await service.get_item(item_id=item_id)


@router.patch("/items/{item_id}", response_model=ItemResponse, status_code=200)
async def update_item(
    item_id: UUID,
    data: UpdateItemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update item details.

    Requires: Item owner (seller)

    Business rules:
    - Only item owner can update
    - Cannot update items in active auctions (status IN_AUCTION)
    - Only provided fields are updated (PATCH semantics)
    """
    service = AuctionService(db)
    return await service.update_item(
        item_id=item_id,
        seller_id=current_user.id,
        data=data.model_dump(exclude_unset=True),  # Only send provided fields
    )


@router.delete("/items/{item_id}", response_model=MessageResponse, status_code=200)
async def delete_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete an item.

    Requires: Item owner (seller)

    Business rules:
    - Only item owner can delete
    - Cannot delete items in active auctions
    - All images are deleted from Cloudinary first
    - Database cascade deletes related records
    """
    service = AuctionService(db)
    return await service.delete_item(item_id=item_id, seller_id=current_user.id)


@router.post(
    "/items/{item_id}/images",
    response_model=ItemImageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_item_image(
    item_id: UUID,
    file: UploadFile = File(...),
    is_primary: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Upload an image for an item.

    Requires: Item owner (seller)

    Business rules:
    - Only item owner can upload images
    - Maximum 8 images per item
    - Accepted formats: JPEG, PNG, WebP
    - Maximum file size: 5MB
    - If is_primary=True, all other images set to is_primary=False
    - Images uploaded to Cloudinary

    Form data:
    - file: Image file (multipart/form-data)
    - is_primary: Boolean (default: False)
    """
    service = AuctionService(db)
    return await service.upload_item_image(
        seller_id=current_user.id,
        item_id=item_id,
        file=file,
        is_primary=is_primary,
    )


@router.delete(
    "/items/{item_id}/images/{image_id}",
    response_model=MessageResponse,
    status_code=200,
)
async def delete_item_image(
    item_id: UUID,
    image_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete an item image.

    Requires: Item owner (seller)

    Business rules:
    - Only item owner can delete images
    - Image deleted from Cloudinary first
    - Then deleted from database
    """
    service = AuctionService(db)
    return await service.delete_item_image(
        image_id=image_id,
        seller_id=current_user.id,
    )


@router.get("/users/me/items", response_model=dict, status_code=200)
async def list_my_items(
    status: Optional[ItemStatus] = Query(None, description="Filter by item status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get current user's items (paginated).

    Requires: Authenticated user

    Query parameters:
    - status: Optional filter by ItemStatus (DRAFT, PENDING_REVIEW, APPROVED, etc.)
    - page: Page number (default: 1)
    - limit: Items per page (default: 20, max: 100)

    Returns paginated response with items.
    """
    service = AuctionService(db)
    return await service.list_my_items(
        seller_id=current_user.id,
        status=status,
        page=page,
        limit=limit,
    )


# ============================================================================
# ADMIN ITEM ENDPOINTS
# ============================================================================


@router.patch(
    "/admin/items/{item_id}/approve",
    response_model=ItemResponse,
    status_code=200,
)
async def approve_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Approve a pending item (admin only).

    Requires: Admin user

    Business rules:
    - Only admins can approve items
    - Item status changes from PENDING_REVIEW to APPROVED
    - Seller receives email notification
    - Item can now be attached to auctions
    """
    service = AuctionService(db)
    return await service.approve_item(admin_user_id=admin_user.id, item_id=item_id)


@router.patch(
    "/admin/items/{item_id}/reject",
    response_model=ItemResponse,
    status_code=200,
)
async def reject_item(
    item_id: UUID,
    data: RejectItemRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Reject a pending item (admin only).

    Requires: Admin user

    Business rules:
    - Only admins can reject items
    - Item status changes from PENDING_REVIEW to REJECTED
    - Seller receives email notification with reason
    - Seller can edit and resubmit

    Request body:
    - reason: Text explaining why item was rejected (10-500 chars)
    """
    service = AuctionService(db)
    return await service.reject_item(
        admin_user_id=admin_user.id,
        item_id=item_id,
        reason=data.reason,
    )


@router.get("/admin/items/pending", response_model=dict, status_code=200)
async def get_pending_items(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Get pending items for review (admin only).

    Requires: Admin user

    Returns items with status PENDING_REVIEW, ordered by created_at ASC (oldest first).
    This ensures admins review items in the order they were submitted.

    Query parameters:
    - page: Page number (default: 1)
    - limit: Items per page (default: 20, max: 100)
    """
    service = AuctionService(db)
    return await service.get_pending_items(page=page, limit=limit)


# ============================================================================
# AUCTION ENDPOINTS
# ============================================================================


@router.get("/auctions", response_model=PaginatedResponse, status_code=200)
async def browse_auctions(
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    sort_by: str = Query(
        "newest",
        description="Sort order: newest, ending_soon, lowest_price, highest_price",
    ),
    view: str = Query(
        "active",
        description="Which auctions to show: active, scheduled, all",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """Browse auctions (public).

    Public endpoint - no authentication required.

    Query parameters:
    - view: active (default) | scheduled | all
    - category_id: Filter by category UUID
    - min_price: Minimum current bid/starting price
    - max_price: Maximum current bid/starting price
    - sort_by: newest (default), ending_soon, lowest_price, highest_price
    - page: Page number (default: 1)
    - limit: Items per page (default: 20, max: 100)
    """
    service = AuctionService(db)
    filters = {
        "category_id": category_id,
        "min_price": min_price,
        "max_price": max_price,
        "sort_by": sort_by,
        "view": view,
    }
    return await service.browse_auctions(filters=filters, page=page, limit=limit)


@router.get("/auctions/{auction_id}", response_model=AuctionResponse, status_code=200)
async def get_auction(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get auction details (public).

    Public endpoint - no authentication required.

    Returns:
    - Full auction details with items, seller, highest bid
    - Computed fields: time_remaining_seconds, reserve_price_met
    - Bid history (if any)
    - Item images and details

    Note: Reserve price amount is NEVER exposed, only whether it's met.

    """
    service = AuctionService(db)
    return await service.get_auction(auction_id=auction_id)


@router.post(
    "/auctions",
    response_model=AuctionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_auction(
    data: CreateAuctionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new auction shell (draft).

    Requires: Authenticated user

    Creates an auction in DRAFT status. Seller must then:
    1. Attach items (POST /auctions/{id}/items)
    2. Publish auction (PATCH /auctions/{id}/publish)

    Business rules:
    - starts_at must be in future (> now + 1 hour)
    - ends_at must be after starts_at
    - Minimum duration: 1 hour
    - Maximum duration: 30 days
    """
    service = AuctionService(db)
    return await service.create_auction(seller_id=current_user.id, data=data)


@router.patch("/auctions/{auction_id}", response_model=AuctionResponse, status_code=200)
async def update_auction(
    auction_id: UUID,
    data: UpdateAuctionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a draft auction.

    Requires: Auction owner (seller)

    Business rules:
    - Only auction owner can update
    - Can only update DRAFT auctions
    - Once published, auction cannot be edited
    - Only provided fields are updated (PATCH semantics)
    """
    service = AuctionService(db)
    return await service.update_auction(
        seller_id=current_user.id,
        auction_id=auction_id,
        data=data.model_dump(exclude_unset=True),  # PATCH semantics
    )


@router.delete(
    "/auctions/{auction_id}",
    response_model=MessageResponse,
    status_code=200,
)
async def cancel_auction(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Cancel an auction.

    Requires: Auction owner (seller)

    Business rules:
    - Only auction owner can cancel
    - Cannot cancel if auction has any bids
    - Auction status changes to CANCELLED
    - All attached items revert to APPROVED status
    - Items can be attached to other auctions
    """
    service = AuctionService(db)
    return await service.cancel_auction(
        seller_id=current_user.id,
        auction_id=auction_id,
    )


@router.post(
    "/auctions/{auction_id}/items",
    response_model=AuctionResponse,
    status_code=200,
)
async def attach_item_to_auction(
    auction_id: UUID,
    data: AttachItemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Attach an item to a draft auction.

    Requires: Auction owner (seller)

    Business rules:
    - Only auction owner can attach items
    - Can only attach to DRAFT auctions
    - Item must belong to the seller
    - Item must have status APPROVED (not PENDING_REVIEW or REJECTED)
    - Item status changes to IN_AUCTION
    - Item cannot be attached to multiple auctions simultaneously

    Request body:
    - item_id: UUID of the item to attach
    - starting_price: Starting bid price (minimum ₦0)
    - quantity: Number of units (default: 1)
    """
    service = AuctionService(db)
    return await service.attach_item_to_auction(
        seller_id=current_user.id,
        auction_id=auction_id,
        data=data,
    )


@router.delete(
    "/auctions/{auction_id}/items/{item_id}",
    response_model=AuctionResponse,
    status_code=200,
)
async def detach_item_from_auction(
    auction_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Remove an item from a draft auction.

    Requires: Auction owner (seller)

    Business rules:
    - Only auction owner can detach items
    - Can only detach from DRAFT auctions
    - Item status reverts to APPROVED
    - Item can be attached to other auctions
    """
    service = AuctionService(db)
    return await service.detach_item(
        auction_id=auction_id,
        seller_id=current_user.id,
        item_id=item_id,
    )


@router.patch(
    "/auctions/{auction_id}/publish",
    response_model=AuctionResponse,
    status_code=200,
)
async def publish_auction(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Publish a draft auction to make it active.

    Requires: Auction owner (seller)

    Business rules:
    - Only auction owner can publish
    - Can only publish DRAFT auctions
    - Auction must have at least 1 item attached
    - starts_at must still be in the future
    - Auction status changes to ACTIVE
    - Auction becomes visible in public browse
    - Bidding can begin once starts_at is reached

    Validation errors:
    - NO_ITEMS_ATTACHED: Auction has no items
    - INVALID_START_TIME: starts_at is in the past
    - AUCTION_NOT_DRAFT: Auction already published
    """
    service = AuctionService(db)

    return await service.publish_auction(
        seller_id=current_user.id,
        auction_id=auction_id,
    )


@router.get("/users/me/auctions", response_model=PaginatedResponse, status_code=200)
async def list_my_auctions(
    status: Optional[str] = Query(None, description="Filter by auction status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get current user's auctions (paginated).

    Requires: Authenticated user

    Query parameters:
    - status: Optional filter by AuctionStatus (DRAFT, ACTIVE, COMPLETED, etc.)
    - page: Page number (default: 1)
    - limit: Items per page (default: 20, max: 100)

    Returns paginated response with seller's auctions.
    Useful for seller dashboard to manage their listings.
    """
    service = AuctionService(db)
    auction_status = None
    if status:
        # Map frontend shorthand values to actual enum values
        status_upper = status.upper()
        # "ended" is a frontend convenience — maps to all terminal statuses
        # The frontend handles this by making separate calls, but we support
        # direct status values too
        try:
            auction_status = AuctionStatus(status_upper)
        except ValueError:
            pass  # Unknown status — return all

    return await service.get_seller_auctions(
        seller_id=current_user.id,
        status=auction_status,
        page=page,
        limit=limit,
    )
