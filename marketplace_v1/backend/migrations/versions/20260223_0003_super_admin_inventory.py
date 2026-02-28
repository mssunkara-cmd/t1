"""add super admin role and inventory

Revision ID: 20260223_0003
Revises: 20260223_0002
Create Date: 2026-02-23 00:35:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260223_0003"
down_revision: str | None = "20260223_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku"),
    )
    op.create_index(op.f("ix_inventory_items_sku"), "inventory_items", ["sku"], unique=False)

    connection = op.get_bind()
    connection.execute(sa.text("INSERT INTO roles (name) VALUES ('super_admin') ON CONFLICT (name) DO NOTHING"))

    new_permissions = ["inventory.read", "inventory.update", "admin.manage"]
    for code in new_permissions:
        connection.execute(
            sa.text(
                "INSERT INTO permissions (code) VALUES (:code) "
                "ON CONFLICT (code) DO NOTHING"
            ),
            {"code": code},
        )

    # Ensure admin and super_admin can manage inventory and admins.
    connection.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            JOIN permissions p ON p.code IN ('inventory.read', 'inventory.update')
            WHERE r.name = 'admin'
            ON CONFLICT ON CONSTRAINT uq_role_permissions DO NOTHING
            """
        )
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            JOIN permissions p ON p.code IN (
              'order.read', 'order.create', 'order.update', 'order.status.update',
              'user.read', 'user.role.update', 'audit.read',
              'inventory.read', 'inventory.update', 'admin.manage'
            )
            WHERE r.name = 'super_admin'
            ON CONFLICT ON CONSTRAINT uq_role_permissions DO NOTHING
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()

    connection.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE role_id IN ("
            "SELECT id FROM roles WHERE name IN ('admin', 'super_admin')"
            ") AND permission_id IN ("
            "SELECT id FROM permissions WHERE code IN ('inventory.read', 'inventory.update', 'admin.manage')"
            ")"
        )
    )
    connection.execute(
        sa.text(
            "DELETE FROM permissions WHERE code IN ('inventory.read', 'inventory.update', 'admin.manage')"
        )
    )
    connection.execute(sa.text("DELETE FROM roles WHERE name = 'super_admin'"))

    op.drop_index(op.f("ix_inventory_items_sku"), table_name="inventory_items")
    op.drop_table("inventory_items")
