"""add order item inventory references

Revision ID: 20260228_0019
Revises: 20260228_0018
Create Date: 2026-02-28 19:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260228_0019"
down_revision: str | None = "20260228_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("order_items") as batch_op:
        batch_op.add_column(sa.Column("product_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("inventory_kind", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("source_inventory_item_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_order_items_product_id",
            "products",
            ["product_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_check_constraint(
            "ck_order_items_inventory_kind",
            "inventory_kind IN ('regular', 'fresh_produce') OR inventory_kind IS NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("order_items") as batch_op:
        batch_op.drop_constraint("ck_order_items_inventory_kind", type_="check")
        batch_op.drop_constraint("fk_order_items_product_id", type_="foreignkey")
        batch_op.drop_column("source_inventory_item_id")
        batch_op.drop_column("inventory_kind")
        batch_op.drop_column("product_id")
