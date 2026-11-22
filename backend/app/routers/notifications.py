"""Router API quản lý thông báo (Task T3D2BAD).

Chỉ dành cho tài khoản đang đăng nhập (kiểm tra chặt chẽ recipient_id):
- GET   /api/notifications
- GET   /api/notifications/unread-count
- PATCH /api/notifications/{id}/read
- PATCH /api/notifications/read-all
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud import notification as notif_crud
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.notification import (
    NotificationBatchReadResponse,
    NotificationOut,
    NotificationUnreadCount,
)

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
    dependencies=[Depends(get_current_user)],  # Bắt buộc đăng nhập
)


@router.get("", response_model=list[NotificationOut])
def get_my_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy danh sách thông báo của tài khoản đang đăng nhập."""
    return notif_crud.list_notifications(
        db, user_id=user.id, skip=skip, limit=limit, unread_only=unread_only
    )


@router.get("/unread-count", response_model=NotificationUnreadCount)
def get_unread_count(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đếm số thông báo chưa đọc của tài khoản đang đăng nhập."""
    count = notif_crud.count_unread(db, user_id=user.id)
    return {"unread_count": count}


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đánh dấu một thông báo của mình là đã đọc."""
    notification = notif_crud.mark_notification_as_read(
        db, notification_id=notification_id, user_id=user.id
    )
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo hoặc bạn không có quyền truy cập",
        )
    return notification


@router.patch("/read-all", response_model=NotificationBatchReadResponse)
def mark_all_notifications_read(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đánh dấu tất cả thông báo của tài khoản đang đăng nhập là đã đọc."""
    updated = notif_crud.mark_all_notifications_as_read(db, user_id=user.id)
    return {
        "message": "Đã đánh dấu tất cả thông báo là đã đọc",
        "updated_count": updated,
    }
