"""Repository for escrow database operations."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.escrow.enums import EscrowStatus
from apps.escrow.models import Escrow


class EscrowRepository:
    """Repository for all escrow-related database operations.

    Attributes:
        _db: The active ``AsyncSession`` injected at construction time.

    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialise the repository with an async database session.

        Args:
            db: An active ``AsyncSession`` to use for all queries.

        """
        self._db = db

    async def create(self, data: dict) -> Escrow:
        """Create a new escrow record.

        Called by the auction settlement task. Uses ``flush()`` not
        ``commit()`` — the settlement task owns the transaction boundary.

        Args:
            data: Dictionary of field values for the ``Escrow`` model.

        Returns:
            The newly created ``Escrow`` instance.

        """
        escrow = Escrow(**data)
        self._db.add(escrow)
        await self._db.flush()
        return escrow

    async def get_by_id(self, escrow_id: UUID) -> Escrow | None:
        """Fetch an escrow record by its UUID primary key.

        Args:
            escrow_id: UUID of the escrow to retrieve.

        Returns:
            The matching ``Escrow`` instance, or ``None`` if not found.

        """
        stmt = select(Escrow).where(Escrow.id == escrow_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_order_id(self, order_id: UUID) -> Escrow | None:
        """Return the escrow for a given order (one order → one escrow).

        Args:
            order_id: UUID of the order.

        Returns:
            The matching ``Escrow``, or ``None`` if not found.

        """
        stmt = select(Escrow).where(Escrow.order_id == order_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        escrow_id: UUID,
        status: EscrowStatus,
        extra_fields: dict | None = None,
    ) -> Escrow | None:
        """Update escrow status and optional extra fields.

        ``extra_fields`` handles ``released_at`` and ``refunded_at``,
        set alongside the status change in the same flush.

        Args:
            escrow_id: UUID of the escrow to update.
            status: The new ``EscrowStatus`` value.
            extra_fields: Optional dictionary of additional fields to set.

        Returns:
            The updated ``Escrow`` instance, or ``None`` if not found.

        """
        escrow = await self.get_by_id(escrow_id)
        if not escrow:
            return None

        escrow.status = status
        if extra_fields:
            for key, value in extra_fields.items():
                setattr(escrow, key, value)

        await self._db.flush()
        return escrow

    async def get_pending_auto_releases(self) -> list[Escrow]:
        """Fetch escrows ready for auto-release.

        Returns ``HOLDING`` escrows whose ``auto_release_at`` has passed.
        Used by the Celery beat task every 5 minutes.

        Returns:
            A list of ``Escrow`` instances ready for release.

        """
        now = datetime.now(timezone.utc)
        stmt = (
            select(Escrow)
            .where(Escrow.status == EscrowStatus.HOLDING)
            .where(Escrow.auto_release_at <= now)
        )
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def claim_for_release(self, escrow_id: UUID) -> bool:
        """Atomically claim an escrow for release.

        Issues a single ``UPDATE … WHERE status = HOLDING`` so that only
        one worker wins the race when multiple workers run simultaneously.
        The winner gets ``rowcount = 1``; all others get ``rowcount = 0``
        and skip the release entirely.

        Args:
            escrow_id: UUID of the escrow to claim.

        Returns:
            ``True`` if successfully claimed, ``False`` if already taken.

        """
        stmt = (
            update(Escrow)
            .where(Escrow.id == escrow_id)
            .where(Escrow.status == EscrowStatus.HOLDING)
            .values(status=EscrowStatus.PROCESSING)
        )
        result = await self._db.execute(stmt)
        return result.rowcount > 0
