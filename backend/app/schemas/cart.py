from pydantic import BaseModel, Field
from typing import List

class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, description="Số lượng phải lớn hơn 0")

class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0)

class CartItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int

    class Config:
        from_attributes = True

class CartResponse(BaseModel):
    id: int
    user_id: int
    items: List[CartItemResponse] = []

    class Config:
        from_attributes = True