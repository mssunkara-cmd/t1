from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class FreshProduceInventoryItem(db.Model):
    __tablename__ = "fresh_produce_inventory"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    seller_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.supplier_id", ondelete="RESTRICT")
    )
    origin_type: Mapped[str] = mapped_column(db.String(20), nullable=False, default="seller_direct")
    origin: Mapped[str | None] = mapped_column(db.String(20))
    entry_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_by_admin_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    estimated_quantity: Mapped[int] = mapped_column(nullable=False, default=0)
    reserved_quantity: Mapped[int] = mapped_column(nullable=False, default=0)
    price_per_unit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    product = relationship("Product", foreign_keys=[product_id], lazy="joined")
    seller = relationship("User", foreign_keys=[seller_id], lazy="joined")
    supplier = relationship("Supplier", foreign_keys=[supplier_id], lazy="joined")
