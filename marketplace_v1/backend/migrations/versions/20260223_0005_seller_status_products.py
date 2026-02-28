"""add seller status and products table

Revision ID: 20260223_0005
Revises: 20260223_0004
Create Date: 2026-02-23 02:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260223_0005"
down_revision: str | None = "20260223_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("seller_status", sa.String(length=32), nullable=True))

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=100), nullable=False),
        sa.Column("product_type", sa.String(length=50), nullable=False),
        sa.Column("product_unit", sa.String(length=10), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE users SET seller_status = 'valid' "
            "WHERE id IN ("
            "SELECT ur.user_id FROM user_roles ur "
            "JOIN roles r ON r.id = ur.role_id "
            "WHERE r.name = 'seller'"
            ")"
        )
    )

    connection.execute(
        sa.text("INSERT INTO permissions (code) VALUES ('seller.validate') ON CONFLICT (code) DO NOTHING")
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            JOIN permissions p ON p.code IN ('seller.validate')
            WHERE r.name IN ('admin', 'super_admin')
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
            "SELECT id FROM permissions WHERE code IN ('seller.validate')"
            ")"
        )
    )
    connection.execute(sa.text("DELETE FROM permissions WHERE code = 'seller.validate'"))

    op.drop_table("products")
    op.drop_column("users", "seller_status")
