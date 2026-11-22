"""Model đơn đăng ký trở thành người bán."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.user import utc_now


class SellerApplication(Base):
    __tablename__ = "seller_applications"

    __table_args__ = (
        Index("idx_sa_user_status", "user_id", "status"),
        Index("idx_sa_status_created", "status", "created_at"),
        Index("idx_sa_reviewed_by", "reviewed_by"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )

    id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    # Tài khoản gửi đơn.
    user_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )

    proposed_shop_name: Mapped[str] = mapped_column(
        String(150), nullable=False
    )

    phone: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    description: Mapped[str] = mapped_column(
        Text, nullable=False
    )

    status: Mapped[str] = mapped_column(
        Enum(
            "PENDING",
            "APPROVED",
            "REJECTED",
            name="seller_application_status",
            validate_strings=True,
        ),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
    )

    rejection_reason: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    # Tài khoản ADMIN xét duyệt; chưa duyệt thì để NULL.
    reviewed_by: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )