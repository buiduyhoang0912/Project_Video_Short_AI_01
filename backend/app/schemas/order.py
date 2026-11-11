from pydantic import BaseModel
from typing import List
from datetime import datetime

class OrderCreate(BaseModel):
    shop_id: int
    address_id: int
    payment_method: str = "COD"  # COD hoặc MÔ PHỎNG

class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    buyer_id: int
    shop_id: int
    total_amount: float
    payment_method: str
    status: str
    recipient_name: str
    recipient_phone: str
    recipient_address: str
    created_at: datetime
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True
        