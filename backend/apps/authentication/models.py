"""ORM models for the authentication application."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import BaseModel

if TYPE_CHECKING:
    from apps.users.models import User


class PasswordResetToken(BaseModel):
    """A hashed token used for password reset flows.

    Immutable once created — a new token is issued for each
    reset request. The used_at timestamp marks it as consumed.

    Attributes:
        user_id: FK to the User requesting the reset.
        token: Hashed token string, never stored in plain text.
        expires_at: Timestamp after which the token is invalid.
        used_at: Timestamp when the token was consumed, nullable.
    """

    __tablename__ = "password_reset_tokens"

    updated_at = None  # immutable record

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="password_reset_tokens")
