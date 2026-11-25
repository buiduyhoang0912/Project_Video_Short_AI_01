"""Xử lý nghiệp vụ cho Admin: duyệt/từ chối đơn bán hàng, tìm kiếm/khoá tài khoản."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.crud.notification import create_notification
from app.models.seller_application import SellerApplication
from app.models.user import User, utc_now


class AdminError(Exception):
    """Lỗi nghiệp vụ; router đổi thành HTTPException theo status_code."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def list_applications(db: Session, status_filter: str | None = None):
    query = (
        select(SellerApplication, User)
        .join(User, User.id == SellerApplication.user_id)
        .order_by(SellerApplication.id.desc())
    )
    if status_filter:
        query = query.where(SellerApplication.status == status_filter)
    return list(db.execute(query).all())


def _get_pending_for_update(db: Session, application_id: int) -> SellerApplication:
    application = db.scalar(
        select(SellerApplication)
        .where(SellerApplication.id == application_id)
        .with_for_update()
    )
    if application is None:
        raise AdminError(404, "Không tìm thấy đơn đăng ký bán hàng")
    if application.status != "PENDING":
        raise AdminError(409, "Đơn không còn ở trạng thái chờ duyệt")
    return application


def approve_application(db: Session, application_id: int, admin_id: int):
    """Cập nhật đơn + quyền tài khoản trong CÙNG một transaction (commit 1 lần)."""
    try:
        application = _get_pending_for_update(db, application_id)
        applicant = db.scalar(
            select(User).where(User.id == application.user_id).with_for_update()
        )
        if applicant is None:
            raise AdminError(404, "Không tìm thấy tài khoản người đăng ký")
        application.status = "APPROVED"
        application.rejection_reason = None
        application.reviewed_by = admin_id
        application.reviewed_at = utc_now()
        if applicant.role == "USER":
            applicant.role = "SELLER"
        create_notification(
            db,
            recipient_id=applicant.id,
            actor_id=admin_id,
            type="SELLER_APPROVED",
            content=f"Đơn đăng ký bán hàng '{application.proposed_shop_name}' của bạn đã được duyệt! Hãy tạo cửa hàng ngay.",
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return application, applicant


def reject_application(db: Session, application_id: int, admin_id: int, reason: str):
    try:
        application = _get_pending_for_update(db, application_id)
        application.status = "REJECTED"
        application.rejection_reason = reason
        application.reviewed_by = admin_id
        application.reviewed_at = utc_now()
        create_notification(
            db,
            recipient_id=application.user_id,
            actor_id=admin_id,
            type="SELLER_REJECTED",
            content=f"Đơn đăng ký bán hàng '{application.proposed_shop_name}' bị từ chối. Lý do: {reason}",
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return application, db.get(User, application.user_id)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_users(db: Session, search: str | None = None) -> list[User]:
    query = select(User).order_by(User.id.desc())
    keyword = (search or "").strip()
    if keyword:
        pattern = f"%{_escape_like(keyword)}%"
        query = query.where(
            or_(
                User.username.like(pattern, escape="\\"),
                User.email.like(pattern, escape="\\"),
                User.display_name.like(pattern, escape="\\"),
            )
        )
    return list(db.scalars(query))


def set_user_status(db: Session, user_id: int, admin_id: int, new_status: str) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise AdminError(404, "Không tìm thấy tài khoản")
    if new_status == "LOCKED" and user.id == admin_id:
        raise AdminError(400, "Không thể tự khoá chính tài khoản của bạn")
    if user.status == new_status:
        msg = "Tài khoản đã bị khoá" if new_status == "LOCKED" else "Tài khoản đang hoạt động"
        raise AdminError(409, msg)
    user.status = new_status
    db.commit()
    db.refresh(user)
    return user
