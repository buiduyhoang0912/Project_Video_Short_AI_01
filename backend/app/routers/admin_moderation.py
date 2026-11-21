"""API Admin: kiểm duyệt video/sản phẩm và dashboard (T3D201D). Chỉ ADMIN.

- GET   /api/admin/videos?status=VISIBLE|HIDDEN&search=
- PATCH /api/admin/videos/{id}/visibility  body: {"status": "HIDDEN", "reason": "..."}
- PATCH /api/admin/videos/{id}/hide        body: {"reason": "..."}
- PATCH /api/admin/videos/{id}/show
- GET   /api/admin/products?status=ACTIVE|HIDDEN|INACTIVE&search=
- PATCH /api/admin/products/{id}/visibility body: {"status": "HIDDEN", "reason": "..."}
- PATCH /api/admin/products/{id}/hide       body: {"reason": "..."}
- PATCH /api/admin/products/{id}/show
- GET   /api/admin/dashboard                query: from_date, to_date, days
- GET   /api/admin/dashboard/summary
- GET   /api/admin/dashboard/daily          query: days
"""

from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session

from app.crud import admin_moderation as crud
from app.crud.admin import AdminError
from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.models.user import User, utc_now
from app.schemas.admin_moderation import (
    DashboardCombined,
    DashboardDaily,
    DashboardSummary,
    HideRequest,
    ModerationProductOut,
    ModerationVideoOut,
    ProductVisibilityRequest,
    VideoVisibilityRequest,
)

router = APIRouter(
    prefix="/admin",
    tags=["Admin - Kiểm duyệt & Dashboard"],
    dependencies=[Depends(require_admin)],  # Chặn toàn bộ router nếu không phải ADMIN
)


def _video_out(video, owner) -> dict:
    return {
        "id": video.id,
        "title": video.title,
        "owner": {
            "id": owner.id,
            "username": owner.username,
            "display_name": owner.display_name,
        },
        "status": video.status,
        "view_count": video.view_count or 0,
        "thumbnail_url": video.thumbnail_url,
        "moderation_reason": video.moderation_reason,
        "moderated_at": video.moderated_at,
        "created_at": video.created_at,
    }


def _product_out(product, shop) -> dict:
    thumb = getattr(product, "thumbnail_url", None)
    return {
        "id": product.id,
        "name": product.name,
        "shop_id": product.shop_id,
        "shop_name": shop.name if shop else "",
        "price": product.price,
        "status": product.status,
        "thumbnail_url": thumb,
        "moderation_reason": product.moderation_reason,
        "moderated_at": product.moderated_at,
        "created_at": product.created_at,
    }


def _http(error: AdminError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.detail)


# ---------- Video ----------
@router.get("/videos", response_model=list[ModerationVideoOut])
def list_videos(
    status: Literal["VISIBLE", "HIDDEN"] | None = None,
    search: str | None = Query(None, max_length=100),
    db: Session = Depends(get_db),
):
    return [_video_out(v, u) for v, u in crud.list_videos(db, status, search)]


@router.patch("/videos/{video_id}/visibility", response_model=ModerationVideoOut)
def update_video_visibility(
    video_id: int,
    data: VideoVisibilityRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    is_hide = (
        data.status == "HIDDEN"
        or data.is_visible is False
    )
    if is_hide:
        reason = (data.reason or "").strip()
        if not reason:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Lý do ẩn video là bắt buộc",
            )
        try:
            return _video_out(*crud.hide_video(db, video_id, admin.id, reason))
        except AdminError as e:
            raise _http(e)
    else:
        try:
            return _video_out(*crud.show_video(db, video_id))
        except AdminError as e:
            raise _http(e)


@router.patch("/videos/{video_id}/hide", response_model=ModerationVideoOut)
def hide_video(
    video_id: int,
    data: HideRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return _video_out(*crud.hide_video(db, video_id, admin.id, data.reason))
    except AdminError as e:
        raise _http(e)


@router.patch("/videos/{video_id}/show", response_model=ModerationVideoOut)
def show_video(video_id: int, db: Session = Depends(get_db)):
    try:
        return _video_out(*crud.show_video(db, video_id))
    except AdminError as e:
        raise _http(e)


# ---------- Sản phẩm ----------
@router.get("/products", response_model=list[ModerationProductOut])
def list_products(
    status: Literal["ACTIVE", "HIDDEN", "INACTIVE"] | None = None,
    search: str | None = Query(None, max_length=100),
    db: Session = Depends(get_db),
):
    return [_product_out(p, s) for p, s in crud.list_products(db, status, search)]


@router.patch("/products/{product_id}/visibility", response_model=ModerationProductOut)
def update_product_visibility(
    product_id: int,
    data: ProductVisibilityRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    is_hide = (
        data.status == "HIDDEN"
        or data.is_visible is False
    )
    if is_hide:
        reason = (data.reason or "").strip()
        if not reason:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Lý do ẩn sản phẩm là bắt buộc",
            )
        try:
            return _product_out(*crud.hide_product(db, product_id, admin.id, reason))
        except AdminError as e:
            raise _http(e)
    else:
        try:
            return _product_out(*crud.show_product(db, product_id))
        except AdminError as e:
            raise _http(e)


@router.patch("/products/{product_id}/hide", response_model=ModerationProductOut)
def hide_product(
    product_id: int,
    data: HideRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return _product_out(*crud.hide_product(db, product_id, admin.id, data.reason))
    except AdminError as e:
        raise _http(e)


@router.patch("/products/{product_id}/show", response_model=ModerationProductOut)
def show_product(product_id: int, db: Session = Depends(get_db)):
    try:
        return _product_out(*crud.show_product(db, product_id))
    except AdminError as e:
        raise _http(e)


# ---------- Dashboard ----------
def _parse_dates(
    from_date_str: str | None, to_date_str: str | None, days: int
) -> tuple[date, date]:
    today = utc_now().date()
    if from_date_str and to_date_str:
        try:
            f = datetime.strptime(from_date_str.strip(), "%Y-%m-%d").date()
            t = datetime.strptime(to_date_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Định dạng ngày không hợp lệ (phải là YYYY-MM-DD)",
            )
        if f > t:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="from_date không được lớn hơn to_date",
            )
        if (t - f).days > 365:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Khoảng thời gian không được vượt quá 365 ngày",
            )
        return f, t
    elif from_date_str:
        try:
            f = datetime.strptime(from_date_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Định dạng ngày không hợp lệ (phải là YYYY-MM-DD)",
            )
        if f > today:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="from_date không được trong tương lai",
            )
        return f, today
    else:
        return today - timedelta(days=days - 1), today


@router.get("/dashboard", response_model=DashboardCombined)
def get_dashboard(
    from_date: str | None = Query(None, description="Từ ngày (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Đến ngày (YYYY-MM-DD)"),
    days: int = Query(30, ge=1, le=365, description="Số ngày gần nhất nếu không chọn khoảng"),
    db: Session = Depends(get_db),
):
    start_d, end_d = _parse_dates(from_date, to_date, days)
    summary = crud.dashboard_summary(db)
    points = crud.dashboard_daily_range(db, start_d, end_d)
    return {
        "summary": summary,
        "daily": points,
        "from_date": start_d.isoformat(),
        "to_date": end_d.isoformat(),
    }


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    return crud.dashboard_summary(db)


@router.get("/dashboard/daily", response_model=DashboardDaily)
def dashboard_daily(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    return {"days": days, "points": crud.dashboard_daily(db, days)}
