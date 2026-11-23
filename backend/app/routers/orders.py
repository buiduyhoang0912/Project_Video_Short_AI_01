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
- Lọc đơn theo trạng thái
- Xem chi tiết đơn hàng kèm dòng thời gian trạng thái
- Huỷ đơn khi còn Chờ xác nhận và hoàn tồn đúng một lần
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.crud import order as order_crud
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.order import (
    OrderCancelResponse,
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


@router.get("", response_model=list[OrderResponse], summary="Lấy danh sách các đơn hàng của tôi (hỗ trợ lọc theo status)")
def get_my_orders(
    status_filter: str | None = Query(default=None, alias="status", description="Lọc theo trạng thái: PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy danh sách đơn hàng của người dùng hiện tại, có thể lọc theo trạng thái."""
    return order_crud.get_user_orders(db, current_user.id, status_filter)


@router.get("/{order_id}", response_model=OrderResponse, summary="Xem chi tiết một đơn hàng kèm dòng thời gian trạng thái")
def get_order_by_id(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xem chi tiết đơn hàng (kèm danh sách sản phẩm, shop, giá lúc đặt và dòng thời gian trạng thái)."""
    return order_crud.get_order_detail(db, current_user.id, order_id)


@router.post("/{order_id}/cancel", response_model=OrderCancelResponse, summary="Huỷ đơn hàng khi còn Chờ xác nhận và hoàn tồn kho đúng một lần")
def cancel_my_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Huỷ đơn hàng của chính mình:
    - Chỉ cho phép huỷ khi đơn ở trạng thái Chờ xác nhận (PENDING)
    - Khóa đơn và hoàn tồn kho cho toàn bộ sản phẩm trong đơn đúng 1 lần (dùng Transaction)
    - Chuyển trạng thái đơn thành CANCELLED
    """
    return order_crud.cancel_order(db, current_user.id, order_id)
