"""Schema cho Mã giảm giá của shop (Task T3D2BFB)."""

import re
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CODE_PATTERN = re.compile(r"^[A-Z0-9_-]+$")


def normalize_code(value: str) -> str:
    """Chuẩn hoá mã: bỏ khoảng trắng 2 đầu, viết hoa."""
    return (value or "").strip().upper()


def to_local_naive(value: datetime | None) -> datetime | None:
    """Đổi datetime có múi giờ (VD '...Z') về giờ máy chủ, bỏ tzinfo để so sánh thống nhất."""
    if value is not None and value.tzinfo is not None:
        return value.astimezone().replace(tzinfo=None)
    return value


class VoucherCreate(BaseModel):
    code: str = Field(min_length=3, max_length=30, examples=["GIAM10"])
    description: str | None = Field(default=None, max_length=255)
    discount_type: Literal["PERCENT", "FIXED"] = Field(examples=["PERCENT"])
    discount_value: Decimal = Field(gt=0, examples=[10])
    max_discount_amount: Decimal | None = Field(default=None, gt=0, examples=[30000])
    min_order_amount: Decimal = Field(default=Decimal("0"), ge=0, examples=[200000])
    usage_limit: int = Field(ge=1, le=100000, examples=[100])
    per_user_limit: int = Field(default=1, ge=1, le=100)
    starts_at: datetime | None = None
    expires_at: datetime

    @field_validator("code")
    @classmethod
    def _check_code(cls, value: str) -> str:
        code = normalize_code(value)
        if len(code) < 3:
            raise ValueError("Mã giảm giá phải có ít nhất 3 ký tự")
        if not CODE_PATTERN.match(code):
            raise ValueError(
                "Mã chỉ gồm chữ cái không dấu, chữ số, dấu gạch ngang (-) hoặc gạch dưới (_)"
            )
        return code

    @field_validator("starts_at", "expires_at")
    @classmethod
    def _normalize_dt(cls, value: datetime | None) -> datetime | None:
        return to_local_naive(value)

    @model_validator(mode="after")
    def _check_rules(self):
        if self.discount_type == "PERCENT" and self.discount_value > 100:
            raise ValueError("Giảm theo phần trăm chỉ được từ 1% đến 100%")
        if self.discount_type == "FIXED":
            self.max_discount_amount = None
        if self.starts_at and self.expires_at <= self.starts_at:
            raise ValueError("Hạn dùng phải sau thời điểm bắt đầu")
        if self.expires_at <= datetime.now():
            raise ValueError("Hạn dùng phải sau thời điểm hiện tại")
        if self.per_user_limit > self.usage_limit:
            raise ValueError("Số lượt mỗi người không được lớn hơn tổng số lượt")
        return self


class VoucherUpdate(BaseModel):
    """Sửa mã (không cho đổi code để tránh nhầm lẫn với đơn đã dùng)."""

    description: str | None = Field(default=None, max_length=255)
    discount_type: Literal["PERCENT", "FIXED"] | None = None
    discount_value: Decimal | None = Field(default=None, gt=0)
    max_discount_amount: Decimal | None = Field(default=None, gt=0)
    min_order_amount: Decimal | None = Field(default=None, ge=0)
    usage_limit: int | None = Field(default=None, ge=1, le=100000)
    per_user_limit: int | None = Field(default=None, ge=1, le=100)
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    status: Literal["ACTIVE", "INACTIVE"] | None = None

    @field_validator("starts_at", "expires_at")
    @classmethod
    def _normalize_dt(cls, value: datetime | None) -> datetime | None:
        return to_local_naive(value)


class VoucherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_id: int
    code: str
    description: str | None = None
    discount_type: str
    discount_value: float
    max_discount_amount: float | None = None
    min_order_amount: float
    usage_limit: int
    used_count: int
    remaining_uses: int
    per_user_limit: int
    starts_at: datetime | None = None
    expires_at: datetime
    status: str
    # Trạng thái hiển thị: ACTIVE | UPCOMING | EXPIRED | USED_UP | INACTIVE
    state: str
    created_at: datetime | None = None


class VoucherPublicOut(BaseModel):
    """Thông tin mã hiển thị công khai cho người mua (không lộ số liệu nội bộ)."""

    code: str
    description: str | None = None
    discount_type: str
    discount_value: float
    max_discount_amount: float | None = None
    min_order_amount: float
    expires_at: datetime
    remaining_uses: int


class VoucherDeleteResult(BaseModel):
    action: Literal["deleted", "deactivated"]
    message: str
    voucher: VoucherOut | None = None


class VoucherApplyRequest(BaseModel):
    code: str = Field(min_length=1, max_length=30, examples=["GIAM10"])
    cart_item_ids: list[int] | None = Field(
        default=None, description="Chỉ tính trên các dòng giỏ hàng được chọn (None = cả giỏ)"
    )


class VoucherApplyResponse(BaseModel):
    voucher_id: int
    code: str
    shop_id: int
    shop_name: str
    discount_type: str
    discount_value: float
    subtotal: float
    discount_amount: float
    total_after_discount: float
    message: str
