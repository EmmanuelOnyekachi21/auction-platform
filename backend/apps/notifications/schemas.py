"""Pydantic schemas for in-app notification API responses."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from apps.notifications.enums import NotificationReferenceType, NotificationType


class NotificationResponse(BaseModel):
    """Response schema for a single in-app notification.

    Attributes:
        id: Notification UUID.
        title: Short notification title.
        message: Full notification message body.
        notification_type: Enum value for the notification category.
        is_read: Whether the user has read this notification.
        read_at: Timestamp when the notification was read, if applicable.
        reference_id: Optional UUID of the related entity.
        reference_type: Optional type of the related entity.
        created_at: Timestamp when the notification was created.

    """

    id: UUID
    title: str
    message: str
    notification_type: NotificationType
    is_read: bool
    read_at: Optional[datetime] = None
    reference_id: Optional[UUID] = None
    reference_type: Optional[NotificationReferenceType] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnreadCountResponse(BaseModel):
    """Response schema for the unread notification count.

    Attributes:
        count: Number of unread notifications for the user.

    """

    count: int
