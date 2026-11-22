from pydantic import BaseModel
from typing import Optional

class AddressCreate(BaseModel):
    recipient_name: str
    phone: str
    address_line: str
    is_default: Optional[bool] = False

class AddressResponse(AddressCreate):
    id: int
    user_id: int

    class Config:
        from_attributes = True