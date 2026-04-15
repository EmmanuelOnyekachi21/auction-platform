"""Add bid_increment_tiers table.

Revision ID: ce85df6c97df
Revises: 0e7589e1c450
Create Date: 2026-04-11 15:39:05.598881

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ce85df6c97df"
down_revision: Union[str, Sequence[str], None] = "0e7589e1c450"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "bid_increment_tiers",
        sa.Column("min_value", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("max_value", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("increment", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("increment > 0", name="ck_bid_tier_increment_positive"),
        sa.CheckConstraint("min_value >= 0", name="ck_bid_tier_min_value_non_negative"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("bid_increment_tiers")
