from sqladmin import ModelView, action
from sqladmin.filters import BooleanFilter, StaticValuesFilter

from apps.auctions.enums import AuctionStatus, ItemCondition, ItemStatus
from apps.auctions.models import Auction, BidIncrementTier, Item


class ItemAdmin(ModelView, model=Item):
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
            Item.status, title="Status", values=[(s.value, s.value) for s in ItemStatus]
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
    name = "Auction"
    name_plural = "Auctions"

    # Auctions are financial records — read only
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
        Auction.highest_bid,  # real relationship — SQLAdmin eager-loads it
        Auction.reserve_price,
        Auction.created_at,
    ]

    column_formatters = {
        Auction.id: lambda m, a: str(m.id)[:8] + "...",
        Auction.seller: lambda m, a: m.seller.email if m.seller else "—",
        # highest_bid is now eager-loaded — safe to access here
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

    # Show everything in the detail view
    column_details_list = "__all__"

    column_formatters_detail = {
        Auction.seller: lambda m, a: m.seller.email if m.seller else "—",
    }


class BidIncrementTierAdmin(ModelView, model=BidIncrementTier):
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
