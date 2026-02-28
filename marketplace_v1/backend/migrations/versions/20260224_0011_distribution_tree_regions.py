"""add distribution tree fields and buyer major distribution region

Revision ID: 20260224_0011
Revises: 20260223_0010
Create Date: 2026-02-24 10:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260224_0011"
down_revision: str | None = "20260223_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("regions", sa.Column("distribution_level", sa.String(length=20), nullable=True))
    op.add_column("regions", sa.Column("parent_region_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_regions_parent_region_id",
        "regions",
        "regions",
        ["parent_region_id"],
        ["region_id"],
    )

    op.execute("UPDATE regions SET distribution_level = 'major' WHERE region_type = 'distribution'")

    op.add_column("users", sa.Column("major_distribution_region_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_users_major_distribution_region_id",
        "users",
        "regions",
        ["major_distribution_region_id"],
        ["region_id"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        JOIN permissions p ON p.code IN ('buyer.group.manage', 'user.read')
        WHERE r.name = 'ambassador'
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE role_id = (SELECT id FROM roles WHERE name = 'ambassador')
          AND permission_id IN (
            SELECT id FROM permissions WHERE code IN ('buyer.group.manage', 'user.read')
          )
        """
    )

    op.drop_constraint("fk_users_major_distribution_region_id", "users", type_="foreignkey")
    op.drop_column("users", "major_distribution_region_id")

    op.drop_constraint("fk_regions_parent_region_id", "regions", type_="foreignkey")
    op.drop_column("regions", "parent_region_id")
    op.drop_column("regions", "distribution_level")
