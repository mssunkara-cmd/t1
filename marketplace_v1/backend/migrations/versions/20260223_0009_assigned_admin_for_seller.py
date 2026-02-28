"""add assigned admin for sellers

Revision ID: 20260223_0009
Revises: 20260223_0008
Create Date: 2026-02-23 03:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260223_0009"
down_revision: str | None = "20260223_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("assigned_admin_user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_users_assigned_admin_user_id",
        "users",
        "users",
        ["assigned_admin_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE users u
            SET assigned_admin_user_id = rd.default_admin_user_id
            FROM region_defaults rd, regions r
            WHERE u.source_region_id = rd.region_id
              AND rd.region_id = r.region_id
              AND r.region_type = 'source'
              AND u.id IN (
                SELECT ur.user_id
                FROM user_roles ur
                JOIN roles ro ON ro.id = ur.role_id
                WHERE ro.name = 'seller'
              )
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_assigned_admin_user_id", "users", type_="foreignkey")
    op.drop_column("users", "assigned_admin_user_id")
