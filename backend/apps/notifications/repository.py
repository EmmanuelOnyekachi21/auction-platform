"""Data access layer for in-app notification operations."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.notifications.models import Notification
from common.pagination import paginate


class NotificationRepository:
    """Repository for all notification-related database operations.

    Attributes:
        _db: The active ``AsyncSession`` injected at construction time.

    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialise the repository with an async database session.

        Args:
            db: An active ``AsyncSession`` to use for all queries.

        """
        self._db = db

    async def create(
        self,
        user_id: UUID,
        title: str,
        message: str,
        notification_type: str,
        reference_id: UUID | None = None,
        reference_type: str | None = None,
    ) -> Notification:
        """Create and persist a new in-app notification.

        Args:
            user_id: UUID of the recipient user.
            title: Short notification title.
            message: Full notification message body.
            notification_type: Enum value string for the notification type.
            reference_id: Optional UUID of the related entity.
            reference_type: Optional type string of the related entity.

        Returns:
            The newly created ``Notification`` instance.

        """
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            reference_id=reference_id,
            reference_type=reference_type,
        )
        self._db.add(notification)
        await self._db.flush()
        return notification

    async def get_for_user(
        self,
        user_id: UUID,
        page: int,
        limit: int,
        unread_only: bool = False,
    ):
        """Return paginated notifications for a user, newest first.

        Args:
            user_id: UUID of the user.
            page: Page number (1-indexed).
            limit: Maximum number of notifications per page.
            unread_only: If ``True``, only return unread notifications.

        Returns:
            A ``PaginatedResponse`` containing the notification records.

        """
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(~Notification.is_read)
        stmt = stmt.order_by(Notification.created_at.desc())
        return await paginate(stmt, page, limit, self._db)

    async def get_unread_count(self, user_id: UUID) -> int:
        """Return the number of unread notifications for a user.

        Args:
            user_id: UUID of the user.

        Returns:
            Integer count of unread notifications.

        """
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id)
            .where(~Notification.is_read)
        )
        result = await self._db.execute(stmt)
        return result.scalar()

    async def mark_read(
        self, notification_id: UUID, user_id: UUID
    ) -> Notification | None:
        """Mark a single notification as read.

        Args:
            notification_id: UUID of the notification to mark.
            user_id: UUID of the owning user (for ownership check).

        Returns:
            The updated ``Notification``, or ``None`` if not found.

        """
        stmt = (
            select(Notification)
            .where(Notification.id == notification_id)
            .where(Notification.user_id == user_id)
        )
        result = await self._db.execute(stmt)
        notification = result.scalar_one_or_none()
        if notification:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            await self._db.flush()
        return notification

    async def mark_all_read(self, user_id: UUID) -> None:
        """Mark all unread notifications as read for a user.

        Args:
            user_id: UUID of the user whose notifications to mark.

        """
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .where(~Notification.is_read)
        )
        results = await self._db.execute(stmt)
        notifications = results.scalars().all()

        for notification in notifications:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)

        await self._db.flush()
