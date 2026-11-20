"""Schema cho kiểm duyệt video/sản phẩm và dashboard Admin (T3D201D)."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HideRequest(BaseModel):
    """Body khi ẩn nội dung vi phạm: lý do bắt buộc."""

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def trim_reason(cls, value):
        return value.strip() if isinstance(value, str) else value


class VideoVisibilityRequest(BaseModel):
    """Body cho endpoint /api/admin/videos/{id}/visibility."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["VISIBLE", "HIDDEN"] | None = None
    is_visible: bool | None = None
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def trim_reason(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_visibility(self):
        # Bắt buộc phải có ít nhất một lựa chọn trạng thái
        if self.status is None and self.is_visible is None:
            raise ValueError("Phải chỉ định trạng thái hiển thị (status hoặc is_visible)")

        # Kiểm tra mâu thuẫn nếu truyền cả 2
        if self.status is not None and self.is_visible is not None:
            if (self.status == "VISIBLE" and not self.is_visible) or (
                self.status == "HIDDEN" and self.is_visible
            ):
                raise ValueError("status và is_visible mâu thuẫn nhau")

        is_hide = (self.status == "HIDDEN") or (self.is_visible is False)
        if is_hide and not self.reason:
            raise ValueError("Lý do ẩn video là bắt buộc")
        return self


class ProductVisibilityRequest(BaseModel):
    """Body cho endpoint /api/admin/products/{id}/visibility."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ACTIVE", "HIDDEN"] | None = None
    is_visible: bool | None = None
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def trim_reason(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_visibility(self):
        # Bắt buộc phải có ít nhất một lựa chọn trạng thái
        if self.status is None and self.is_visible is None:
            raise ValueError("Phải chỉ định trạng thái hiển thị (status hoặc is_visible)")

        # Kiểm tra mâu thuẫn nếu truyền cả 2
        if self.status is not None and self.is_visible is not None:
            if (self.status == "ACTIVE" and not self.is_visible) or (
                self.status == "HIDDEN" and self.is_visible
            ):
                raise ValueError("status và is_visible mâu thuẫn nhau")

        is_hide = (self.status == "HIDDEN") or (self.is_visible is False)
        if is_hide and not self.reason:
            raise ValueError("Lý do ẩn sản phẩm là bắt buộc")
        return self


class OwnerInfo(BaseModel):
    id: int
    username: str
    display_name: str


class ModerationVideoOut(BaseModel):
    id: int
    title: str
    owner: OwnerInfo
    status: str  # VISIBLE | HIDDEN
    view_count: int
    thumbnail_url: str | None = None
    moderation_reason: str | None = None
    moderated_at: datetime | None = None
    created_at: datetime


class ModerationProductOut(BaseModel):
    id: int
    name: str
    shop_id: int
    shop_name: str
    price: Decimal
    status: str  # ACTIVE | HIDDEN | INACTIVE
    thumbnail_url: str | None = None
    moderation_reason: str | None = None
    moderated_at: datetime | None = None
    created_at: datetime


class DashboardSummary(BaseModel):
    total_users: int
    total_sellers: int
    total_videos: int
    total_products: int
    total_orders: int
    total_revenue: Decimal


class DailyPoint(BaseModel):
    date: str  # YYYY-MM-DD
    new_users: int
    new_videos: int
    orders: int
    revenue: Decimal


class DashboardDaily(BaseModel):
    days: int
    points: list[DailyPoint]


class DashboardCombined(BaseModel):
    summary: DashboardSummary
    daily: list[DailyPoint]
    from_date: str
    to_date: str
