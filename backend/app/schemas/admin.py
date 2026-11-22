"""Schema cho API quản trị (Admin): duyệt đơn bán hàng và quản lý tài khoản."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApplicantInfo(BaseModel):
    id: int
    username: str
    display_name: str
    email: str


class AdminSellerApplicationRead(BaseModel):
    id: int
    user_id: int
    applicant: ApplicantInfo
    proposed_shop_name: str
    phone: str
    description: str
    status: Literal["PENDING", "APPROVED", "REJECTED"]
    rejection_reason: str | None
    reviewed_by: int | None
    reviewed_at: datetime | None
    created_at: datetime


class AdminRejectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rejection_reason: str = Field(min_length=1, max_length=500)

    @field_validator("rejection_reason", mode="before")
    @classmethod
    def trim_reason(cls, value):
        return value.strip() if isinstance(value, str) else value


class AdminUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    email: str
    role: Literal["USER", "SELLER", "ADMIN"]
    status: Literal["ACTIVE", "LOCKED"]
    created_at: datetime
