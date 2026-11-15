from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product_image import ProductImageOut


class ProductCreate(BaseModel):
    shop_id: int | None = None
    category_id: int
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    price: Decimal = Field(gt=0)
    stock: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    status: Literal["ACTIVE", "HIDDEN", "INACTIVE"] | None = None


class ProductStockUpdate(BaseModel):
    stock: int = Field(ge=0)


class ProductOut(BaseModel):
    id: int
    shop_id: int
    category_id: int
    name: str
    description: str | None
    price: Decimal
    stock: int
    status: str
    created_at: datetime
    images: list[ProductImageOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
