"""Custom analytics dashboard for the KaraKaja admin panel.

All metrics are calculated via direct database queries — not API endpoints.
This gives the admin panel its own read path independent of the application layer.
"""

from datetime import datetime, timedelta, timezone

from sqladmin import BaseView, expose
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.requests import Request

from apps.auctions.enums import AuctionStatus, ItemStatus
from apps.auctions.models import Auction, Item
from apps.disputes.enums import DisputeStatus
from apps.disputes.models import Dispute
from apps.orders.enums import OrderStatus
from apps.orders.models import Order
from apps.users.enums import KYCTier
from apps.users.kyc_models import KYCDocumentModel
from apps.users.models import User
from apps.wallet.enums import BalanceType, TransactionType
from apps.wallet.models import WalletTransactions
from config.database import engine


class DashboardView(BaseView):
    """Custom analytics dashboard view for the KaraKaja admin panel."""

    name = "Dashboard"
    icon = "fa-solid fa-chart-line"

    @expose("/dashboard", methods=["GET"])
    async def dashboard(self, request: Request):
        """Render the admin analytics dashboard.

        Queries the database directly for platform metrics and renders
        the ``dashboard.html`` template with the results.

        Args:
            request: The incoming Starlette request.

        Returns:
            A ``TemplateResponse`` rendering the dashboard template.

        """
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        two_hours_from_now = now + timedelta(hours=2)
        month_start = today_start.replace(day=1)

        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:

            # ── Platform Overview ──────────────────────────────────────────
            total_users = await session.scalar(select(func.count(User.id)))

            # Users grouped by KYC tier — returns list of (tier, count) rows
            kyc_rows = (
                await session.execute(
                    select(User.kyc_tier, func.count(User.id)).group_by(User.kyc_tier)
                )
            ).all()
            kyc_by_tier = {row[0]: row[1] for row in kyc_rows}

            new_users_today = await session.scalar(
                select(func.count(User.id)).where(User.created_at >= today_start)
            )
            new_users_this_week = await session.scalar(
                select(func.count(User.id)).where(User.created_at >= week_start)
            )

            # ── Auction Activity ───────────────────────────────────────────
            active_auctions = await session.scalar(
                select(func.count(Auction.id)).where(
                    Auction.status == AuctionStatus.ACTIVE
                )
            )
            ending_soon = await session.scalar(
                select(func.count(Auction.id)).where(
                    Auction.status == AuctionStatus.ACTIVE,
                    Auction.ends_at <= two_hours_from_now,
                    Auction.ends_at > now,
                )
            )
            settled_today = await session.scalar(
                select(func.count(Auction.id)).where(
                    Auction.status == AuctionStatus.SETTLED,
                    Auction.updated_at >= today_start,
                )
            )
            reserve_not_met_today = await session.scalar(
                select(func.count(Auction.id)).where(
                    Auction.status == AuctionStatus.ENDED_RESERVE_NOT_MET,
                    Auction.updated_at >= today_start,
                )
            )

            # ── Financial Summary ──────────────────────────────────────────
            deposits_today = await session.scalar(
                select(func.coalesce(func.sum(WalletTransactions.amount), 0)).where(
                    WalletTransactions.transaction_type == TransactionType.DEPOSIT,
                    WalletTransactions.created_at >= today_start,
                )
            )
            commission_today = await session.scalar(
                select(func.coalesce(func.sum(WalletTransactions.amount), 0)).where(
                    WalletTransactions.transaction_type == TransactionType.COMMISION,
                    WalletTransactions.created_at >= today_start,
                )
            )
            commission_this_month = await session.scalar(
                select(func.coalesce(func.sum(WalletTransactions.amount), 0)).where(
                    WalletTransactions.transaction_type == TransactionType.COMMISION,
                    WalletTransactions.created_at >= month_start,
                )
            )
            escrow_held = await session.scalar(
                select(func.coalesce(func.sum(WalletTransactions.amount), 0)).where(
                    WalletTransactions.balance_type == BalanceType.ESCROW,
                )
            )
            locked_bids = await session.scalar(
                select(func.coalesce(func.sum(WalletTransactions.amount), 0)).where(
                    WalletTransactions.balance_type == BalanceType.LOCKED,
                )
            )

            # ── Moderation Queue ───────────────────────────────────────────
            pending_items = await session.scalar(
                select(func.count(Item.id)).where(
                    Item.status == ItemStatus.PENDING_REVIEW
                )
            )
            open_disputes = await session.scalar(
                select(func.count(Dispute.id)).where(
                    Dispute.status == DisputeStatus.OPEN
                )
            )
            pending_kyc_docs = await session.scalar(
                select(func.count(KYCDocumentModel.id)).where(
                    KYCDocumentModel.status == "PENDING"
                )
            )

            # ── Recent Activity ────────────────────────────────────────────
            recent_users_rows = (
                await session.execute(
                    select(User.email, User.created_at)
                    .order_by(User.created_at.desc())
                    .limit(10)
                )
            ).all()

            recent_orders_rows = (
                await session.execute(
                    select(Order.id, Order.amount, Order.status, Order.created_at)
                    .where(Order.status == OrderStatus.COMPLETED)
                    .order_by(Order.created_at.desc())
                    .limit(10)
                )
            ).all()

            recent_disputes_rows = (
                await session.execute(
                    select(Dispute.title, Dispute.status, Dispute.created_at)
                    .order_by(Dispute.created_at.desc())
                    .limit(5)
                )
            ).all()

        context = {
            "request": request,
            # Platform Overview
            "total_users": total_users or 0,
            "kyc_tier_1": kyc_by_tier.get(KYCTier.TIER_1, 0),
            "kyc_tier_2": kyc_by_tier.get(KYCTier.TIER_2, 0),
            "kyc_tier_3": kyc_by_tier.get(KYCTier.TIER_3, 0),
            "new_users_today": new_users_today or 0,
            "new_users_this_week": new_users_this_week or 0,
            # Auction Activity
            "active_auctions": active_auctions or 0,
            "ending_soon": ending_soon or 0,
            "settled_today": settled_today or 0,
            "reserve_not_met_today": reserve_not_met_today or 0,
            # Financial Summary
            "deposits_today": deposits_today or 0,
            "commission_today": commission_today or 0,
            "commission_this_month": commission_this_month or 0,
            "escrow_held": escrow_held or 0,
            "locked_bids": locked_bids or 0,
            # Moderation Queue
            "pending_items": pending_items or 0,
            "open_disputes": open_disputes or 0,
            "pending_kyc_docs": pending_kyc_docs or 0,
            # Recent Activity
            "recent_users": recent_users_rows,
            "recent_orders": recent_orders_rows,
            "recent_disputes": recent_disputes_rows,
        }

        return await self.templates.TemplateResponse(request, "dashboard.html", context)
