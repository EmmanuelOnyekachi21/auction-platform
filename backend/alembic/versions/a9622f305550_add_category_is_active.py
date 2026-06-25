"""Add is_active column to categories table.

Revision ID: a9622f305550
Revises: a30e133eab53
Create Date: 2026-05-05 05:33:18.564813

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9622f305550"
down_revision: Union[str, Sequence[str], None] = "a30e133eab53"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default='true' backfills existing rows before NOT NULL is enforced.
    op.add_column(
        "categories",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    # Remove server_default after backfill — the model default handles new rows.
    op.alter_column("categories", "is_active", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("categories", "is_active")
