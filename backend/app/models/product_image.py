from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ProductImage(Base):
    __tablename__ = "product_images"

    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
    }

    id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    product_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("products.id"),
        nullable=False,
    )

    object_key: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )

    product: Mapped["Product"] = relationship("Product", back_populates="images")  # noqa: F821

    @property
    def image_url(self) -> str:
        return self.object_key

    @property
    def display_order(self) -> int:
        return self.sort_order
