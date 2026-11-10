from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.order import OrderStatus, PaymentMethod
from app.schemas.address import validate_phone


class OrderCreate(BaseModel):
    """Checkout MỘT shop: backend lấy các dòng giỏ thuộc `shop_id`, tự đọc giá/tồn kho từ DB
    (không tin dữ liệu giá/tồn từ frontend). Giỏ nhiều shop → gọi lần lượt từng shop.
    Địa chỉ: chọn `address_id` HOẶC nhập trực tiếp 3 trường recipient_*/shipping_address."""

    shop_id: int
    payment_method: PaymentMethod
    address_id: int | None = None
    recipient_name: str | None = Field(default=None, min_length=1, max_length=100)
    recipient_phone: str | None = None
    shipping_address: str | None = Field(default=None, min_length=5, max_length=500)

    @field_validator("recipient_phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return None if v is None else validate_phone(v)

    @model_validator(mode="after")
    def _address_xor_inline(self):
        inline = (self.recipient_name, self.recipient_phone, self.shipping_address)
        if self.address_id is not None:
            if any(x is not None for x in inline):
                raise ValueError("Chỉ dùng address_id hoặc nhập địa chỉ trực tiếp, không dùng cả hai")
        elif not all(inline):
            raise ValueError("Cần address_id hoặc đủ recipient_name, recipient_phone, shipping_address")
        return self


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    unit_price: Decimal  # giá tại thời điểm đặt
    quantity: int
    line_total: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_code: str
    buyer_id: int
    shop_id: int
    recipient_name: str
    recipient_phone: str
    shipping_address: str
    payment_method: PaymentMethod
    total_amount: Decimal
    status: OrderStatus
    created_at: datetime
    items: list[OrderItemRead] = []


class OrderStatusUpdate(BaseModel):
    """PATCH /api/seller/orders/{id}/status — service kiểm tra Order.can_transition_to()."""

    status: OrderStatus
