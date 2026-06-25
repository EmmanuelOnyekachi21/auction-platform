"""add_settlement_status_values_to_auctionstatus

Revision ID: a1b2c3d4e5f6
Revises: 9bb54b826f56
Create Date: 2026-04-02 00:00:00.000000

"""

from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "9bb54b826f56"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE auctionstatus ADD VALUE IF NOT EXISTS 'SETTLEMENT_IN_PROGRESS'"
    )
    op.execute("ALTER TYPE auctionstatus ADD VALUE IF NOT EXISTS 'SETTLEMENT_FAILED'")


def downgrade() -> None:
    # Postgres does not support removing enum values directly
    pass
