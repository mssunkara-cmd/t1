"""add region defaults table

Revision ID: 20260223_0008
Revises: 20260223_0007
Create Date: 2026-02-23 03:05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260223_0008"
down_revision: str | None = "20260223_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "region_defaults",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=False),
        sa.Column("default_admin_user_id", sa.Integer(), nullable=True),
        sa.Column("default_ambassador_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["region_id"], ["regions.region_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["default_admin_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["default_ambassador_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("region_id", name="uq_region_defaults_region_id"),
    )


def downgrade() -> None:
    op.drop_table("region_defaults")
