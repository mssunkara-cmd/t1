from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class RegionDefault(db.Model):
    __tablename__ = "region_defaults"
    __table_args__ = (UniqueConstraint("region_id", name="uq_region_defaults_region_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.region_id", ondelete="CASCADE"),
        nullable=False,
    )
    default_admin_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    default_ambassador_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
