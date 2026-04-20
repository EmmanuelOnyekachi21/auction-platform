"""Order service — handles order lifecycle and escrow release."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from apps.disputes.schemas import DisputeSummary
from apps.escrow.enums import EscrowStatus
from apps.escrow.repository import EscrowRepository
from apps.escrow.schemas import EscrowResponse
from apps.notifications.tasks import (
    notify_item_shipped,
    notify_order_cancelled_buyer,
    notify_order_cancelled_seller,
    notify_payment_released,
    notify_transaction_completed,
)
from apps.orders.enums import OrderStatus
from apps.orders.repository import OrderRepository
from apps.orders.schemas import AuctionSummary as AuctionSummarySchema
from apps.orders.schemas import (
    ItemSummary,
    OrderDetailResponse,
    OrderSummaryResponse,
    ShipOrderRequest,
)
from apps.users.repository import UserRepository
from apps.users.schemas import PublicUserResponse
from apps.wallet.enums import (
    BalanceType,
    ReferenceType,
    TransactionDirection,
    TransactionType,
)
from apps.wallet.repository import WalletRepository
from common.exceptions import (
    OrderNotFoundException,
    PermissionDeniedException,
    ValidationException,
)


class OrderService:
    """Service layer for order lifecycle and escrow release operations.

    Attributes:
        _db: The active ``AsyncSession`` shared across all repositories.
        _order_repo: Repository for order CRUD operations.
        _escrow_repo: Repository for escrow queries.
        _wallet_repo: Repository for wallet balance operations.

    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialise the service with a shared async database session.

        Args:
            db: An active ``AsyncSession`` used for all database operations.

        """
        self._db = db
        self._order_repo = OrderRepository(db)
        self._escrow_repo = EscrowRepository(db)
        self._wallet_repo = WalletRepository(db)

    def _build_order_detail(self, order, escrow=None) -> OrderDetailResponse:
        """Build an ``OrderDetailResponse`` from ORM objects.

        Shared by all service methods that return order detail.

        Args:
            order: The ``Order`` ORM instance.
            escrow: Optional ``Escrow`` ORM instance.

        Returns:
            A fully populated ``OrderDetailResponse``.

        """
        item_summary = None
        if order.auction_item and order.auction_item.item:
            raw_item = order.auction_item.item
            primary_image = next(
                (img.url for img in (raw_item.images or []) if img.is_primary),
                raw_item.images[0].url if raw_item.images else None,
            )
            item_summary = ItemSummary(
                id=raw_item.id,
                title=raw_item.title,
                condition=raw_item.condition,
                primary_image_url=primary_image,
            )

        return OrderDetailResponse(
            id=order.id,
            status=order.status,
            amount=order.amount,
            created_at=order.created_at,
            shipping_deadline_at=order.shipping_deadline_at,
            shipped_at=order.shipped_at,
            delivered_at=order.delivered_at,
            dispute_raised_at=order.dispute_raised_at,
            tracking_number=order.tracking_number,
            auction=(
                AuctionSummarySchema.model_validate(order.auction)
                if order.auction
                else None
            ),
            item=item_summary,
            buyer=(
                PublicUserResponse.model_validate(order.buyer) if order.buyer else None
            ),
            seller=(
                PublicUserResponse.model_validate(order.seller)
                if order.seller
                else None
            ),
            escrow=EscrowResponse.model_validate(escrow) if escrow else None,
            dispute=(
                DisputeSummary.model_validate(order.dispute) if order.dispute else None
            ),
        )

    async def get_order(
        self, order_id: UUID, requesting_user_id: UUID
    ) -> OrderDetailResponse:
        """Return full order detail for the buyer or seller.

        Args:
            order_id: UUID of the order.
            requesting_user_id: UUID of the user requesting the order.

        Returns:
            The ``OrderDetailResponse`` for the order.

        Raises:
            OrderNotFoundException: If the order does not exist.
            PermissionDeniedException: If the caller is not the buyer or seller.

        """
        order = await self._order_repo.get_by_id(order_id)
        if not order:
            raise OrderNotFoundException()
        if requesting_user_id not in (order.buyer_id, order.seller_id):
            raise PermissionDeniedException()
        escrow = await self._escrow_repo.get_by_order_id(order_id)
        return self._build_order_detail(order, escrow)

    async def get_my_orders(
        self,
        user_id: UUID,
        role: str,
        status: OrderStatus | None,
        page: int,
        limit: int,
    ):
        """Return paginated orders for the authenticated user.

        Args:
            user_id: UUID of the user.
            role: ``"buyer"`` or ``"seller"``.
            status: Optional ``OrderStatus`` filter.
            page: Page number (1-indexed).
            limit: Maximum number of orders per page.

        Returns:
            A ``PaginatedResponse`` of ``OrderSummaryResponse`` objects.

        """
        result = await self._order_repo.get_user_orders(
            user_id, role, status, page, limit
        )

        serialized = []
        for order in result.data:
            item_summary = None
            if order.auction_item and order.auction_item.item:
                raw_item = order.auction_item.item
                primary_image = next(
                    (img.url for img in (raw_item.images or []) if img.is_primary),
                    raw_item.images[0].url if raw_item.images else None,
                )
                item_summary = ItemSummary(
                    id=raw_item.id,
                    title=raw_item.title,
                    condition=raw_item.condition,
                    primary_image_url=primary_image,
                )

            serialized.append(
                OrderSummaryResponse(
                    id=order.id,
                    status=order.status,
                    amount=order.amount,
                    created_at=order.created_at,
                    auction=(
                        AuctionSummarySchema.model_validate(order.auction)
                        if order.auction
                        else None
                    ),
                    item=item_summary,
                    buyer=(
                        PublicUserResponse.model_validate(order.buyer)
                        if order.buyer
                        else None
                    ),
                    seller=(
                        PublicUserResponse.model_validate(order.seller)
                        if order.seller
                        else None
                    ),
                )
            )

        result.data = serialized
        return result

    async def ship_order(
        self,
        seller_id: UUID,
        order_id: UUID,
        data: ShipOrderRequest,
    ) -> OrderDetailResponse:
        """Mark an order as shipped.

        Args:
            seller_id: UUID of the seller marking the order shipped.
            order_id: UUID of the order.
            data: Validated ship request with optional tracking number.

        Returns:
            The updated ``OrderDetailResponse``.

        Raises:
            OrderNotFoundException: If the order does not exist.
            PermissionDeniedException: If the caller is not the seller.
            ValidationException: If the order is not awaiting shipment.

        """
        order = await self._order_repo.get_by_id(order_id)
        if not order:
            raise OrderNotFoundException()
        if order.seller_id != seller_id:
            raise PermissionDeniedException()
        if order.status != OrderStatus.PENDING_SHIPMENT:
            raise ValidationException(message="Order is not awaiting shipment")

        now = datetime.now(timezone.utc)
        order = await self._order_repo.update_status(
            order_id=order_id,
            status=OrderStatus.SHIPPED,
            extra_fields={
                "shipped_at": now,
                "tracking_number": data.tracking_number,
            },
        )
        await self._db.commit()

        if order.buyer:
            notify_item_shipped.delay(
                buyer_email=order.buyer.email,
                buyer_name=(
                    f"{order.buyer.first_name or ''} "
                    f"{order.buyer.last_name or ''}".strip()
                ),
                order_id=str(order_id),
                tracking_number=data.tracking_number,
            )
        escrow = await self._escrow_repo.get_by_order_id(order_id)
        return self._build_order_detail(order, escrow)

    async def _release_escrow_to_seller(self, escrow_id: UUID) -> None:
        """Release escrow funds to the seller after successful delivery.

        Called from ``confirm_delivery``, the auto-release Celery task,
        and dispute resolution in the seller's favour.

        Steps:
            1. Fetch escrow.
            2. Lock seller wallet (``SELECT FOR UPDATE``).
            3. Move ``escrow_funds`` → ``available_funds`` minus commission.
            4. Record seller payout transaction.
            5. Record commission transaction (platform revenue audit trail).
            6. Mark escrow ``RELEASED``.
            7. Increment seller ``total_sales`` on ``UserProfile``.

        Args:
            escrow_id: UUID of the escrow to release.

        Raises:
            ValidationException: If the escrow or a wallet is not found.

        """
        escrow = await self._escrow_repo.get_by_id(escrow_id)
        if not escrow:
            raise ValidationException(message="Escrow not found")

        buyer_wallet = await self._wallet_repo.get_by_user_id_with_lock(
            escrow.winner_id
        )
        if not buyer_wallet:
            raise ValidationException(message="Buyer wallet not found")

        await self._wallet_repo.update_balances(
            wallet_id=buyer_wallet.id,
            available_delta=Decimal("0"),
            locked_delta=Decimal("0"),
            escrow_delta=-escrow.amount,
        )

        seller_wallet = await self._wallet_repo.get_by_user_id_with_lock(
            escrow.seller_id
        )
        if not seller_wallet:
            raise ValidationException(message="Seller wallet not found")

        seller_payout = escrow.amount - escrow.commission_amount
        balance_before = seller_wallet.available_funds

        # Credit seller with net payout (full amount minus commission) in one step.
        # Commission is an internal platform deduction — showing it as a separate
        # transaction confuses sellers. One clean line: "you received ₦X".
        seller_wallet = await self._wallet_repo.update_balances(
            wallet_id=seller_wallet.id,
            available_delta=seller_payout,
            locked_delta=Decimal("0"),
            escrow_delta=Decimal("0"),
        )

        await self._wallet_repo.create_transaction(
            wallet_id=seller_wallet.id,
            data={
                "amount": seller_payout,
                "balance_before": balance_before,
                "balance_after": seller_wallet.available_funds,
                "description": (
                    f"Sale proceeds for order {escrow.order_id} "
                    f"(₦{escrow.amount:,.2f} - 5% commission)"
                ),
                "transaction_type": TransactionType.ESCROW_RELEASE,
                "direction": TransactionDirection.CREDIT,
                "balance_type": BalanceType.AVAILABLE,
                "reference_id": str(escrow.id),
                "reference_type": ReferenceType.ESCROW,
            },
        )

        now = datetime.now(timezone.utc)
        await self._escrow_repo.update_status(
            escrow_id=escrow.id,
            status=EscrowStatus.RELEASED,
            extra_fields={"released_at": now},
        )

        user_repo = UserRepository(self._db)
        await user_repo.increment_total_sales(escrow.seller_id)

    async def confirm_delivery(
        self, buyer_id: UUID, order_id: UUID
    ) -> OrderDetailResponse:
        """Buyer confirms receipt of the item, triggering escrow release.

        Args:
            buyer_id: UUID of the buyer confirming delivery.
            order_id: UUID of the order.

        Returns:
            The updated ``OrderDetailResponse``.

        Raises:
            OrderNotFoundException: If the order does not exist.
            PermissionDeniedException: If the caller is not the buyer.
            ValidationException: If the order has not been shipped yet.

        """
        order = await self._order_repo.get_by_id(order_id)
        if not order:
            raise OrderNotFoundException()
        if order.buyer_id != buyer_id:
            raise PermissionDeniedException()
        if order.status != OrderStatus.SHIPPED:
            raise ValidationException(
                message="Cannot confirm delivery before item is marked as shipped"
            )

        escrow = await self._escrow_repo.get_by_order_id(order_id)

        try:
            now = datetime.now(timezone.utc)
            await self._order_repo.update_status(
                order_id=order_id,
                status=OrderStatus.DELIVERED,
                extra_fields={"delivered_at": now},
            )
            await self._release_escrow_to_seller(escrow.id)
            order = await self._order_repo.update_status(
                order_id=order_id,
                status=OrderStatus.COMPLETED,
            )
            await self._db.commit()
        except Exception:
            await self._db.rollback()
            raise

        if order.seller:
            notify_payment_released.delay(
                seller_email=order.seller.email,
                seller_name=(
                    f"{order.seller.first_name or ''} "
                    f"{order.seller.last_name or ''}".strip()
                ),
                order_id=str(order_id),
                amount=str(order.amount),
            )
        if order.buyer:
            notify_transaction_completed.delay(
                buyer_email=order.buyer.email,
                buyer_name=(
                    f"{order.buyer.first_name or ''} "
                    f"{order.buyer.last_name or ''}".strip()
                ),
                order_id=str(order_id),
            )

        escrow = await self._escrow_repo.get_by_order_id(order_id)
        return self._build_order_detail(order, escrow)

    async def cancel_order(self, buyer_id: UUID, order_id: UUID) -> OrderDetailResponse:
        """Buyer cancels an order after the seller missed the shipping deadline.

        Args:
            buyer_id: UUID of the buyer cancelling the order.
            order_id: UUID of the order.

        Returns:
            The updated ``OrderDetailResponse``.

        Raises:
            OrderNotFoundException: If the order does not exist.
            PermissionDeniedException: If the caller is not the buyer.
            ValidationException: If the order cannot be cancelled or the
                deadline has not yet passed.

        """
        order = await self._order_repo.get_by_id(order_id)
        if not order:
            raise OrderNotFoundException()
        if order.buyer_id != buyer_id:
            raise PermissionDeniedException()
        if order.status != OrderStatus.PENDING_SHIPMENT:
            raise ValidationException(
                message="Order cannot be cancelled in its current status"
            )

        now = datetime.now(timezone.utc)
        if order.shipping_deadline_at > now:
            raise ValidationException(
                message=(
                    f"Seller still has time to ship. "
                    f"Deadline: "
                    f"{order.shipping_deadline_at.strftime('%d %b %Y %H:%M UTC')}"
                )
            )

        escrow = await self._escrow_repo.get_by_order_id(order_id)

        try:
            buyer_wallet = await self._wallet_repo.get_by_user_id_with_lock(buyer_id)
            # available_funds before refund
            balance_before = buyer_wallet.available_funds

            buyer_wallet = await self._wallet_repo.update_balances(
                wallet_id=buyer_wallet.id,
                available_delta=escrow.amount,
                locked_delta=Decimal("0"),
                escrow_delta=-escrow.amount,
            )
            await self._wallet_repo.create_transaction(
                wallet_id=buyer_wallet.id,
                data={
                    "amount": escrow.amount,
                    "balance_before": balance_before,
                    "balance_after": buyer_wallet.available_funds,
                    "description": f"Refund for cancelled order {order_id}",
                    "transaction_type": TransactionType.REFUND,
                    "direction": TransactionDirection.CREDIT,
                    "balance_type": BalanceType.AVAILABLE,
                    "reference_id": str(escrow.id),
                    "reference_type": ReferenceType.ESCROW,
                },
            )
            await self._escrow_repo.update_status(
                escrow_id=escrow.id,
                status=EscrowStatus.REFUNDED,
                extra_fields={"refunded_at": now},
            )
            order = await self._order_repo.update_status(
                order_id=order_id,
                status=OrderStatus.CANCELLED,
            )
            await self._db.commit()
        except Exception:
            await self._db.rollback()
            raise

        if order.buyer:
            notify_order_cancelled_buyer.delay(
                buyer_email=order.buyer.email,
                buyer_name=(
                    f"{order.buyer.first_name or ''} "
                    f"{order.buyer.last_name or ''}".strip()
                ),
                order_id=str(order_id),
            )
        if order.seller:
            notify_order_cancelled_seller.delay(
                seller_email=order.seller.email,
                seller_name=(
                    f"{order.seller.first_name or ''} "
                    f"{order.seller.last_name or ''}".strip()
                ),
                order_id=str(order_id),
            )

        escrow = await self._escrow_repo.get_by_order_id(order_id)
        return self._build_order_detail(order, escrow)
