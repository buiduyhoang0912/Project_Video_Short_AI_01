
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CategoryCreate(BaseModel):
    name: str
    description: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class CategoryOut(BaseModel):
    id: int
    name: str
    description: str | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

