"""Add public_id column to dispute_evidence table.

Revision ID: d0564e190198
Revises: 05f5678d257e
Create Date: 2026-05-01 13:39:36.752316

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d0564e190198"
down_revision: Union[str, Sequence[str], None] = "05f5678d257e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "dispute_evidence",
        sa.Column("public_id", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("dispute_evidence", "public_id")
