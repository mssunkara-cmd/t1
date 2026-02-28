from sqlalchemy import CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class Region(db.Model):
    __tablename__ = "regions"
    __table_args__ = (
        UniqueConstraint("region_name", "region_type", name="uq_regions_name_type"),
        CheckConstraint("region_type IN ('source', 'distribution')", name="ck_regions_type"),
    )

    region_id: Mapped[int] = mapped_column(primary_key=True)
    region_name: Mapped[str] = mapped_column(String(150), nullable=False)
    region_description: Mapped[str | None] = mapped_column(String(1500))
    region_type: Mapped[str] = mapped_column(String(20), nullable=False)
    distribution_level: Mapped[str | None] = mapped_column(String(20))
    parent_region_id: Mapped[int | None] = mapped_column(
        db.ForeignKey("regions.region_id"),
        nullable=True,
    )
