"""Business logic layer for in-app notifications."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .repository import NotificationRepository


class NotificationService:
    """Service layer for in-app notification operations.

    Attributes:
        _db: The active ``AsyncSession`` shared with the repository.
        _repo: Repository for notification CRUD operations.

    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialise the service with a shared async database session.

        Args:
            db: An active ``AsyncSession`` used for all database operations.

        """
        self._db = db
        self._repo = NotificationRepository(db)

    async def get_notifications(
        self,
        user_id: UUID,
        page: int,
        limit: int,
        unread_only: bool = False,
    ):
        """Return paginated notifications for a user.

        Args:
            user_id: UUID of the user.
            page: Page number (1-indexed).
            limit: Maximum number of notifications per page.
            unread_only: If ``True``, only return unread notifications.

        Returns:
            A ``PaginatedResponse`` of notification records.

        """
        return await self._repo.get_for_user(user_id, page, limit, unread_only)

    async def get_unread_count(self, user_id: UUID) -> int:
        """Return the count of unread notifications for a user.

        Args:
            user_id: UUID of the user.

        Returns:
            Integer count of unread notifications.

        """
        return await self._repo.get_unread_count(user_id)

    async def mark_read(self, notification_id: UUID, user_id: UUID):
        """Mark a single notification as read.

        Args:
            notification_id: UUID of the notification to mark.
            user_id: UUID of the owning user.

        Returns:
            The updated notification, or ``None`` if not found.

        """
        result = await self._repo.mark_read(notification_id, user_id)
        await self._db.commit()
        return result

    async def mark_all_read(self, user_id: UUID) -> None:
        """Mark all notifications as read for a user.

        Args:
            user_id: UUID of the user.

        """
        await self._repo.mark_all_read(user_id)
        await self._db.commit()
