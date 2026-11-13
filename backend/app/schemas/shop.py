
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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


