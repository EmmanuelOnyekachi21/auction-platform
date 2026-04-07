"""Add ended_reserve_not_met auction status.

Revision ID: 15dffe28db1b
Revises: a1b2c3d4e5f6
Create Date: 2026-04-06 04:30:56.400093

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "15dffe28db1b"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TYPE auctionstatus ADD VALUE IF NOT EXISTS 'ENDED_RESERVE_NOT_MET'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # PostgreSQL does not support removing values from an ENUM type.
    # To fully revert, the type would need to be recreated — which is
    # destructive if rows reference the value. This is intentionally a no-op.
    pass
