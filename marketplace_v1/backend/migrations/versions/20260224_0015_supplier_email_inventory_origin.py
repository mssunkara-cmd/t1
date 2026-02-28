"""supplier email and inventory origin/source fields

Revision ID: 20260224_0015
Revises: 20260224_0014
Create Date: 2026-02-24 20:05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260224_0015"
down_revision: str | None = "20260224_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("suppliers", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column(
        "procurement_orders",
        sa.Column("pushed_to_inventory", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.alter_column("procurement_orders", "pushed_to_inventory", server_default=None)

    with op.batch_alter_table("inventory_items") as batch_op:
        batch_op.add_column(sa.Column("supplier_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("origin_type", sa.String(length=20), nullable=False, server_default="seller_direct")
        )
        batch_op.add_column(sa.Column("origin", sa.String(length=20), nullable=True))
        batch_op.add_column(
            sa.Column("entry_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"))
        )
        batch_op.create_foreign_key(
            "fk_inventory_items_supplier_id", "suppliers", ["supplier_id"], ["supplier_id"], ondelete="RESTRICT"
        )
        batch_op.alter_column("seller_id", existing_type=sa.Integer(), nullable=True)

    op.execute("UPDATE inventory_items SET origin_type='seller_direct' WHERE origin_type IS NULL")
    op.execute("UPDATE inventory_items SET origin='seller_direct' WHERE origin IS NULL")
    op.execute("UPDATE inventory_items SET entry_date=updated_at WHERE entry_date IS NULL")

    with op.batch_alter_table("inventory_items") as batch_op:
        batch_op.alter_column("origin_type", server_default=None)
        batch_op.alter_column("entry_date", server_default=None)
        batch_op.create_check_constraint(
            "ck_inventory_items_origin_type", "origin_type IN ('seller_direct', 'procurement')"
        )
        batch_op.create_check_constraint(
            "ck_inventory_items_origin", "origin IN ('seller_direct', 'primary', 'secondary', 'reseller')"
        )


def downgrade() -> None:
    with op.batch_alter_table("inventory_items") as batch_op:
        batch_op.drop_constraint("ck_inventory_items_origin", type_="check")
        batch_op.drop_constraint("ck_inventory_items_origin_type", type_="check")
        batch_op.alter_column("seller_id", existing_type=sa.Integer(), nullable=False)
        batch_op.drop_constraint("fk_inventory_items_supplier_id", type_="foreignkey")
        batch_op.drop_column("entry_date")
        batch_op.drop_column("origin")
        batch_op.drop_column("origin_type")
        batch_op.drop_column("supplier_id")

    op.drop_column("suppliers", "email")
    op.drop_column("procurement_orders", "pushed_to_inventory")
