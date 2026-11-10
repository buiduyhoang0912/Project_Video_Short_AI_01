
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ShopCreate(BaseModel):
    owner_id: int
    name: str
    avatar_key: str | None = None
    description: str | None = None
    address: str | None = None


class ShopUpdate(BaseModel):
    name: str | None = None
    avatar_key: str | None = None
    description: str | None = None
    address: str | None = None
    status: str | None = None


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

