from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.mysql import BIGINT, ENUM, INTEGER, JSON

from app.db.session import Base


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        CheckConstraint("duration_seconds > 0", name="ck_videos_duration_positive"),
        Index("ix_videos_status_created_at", "status", "created_at"),
    )

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    hashtags = Column(JSON, nullable=True)
    video_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    duration_seconds = Column(INTEGER(unsigned=True), nullable=False)
    view_count = Column(BIGINT(unsigned=True), nullable=False, server_default=text("0"))
    status = Column(
        ENUM("VISIBLE", "HIDDEN"), nullable=False, server_default="VISIBLE"
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now())

class VideoProduct(Base):
    __tablename__ = "video_products"

    video_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        primary_key=True,
    )
    product_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("products.id"),
        primary_key=True,
        index=True,
    )