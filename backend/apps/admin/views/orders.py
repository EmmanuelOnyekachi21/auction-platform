from datetime import datetime, timezone

from markupsafe import Markup
from sqladmin import ModelView, action
from sqladmin.filters import StaticValuesFilter

from apps.disputes.enums import DisputeStatus
from apps.disputes.models import Dispute
from apps.escrow.enums import EscrowStatus
from apps.escrow.models import Escrow
from apps.orders.enums import OrderStatus
from apps.orders.models import Order


class OrderAdmin(ModelView, model=Order):
    name = "Order"
    name_plural = "Orders"

    can_create = False
    can_delete = False

    column_list = [
        Order.id,
        Order.buyer,
        Order.seller,
        Order.amount,
        Order.status,
        Order.shipping_deadline_at,
        Order.created_at,
    ]

    column_formatters = {
        Order.id: lambda m, a: str(m.id)[:8] + "...",
        Order.buyer: lambda m, a: m.buyer.email if m.buyer else "—",
        Order.seller: lambda m, a: m.seller.email if m.seller else "—",
        Order.status: lambda m, a: Markup(
            f"<span style='color:{_order_status_color(m)};font-weight:600'>"
            f"{m.status.value}</span>"
        ),
    }

    column_filters = [
        StaticValuesFilter(
            Order.status,
            title="Status",
            values=[(s.value, s.value) for s in OrderStatus],
        )
    ]

    form_columns = [Order.status]

    column_details_list = "__all__"

    column_formatters_detail = {
        Order.buyer: lambda m, a: m.buyer.email if m.buyer else "—",
        Order.seller: lambda m, a: m.seller.email if m.seller else "—",
    }


def _order_status_color(order: Order) -> str:
    """Return a CSS colour string based on order status and deadline."""
    now = datetime.now(timezone.utc)
    if order.status == OrderStatus.DISPUTED:
        return "red"
    if (
        order.status == OrderStatus.PENDING_SHIPMENT
        and order.shipping_deadline_at
        and order.shipping_deadline_at < now
    ):
        return "orange"
    if order.status == OrderStatus.COMPLETED:
        return "green"
    return "gray"


class EscrowAdmin(ModelView, model=Escrow):
    name = "Escrow"
    name_plural = "Escrows"

    # Financial record — fully read-only
    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        Escrow.order_id,  # raw FK column — no relationship load needed
        Escrow.winner,
        Escrow.seller,
        Escrow.amount,
        Escrow.commission_amount,
        Escrow.status,
        Escrow.auto_release_at,
        Escrow.created_at,
    ]

    column_formatters = {
        Escrow.order_id: lambda m, a: (
            str(m.order_id)[:8] + "..." if m.order_id else "—"
        ),
        Escrow.winner: lambda m, a: m.winner.email if m.winner else "—",
        Escrow.seller: lambda m, a: m.seller.email if m.seller else "—",
    }

    column_filters = [
        StaticValuesFilter(
            Escrow.status,
            title="Status",
            values=[(s.value, s.value) for s in EscrowStatus],
        )
    ]

    column_details_list = "__all__"

    column_formatters_detail = {
        Escrow.order_id: lambda m, a: (
            str(m.order_id)[:8] + "..." if m.order_id else "—"
        ),
        Escrow.winner: lambda m, a: m.winner.email if m.winner else "—",
        Escrow.seller: lambda m, a: m.seller.email if m.seller else "—",
    }


class DisputeAdmin(ModelView, model=Dispute):
    name = "Dispute"
    name_plural = "Disputes"

    can_create = False
    can_delete = False

    column_list = [
        Dispute.title,
        Dispute.raised_by,
        Dispute.against,
        Dispute.status,
        Dispute.created_at,
        Dispute.resolved_at,
    ]

    column_formatters = {
        Dispute.raised_by: lambda m, a: m.raised_by.email if m.raised_by else "—",
        Dispute.against: lambda m, a: m.against.email if m.against else "—",
    }

    column_filters = [
        StaticValuesFilter(
            Dispute.status,
            title="Status",
            values=[(s.value, s.value) for s in DisputeStatus],
        )
    ]

    form_columns = [
        Dispute.status,
        Dispute.resolution,
        Dispute.resolved_by_id,
        Dispute.resolved_at,
    ]

    column_details_list = "__all__"

    column_formatters_detail = {
        Dispute.raised_by: lambda m, a: m.raised_by.email if m.raised_by else "—",
        Dispute.against: lambda m, a: m.against.email if m.against else "—",
        Dispute.resolved_by: lambda m, a: m.resolved_by.email if m.resolved_by else "—",
    }

    @action(
        name="mark_under_review",
        label="Mark Under Review",
        confirmation_message="Mark selected disputes as under review?",
    )
    async def mark_under_review(self, request, pks):
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from config.database import engine

        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            for pk in pks:
                dispute = await session.get(Dispute, pk)
                if dispute:
                    dispute.status = DisputeStatus.UNDER_REVIEW
            await session.commit()

    @action(
        name="resolve_buyer_favour",
        label="Resolve — Buyer's Favour",
        confirmation_message="Resolve selected disputes in the buyer's favour?",
    )
    async def resolve_buyer_favour(self, request, pks):
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from config.database import engine

        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            for pk in pks:
                dispute = await session.get(Dispute, pk)
                if dispute:
                    dispute.status = DisputeStatus.RESOLVED
                    dispute.resolution = "Resolved in buyer's favour"
                    dispute.resolved_at = datetime.now(timezone.utc)
            await session.commit()

    @action(
        name="resolve_seller_favour",
        label="Resolve — Seller's Favour",
        confirmation_message="Resolve selected disputes in the seller's favour?",
    )
    async def resolve_seller_favour(self, request, pks):
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from config.database import engine

        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            for pk in pks:
                dispute = await session.get(Dispute, pk)
                if dispute:
                    dispute.status = DisputeStatus.RESOLVED
                    dispute.resolution = "Resolved in seller's favour"
                    dispute.resolved_at = datetime.now(timezone.utc)
            await session.commit()
