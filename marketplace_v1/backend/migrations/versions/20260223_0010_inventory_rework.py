"""rework inventory table with product and seller references

Revision ID: 20260223_0010
Revises: 20260223_0009
Create Date: 2026-02-23 04:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260223_0010"
down_revision: str | None = "20260223_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Recreate inventory_items for new relational structure.
    op.drop_index(op.f("ix_inventory_items_sku"), table_name="inventory_items")
    op.drop_table("inventory_items")

    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("created_by_admin_user_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_inventory_items_product_id", "inventory_items", ["product_id"], unique=False)
    op.create_index("ix_inventory_items_seller_id", "inventory_items", ["seller_id"], unique=False)
    op.create_index(
        "ix_inventory_items_created_by_admin_user_id",
        "inventory_items",
        ["created_by_admin_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_items_created_by_admin_user_id", table_name="inventory_items")
    op.drop_index("ix_inventory_items_seller_id", table_name="inventory_items")
    op.drop_index("ix_inventory_items_product_id", table_name="inventory_items")
    op.drop_table("inventory_items")

    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku"),
    )
    op.create_index(op.f("ix_inventory_items_sku"), "inventory_items", ["sku"], unique=False)
