"""Dispute service — handles dispute lifecycle and resolution."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from apps.disputes.enums import DisputeStatus
from apps.disputes.repository import DisputeRepository
from apps.disputes.schemas import (
    DisputeDetailResponse,
    DisputeSummary,
    EvidenceResponse,
    RaiseDisputeRequest,
    ResolveDisputeRequest,
    SubmitEvidenceRequest,
)
from apps.escrow.enums import EscrowStatus
from apps.escrow.repository import EscrowRepository
from apps.notifications.tasks import (
    notify_dispute_raised_seller,
    notify_dispute_resolved_buyer,
    notify_dispute_resolved_seller,
    notify_dispute_under_review,
)
from apps.orders.enums import OrderStatus
from apps.orders.repository import OrderRepository
from apps.orders.service import OrderService
from apps.users.repository import UserRepository
from apps.wallet.enums import (
    BalanceType,
    ReferenceType,
    TransactionDirection,
    TransactionType,
)
from apps.wallet.repository import WalletRepository
from common.exceptions import (
    AlreadyExistsException,
    OrderNotFoundException,
    PermissionDeniedException,
    ValidationException,
)


class DisputeService:
    """Service layer for dispute lifecycle and resolution operations.

    Attributes:
        _db: The active ``AsyncSession`` shared across all repositories.
        _dispute_repo: Repository for dispute CRUD operations.
        _order_repo: Repository for order queries.
        _escrow_repo: Repository for escrow queries.
        _user_repo: Repository for user queries.
        _wallet_repo: Repository for wallet balance operations.

    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialise the service with a shared async database session.

        Args:
            db: An active ``AsyncSession`` used for all database operations.

        """
        self._db = db
        self._dispute_repo = DisputeRepository(db)
        self._order_repo = OrderRepository(db)
        self._escrow_repo = EscrowRepository(db)
        self._user_repo = UserRepository(db)
        self._wallet_repo = WalletRepository(db)

    def _build_dispute_detail(self, dispute) -> DisputeDetailResponse:
        """Serialise a ``Dispute`` ORM object into a ``DisputeDetailResponse``.

        Args:
            dispute: The ``Dispute`` ORM instance to serialise.

        Returns:
            A ``DisputeDetailResponse`` Pydantic model.

        """
        return DisputeDetailResponse.model_validate(dispute)

    async def raise_dispute(
        self,
        buyer_id: UUID,
        order_id: UUID,
        data: RaiseDisputeRequest,
    ) -> DisputeDetailResponse:
        """Open a new dispute on an order.

        Args:
            buyer_id: UUID of the buyer raising the dispute.
            order_id: UUID of the order being disputed.
            data: Validated dispute request with title and description.

        Returns:
            The newly created ``DisputeDetailResponse``.

        Raises:
            OrderNotFoundException: If the order does not exist.
            PermissionDeniedException: If the caller is not the buyer.
            ValidationException: If the order status does not allow disputes.
            AlreadyExistsException: If a dispute already exists for the order.

        """
        order = await self._order_repo.get_by_id(order_id)
        if not order:
            raise OrderNotFoundException()
        if order.buyer_id != buyer_id:
            raise PermissionDeniedException()
        if order.status not in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            raise ValidationException(
                message="You can only raise a dispute after the seller has shipped"
            )
        existing = await self._dispute_repo.get_by_order_id(order_id)
        if existing:
            raise AlreadyExistsException(
                message="A dispute already exists for this order"
            )

        now = datetime.now(timezone.utc)
        try:
            dispute = await self._dispute_repo.create(
                {
                    "order_id": order_id,
                    "auction_id": order.auction_id,
                    "raised_by_id": buyer_id,
                    "against_id": order.seller_id,
                    "title": data.title,
                    "description": data.description,
                    "status": DisputeStatus.OPEN,
                }
            )
            await self._order_repo.update_status(
                order_id=order_id,
                status=OrderStatus.DISPUTED,
                extra_fields={"dispute_raised_at": now, "dispute_id": dispute.id},
            )
            await self._db.commit()
        except Exception:
            await self._db.rollback()
            raise

        if order.seller:
            notify_dispute_raised_seller.delay(
                seller_email=order.seller.email,
                seller_name=(
                    f"{order.seller.first_name or ''} "
                    f"{order.seller.last_name or ''}".strip()
                ),
                order_id=str(order_id),
                dispute_id=str(dispute.id),
            )
        dispute = await self._dispute_repo.get_by_id(dispute.id)
        return self._build_dispute_detail(dispute)

    async def submit_evidence(
        self,
        user_id: UUID,
        dispute_id: UUID,
        data: SubmitEvidenceRequest,
    ) -> EvidenceResponse:
        """Submit evidence to an open dispute.

        Args:
            user_id: UUID of the user submitting evidence.
            dispute_id: UUID of the dispute.
            data: Validated evidence request with URL, type, and description.

        Returns:
            The created ``EvidenceResponse``.

        Raises:
            ValidationException: If the dispute is not found or already resolved.
            PermissionDeniedException: If the caller is not a party to the dispute.

        """
        dispute = await self._dispute_repo.get_by_id(dispute_id)
        if not dispute:
            raise ValidationException(message="Dispute not found")
        if user_id not in (dispute.raised_by_id, dispute.against_id):
            raise PermissionDeniedException()
        if dispute.status not in (DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW):
            raise ValidationException(
                message="Cannot submit evidence on a resolved dispute"
            )

        evidence = await self._dispute_repo.add_evidence(
            dispute_id=dispute_id,
            data={
                "uploaded_by_id": user_id,
                "url": str(data.url),
                "file_type": data.file_type,
                "description": data.description,
            },
        )
        await self._db.commit()
        return EvidenceResponse.model_validate(evidence)

    async def get_dispute(
        self, user_id: UUID, dispute_id: UUID
    ) -> DisputeDetailResponse:
        """Return dispute detail for a party or admin.

        Args:
            user_id: UUID of the requesting user.
            dispute_id: UUID of the dispute.

        Returns:
            The ``DisputeDetailResponse`` for the dispute.

        Raises:
            ValidationException: If the dispute is not found.
            PermissionDeniedException: If the caller is not a party or admin.

        """
        user = await self._user_repo.get_by_id(user_id)
        dispute = await self._dispute_repo.get_by_id(dispute_id)
        if not dispute:
            raise ValidationException(message="Dispute not found")

        is_admin = user and user.role.value in ("ADMIN", "SUPERUSER")
        is_party = user_id in (dispute.raised_by_id, dispute.against_id)
        if not is_admin and not is_party:
            raise PermissionDeniedException()

        return self._build_dispute_detail(dispute)

    async def resolve_dispute(
        self,
        admin_id: UUID,
        dispute_id: UUID,
        data: ResolveDisputeRequest,
    ) -> DisputeDetailResponse:
        """Admin resolves a dispute in favour of buyer or seller.

        Args:
            admin_id: UUID of the admin resolving the dispute.
            dispute_id: UUID of the dispute to resolve.
            data: Validated resolution request with outcome and notes.

        Returns:
            The updated ``DisputeDetailResponse``.

        Raises:
            ValidationException: If the dispute is not found or already resolved.
            PermissionDeniedException: If the caller is not an admin.
            OrderNotFoundException: If the associated order is not found.

        """
        dispute = await self._dispute_repo.get_by_id(dispute_id)
        if not dispute:
            raise ValidationException(message="Dispute not found")

        admin = await self._user_repo.get_by_id(admin_id)
        if not admin or admin.role.value not in ("ADMIN", "SUPERUSER"):
            raise PermissionDeniedException()

        if dispute.status not in (DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW):
            raise ValidationException(message="Dispute is already resolved")

        order = await self._order_repo.get_by_id(dispute.order_id)
        if not order:
            raise OrderNotFoundException()

        escrow = await self._escrow_repo.get_by_order_id(dispute.order_id)
        now = datetime.now(timezone.utc)

        try:
            if data.resolution == "in_favour_of_buyer":
                buyer_wallet = await self._wallet_repo.get_by_user_id_with_lock(
                    order.buyer_id
                )
                balance_before = buyer_wallet.escrow_funds
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
                        "description": "Dispute resolved in buyer's favour",
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
                await self._order_repo.update_status(order.id, OrderStatus.REFUNDED)
            else:
                order_service = OrderService(self._db)
                await order_service._release_escrow_to_seller(escrow.id)
                await self._order_repo.update_status(order.id, OrderStatus.COMPLETED)

            await self._dispute_repo.update_status(
                dispute_id=dispute_id,
                status=DisputeStatus.RESOLVED,
                extra_fields={
                    "resolution": data.resolution_notes,
                    "resolved_by_id": admin_id,
                    "resolved_at": now,
                },
            )
            await self._db.commit()

        except Exception:
            await self._db.rollback()
            raise

        buyer_favour = data.resolution == "in_favour_of_buyer"
        if order.buyer:
            notify_dispute_resolved_buyer.delay(
                buyer_email=order.buyer.email,
                buyer_name=(
                    f"{order.buyer.first_name or ''} "
                    f"{order.buyer.last_name or ''}".strip()
                ),
                dispute_id=str(dispute_id),
                in_favour=buyer_favour,
            )
        if order.seller:
            notify_dispute_resolved_seller.delay(
                seller_email=order.seller.email,
                seller_name=(
                    f"{order.seller.first_name or ''} "
                    f"{order.seller.last_name or ''}".strip()
                ),
                dispute_id=str(dispute_id),
                in_favour=not buyer_favour,
            )

        dispute = await self._dispute_repo.get_by_id(dispute_id)
        return self._build_dispute_detail(dispute)

    async def mark_under_review(
        self, admin_id: UUID, dispute_id: UUID
    ) -> DisputeDetailResponse:
        """Admin marks a dispute as under review.

        Args:
            admin_id: UUID of the admin performing the action.
            dispute_id: UUID of the dispute to mark.

        Returns:
            The updated ``DisputeDetailResponse``.

        Raises:
            ValidationException: If the dispute is not found or not OPEN.
            PermissionDeniedException: If the caller is not an admin.

        """
        dispute = await self._dispute_repo.get_by_id(dispute_id)
        if not dispute:
            raise ValidationException(message="Dispute not found")
        admin = await self._user_repo.get_by_id(admin_id)
        if not admin or admin.role.value not in ("ADMIN", "SUPERUSER"):
            raise PermissionDeniedException()
        if dispute.status != DisputeStatus.OPEN:
            raise ValidationException(message="Dispute is not in OPEN status")

        await self._dispute_repo.update_status(
            dispute_id=dispute_id, status=DisputeStatus.UNDER_REVIEW
        )
        await self._db.commit()
        dispute = await self._dispute_repo.get_by_id(dispute_id)

        for party in (dispute.raised_by, dispute.against):
            if party:
                name = (
                    f"{party.first_name or ''} {party.last_name or ''}".strip()
                    or "User"
                )
                notify_dispute_under_review.delay(
                    email=party.email,
                    name=name,
                    dispute_id=str(dispute_id),
                )

        return self._build_dispute_detail(dispute)

    async def get_open_disputes(self, page: int, limit: int):
        """Return paginated open disputes for admin review.

        Args:
            page: Page number (1-indexed).
            limit: Maximum number of disputes per page.

        Returns:
            A ``PaginatedResponse`` of ``DisputeSummary`` objects.

        """
        result = await self._dispute_repo.get_open_disputes(page, limit)
        result.data = [DisputeSummary.model_validate(d) for d in result.data]
        return result
