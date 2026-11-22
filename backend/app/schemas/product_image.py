
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProductImageCreate(BaseModel):
    product_id: int
    object_key: str
    is_primary: bool = False
    sort_order: int = 0


class ProductImageUpdate(BaseModel):
    object_key: str | None = None
    is_primary: bool | None = None
    sort_order: int | None = None


class ProductImageOut(BaseModel):
    id: int
    product_id: int
    object_key: str
    is_primary: bool
    sort_order: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
