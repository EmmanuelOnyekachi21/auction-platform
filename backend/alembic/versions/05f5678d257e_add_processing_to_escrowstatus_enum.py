"""Add PROCESSING value to EscrowStatus enum and drop KYC profile columns.

Revision ID: 05f5678d257e
Revises: 25511f4a4dd1
Create Date: 2026-04-26 15:58:17.279626

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "05f5678d257e"
down_revision: Union[str, Sequence[str], None] = "25511f4a4dd1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("kyc_profiles", "id_number")
    op.drop_column("kyc_profiles", "current_address")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "kyc_profiles",
        sa.Column("current_address", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "kyc_profiles",
        sa.Column("id_number", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
