"""Model tài khoản và hồ sơ người dùng."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

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

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )

    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )

    # Chỉ lưu kết quả băm bcrypt.
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    display_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    avatar_key: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )

    bio: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    role: Mapped[str] = mapped_column(
        Enum(
            "USER", "SELLER", "ADMIN",
            name="user_role",
            validate_strings=True,
        ),
        nullable=False,
        default="USER",
        server_default="USER",
    )

    status: Mapped[str] = mapped_column(
        Enum(
            "ACTIVE", "LOCKED",
            name="user_status",
            validate_strings=True,
        ),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )