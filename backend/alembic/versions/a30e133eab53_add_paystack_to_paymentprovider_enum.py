"""Add PAYSTACK to PaymentProvider enum via EscrowStatus ALTER TYPE.

Revision ID: a30e133eab53
Revises: d0564e190198
Create Date: 2026-05-02 14:03:47.974703

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a30e133eab53"
down_revision: Union[str, Sequence[str], None] = "d0564e190198"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE escrowstatus ADD VALUE IF NOT EXISTS 'PROCESSING'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
