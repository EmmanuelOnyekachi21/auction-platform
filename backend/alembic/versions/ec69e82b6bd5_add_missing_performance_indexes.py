"""add_missing_performance_indexes

Revision ID: ec69e82b6bd5
Revises: 195a1220d3fa
Create Date: 2026-06-20 11:35:34.883109

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ec69e82b6bd5"
down_revision: Union[str, Sequence[str], None] = "195a1220d3fa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_wallet_transactions_created_at",
        "wallet_transactions",
        ["created_at"],
    )
    op.create_index(
        "ix_bids_status",
        "bids",
        ["status"],
    )
    op.create_index(
        "ix_escrows_status_auto_release",
        "escrows",
        ["status", "auto_release_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_escrows_status_auto_release", table_name="escrows")
    op.drop_index("ix_bids_status", table_name="bids")
    op.drop_index("ix_wallet_transactions_created_at", table_name="wallet_transactions")
