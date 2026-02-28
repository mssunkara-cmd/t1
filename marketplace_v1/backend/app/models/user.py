from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    first_name: Mapped[str | None] = mapped_column(String(250))
    last_name: Mapped[str | None] = mapped_column(String(250))
    address_line1: Mapped[str | None] = mapped_column(String(100))
    address_line2: Mapped[str | None] = mapped_column(String(100))
    address_line3: Mapped[str | None] = mapped_column(String(100))
    zip_code: Mapped[str | None] = mapped_column(String(6))
    phone_number: Mapped[str | None] = mapped_column(String(12))
    region: Mapped[str | None] = mapped_column(String(100))
    source_region_id: Mapped[int | None] = mapped_column(
        ForeignKey("regions.region_id", ondelete="SET NULL")
    )
    major_distribution_region_id: Mapped[int | None] = mapped_column(
        ForeignKey("regions.region_id", ondelete="SET NULL")
    )
    assigned_admin_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    seller_status: Mapped[str | None] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles", back_populates="users", lazy="selectin"
    )

    buyer_orders: Mapped[list["Order"]] = relationship(
        foreign_keys="Order.buyer_id", back_populates="buyer", lazy="selectin"
    )
    seller_orders: Mapped[list["Order"]] = relationship(
        foreign_keys="Order.seller_id", back_populates="seller", lazy="selectin"
    )


from .order import Order  # noqa: E402
from .role import Role  # noqa: E402


class AmbassadorBuyerAssignment(db.Model):
    __tablename__ = "ambassador_buyer_assignments"
    __table_args__ = (
        UniqueConstraint(
            "ambassador_user_id",
            "buyer_user_id",
            name="uq_ambassador_buyer_assignment",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ambassador_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    buyer_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
