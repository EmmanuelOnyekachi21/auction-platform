"""ORM models for the notifications application."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import BaseModel

from .enums import NotificationReferenceType, NotificationType

if TYPE_CHECKING:
    from apps.users.models import User


class Notification(BaseModel):
    """A notification sent to a user about a platform event.

    Attributes:
        user_id: FK to the recipient User.
        title: Short notification heading.
        message: Full notification body.
        notification_type: Category of the notification.
        is_read: Whether the user has read this notification.
        read_at: Timestamp when the notification was read.
        reference_id: UUID of the related entity, nullable.
        reference_type: Type of the related entity, nullable.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        Index(
            "ix_notifications_user_unread",
            "user_id",
            "is_read",
            postgresql_where=Text("is_read = false"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[NotificationType] = mapped_column(nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    reference_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    reference_type: Mapped[NotificationReferenceType] = mapped_column(nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="notifications")
