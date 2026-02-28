"""add product permissions

Revision ID: 20260223_0006
Revises: 20260223_0005
Create Date: 2026-02-23 02:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260223_0006"
down_revision: str | None = "20260223_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()

    for code in ["product.read", "product.manage"]:
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
            JOIN permissions p ON p.code IN ('product.read', 'product.manage')
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
            "SELECT id FROM permissions WHERE code IN ('product.read', 'product.manage')"
            ")"
        )
    )
    connection.execute(
        sa.text("DELETE FROM permissions WHERE code IN ('product.read', 'product.manage')")
    )
