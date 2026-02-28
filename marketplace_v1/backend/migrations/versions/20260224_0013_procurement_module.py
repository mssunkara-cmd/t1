"""add procurement module tables and permissions

Revision ID: 20260224_0013
Revises: 20260224_0012
Create Date: 2026-02-24 16:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260224_0013"
down_revision: str | None = "20260224_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("supplier_name", sa.String(length=250), nullable=False),
        sa.Column("address_line1", sa.String(length=100), nullable=True),
        sa.Column("address_line2", sa.String(length=100), nullable=True),
        sa.Column("address_line3", sa.String(length=100), nullable=True),
        sa.Column("phone_number", sa.String(length=12), nullable=True),
        sa.Column("supplier_type", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "supplier_type IN ('primary', 'secondary', 'reseller')",
            name="ck_suppliers_type",
        ),
        sa.PrimaryKeyConstraint("supplier_id"),
    )
    op.alter_column("suppliers", "is_active", server_default=None)

    op.create_table(
        "supplier_products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.supplier_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supplier_id", "product_id", name="uq_supplier_product"),
    )

    op.create_table(
        "procurement_orders",
        sa.Column("procurement_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price_per_unit", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("procurement_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by_admin_user_id", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity >= 0", name="ck_procurement_quantity_non_negative"),
        sa.CheckConstraint("price_per_unit >= 0", name="ck_procurement_price_non_negative"),
        sa.CheckConstraint(
            "status IN ('draft', 'placed', 'received', 'cancelled')",
            name="ck_procurement_status",
        ),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.supplier_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("procurement_id"),
    )

    op.create_table(
        "supplier_ratings",
        sa.Column("rating_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("rated_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("rating >= 1 AND rating <= 10", name="ck_supplier_rating_range"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.supplier_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("rating_id"),
    )

    connection = op.get_bind()
    permission_codes = [
        "supplier.read",
        "supplier.manage",
        "procurement.read",
        "procurement.manage",
        "supplier.rating.read",
        "supplier.rating.manage",
    ]

    for code in permission_codes:
        connection.execute(
            sa.text("INSERT INTO permissions (code) VALUES (:code) ON CONFLICT (code) DO NOTHING"),
            {"code": code},
        )

    connection.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            JOIN permissions p ON p.code IN (
              'supplier.read',
              'supplier.manage',
              'procurement.read',
              'procurement.manage',
              'supplier.rating.read',
              'supplier.rating.manage'
            )
            WHERE r.name IN ('admin', 'super_admin')
            ON CONFLICT ON CONSTRAINT uq_role_permissions DO NOTHING
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE role_id IN (SELECT id FROM roles WHERE name IN ('admin', 'super_admin'))
              AND permission_id IN (
                SELECT id FROM permissions WHERE code IN (
                  'supplier.read',
                  'supplier.manage',
                  'procurement.read',
                  'procurement.manage',
                  'supplier.rating.read',
                  'supplier.rating.manage'
                )
              )
            """
        )
    )
    connection.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE code IN (
              'supplier.read',
              'supplier.manage',
              'procurement.read',
              'procurement.manage',
              'supplier.rating.read',
              'supplier.rating.manage'
            )
            """
        )
    )

    op.drop_table("supplier_ratings")
    op.drop_table("procurement_orders")
    op.drop_table("supplier_products")
    op.drop_table("suppliers")
