"""Nghiệp vụ Admin: kiểm duyệt video/sản phẩm và số liệu dashboard (T3D201D)."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.crud.admin import AdminError, _escape_like
from app.crud.notification import create_notification
from app.models.order import Order
from app.models.product import Product
from app.models.shop import Shop
from app.models.user import User, utc_now
from app.models.video import Video

# Đơn tính vào doanh thu: đã thanh toán/xác nhận, đang giao hoặc hoàn tất.
# Loại bỏ đơn chờ (pending) và đơn huỷ (cancelled).
# Lưu ý: tính trên bảng Order (không join OrderItem) để tránh cộng trùng đơn nhiều sản phẩm.
REVENUE_STATUSES = ("confirmed", "shipping", "completed")


# ---------- Video ----------
def list_videos(db: Session, status_filter: str | None, search: str | None):
    query = (
        select(Video, User)
        .join(User, User.id == Video.user_id)
        .order_by(Video.id.desc())
    )
    if status_filter:
        query = query.where(Video.status == status_filter)
    keyword = (search or "").strip()
    if keyword:
        pattern = f"%{_escape_like(keyword)}%"
        query = query.where(
            or_(
                Video.title.like(pattern, escape="\\"),
                User.username.like(pattern, escape="\\"),
            )
        )
    return list(db.execute(query).all())


def _get_video_for_update(db: Session, video_id: int) -> Video:
    video = db.scalar(select(Video).where(Video.id == video_id).with_for_update())
    if video is None:
        raise AdminError(404, "Không tìm thấy video")
    return video


def hide_video(db: Session, video_id: int, admin_id: int, reason: str):
    try:
        video = _get_video_for_update(db, video_id)
        if video.status == "HIDDEN":
            raise AdminError(409, "Video đã bị ẩn")
        video.status = "HIDDEN"
        video.moderation_reason = reason
        video.moderated_by = admin_id
        video.moderated_at = utc_now()
        create_notification(
            db,
            recipient_id=video.user_id,
            actor_id=admin_id,
            type="MODERATION_VIDEO",
            content=f"Video '{video.title}' đã bị Admin ẩn. Lý do: {reason}",
            video_id=video.id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return video, db.get(User, video.user_id)


def show_video(db: Session, video_id: int):
    try:
        video = _get_video_for_update(db, video_id)
        if video.status != "HIDDEN":
            raise AdminError(409, "Video đang hiển thị")
        video.status = "VISIBLE"
        video.moderation_reason = None
        video.moderated_by = None
        video.moderated_at = None
        create_notification(
            db,
            recipient_id=video.user_id,
            actor_id=None,
            type="MODERATION_VIDEO",
            content=f"Video '{video.title}' đã được Admin hiển thị lại.",
            video_id=video.id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return video, db.get(User, video.user_id)


# ---------- Sản phẩm ----------
def list_products(db: Session, status_filter: str | None, search: str | None):
    query = (
        select(Product, Shop)
        .join(Shop, Shop.id == Product.shop_id)
        .options(selectinload(Product.images))
        .order_by(Product.id.desc())
    )
    if status_filter:
        query = query.where(Product.status == status_filter)
    keyword = (search or "").strip()
    if keyword:
        pattern = f"%{_escape_like(keyword)}%"
        query = query.where(
            or_(
                Product.name.like(pattern, escape="\\"),
                Shop.name.like(pattern, escape="\\"),
            )
        )
    return list(db.execute(query).all())


def _get_product_for_update(db: Session, product_id: int) -> Product:
    product = db.scalar(
        select(Product)
        .options(selectinload(Product.images))
        .where(Product.id == product_id)
        .with_for_update()
    )
    if product is None:
        raise AdminError(404, "Không tìm thấy sản phẩm")
    return product


def hide_product(db: Session, product_id: int, admin_id: int, reason: str):
    try:
        product = _get_product_for_update(db, product_id)
        if product.status == "HIDDEN" and product.moderated_at is not None:
            raise AdminError(409, "Sản phẩm đã bị Admin ẩn")
        product.status = "HIDDEN"
        product.moderation_reason = reason
        product.moderated_by = admin_id
        product.moderated_at = utc_now()
        shop_obj = db.get(Shop, product.shop_id)
        if shop_obj and shop_obj.owner_id:
            create_notification(
                db,
                recipient_id=shop_obj.owner_id,
                actor_id=admin_id,
                type="MODERATION_PRODUCT",
                content=f"Sản phẩm '{product.name}' đã bị Admin ẩn. Lý do: {reason}",
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return product, db.get(Shop, product.shop_id)


def show_product(db: Session, product_id: int):
    try:
        product = _get_product_for_update(db, product_id)
        if product.status != "HIDDEN":
            raise AdminError(409, "Sản phẩm đang hiển thị")
        product.status = "ACTIVE"
        product.moderation_reason = None
        product.moderated_by = None
        product.moderated_at = None
        shop_obj = db.get(Shop, product.shop_id)
        if shop_obj and shop_obj.owner_id:
            create_notification(
                db,
                recipient_id=shop_obj.owner_id,
                actor_id=None,
                type="MODERATION_PRODUCT",
                content=f"Sản phẩm '{product.name}' đã được Admin hiển thị lại.",
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return product, db.get(Shop, product.shop_id)


# ---------- Dashboard ----------
def _count(db: Session, stmt) -> int:
    return int(db.scalar(stmt) or 0)


def dashboard_summary(db: Session) -> dict:
    revenue = db.scalar(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            Order.status.in_(REVENUE_STATUSES)
        )
    )
    return {
        "total_users": _count(db, select(func.count(User.id))),
        "total_sellers": _count(
            db, select(func.count(User.id)).where(User.role == "SELLER")
        ),
        "total_videos": _count(db, select(func.count(Video.id))),
        "total_products": _count(db, select(func.count(Product.id))),
        "total_orders": _count(db, select(func.count(Order.id))),
        "total_revenue": Decimal(revenue or 0),
    }


def _by_day_range(db: Session, column, start_dt, end_dt, *extra_where, value=None):
    day = func.date(column)
    agg = value if value is not None else func.count()
    rows = db.execute(
        select(day, agg)
        .where(column >= start_dt, column < end_dt, *extra_where)
        .group_by(day)
    ).all()
    return {str(d): v for d, v in rows}


def dashboard_daily_range(
    db: Session, start_date: date, end_date: date
) -> list[dict]:
    """Số liệu theo từng ngày từ start_date đến end_date (bao gồm cả 2 đầu)."""
    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date + timedelta(days=1), time.min)

    users = _by_day_range(db, User.created_at, start_dt, end_dt)
    videos = _by_day_range(db, Video.created_at, start_dt, end_dt)
    orders = _by_day_range(
        db, Order.created_at, start_dt, end_dt, Order.status != "cancelled"
    )
    revenue = _by_day_range(
        db,
        Order.created_at,
        start_dt,
        end_dt,
        Order.status.in_(REVENUE_STATUSES),
        value=func.sum(Order.total_amount),
    )

    days_count = (end_date - start_date).days + 1
    points = []
    for i in range(days_count):
        key = (start_date + timedelta(days=i)).isoformat()
        points.append(
            {
                "date": key,
                "new_users": int(users.get(key, 0)),
                "new_videos": int(videos.get(key, 0)),
                "orders": int(orders.get(key, 0)),
                "revenue": Decimal(revenue.get(key, 0) or 0),
            }
        )
    return points


def dashboard_daily(db: Session, days: int) -> list[dict]:
    today = utc_now().date()
    start_date = today - timedelta(days=days - 1)
    return dashboard_daily_range(db, start_date, today)
