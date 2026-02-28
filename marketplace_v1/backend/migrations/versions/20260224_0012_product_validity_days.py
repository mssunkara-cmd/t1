"""add product validity days

Revision ID: 20260224_0012
Revises: 20260224_0011
Create Date: 2026-02-24 13:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260224_0012"
down_revision: str | None = "20260224_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("validity_days", sa.Integer(), nullable=False, server_default="365"),
    )
    op.alter_column("products", "validity_days", server_default=None)


def downgrade() -> None:
    op.drop_column("products", "validity_days")
