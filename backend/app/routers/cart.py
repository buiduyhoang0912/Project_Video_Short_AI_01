"""Router cho API Giỏ hàng.

Đường dẫn: /api/cart
Yêu cầu:
- Thêm (cộng dồn)
- Sửa số lượng (không vượt tồn)
- Xoá sản phẩm
- Xem giỏ nhóm theo shop
- Tạm tính tính ở server
- Chặn sản phẩm đã ẩn
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.crud import cart as cart_crud
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.cart import (
    CartItemAdd,
    CartItemOut,
    CartItemUpdate,
    CartViewResponse,
)

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("", response_model=CartViewResponse, summary="Xem giỏ hàng nhóm theo shop và tính tạm tính tại server")
def get_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xem giỏ hàng của người dùng hiện tại:

    - Nhóm sản phẩm theo từng Shop
    - Chặn/cảnh báo nếu sản phẩm đã bị ẩn hoặc hết hàng
    - Tính tổng tiền tạm tính chính xác tại server
    """
    return cart_crud.get_cart_view(db, current_user.id)


@router.post("/items", status_code=status.HTTP_201_CREATED, summary="Thêm sản phẩm vào giỏ (cộng dồn nếu đã có)")
def add_item_to_cart(
    data: CartItemAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Thêm sản phẩm vào giỏ hàng:

    - Nếu sản phẩm đã có trong giỏ -> tự động cộng dồn số lượng
    - Chặn thêm nếu sản phẩm đã bị ẩn hoặc không hoạt động
    - Kiểm tra không vượt quá số lượng tồn kho còn lại
    """
    cart_item = cart_crud.add_to_cart(db, current_user.id, data.product_id, data.quantity)
    return {
        "message": "Đã thêm sản phẩm vào giỏ hàng thành công",
        "cart_item_id": cart_item.id,
        "product_id": cart_item.product_id,
        "quantity": cart_item.quantity,
    }


@router.put("/items/{item_id}", summary="Cập nhật số lượng sản phẩm trong giỏ")
def update_item_quantity(
    item_id: int,
    data: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sửa số lượng của 1 dòng trong giỏ hàng:

    - Kiểm tra số lượng > 0 và không vượt quá tồn kho
    - Chặn sửa nếu sản phẩm đã bị ẩn
    """
    updated_item = cart_crud.update_cart_item_quantity(db, current_user.id, item_id, data.quantity)
    return {
        "message": "Cập nhật số lượng thành công",
        "cart_item_id": updated_item.id,
        "quantity": updated_item.quantity,
    }


@router.delete("/items/{item_id}", status_code=status.HTTP_200_OK, summary="Xoá một sản phẩm khỏi giỏ hàng")
def delete_item_from_cart(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xóa sản phẩm ra khỏi giỏ hàng."""
    cart_crud.delete_cart_item(db, current_user.id, item_id)
    return {"message": f"Đã xóa sản phẩm #{item_id} khỏi giỏ hàng"}


@router.delete("", status_code=status.HTTP_200_OK, summary="Xoá toàn bộ giỏ hàng")
def clear_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Làm trống giỏ hàng của người dùng."""
    cart_crud.clear_user_cart(db, current_user.id)
    return {"message": "Đã làm trống giỏ hàng thành công"}
