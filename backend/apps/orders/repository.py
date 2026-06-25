"""Repository for order database operations."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.auctions.models import AuctionItem, Item
from apps.orders.enums import OrderStatus
from apps.orders.models import Order
from apps.users.models import User
from common.pagination import paginate
from common.schemas import PaginatedResponse


def _order_detail_options():
    """Return shared eager-load options for full order detail queries.

    Loads seller and buyer profiles to avoid lazy-load errors when
    ``PublicUserResponse`` accesses ``seller_profile.is_verified``.

    Returns:
        A list of SQLAlchemy ``selectinload`` option objects.

    """
    return [
        selectinload(Order.buyer).selectinload(User.seller_profile),
        selectinload(Order.buyer).selectinload(User.profile),
        selectinload(Order.seller).selectinload(User.seller_profile),
        selectinload(Order.seller).selectinload(User.profile),
        selectinload(Order.auction),
        selectinload(Order.auction_item)
        .selectinload(AuctionItem.item)
        .selectinload(Item.images),
        selectinload(Order.dispute),
    ]


class OrderRepository:
    """Repository for all order-related database operations.

    Attributes:
        _db: The active ``AsyncSession`` injected at construction time.

    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialise the repository with an async database session.

        Args:
            db: An active ``AsyncSession`` to use for all queries.

        """
        self._db = db

    async def create(self, data: dict) -> Order:
        """Create a new order record.

        Called by the auction settlement task after a winner is determined.
        Uses ``flush()`` — the settlement task controls the transaction.

        Args:
            data: Dictionary of field values for the ``Order`` model.

        Returns:
            The newly created ``Order`` instance.

        """
        order = Order(**data)
        self._db.add(order)
        await self._db.flush()
        return order

    async def get_by_id(self, order_id: UUID) -> Order | None:
        """Load an order with all relationships for the detail view.

        Args:
            order_id: UUID of the order to retrieve.

        Returns:
            The matching ``Order`` instance, or ``None`` if not found.

        """
        stmt = (
            select(Order).where(Order.id == order_id).options(*_order_detail_options())
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_auction_id(self, auction_id: UUID) -> Order | None:
        """Return the order for a given auction (one auction → one order).

        Args:
            auction_id: UUID of the auction.

        Returns:
            The matching ``Order``, or ``None`` if not found.

        """
        stmt = (
            select(Order)
            .where(Order.auction_id == auction_id)
            .options(*_order_detail_options())
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_orders(
        self,
        user_id: UUID,
        role: str,
        status: OrderStatus | None,
        page: int,
        limit: int,
    ):
        """Return paginated orders for a user filtered by their role.

        ``role='buyer'`` returns orders where the user is the buyer;
        ``role='seller'`` returns orders where the user is the seller.
        This is a filter direction string, not a ``UserRole`` enum value.

        Args:
            user_id: UUID of the user.
            role: ``"buyer"`` or ``"seller"``.
            status: Optional ``OrderStatus`` filter.
            page: Page number (1-indexed).
            limit: Maximum number of orders per page.

        Returns:
            A ``PaginatedResponse`` containing the order records.

        """
        if role == "buyer":
            stmt = select(Order).where(Order.buyer_id == user_id)
        else:
            stmt = select(Order).where(Order.seller_id == user_id)

        if status:
            stmt = stmt.where(Order.status == status)

        stmt = stmt.options(
            selectinload(Order.buyer).selectinload(User.seller_profile),
            selectinload(Order.buyer).selectinload(User.profile),
            selectinload(Order.seller).selectinload(User.seller_profile),
            selectinload(Order.seller).selectinload(User.profile),
            selectinload(Order.auction),
            selectinload(Order.auction_item)
            .selectinload(AuctionItem.item)
            .selectinload(Item.images),
        ).order_by(Order.created_at.desc())

        return await paginate(stmt, page, limit, self._db)

    async def update_status(
        self,
        order_id: UUID,
        status: OrderStatus,
        extra_fields: dict | None = None,
    ) -> Order | None:
        """Update order status and any extra fields atomically.

        ``extra_fields`` handles ``shipped_at``, ``delivered_at``,
        ``tracking_number``, ``dispute_raised_at``, and ``dispute_id``.

        Args:
            order_id: UUID of the order to update.
            status: The new ``OrderStatus`` value.
            extra_fields: Optional dictionary of additional fields to set.

        Returns:
            The updated ``Order`` instance, or ``None`` if not found.

        """
        order = await self.get_by_id(order_id)
        if not order:
            return None

        order.status = status
        if extra_fields:
            for key, value in extra_fields.items():
                setattr(order, key, value)

        await self._db.flush()
        return order

    async def get_overdue_shipments(self) -> list[Order]:
        """Fetch orders where the seller missed the shipping deadline.

        Returns ``PENDING_SHIPMENT`` orders whose ``shipping_deadline_at``
        has passed. Used by the Celery beat task to auto-cancel and refund.

        Returns:
            A list of overdue ``Order`` instances with buyer/seller loaded.

        """
        now = datetime.now(timezone.utc)
        stmt = (
            select(Order)
            .where(Order.status == OrderStatus.PENDING_SHIPMENT)
            .where(Order.shipping_deadline_at <= now)
            .options(
                selectinload(Order.buyer).selectinload(User.seller_profile),
                selectinload(Order.buyer).selectinload(User.profile),
                selectinload(Order.seller).selectinload(User.seller_profile),
                selectinload(Order.seller).selectinload(User.profile),
            )
        )
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def get_all(
        self,
        page: int,
        limit: int,
        status: Optional[OrderStatus] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse:
        stmt = (
            select(Order)
            .options(*_order_detail_options())
            .order_by(Order.created_at.desc())
        )

        if status:
            stmt = stmt.where(Order.status == status)

        if search:
            query = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Order.tracking_number.ilike(query),
                    Order.buyer.has(User.email.ilike(query)),
                    Order.buyer.has(User.first_name.ilike(query)),
                    Order.buyer.has(User.last_name.ilike(query)),
                    Order.seller.has(User.email.ilike(query)),
                    Order.seller.has(User.first_name.ilike(query)),
                    Order.seller.has(User.last_name.ilike(query)),
                )
            )

        return await paginate(stmt, page, limit, self._db)
