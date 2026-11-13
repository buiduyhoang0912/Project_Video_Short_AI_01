"""API đơn đăng ký bán hàng: /api/seller-applications

- POST /api/seller-applications               Gửi đơn đăng ký bán hàng (mỗi người 1 đơn PENDING)
- GET  /api/seller-applications/me            Xem các đơn đăng ký của chính mình
- GET  /api/seller-applications               Danh sách đơn (Admin xem tất cả, User xem của mình)
- GET  /api/seller-applications/{id}          Xem chi tiết 1 đơn
- PUT  /api/seller-applications/{id}/approve  Admin duyệt đơn (chuyển User -> SELLER)
- PUT  /api/seller-applications/{id}/reject   Admin từ chối đơn kèm lý do
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import seller_application as sa_crud
from app.crud import shop as shop_crud
from app.db.session import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.seller_application import (
    SellerApplicationCreate,
    SellerApplicationRead,
    SellerApplicationReject,
)

router = APIRouter(prefix="/seller-applications", tags=["Seller Applications"])


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Admin mới có quyền thực hiện thao tác này",
        )
    return user


@router.post(
    "",
    response_model=SellerApplicationRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_seller_application(
    data: SellerApplicationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if (
        user.role == "SELLER"
        or sa_crud.get_approved_application_by_user(db, user.id) is not None
        or shop_crud.get_shop_by_owner(db, user.id) is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tài khoản của bạn đã được duyệt làm người bán",
        )

    if sa_crud.get_pending_application_by_user(db, user.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bạn đã có một đơn đăng ký bán hàng đang chờ duyệt",
        )

    return sa_crud.create_application(db, user.id, data)


@router.get("/me", response_model=list[SellerApplicationRead])
def list_my_applications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return sa_crud.get_applications_by_user(db, user.id)


@router.get("", response_model=list[SellerApplicationRead])
def list_applications(
    status_filter: Literal["PENDING", "APPROVED", "REJECTED"] | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role == "ADMIN":
        return sa_crud.get_all_applications(db, status_filter=status_filter)
    return sa_crud.get_applications_by_user(db, user.id)


@router.get("/{application_id}", response_model=SellerApplicationRead)
def get_application_detail(
    application_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    application = sa_crud.get_application(db, application_id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đơn đăng ký bán hàng",
        )

    if user.role != "ADMIN" and application.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xem đơn đăng ký này",
        )

    return application


@router.put("/{application_id}/approve", response_model=SellerApplicationRead)
def approve_seller_application(
    application_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    application = sa_crud.get_application(db, application_id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đơn đăng ký bán hàng",
        )

    if application.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chỉ có thể duyệt đơn đang ở trạng thái chờ (PENDING)",
        )

    return sa_crud.approve_application(db, application, admin.id)


@router.put("/{application_id}/reject", response_model=SellerApplicationRead)
def reject_seller_application(
    application_id: int,
    data: SellerApplicationReject,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    application = sa_crud.get_application(db, application_id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đơn đăng ký bán hàng",
        )

    if application.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chỉ có thể từ chối đơn đang ở trạng thái chờ (PENDING)",
        )

    return sa_crud.reject_application(
        db, application, admin.id, data.rejection_reason
    )

