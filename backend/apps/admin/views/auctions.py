"""SQLAdmin model views for auction-related entities.

Registers ``CategoryAdmin``, ``ItemAdmin``, ``AuctionAdmin``, and
``BidIncrementTierAdmin`` with the admin panel.
"""

from sqladmin import ModelView, action
from sqladmin.filters import BooleanFilter, StaticValuesFilter

from apps.auctions.enums import AuctionStatus, ItemCondition, ItemStatus
from apps.auctions.models import Auction, BidIncrementTier, Category, Item


class CategoryAdmin(ModelView, model=Category):
    """Admin view for product categories.

    Supports full CRUD — admins manage categories directly.
    """

    name = "Category"
    name_plural = "Categories"
    icon = "fa-solid fa-tags"

    column_list = [
        Category.name,
        Category.slug,
        Category.parent,
        Category.is_active,
        "item_count",
        Category.created_at,
    ]

    column_formatters = {
        Category.parent: lambda m, a: m.parent.name if m.parent else "— (root)",
        "item_count": lambda m, a: m.item_count,
    }

    column_filters = [
        BooleanFilter(Category.is_active, title="Active"),
    ]

    column_searchable_list = [Category.name, Category.slug]

    form_columns = [
        Category.name,
        Category.slug,
        Category.parent_id,
        Category.is_active,
    ]


class ItemAdmin(ModelView, model=Item):
    """Admin view for auction items with approve/reject bulk actions."""

    name = "Item"
    name_plural = "Items"

    column_list = [
        Item.title,
        Item.seller,
        Item.category,
        Item.condition,
        Item.status,
        Item.created_at,
    ]

    column_formatters = {
        Item.seller: lambda m, a: m.seller.email if m.seller else "—",
        Item.category: lambda m, a: m.category.name if m.category else "—",
    }

    column_filters = [
        StaticValuesFilter(
            Item.status,
            title="Status",
            values=[(s.value, s.value) for s in ItemStatus],
        ),
        StaticValuesFilter(
            Item.condition,
            title="Condition",
            values=[(c.value, c.value) for c in ItemCondition],
        ),
    ]

    column_searchable_list = [Item.title]

    form_columns = [Item.status]

    @action(
        name="approve_items",
        label="Approve Items",
        confirmation_message="Approve selected items?",
    )
    async def approve_items(self, request, pks):
        """Bulk-approve selected items by setting their status to APPROVED."""
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from config.database import engine

        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            for pk in pks:
                item = await session.get(Item, pk)
                if item:
                    item.status = ItemStatus.APPROVED
            await session.commit()

    @action(
        name="reject_items",
        label="Reject Items",
        confirmation_message="Reject selected items?",
    )
    async def reject_items(self, request, pks):
        """Bulk-reject selected items by setting their status to REJECTED."""
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from config.database import engine

        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            for pk in pks:
                item = await session.get(Item, pk)
                if item:
                    item.status = ItemStatus.REJECTED
            await session.commit()


class AuctionAdmin(ModelView, model=Auction):
    """Read-only admin view for auctions.

    Auctions are financial records and must not be edited or deleted
    through the admin panel.
    """

    name = "Auction"
    name_plural = "Auctions"

    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        Auction.id,
        Auction.title,
        Auction.seller,
        Auction.status,
        Auction.starts_at,
        Auction.ends_at,
        Auction.highest_bid,
        Auction.reserve_price,
        Auction.created_at,
    ]

    column_formatters = {
        Auction.id: lambda m, a: str(m.id)[:8] + "...",
        Auction.seller: lambda m, a: m.seller.email if m.seller else "—",
        Auction.highest_bid: lambda m, a: (
            f"₦{m.highest_bid.amount:,.2f}" if m.highest_bid else "No bids"
        ),
    }

    column_filters = [
        StaticValuesFilter(
            Auction.status,
            title="Status",
            values=[(s.value, s.value) for s in AuctionStatus],
        ),
    ]

    column_searchable_list = [Auction.title]

    column_details_list = "__all__"

    column_formatters_detail = {
        Auction.seller: lambda m, a: m.seller.email if m.seller else "—",
    }


class BidIncrementTierAdmin(ModelView, model=BidIncrementTier):
    """Admin view for managing bid increment tiers."""

    name = "Bid Increment Tier"
    name_plural = "Bid Increment Tiers"

    column_list = [
        BidIncrementTier.min_value,
        BidIncrementTier.max_value,
        BidIncrementTier.increment,
        BidIncrementTier.is_active,
        BidIncrementTier.created_at,
    ]

    form_columns = [
        BidIncrementTier.min_value,
        BidIncrementTier.max_value,
        BidIncrementTier.increment,
        BidIncrementTier.is_active,
    ]

    column_filters = [
        BooleanFilter(BidIncrementTier.is_active, title="Active"),
    ]
