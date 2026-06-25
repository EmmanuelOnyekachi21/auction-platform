"""Repository for dispute database operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.disputes.enums import DisputeStatus
from apps.disputes.models import Dispute, DisputeEvidence
from common.pagination import paginate


class DisputeRepository:
    """Repository for all dispute-related database operations.

    Attributes:
        _db: The active ``AsyncSession`` injected at construction time.

    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialise the repository with an async database session.

        Args:
            db: An active ``AsyncSession`` to use for all queries.

        """
        self._db = db

    async def create(self, data: dict) -> Dispute:
        """Create a new dispute record.

        Uses ``flush()`` not ``commit()`` — the service controls the
        transaction boundary.

        Args:
            data: Dictionary of field values for the ``Dispute`` model.

        Returns:
            The newly created ``Dispute`` instance.

        """
        dispute = Dispute(**data)
        self._db.add(dispute)
        await self._db.flush()
        return dispute

    async def get_by_id(self, dispute_id: UUID) -> Dispute | None:
        """Load a dispute with all relationships eagerly loaded.

        Evidence is always needed when viewing a dispute, so it is loaded
        upfront to avoid lazy-loading errors in an async context.

        Args:
            dispute_id: UUID of the dispute to retrieve.

        Returns:
            The matching ``Dispute`` instance, or ``None`` if not found.

        """
        stmt = (
            select(Dispute)
            .where(Dispute.id == dispute_id)
            .options(
                selectinload(Dispute.evidence).selectinload(
                    DisputeEvidence.uploaded_by
                ),
                selectinload(Dispute.raised_by),
                selectinload(Dispute.against),
                selectinload(Dispute.resolved_by),
                selectinload(Dispute.order),
            )
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_order_id(self, order_id: UUID) -> Dispute | None:
        """Return the dispute for a given order (one order → one dispute).

        Args:
            order_id: UUID of the order.

        Returns:
            The matching ``Dispute``, or ``None`` if no dispute exists.

        """
        stmt = select(Dispute).where(Dispute.order_id == order_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def add_evidence(self, dispute_id: UUID, data: dict) -> DisputeEvidence:
        """Add a piece of evidence to a dispute.

        Evidence is immutable once submitted — no update method exists.
        The model sets ``updated_at = None`` to enforce this.

        Args:
            dispute_id: UUID of the parent dispute.
            data: Dictionary of field values for the ``DisputeEvidence`` model.

        Returns:
            The newly created ``DisputeEvidence`` instance.

        """
        evidence = DisputeEvidence(dispute_id=dispute_id, **data)
        self._db.add(evidence)
        await self._db.flush()
        return evidence

    async def update_status(
        self,
        dispute_id: UUID,
        status: DisputeStatus,
        extra_fields: dict | None = None,
    ) -> Dispute | None:
        """Update dispute status and optional resolution fields.

        ``extra_fields`` handles ``resolution``, ``resolved_by_id``, and
        ``resolved_at`` — all set together when an admin resolves the dispute.

        Args:
            dispute_id: UUID of the dispute to update.
            status: The new ``DisputeStatus`` value.
            extra_fields: Optional dictionary of additional fields to set.

        Returns:
            The updated ``Dispute`` instance, or ``None`` if not found.

        """
        dispute = await self.get_by_id(dispute_id)
        if not dispute:
            return None

        dispute.status = status
        if extra_fields:
            for key, value in extra_fields.items():
                setattr(dispute, key, value)

        await self._db.flush()
        return dispute

    async def get_open_disputes(self, page: int, limit: int):
        """Return paginated open disputes for admin review, oldest first.

        Returns ``OPEN`` and ``UNDER_REVIEW`` disputes ordered by
        ``created_at`` ascending to ensure fair FIFO processing.

        Args:
            page: Page number (1-indexed).
            limit: Maximum number of disputes per page.

        Returns:
            A ``PaginatedResponse`` containing the dispute records.

        """
        stmt = (
            select(Dispute)
            .where(Dispute.status.in_([DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW]))
            .options(
                selectinload(Dispute.raised_by),
                selectinload(Dispute.against),
            )
            .order_by(Dispute.created_at.asc())
        )
        return await paginate(stmt, page, limit, self._db)
