"""add price per unit to inventory tables

Revision ID: 20260228_0020
Revises: 20260228_0019
Create Date: 2026-02-28 20:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260228_0020"
down_revision: str | None = "20260228_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("inventory_items") as batch_op:
        batch_op.add_column(sa.Column("price_per_unit", sa.Numeric(12, 2), nullable=False, server_default="0.00"))
        batch_op.alter_column("price_per_unit", server_default=None)

    with op.batch_alter_table("fresh_produce_inventory") as batch_op:
        batch_op.add_column(sa.Column("price_per_unit", sa.Numeric(12, 2), nullable=False, server_default="0.00"))
        batch_op.alter_column("price_per_unit", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("fresh_produce_inventory") as batch_op:
        batch_op.drop_column("price_per_unit")

    with op.batch_alter_table("inventory_items") as batch_op:
        batch_op.drop_column("price_per_unit")
