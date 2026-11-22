"""Model lưu trữ thông báo trong ứng dụng (Task T3D2BAD).

Hỗ trợ 4 loại thông báo:
- LIKE: Có người thích video của bạn
- COMMENT: Có người bình luận video của bạn
- FOLLOW: Có người bắt đầu theo dõi bạn
- ORDER_STATUS: Đơn hàng thay đổi trạng thái
"""

from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Notification(Base):
    __tablename__ = "notifications"

    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
    }

    id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    recipient_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # LIKE, COMMENT, FOLLOW, ORDER_STATUS
    content: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    video_id: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    order_id: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, server_default=func.now(), nullable=False, index=True
    )

    recipient = relationship("User", foreign_keys=[recipient_id])
    actor = relationship("User", foreign_keys=[actor_id])
    video = relationship("Video", foreign_keys=[video_id])
    order = relationship("Order", foreign_keys=[order_id])
