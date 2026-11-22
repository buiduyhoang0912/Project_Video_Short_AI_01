from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ShopCreate(BaseModel):
    owner_id: int | None = None
    name: str = Field(min_length=1, max_length=150)
    avatar_key: str | None = Field(default=None, max_length=512)
    description: str | None = None
    address: str | None = Field(default=None, max_length=255)


class ShopUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    avatar_key: str | None = Field(default=None, max_length=512)
    description: str | None = None
    address: str | None = Field(default=None, max_length=255)
    status: Literal["ACTIVE", "INACTIVE"] | None = None


class ShopOut(BaseModel):
    id: int
    owner_id: int
    name: str
    avatar_key: str | None
    description: str | None
    address: str | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


OrderStatusLiteral = Literal[
    "pending", "confirmed", "shipping", "completed", "cancelled"
]


class ShopOrderStatusUpdate(BaseModel):
    status: OrderStatusLiteral

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value


class DailyRevenueItem(BaseModel):
    date: str
    revenue: float
    completed_orders: int
    total_orders: int


class BestSellingProductItem(BaseModel):
    product_id: int
    product_name: str
    price: float
    stock: int
    total_quantity_sold: int
    total_revenue: float
    thumbnail_url: str | None = None


class ShopAnalyticsOut(BaseModel):
    shop_id: int
    shop_name: str
    total_orders: int
    pending_orders: int
    confirmed_orders: int
    shipping_orders: int
    completed_orders: int
    cancelled_orders: int
    total_revenue: float
    estimated_revenue: float
    daily_revenue: list[DailyRevenueItem] = Field(default_factory=list)
    best_selling_products: list[BestSellingProductItem] = Field(
        default_factory=list
    )
