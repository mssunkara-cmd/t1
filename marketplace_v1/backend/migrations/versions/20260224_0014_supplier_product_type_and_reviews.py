"""supplier product type and procurement reviews

Revision ID: 20260224_0014
Revises: 20260224_0013
Create Date: 2026-02-24 18:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260224_0014"
down_revision: str | None = "20260224_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "supplier_products",
        sa.Column("supplier_type", sa.String(length=20), nullable=False, server_default="primary"),
    )
    op.create_check_constraint(
        "ck_supplier_products_type",
        "supplier_products",
        "supplier_type IN ('primary', 'secondary', 'reseller')",
    )

    op.execute(
        """
        UPDATE supplier_products sp
        SET supplier_type = s.supplier_type
        FROM suppliers s
        WHERE sp.supplier_id = s.supplier_id
        """
    )

    op.alter_column("supplier_products", "supplier_type", server_default=None)
    op.drop_constraint("ck_suppliers_type", "suppliers", type_="check")
    op.drop_column("suppliers", "supplier_type")

    op.create_table(
        "procurement_order_reviews",
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("procurement_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("review_text", sa.String(length=3000), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("rating >= 1 AND rating <= 10", name="ck_procurement_review_rating_range"),
        sa.ForeignKeyConstraint(["procurement_id"], ["procurement_orders.procurement_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.supplier_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("review_id"),
        sa.UniqueConstraint("procurement_id", name="uq_procurement_review_per_order"),
    )

    op.create_table(
        "procurement_order_review_images",
        sa.Column("image_id", sa.Integer(), nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["procurement_order_reviews.review_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("image_id"),
    )


def downgrade() -> None:
    op.drop_table("procurement_order_review_images")
    op.drop_table("procurement_order_reviews")

    op.add_column("suppliers", sa.Column("supplier_type", sa.String(length=20), nullable=False, server_default="primary"))
    op.create_check_constraint(
        "ck_suppliers_type",
        "suppliers",
        "supplier_type IN ('primary', 'secondary', 'reseller')",
    )
    op.execute(
        """
        UPDATE suppliers s
        SET supplier_type = sp.supplier_type
        FROM supplier_products sp
        WHERE s.supplier_id = sp.supplier_id
        """
    )
    op.alter_column("suppliers", "supplier_type", server_default=None)

    op.drop_constraint("ck_supplier_products_type", "supplier_products", type_="check")
    op.drop_column("supplier_products", "supplier_type")
