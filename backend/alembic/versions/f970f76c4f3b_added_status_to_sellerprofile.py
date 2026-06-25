"""Add verification_status column to seller_profiles table.

Revision ID: f970f76c4f3b
Revises: a9622f305550
Create Date: 2026-05-05 11:34:50.355351

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f970f76c4f3b"
down_revision: Union[str, Sequence[str], None] = "a9622f305550"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the PostgreSQL enum type explicitly before using it.
    seller_status_enum = sa.Enum(
        "PENDING", "APPROVED", "REJECTED", name="sellerverificationstatus"
    )
    seller_status_enum.create(op.get_bind(), checkfirst=True)

    # server_default='PENDING' backfills existing rows before NOT NULL is enforced.
    op.add_column(
        "seller_profiles",
        sa.Column(
            "verification_status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", name="sellerverificationstatus"),
            nullable=False,
            server_default="PENDING",
        ),
    )
    # Remove server_default — the model default handles new rows going forward.
    op.alter_column("seller_profiles", "verification_status", server_default=None)
    op.create_index(
        op.f("ix_seller_profiles_verification_status"),
        "seller_profiles",
        ["verification_status"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_seller_profiles_verification_status"),
        table_name="seller_profiles",
    )
    op.drop_column("seller_profiles", "verification_status")
    sa.Enum(name="sellerverificationstatus").drop(op.get_bind(), checkfirst=True)
