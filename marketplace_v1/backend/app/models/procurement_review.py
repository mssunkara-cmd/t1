from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class ProcurementOrderReview(db.Model):
    __tablename__ = "procurement_order_reviews"
    __table_args__ = (
        UniqueConstraint("procurement_id", name="uq_procurement_review_per_order"),
    )

    review_id: Mapped[int] = mapped_column(primary_key=True)
    procurement_id: Mapped[int] = mapped_column(
        ForeignKey("procurement_orders.procurement_id", ondelete="CASCADE"),
        nullable=False,
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.supplier_id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(nullable=False)
    review_text: Mapped[str | None] = mapped_column(db.String(3000))
    reviewed_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ProcurementOrderReviewImage(db.Model):
    __tablename__ = "procurement_order_review_images"

    image_id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(
        ForeignKey("procurement_order_reviews.review_id", ondelete="CASCADE"),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(db.String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
