"""seed roles and permissions

Revision ID: 20260223_0002
Revises: 20260223_0001
Create Date: 2026-02-23 00:15:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260223_0002"
down_revision: str | None = "20260223_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
    )
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.Integer),
        sa.column("code", sa.String),
    )

    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Integer),
        sa.column("permission_id", sa.Integer),
    )

    op.bulk_insert(
        roles_table,
        [
            {"name": "admin"},
            {"name": "seller"},
            {"name": "buyer"},
            {"name": "support_ops"},
        ],
    )

    permission_codes = [
        "order.read",
        "order.create",
        "order.update",
        "order.status.update",
        "user.read",
        "user.role.update",
        "audit.read",
    ]
    op.bulk_insert(permissions_table, [{"code": code} for code in permission_codes])

    connection = op.get_bind()
    role_rows = connection.execute(sa.text("SELECT id, name FROM roles")).mappings().all()
    permission_rows = (
        connection.execute(sa.text("SELECT id, code FROM permissions")).mappings().all()
    )

    role_id_by_name = {row["name"]: row["id"] for row in role_rows}
    permission_id_by_code = {row["code"]: row["id"] for row in permission_rows}

    role_permissions = {
        "admin": permission_codes,
        "seller": ["order.read", "order.create", "order.update", "order.status.update"],
        "buyer": ["order.read", "order.create"],
        "support_ops": ["order.read", "order.status.update", "audit.read", "user.read"],
    }

    inserts: list[dict[str, int]] = []
    for role_name, codes in role_permissions.items():
        role_id = role_id_by_name[role_name]
        for code in codes:
            inserts.append(
                {
                    "role_id": role_id,
                    "permission_id": permission_id_by_code[code],
                }
            )

    op.bulk_insert(role_permissions_table, inserts)


def downgrade() -> None:
    connection = op.get_bind()

    connection.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE role_id IN ("
            "SELECT id FROM roles WHERE name IN (:admin, :seller, :buyer, :support_ops)"
            ")"
        ),
        {
            "admin": "admin",
            "seller": "seller",
            "buyer": "buyer",
            "support_ops": "support_ops",
        },
    )

    connection.execute(
        sa.text(
            "DELETE FROM permissions WHERE code IN ("
            ":p1, :p2, :p3, :p4, :p5, :p6, :p7"
            ")"
        ),
        {
            "p1": "order.read",
            "p2": "order.create",
            "p3": "order.update",
            "p4": "order.status.update",
            "p5": "user.read",
            "p6": "user.role.update",
            "p7": "audit.read",
        },
    )

    connection.execute(
        sa.text(
            "DELETE FROM roles WHERE name IN (:admin, :seller, :buyer, :support_ops)"
        ),
        {
            "admin": "admin",
            "seller": "seller",
            "buyer": "buyer",
            "support_ops": "support_ops",
        },
    )
