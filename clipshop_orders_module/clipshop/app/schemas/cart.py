from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=999)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=999)


class CartProductBrief(BaseModel):
    """Thông tin sản phẩm hiển thị trong giỏ (đọc từ model Product của module Shop)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_id: int
    name: str
    price: Decimal
    stock: int
    status: str


class CartItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    product: CartProductBrief

    @computed_field
    @property
    def line_total(self) -> Decimal:
        return self.product.price * self.quantity


class CartRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    items: list[CartItemRead] = []

    @computed_field
    @property
    def total_amount(self) -> Decimal:
        return sum((i.line_total for i in self.items), Decimal("0"))
