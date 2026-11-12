"""Schema dữ liệu đơn đăng ký bán hàng."""

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class SellerApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposed_shop_name: str = Field(
        min_length=1,
        max_length=150,
    )

    phone: str = Field(
        min_length=10,
        max_length=20,
        pattern=r"^\+?[0-9]{10,15}$",
    )

    description: str = Field(
        min_length=1,
        max_length=2000,
    )

    @field_validator(
        "proposed_shop_name",
        "phone",
        "description",
        mode="before",
    )
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class SellerApplicationReject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rejection_reason: str = Field(
        min_length=1,
        max_length=500,
    )

    @field_validator("rejection_reason", mode="before")
    @classmethod
    def trim_reason(cls, value):
        return value.strip() if isinstance(value, str) else value


class SellerApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    proposed_shop_name: str
    phone: str
    description: str

    status: Literal["PENDING", "APPROVED", "REJECTED"]

    rejection_reason: str | None
    reviewed_by: int | None
    reviewed_at: datetime | None

    created_at: datetime
    updated_at: datetime