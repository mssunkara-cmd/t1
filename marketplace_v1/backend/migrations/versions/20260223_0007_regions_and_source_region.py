"""add regions table and seller source region

Revision ID: 20260223_0007
Revises: 20260223_0006
Create Date: 2026-02-23 02:45:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260223_0007"
down_revision: str | None = "20260223_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "regions",
        sa.Column("region_id", sa.Integer(), nullable=False),
        sa.Column("region_name", sa.String(length=150), nullable=False),
        sa.Column("region_description", sa.String(length=1500), nullable=True),
        sa.Column("region_type", sa.String(length=20), nullable=False),
        sa.CheckConstraint("region_type IN ('source', 'distribution')", name="ck_regions_type"),
        sa.PrimaryKeyConstraint("region_id"),
        sa.UniqueConstraint("region_name", "region_type", name="uq_regions_name_type"),
    )

    op.add_column("users", sa.Column("source_region_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_users_source_region_id",
        "users",
        "regions",
        ["source_region_id"],
        ["region_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_source_region_id", "users", type_="foreignkey")
    op.drop_column("users", "source_region_id")
    op.drop_table("regions")
