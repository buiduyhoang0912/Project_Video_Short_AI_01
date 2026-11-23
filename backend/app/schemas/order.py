"""Schema cho API Đơn hàng & Đặt hàng (Orders)."""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class OrderCheckout(BaseModel):
    """Dữ liệu yêu cầu thanh toán/đặt hàng."""
    address_id: int | None = Field(default=None, description="ID địa chỉ đã lưu của user")
    recipient_name: str | None = Field(default=None, max_length=100)
    recipient_phone: str | None = Field(default=None, max_length=20)
    recipient_address: str | None = Field(default=None, max_length=255)
    payment_method: str = Field(default="COD", description="Phương thức thanh toán: COD hoặc SIMULATED (Mô phỏng)")
    cart_item_ids: list[int] | None = Field(default=None, description="Danh sách id trong giỏ cần đặt (None = đặt tất cả)")
    voucher_codes: list[str] | None = Field(
        default=None,
        max_length=20,
        description="Mã giảm giá của shop (mỗi shop tối đa 1 mã). Server tự kiểm tra và tính lại tiền.",
    )


class OrderCreate(BaseModel):
    """Schema tạo đơn trực tiếp (cho 1 shop)."""
    shop_id: int
    address_id: int | None = None
    recipient_name: str | None = None
    recipient_phone: str | None = None
    recipient_address: str | None = None
    payment_method: str = "COD"


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str | None = None
    quantity: int
    unit_price: float
    line_total: float | None = None


class OrderStatusTimeline(BaseModel):
    """Một mốc trên dòng thời gian trạng thái đơn hàng."""
    status_code: str
    title: str
    description: str
    timestamp: datetime | None = None
    is_current: bool = False
    is_completed: bool = False


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    buyer_id: int
    shop_id: int
    shop_name: str | None = None
    total_amount: float
    payment_method: str
    status: str
    recipient_name: str
    recipient_phone: str
    recipient_address: str
    created_at: datetime
    items: list[OrderItemResponse] = []
    # Mã giảm giá của shop (T3D2BFB): total_amount = subtotal_amount - discount_amount
    subtotal_amount: float | None = None
    discount_amount: float = 0.0
    voucher_code: str | None = None
    timeline: list[OrderStatusTimeline] = []
    # VietQR payment fields (T3D2C15)
    payment_status: str = "UNPAID"
    vietqr_url: str | None = None
    bank_name: str | None = None
    bank_account_number: str | None = None
    bank_account_holder: str | None = None


class OrderCancelResponse(BaseModel):
    message: str
    order_id: int
    status: str
    restocked_items_count: int



class OrderCheckoutResponse(BaseModel):
    message: str
    total_orders_created: int
    total_amount: float
    orders: list[OrderResponse] = []
    total_before_discount: float | None = None
    total_discount: float = 0.0
