"""add product types table and seed defaults

Revision ID: 20260228_0016
Revises: 20260224_0015
Create Date: 2026-02-28 12:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260228_0016"
down_revision: str | None = "20260224_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_type", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_type", name="uq_product_types_product_type"),
    )

    op.execute(
        """
        INSERT INTO product_types (product_type)
        VALUES ('Fresh_produce'), ('Staple')
        ON CONFLICT (product_type) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO product_types (product_type)
        SELECT DISTINCT TRIM(product_type)
        FROM products
        WHERE product_type IS NOT NULL AND TRIM(product_type) <> ''
        ON CONFLICT (product_type) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("product_types")
