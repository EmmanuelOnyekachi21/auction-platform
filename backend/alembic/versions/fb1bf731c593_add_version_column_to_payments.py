"""add_version_column_to_payments

Revision ID: fb1bf731c593
Revises: 6792719e524a
Create Date: 2026-03-25 13:16:50.507125

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fb1bf731c593"
down_revision: Union[str, Sequence[str], None] = "6792719e524a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add version column to payments table for optimistic locking
    op.add_column(
        "payments",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove version column from payments table
    op.drop_column("payments", "version")
