"""Remove bid_increment column from auctions table.

Revision ID: 25511f4a4dd1
Revises: ce85df6c97df
Create Date: 2026-04-11 16:54:57.706747

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "25511f4a4dd1"
down_revision: Union[str, Sequence[str], None] = "ce85df6c97df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("auctions", "bid_increment")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "auctions",
        sa.Column(
            "bid_increment",
            sa.NUMERIC(precision=10, scale=2),
            autoincrement=False,
            nullable=False,
        ),
    )
