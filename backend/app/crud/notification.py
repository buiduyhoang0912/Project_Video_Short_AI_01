"""Xử lý thao tác cơ sở dữ liệu cho thông báo (Task T3D2BAD)."""

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from app.models.notification import Notification


def create_notification(
    db: Session,
    recipient_id: int,
    actor_id: int | None,
    type: str,
    content: str,
    video_id: int | None = None,
    order_id: int | None = None,
) -> Notification | None:
    """Tạo thông báo mới.

    Ràng buộc nghiệp vụ:
    - Không tạo thông báo cho chính mình khi họ tự thích/bình luận video của mình (actor_id == recipient_id).
    """
    if actor_id is not None and recipient_id == actor_id:
        return None

    notification = Notification(
        recipient_id=recipient_id,
        actor_id=actor_id,
        type=type,
        content=content,
        video_id=video_id,
        order_id=order_id,
        is_read=False,
    )
    db.add(notification)
    db.flush()
    return notification


def list_notifications(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
) -> list[Notification]:
    """Lấy danh sách thông báo của người dùng (mới nhất xếp trước)."""
    query = (
        select(Notification)
        .options(selectinload(Notification.actor))
        .where(Notification.recipient_id == user_id)
    )
    if unread_only:
        query = query.where(Notification.is_read.is_(False))

    query = (
        query.order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(query))


def count_unread(db: Session, user_id: int) -> int:
    """Đếm số lượng thông báo chưa đọc của người dùng."""
    query = select(func.count(Notification.id)).where(
        Notification.recipient_id == user_id,
        Notification.is_read.is_(False),
    )
    return int(db.scalar(query) or 0)


def mark_notification_as_read(
    db: Session, notification_id: int, user_id: int
) -> Notification | None:
    """Đánh dấu một thông báo là đã đọc (kiểm tra chặt chẽ recipient_id == user_id)."""
    query = (
        select(Notification)
        .options(selectinload(Notification.actor))
        .where(
            Notification.id == notification_id,
            Notification.recipient_id == user_id,
        )
    )
    notification = db.scalar(query)
    if notification is None:
        return None

    if not notification.is_read:
        notification.is_read = True
        db.commit()
        db.refresh(notification)

    return notification


def mark_all_notifications_as_read(db: Session, user_id: int) -> int:
    """Đánh dấu tất cả thông báo của người dùng là đã đọc."""
    stmt = (
        update(Notification)
        .where(
            Notification.recipient_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount
