
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    shop_id: int
    category_id: int
    name: str
    description: str | None = None
    price: Decimal = Field(ge=0)
    stock: int = Field(ge=0)


class ProductUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = None
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    status: str | None = None


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

    model_config = ConfigDict(from_attributes=True)
