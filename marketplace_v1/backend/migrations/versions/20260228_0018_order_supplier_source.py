"""allow supplier-backed orders

Revision ID: 20260228_0018
Revises: 20260228_0017
Create Date: 2026-02-28 18:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260228_0018"
down_revision: str | None = "20260228_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.alter_column("seller_id", existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column("supplier_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_orders_supplier_id",
            "suppliers",
            ["supplier_id"],
            ["supplier_id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_constraint("fk_orders_supplier_id", type_="foreignkey")
        batch_op.drop_column("supplier_id")
        batch_op.alter_column("seller_id", existing_type=sa.Integer(), nullable=False)
