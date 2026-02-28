"""add user profile fields and ambassador role

Revision ID: 20260223_0004
Revises: 20260223_0003
Create Date: 2026-02-23 01:05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260223_0004"
down_revision: str | None = "20260223_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("first_name", sa.String(length=250), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=250), nullable=True))
    op.add_column("users", sa.Column("address_line1", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("address_line2", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("address_line3", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("zip_code", sa.String(length=6), nullable=True))
    op.add_column("users", sa.Column("phone_number", sa.String(length=12), nullable=True))
    op.add_column("users", sa.Column("region", sa.String(length=100), nullable=True))

    op.create_table(
        "ambassador_buyer_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ambassador_user_id", sa.Integer(), nullable=False),
        sa.Column("buyer_user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["ambassador_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ambassador_user_id",
            "buyer_user_id",
            name="uq_ambassador_buyer_assignment",
        ),
    )

    connection = op.get_bind()
    connection.execute(sa.text("INSERT INTO roles (name) VALUES ('ambassador') ON CONFLICT (name) DO NOTHING"))

    new_permissions = ["buyer.group.read", "buyer.group.manage"]
    for code in new_permissions:
        connection.execute(
            sa.text(
                "INSERT INTO permissions (code) VALUES (:code) "
                "ON CONFLICT (code) DO NOTHING"
            ),
            {"code": code},
        )

    connection.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            JOIN permissions p ON p.code IN ('buyer.group.read')
            WHERE r.name = 'ambassador'
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
            JOIN permissions p ON p.code IN ('buyer.group.read', 'buyer.group.manage')
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
            "SELECT id FROM roles WHERE name IN ('ambassador', 'admin', 'super_admin')"
            ") AND permission_id IN ("
            "SELECT id FROM permissions WHERE code IN ('buyer.group.read', 'buyer.group.manage')"
            ")"
        )
    )
    connection.execute(
        sa.text(
            "DELETE FROM permissions WHERE code IN ('buyer.group.read', 'buyer.group.manage')"
        )
    )
    connection.execute(sa.text("DELETE FROM roles WHERE name = 'ambassador'"))

    op.drop_table("ambassador_buyer_assignments")

    op.drop_column("users", "region")
    op.drop_column("users", "phone_number")
    op.drop_column("users", "zip_code")
    op.drop_column("users", "address_line3")
    op.drop_column("users", "address_line2")
    op.drop_column("users", "address_line1")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
