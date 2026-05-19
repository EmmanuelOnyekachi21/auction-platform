"""Update sellertype enum to INDIVIDUAL and BUSINESS

Replaces legacy CASUAL/RETAIL/WHOLESALE values with INDIVIDUAL/BUSINESS.
Since the DB is fresh (dropped and recreated), this migration recreates
the enum with the correct values by dropping the old type and creating
the new one before altering the column.

Revision ID: 3a7f2e1d9c84
Revises: e914f9620d06
Create Date: 2026-05-18 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3a7f2e1d9c84"
down_revision: Union[str, Sequence[str], None] = "e914f9620d06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

old_sellertype = sa.Enum("CASUAL", "RETAIL", "WHOLESALE", name="sellertype")
new_sellertype = sa.Enum("INDIVIDUAL", "BUSINESS", name="sellertype")


def upgrade() -> None:
    """Replace sellertype enum values with INDIVIDUAL and BUSINESS."""
    # 1. Drop the column that uses the old enum
    op.drop_column("seller_profiles", "seller_type")

    # 2. Drop the old enum type
    old_sellertype.drop(op.get_bind(), checkfirst=True)

    # 3. Create the new enum type
    new_sellertype.create(op.get_bind(), checkfirst=True)

    # 4. Re-add the column with the new enum
    op.add_column(
        "seller_profiles",
        sa.Column(
            "seller_type",
            sa.Enum("INDIVIDUAL", "BUSINESS", name="sellertype"),
            nullable=False,
            server_default="INDIVIDUAL",
        ),
    )
    # Remove server_default — model handles new rows going forward
    op.alter_column("seller_profiles", "seller_type", server_default=None)


def downgrade() -> None:
    """Restore legacy sellertype enum values."""
    op.drop_column("seller_profiles", "seller_type")
    new_sellertype.drop(op.get_bind(), checkfirst=True)
    old_sellertype.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "seller_profiles",
        sa.Column(
            "seller_type",
            sa.Enum("CASUAL", "RETAIL", "WHOLESALE", name="sellertype"),
            nullable=False,
            server_default="CASUAL",
        ),
    )
    op.alter_column("seller_profiles", "seller_type", server_default=None)
