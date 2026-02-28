from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class Product(db.Model):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)
    product_type: Mapped[str] = mapped_column(String(50), nullable=False)
    product_unit: Mapped[str] = mapped_column(String(10), nullable=False)
    validity_days: Mapped[int] = mapped_column(nullable=False, default=365)
