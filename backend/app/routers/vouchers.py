"""API Mã giảm giá của shop (Task T3D2BFB).

Người bán (cần đăng nhập + có shop):
- GET    /api/shops/me/vouchers                Danh sách mã của shop mình
- POST   /api/shops/me/vouchers                Tạo mã (PERCENT/FIXED, đơn tối thiểu, hạn dùng, số lượt)
- PUT    /api/shops/me/vouchers/{voucher_id}   Sửa mã / bật - tắt mã
- DELETE /api/shops/me/vouchers/{voucher_id}   Xoá mã (đã có đơn dùng thì chỉ tắt)

Công khai:
- GET    /api/shops/{shop_id}/vouchers         Mã đang áp dụng được của shop

Người mua (cần đăng nhập):
- POST   /api/vouchers/apply                   Xem trước số tiền được giảm trên giỏ hàng
- Khi đặt hàng: gửi "voucher_codes" trong POST /api/orders, server kiểm tra và tính lại tiền.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import shop as shop_crud
from app.crud import voucher as voucher_crud
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.shop import Shop
from app.models.user import User
from app.schemas.voucher import (
    VoucherApplyRequest,
    VoucherApplyResponse,
    VoucherCreate,
    VoucherDeleteResult,
    VoucherOut,
    VoucherPublicOut,
    VoucherUpdate,
)

router = APIRouter(tags=["Vouchers"])


def _get_seller_shop(db: Session, user: User) -> Shop:
    if (user.role or "").upper() not in {"SELLER", "ADMIN"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ tài khoản người bán mới được quản lý mã giảm giá",
        )
    shop = shop_crud.get_shop_by_owner(db, user.id)
    if shop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bạn chưa có cửa hàng nào",
        )
    return shop


# ---------- Người bán (đặt các route /me TRƯỚC route /{shop_id}) ----------

@router.get("/shops/me/vouchers", response_model=list[VoucherOut])
def list_my_vouchers(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return voucher_crud.list_shop_vouchers(db, _get_seller_shop(db, user))


@router.post(
    "/shops/me/vouchers",
    response_model=VoucherOut,
    status_code=status.HTTP_201_CREATED,
)
def create_my_voucher(
    data: VoucherCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return voucher_crud.create_voucher(db, _get_seller_shop(db, user), data)


@router.put("/shops/me/vouchers/{voucher_id}", response_model=VoucherOut)
def update_my_voucher(
    voucher_id: int,
    data: VoucherUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return voucher_crud.update_voucher(db, _get_seller_shop(db, user), voucher_id, data)


@router.delete("/shops/me/vouchers/{voucher_id}", response_model=VoucherDeleteResult)
def delete_my_voucher(
    voucher_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return voucher_crud.delete_voucher(db, _get_seller_shop(db, user), voucher_id)


# ---------- Công khai ----------

@router.get("/shops/{shop_id}/vouchers", response_model=list[VoucherPublicOut])
def list_public_shop_vouchers(shop_id: int, db: Session = Depends(get_db)):
    shop = shop_crud.get_public_shop(db, shop_id)
    if shop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy cửa hàng id={shop_id}",
        )
    return voucher_crud.list_public_vouchers(db, shop_id)


# ---------- Người mua ----------

@router.post("/vouchers/apply", response_model=VoucherApplyResponse)
def apply_voucher_preview(
    data: VoucherApplyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return voucher_crud.preview_apply_voucher(db, user.id, data)
