"""Router cho API Đặt hàng & Đơn hàng.

Đường dẫn: /api/orders
Yêu cầu:
- Tách đơn theo shop
- Kiểm tra tồn, trừ kho
- 2 người mua sản phẩm cuối không làm tồn âm
- Lưu giá lúc đặt
- Xoá các dòng đã đặt khỏi giỏ trong một transaction
- Lỗi giữa chừng rollback
- Thanh toán mô phỏng đánh dấu đã thanh toán
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.crud import order as order_crud
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.order import (
    OrderCheckout,
    OrderCheckoutResponse,
    OrderResponse,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", response_model=OrderCheckoutResponse, status_code=status.HTTP_201_CREATED, summary="Đặt hàng trong Transaction (tách đơn theo shop, trừ kho, rollback nếu lỗi)")
def checkout_orders(
    checkout_data: OrderCheckout,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đặt hàng từ giỏ hàng trong một Transaction duy nhất:

    - Tự động tách đơn theo từng Shop riêng biệt
    - Khóa bản ghi (SELECT FOR UPDATE) để chống Race Condition (2 người mua cuối cùng không bị âm kho)
    - Trừ tồn kho và lưu giá chốt tại thời điểm đặt (snapshot price)
    - Xoá các sản phẩm đã đặt khỏi giỏ hàng
    - Lỗi bất kỳ dòng nào đều tự động Rollback toàn bộ
    - Thanh toán mô phỏng (SIMULATED) tự động đánh dấu đã thanh toán (status = confirmed)
    """
    return order_crud.create_orders_from_cart(db, current_user.id, checkout_data)


@router.get("", response_model=list[OrderResponse], summary="Lấy danh sách các đơn hàng của tôi")
def get_my_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy toàn bộ lịch sử đơn hàng của người dùng hiện tại."""
    return order_crud.get_user_orders(db, current_user.id)


@router.get("/{order_id}", response_model=OrderResponse, summary="Xem chi tiết một đơn hàng")
def get_order_by_id(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xem chi tiết đơn hàng (kèm danh sách sản phẩm, shop và giá lúc đặt)."""
    return order_crud.get_order_detail(db, current_user.id, order_id)
