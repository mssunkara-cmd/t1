"""add order groups for grouped checkout

Revision ID: 20260228_0021
Revises: 20260228_0020
Create Date: 2026-02-28 21:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260228_0021"
down_revision: str | None = "20260228_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "order_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_number", sa.String(length=64), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_number"),
    )
    op.create_index(op.f("ix_order_groups_group_number"), "order_groups", ["group_number"], unique=False)

    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("order_group_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_orders_order_group_id"), ["order_group_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_orders_order_group_id",
            "order_groups",
            ["order_group_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_constraint("fk_orders_order_group_id", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_orders_order_group_id"))
        batch_op.drop_column("order_group_id")

    op.drop_index(op.f("ix_order_groups_group_number"), table_name="order_groups")
    op.drop_table("order_groups")
