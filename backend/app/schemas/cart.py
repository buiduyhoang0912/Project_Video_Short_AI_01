"""Schema cho API Giỏ hàng (Cart).

Đáp ứng yêu cầu:
- Thêm (cộng dồn)
- Sửa số lượng (không vượt tồn)
- Xoá sản phẩm
- Xem giỏ hàng nhóm theo shop
- Tạm tính tính tại server
- Chặn/đánh dấu sản phẩm đã ẩn
"""
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = Field(default=1, gt=0, description="Số lượng thêm vào giỏ, phải > 0")


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., gt=0, description="Số lượng mới, phải > 0")


class CartProductBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: float
    stock: int
    status: str
    thumbnail_url: str | None = None


class CartItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    product: CartProductBrief
    line_total: float = Field(..., description="Tạm tính dòng sản phẩm (price * quantity)")
    is_valid: bool = Field(..., description="Có hợp lệ để đặt hàng không (sản phẩm ACTIVE và đủ tồn kho)")
    error_message: str | None = Field(default=None, description="Thông báo lỗi nếu sản phẩm bị ẩn hoặc hết hàng")


class ShopCartGroup(BaseModel):
    shop_id: int
    shop_name: str
    items: list[CartItemOut] = []
    shop_subtotal: float = Field(default=0.0, description="Tạm tính của shop (chỉ tính sản phẩm hợp lệ)")


class CartViewResponse(BaseModel):
    id: int
    user_id: int
    shops: list[ShopCartGroup] = []
    total_valid_items: int = Field(default=0, description="Tổng số lượng sản phẩm hợp lệ")
    subtotal: float = Field(default=0.0, description="Tổng tiền tạm tính tính tại server")


# Backward compatibility schemas
class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int


class CartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    items: list[CartItemResponse] = []
