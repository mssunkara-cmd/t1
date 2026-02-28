"""add reserved quantity to inventory tables

Revision ID: 20260228_0022
Revises: 20260228_0021
Create Date: 2026-02-28 21:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260228_0022"
down_revision: str | None = "20260228_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("inventory_items") as batch_op:
        batch_op.add_column(sa.Column("reserved_quantity", sa.Integer(), nullable=False, server_default="0"))
        batch_op.alter_column("reserved_quantity", server_default=None)

    with op.batch_alter_table("fresh_produce_inventory") as batch_op:
        batch_op.add_column(sa.Column("reserved_quantity", sa.Integer(), nullable=False, server_default="0"))
        batch_op.alter_column("reserved_quantity", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("fresh_produce_inventory") as batch_op:
        batch_op.drop_column("reserved_quantity")

    with op.batch_alter_table("inventory_items") as batch_op:
        batch_op.drop_column("reserved_quantity")
