"""Add transaction status and bank details.

Revision ID: 5d0cccc84f17
Revises: 744b92bb280c
Create Date: 2026-03-26 09:27:17.600457

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d0cccc84f17"
down_revision: Union[str, Sequence[str], None] = "744b92bb280c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add status column to wallet_transactions with default
    # 'COMPLETED' for existing rows
    op.add_column(
        "wallet_transactions",
        sa.Column(
            "status", sa.String(length=10), nullable=False, server_default="COMPLETED"
        ),
    )
    op.create_index(
        op.f("ix_wallet_transactions_status"),
        "wallet_transactions",
        ["status"],
        unique=False,
    )

    # Add bank details to user_profiles
    op.add_column(
        "user_profiles",
        sa.Column("bank_code", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column("account_number", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column("account_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove bank details from user_profiles
    op.drop_column("user_profiles", "account_name")
    op.drop_column("user_profiles", "account_number")
    op.drop_column("user_profiles", "bank_code")

    # Remove status from wallet_transactions
    op.drop_index(
        op.f("ix_wallet_transactions_status"), table_name="wallet_transactions"
    )
    op.drop_column("wallet_transactions", "status")
