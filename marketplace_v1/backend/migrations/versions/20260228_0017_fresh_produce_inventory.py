"""add fresh produce inventory table

Revision ID: 20260228_0017
Revises: 20260228_0016
Create Date: 2026-02-28 15:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260228_0017"
down_revision: str | None = "20260228_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fresh_produce_inventory",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=True),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("origin_type", sa.String(length=20), nullable=False),
        sa.Column("origin", sa.String(length=20), nullable=True),
        sa.Column("entry_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_admin_user_id", sa.Integer(), nullable=False),
        sa.Column("estimated_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.supplier_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "origin_type IN ('seller_direct', 'procurement')",
            name="ck_fresh_produce_inventory_origin_type",
        ),
        sa.CheckConstraint(
            "origin IN ('seller_direct', 'primary', 'secondary', 'reseller')",
            name="ck_fresh_produce_inventory_origin",
        ),
    )
    op.alter_column("fresh_produce_inventory", "estimated_quantity", server_default=None)


def downgrade() -> None:
    op.drop_table("fresh_produce_inventory")
