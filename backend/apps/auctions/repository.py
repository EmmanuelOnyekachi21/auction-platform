"""Repository for auction, item, and category database operations."""

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.auctions.enums import AuctionStatus, ItemStatus
from apps.auctions.models import (
    Auction,
    AuctionItem,
    BidIncrementTier,
    Category,
    Item,
    ItemImage,
)
from apps.bids.models import Bid
from common.pagination import paginate

logger = logging.getLogger(__name__)


class CategoryRepository:
    """Repository for category CRUD operations."""

    def __init__(self, db: AsyncSession):
        """Initialize category repository.

        Args:
            db: Async database session

        """
        self._db = db

    async def get_all(self) -> Sequence[Category]:
        """Get all categories ordered by name.

        Returns:
            Sequence of all categories

        """
        stmt = select(Category).order_by(Category.name.asc())
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, category_id: uuid.UUID) -> Category | None:
        """Get category by ID.

        Args:
            category_id: Category UUID

        Returns:
            Category instance or None if not found

        """
        stmt = select(Category).where(Category.id == category_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Category | None:
        """Get category by slug.

        Args:
            slug: Category slug

        Returns:
            Category instance or None if not found

        """
        query = select(Category).where(Category.slug == slug)
        result = await self._db.execute(query)
        return result.scalar_one_or_none()

    async def get_children(self, parent_id: uuid.UUID) -> Sequence[Category]:
        """Get child categories of a parent category.

        Args:
            parent_id: Parent category UUID

        Returns:
            Sequence of child categories

        """
        query = (
            select(Category)
            .where(Category.parent_id == parent_id)
            .order_by(Category.name.asc())
        )
        result = await self._db.execute(query)
        return result.scalars().all()


class ItemRepository:
    """Repository for item CRUD operations."""

    def __init__(self, db: AsyncSession):
        """Initialize item repository.

        Args:
            db: Async database session

        """
        self._db = db

    async def create(self, seller_id: uuid.UUID, data: dict) -> Item:
        """Create a new item.

        Args:
            seller_id: UUID of the seller
            data: Item data dictionary

        Returns:
            Created Item instance

        """
        item = Item(seller_id=seller_id, status=ItemStatus.DRAFT, **data)
        self._db.add(item)
        await self._db.flush()
        return item

    async def get_by_id(self, item_id: uuid.UUID) -> Item | None:
        """Get item by ID with category and images.

        Args:
            item_id: Item UUID

        Returns:
            Item instance or None if not found

        """
        stmt = (
            select(Item)
            .where(Item.id == item_id)
            .options(selectinload(Item.category), selectinload(Item.images))
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_seller(self, item_id: uuid.UUID) -> Item | None:
        """Get item by ID with seller relationship loaded.

        Args:
            item_id: Item UUID

        Returns:
            Item instance or None if not found

        """
        stmt = select(Item).where(Item.id == item_id).options(selectinload(Item.seller))
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_seller_items(
        self,
        seller_id: uuid.UUID,
        status: ItemStatus | None,
        page: int,
        limit: int,
    ) -> dict:
        """Get paginated items for a seller.

        Args:
            seller_id: Seller UUID
            status: Optional status filter
            page: Page number
            limit: Items per page

        Returns:
            Paginated result dictionary

        """
        stmt = (
            select(Item)
            .where(Item.seller_id == seller_id)
            .options(
                selectinload(Item.category),
                selectinload(Item.images),
            )
        )

        if status:
            stmt = stmt.where(Item.status == status)

        result = await paginate(stmt, page, limit, self._db)
        return result

    async def update(self, item_id: uuid.UUID, data: dict) -> Item | None:
        """Update an item.

        Args:
            item_id: Item UUID
            data: Dictionary of fields to update

        Returns:
            Updated Item instance or None if not found

        """
        item = await self.get_by_id(item_id)
        if not item:
            return None

        for key, value in data.items():
            if value is not None:
                setattr(item, key, value)

        self._db.add(item)
        await self._db.flush()
        return item

    async def add_image(
        self,
        item_id: uuid.UUID,
        url: str,
        public_id: str,
        display_order: int,
        is_primary: bool,
    ) -> ItemImage:
        """Add an image to an item.

        Args:
            item_id: Item UUID
            url: Image URL
            public_id: Cloudinary public ID for the image.
            display_order: Display order
            is_primary: Whether this is the primary image

        Returns:
            Created ItemImage instance

        """
        image = ItemImage(
            item_id=item_id,
            url=url,
            public_id=public_id,
            display_order=display_order,
            is_primary=is_primary,
        )
        self._db.add(image)
        await self._db.flush()
        return image

    async def delete_image(self, image_id: uuid.UUID) -> None:
        """Delete an image.

        Args:
            image_id: Image UUID

        """
        query = select(ItemImage).where(ItemImage.id == image_id)
        result = await self._db.execute(query)
        image = result.scalar_one_or_none()

        if image:
            await self._db.delete(image)
            await self._db.flush()

    async def get_image_by_id(self, image_id: uuid.UUID) -> ItemImage | None:
        """Get an image by ID.

        Args:
            image_id: Image UUID

        Returns:
            ItemImage instance or None if not found

        """
        stmt = select(ItemImage).where(ItemImage.id == image_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_item_status(
        self, item_id: uuid.UUID, status: ItemStatus
    ) -> Item | None:
        """Update item status.

        Args:
            item_id: Item UUID
            status: New status

        Returns:
            Updated Item instance or None if not found

        """
        item = await self.get_by_id(item_id)
        if item:
            item.status = status
            await self._db.flush()
            return item
        return None

    async def get_items_by_status(
        self, status: ItemStatus, page: int, limit: int
    ) -> dict:
        """Get paginated items by status (for admin).

        Args:
            status: Item status to filter by
            page: Page number
            limit: Items per page

        Returns:
            Paginated result dictionary

        """
        stmt = (
            select(Item)
            .where(Item.status == status)
            .order_by(Item.created_at.asc())
            .options(
                selectinload(Item.category),
                selectinload(Item.images),
            )
        )

        result = await paginate(stmt, page, limit, self._db)
        return result

    async def delete(self, item_id: uuid.UUID) -> bool:
        """Delete an item.

        Args:
            item_id: Item UUID

        Returns:
            True if deleted, False if not found

        """
        item = await self.get_by_id(item_id)
        if item:
            await self._db.delete(item)
            await self._db.flush()
            return True
        return False


class AuctionRepository:
    """Repository for auction CRUD operations."""

    def __init__(self, db: AsyncSession):
        """Initialize auction repository.

        Args:
            db: Async database session

        """
        self._db = db

    async def create_auction(self, seller_id: uuid.UUID, data: dict) -> Auction:
        """Create a new auction.

        Args:
            seller_id: UUID of the seller
            data: Auction data dictionary

        Returns:
            Created Auction instance

        """
        auction = Auction(seller_id=seller_id, status=AuctionStatus.DRAFT, **data)
        self._db.add(auction)
        await self._db.flush()
        return auction

    async def get_active_auctions(
        self,
        category_id: uuid.UUID | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        sort_by: str,
        page: int,
        limit: int,
    ) -> dict:
        """Get paginated active auctions with filters.

        Args:
            category_id: Optional category filter
            min_price: Optional minimum price filter
            max_price: Optional maximum price filter
            sort_by: Sort order (ending_soon, lowest_price, highest_price, newest)
            page: Page number
            limit: Items per page

        Returns:
            Paginated result dictionary

        """
        stmt = (
            select(Auction)
            .where(Auction.status == AuctionStatus.ACTIVE)
            .options(
                selectinload(Auction.auction_items)
                .selectinload(AuctionItem.item)
                .selectinload(Item.category),
                selectinload(Auction.auction_items)
                .selectinload(AuctionItem.item)
                .selectinload(Item.images),
                selectinload(Auction.seller),
                selectinload(Auction.highest_bid),
                selectinload(Auction.bids),
            )
        )

        if category_id:
            stmt = (
                stmt.join(Auction.auction_items)
                .join(AuctionItem.item)
                .where(Item.category_id == category_id)
            )

        match sort_by:
            case "ending_soon":
                stmt = stmt.order_by(Auction.ends_at.asc())
            case "lowest_price":
                stmt = stmt.join(Auction.highest_bid, isouter=True).order_by(
                    Bid.amount.asc()
                )
            case "highest_price":
                stmt = stmt.join(Auction.highest_bid, isouter=True).order_by(
                    Bid.amount.desc()
                )
            case _:
                stmt = stmt.order_by(Auction.created_at.desc())

        return await paginate(stmt, page, limit, self._db)

    async def get_scheduled_auctions(self) -> Sequence[Auction]:
        """Get scheduled auctions whose start time has arrived.

        Returns:
            Sequence of auctions ready to be activated.

        """
        now = datetime.now(timezone.utc)
        stmt = select(Auction).where(
            Auction.status == AuctionStatus.SCHEDULED,
            Auction.starts_at <= now,
        )
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def attach_item(
        self,
        auction_id: uuid.UUID,
        item_id: uuid.UUID,
        starting_price: Decimal,
        quantity: int,
    ) -> AuctionItem:
        """Attach an item to an auction.

        Args:
            auction_id: Auction UUID
            item_id: Item UUID
            starting_price: Starting price for the item
            quantity: Quantity of items

        Returns:
            Created AuctionItem instance

        """
        auction_item = AuctionItem(
            auction_id=auction_id,
            item_id=item_id,
            starting_price=starting_price,
            quantity=quantity,
        )
        self._db.add(auction_item)
        await self._db.flush()
        return auction_item

    async def update_status(
        self, auction_id: uuid.UUID, status: AuctionStatus
    ) -> Auction | None:
        """Update auction status.

        Args:
            auction_id: Auction UUID
            status: New status

        Returns:
            Updated Auction instance or None if not found

        """
        auction = await self.get_by_id(auction_id)
        if auction:
            auction.status = status
            await self._db.flush()
            return auction
        return None

    async def get_auctions_to_settle(self) -> Sequence[Auction]:
        """Get auctions that need settlement (ended but still active).

        Also recovers auctions stuck in SETTLEMENT_IN_PROGRESS for over 10
        minutes — handles the case where a worker crashed mid-settlement.

        Returns:
            Sequence of auctions to settle

        """
        from datetime import timedelta

        from sqlalchemy import or_

        now = datetime.now(timezone.utc)
        stale_threshold = now - timedelta(minutes=10)

        stmt = (
            select(Auction)
            .where(
                or_(
                    # Normal case: ended but not yet claimed
                    (Auction.status == AuctionStatus.ACTIVE) & (Auction.ends_at <= now),
                    # Recovery case: claimed but worker died
                    (Auction.status == AuctionStatus.SETTLEMENT_IN_PROGRESS)
                    & (Auction.updated_at <= stale_threshold),
                )
            )
            .options(
                selectinload(Auction.auction_items).selectinload(AuctionItem.item),
                selectinload(Auction.seller),
            )
        )
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def claim_for_settlement(self, auction_id: uuid.UUID) -> bool:
        """Atomically claim an auction for settlement.

        This prevents multiple workers from settling the same auction.

        Args:
            auction_id: Auction UUID

        Returns:
            True if successfully claimed, False if already claimed

        """
        stmt = (
            update(Auction)
            .where(Auction.id == auction_id)
            .where(Auction.status == AuctionStatus.ACTIVE)
            .values(status=AuctionStatus.SETTLEMENT_IN_PROGRESS)
        )
        result = await self._db.execute(stmt)
        return result.rowcount > 0

    async def get_by_id(self, auction_id: uuid.UUID) -> Auction | None:
        """Get auction by ID with relationships loaded.

        Args:
            auction_id: Auction UUID

        Returns:
            Auction instance or None if not found

        """
        stmt = (
            select(Auction)
            .where(Auction.id == auction_id)
            .options(
                selectinload(Auction.auction_items)
                .selectinload(AuctionItem.item)
                .selectinload(Item.category),
                selectinload(Auction.auction_items)
                .selectinload(AuctionItem.item)
                .selectinload(Item.images),
                selectinload(Auction.seller),
                selectinload(Auction.highest_bid),
                selectinload(Auction.bids),
            )
            .with_for_update()
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_seller_auctions(
        self,
        seller_id: uuid.UUID,
        status: AuctionStatus | None,
        page: int,
        limit: int,
    ) -> dict:
        """Get paginated auctions for a seller.

        Args:
            seller_id: Seller UUID
            status: Optional status filter
            page: Page number
            limit: Items per page

        Returns:
            Paginated result dictionary

        """
        stmt = (
            select(Auction)
            .where(Auction.seller_id == seller_id)
            .options(
                selectinload(Auction.auction_items)
                .selectinload(AuctionItem.item)
                .selectinload(Item.category),
                selectinload(Auction.auction_items)
                .selectinload(AuctionItem.item)
                .selectinload(Item.images),
                selectinload(Auction.seller),
                selectinload(Auction.highest_bid),
                selectinload(Auction.bids),
            )
        )

        if status:
            stmt = stmt.where(Auction.status == status)

        stmt = stmt.order_by(Auction.created_at.desc())
        return await paginate(stmt, page, limit, self._db)

    async def update_auction(self, auction_id: uuid.UUID, data: dict) -> Auction | None:
        """Update auction details.

        Args:
            auction_id: Auction UUID
            data: Dictionary of fields to update

        Returns:
            Updated Auction instance or None if not found

        """
        auction = await self.get_by_id(auction_id)
        if not auction:
            return None

        for key, value in data.items():
            if value is not None:
                setattr(auction, key, value)

        self._db.add(auction)
        await self._db.flush()
        return auction

    async def detach_item(self, auction_id: uuid.UUID, item_id: uuid.UUID) -> bool:
        """Remove an item from an auction.

        Args:
            auction_id: Auction UUID
            item_id: Item UUID

        Returns:
            True if item was detached, False if not found

        """
        stmt = select(AuctionItem).where(
            AuctionItem.auction_id == auction_id, AuctionItem.item_id == item_id
        )
        result = await self._db.execute(stmt)
        auction_item = result.scalar_one_or_none()

        if auction_item:
            await self._db.delete(auction_item)
            await self._db.flush()
            return True
        return False

    async def get_auction_items(self, auction_id: uuid.UUID) -> Sequence[AuctionItem]:
        """Get all items attached to an auction.

        Args:
            auction_id: Auction UUID

        Returns:
            Sequence of AuctionItem instances

        """
        stmt = (
            select(AuctionItem)
            .where(AuctionItem.auction_id == auction_id)
            .options(selectinload(AuctionItem.item))
        )
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def get_for_reserve_settlement(self, auction_id: uuid.UUID) -> Auction | None:
        """Get auction with all relationships needed for reserve-not-met settlement.

        Loads bids with bidder, auction items with item, highest bid, and seller.
        Uses a fresh query intended for use in a dedicated session inside
        ``_handle_reserve_not_met``.

        Args:
            auction_id: Auction UUID

        Returns:
            Auction instance or None if not found

        """
        stmt = (
            select(Auction)
            .where(Auction.id == auction_id)
            .options(
                selectinload(Auction.auction_items).selectinload(AuctionItem.item),
                selectinload(Auction.bids).selectinload(Bid.bidder),
                selectinload(Auction.highest_bid),
                selectinload(Auction.seller),
            )
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_highest_bid(
        self, auction_id: uuid.UUID, bid_id: uuid.UUID
    ) -> Auction | None:
        """Update the highest bid reference on an auction.

        Args:
            auction_id: Auction UUID.
            bid_id: UUID of the new highest bid.

        Returns:
            Updated ``Auction`` instance, or ``None`` if not found.

        """
        auction = await self.get_by_id(auction_id)
        if auction:
            auction.highest_bid_id = bid_id
            await self._db.flush()
            return auction
        return None

    async def get_browsable_auctions(
        self,
        statuses: list[AuctionStatus],
        category_id: uuid.UUID | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        sort_by: str,
        page: int,
        limit: int,
    ) -> dict:
        """Get paginated auctions for browsing, with flexible status filtering.

        Args:
            statuses: List of statuses to include.
            category_id: Optional category ID filter.
            min_price: Optional minimum price filter.
            max_price: Optional maximum price filter.
            sort_by: Sort order string.
            page: Page number for pagination.
            limit: Number of items per page.

        Returns:
            Paginated result dictionary.

        """
        stmt = (
            select(Auction)
            .where(Auction.status.in_(statuses))
            .options(
                selectinload(Auction.auction_items)
                .selectinload(AuctionItem.item)
                .selectinload(Item.category),
                selectinload(Auction.auction_items)
                .selectinload(AuctionItem.item)
                .selectinload(Item.images),
                selectinload(Auction.seller),
                selectinload(Auction.highest_bid),
                selectinload(Auction.bids),
            )
        )

        if category_id:
            stmt = (
                stmt.join(Auction.auction_items)
                .join(AuctionItem.item)
                .where(Item.category_id == category_id)
            )

        match sort_by:
            case "lowest_price":
                stmt = stmt.join(Auction.highest_bid, isouter=True).order_by(
                    Bid.amount.asc()
                )
            case "highest_price":
                stmt = stmt.join(Auction.highest_bid, isouter=True).order_by(
                    Bid.amount.desc()
                )
            case _:
                stmt = stmt.order_by(Auction.created_at.desc())

        return await paginate(stmt, page, limit, self._db)

    async def get_increment_for_amount(self, current_bid: Decimal) -> Decimal:
        """Return the bid increment for a given current bid amount.

        Looks up the active ``BidIncrementTier`` whose range covers
        ``current_bid`` and returns its ``increment`` value.  Falls back
        to ₦500 if no matching tier is found.

        Args:
            current_bid: The current highest bid amount.

        Returns:
            The minimum increment the next bid must exceed the current by.

        """
        stmt = (
            select(BidIncrementTier)
            .where(BidIncrementTier.is_active)
            .where(BidIncrementTier.min_value <= current_bid)
            .where(
                or_(
                    BidIncrementTier.max_value.is_(None),
                    BidIncrementTier.max_value >= current_bid,
                )
            )
            .order_by(BidIncrementTier.min_value.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        tier = result.scalar_one_or_none()
        if tier is None:
            logger.warning(
                "No active bid increment tier found for %s. Using default ₦500.",
                current_bid,
            )
            return Decimal("500.00")
        return tier.increment
