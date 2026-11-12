from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator


def check_video_description(value: str) -> str:
    if len(value.encode("utf-8")) > 65_535:
        raise ValueError("Mô tả không được vượt quá 65.535 byte UTF-8.")
    return value


VideoDescription = Annotated[str, AfterValidator(check_video_description)]

class VideoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: VideoDescription | None = None
    hashtags: list[str] | None = None
    video_url: str = Field(min_length=1, max_length=500)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    duration_seconds: int = Field(gt=0)
    status: Literal["VISIBLE", "HIDDEN"] = "VISIBLE"
    product_ids: list[int] = Field(default_factory=list, max_length=3)

    @field_validator("product_ids")
    @classmethod
    def validate_product_ids(cls, product_ids):
        da_gap = []

        for product_id in product_ids:
            if product_id <= 0:
                raise ValueError("ID sản phẩm phải lớn hơn 0")

            if product_id in da_gap:
                raise ValueError("Danh sách có ID sản phẩm bị trùng")

            da_gap.append(product_id)

        return product_ids

class VideoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    description: str | None
    hashtags: list[str] | None
    video_url: str
    thumbnail_url: str | None
    duration_seconds: int
    view_count: int
    status: Literal["VISIBLE", "HIDDEN"]
    created_at: datetime
    product_ids: list[int]

class VideoProductCreate(BaseModel):
    video_id: int = Field(gt=0)
    product_id: int = Field(gt=0)


class VideoProductRead(VideoProductCreate):
    model_config = ConfigDict(from_attributes=True)

class VideoDescriptionUpdate(BaseModel):
    description: VideoDescription | None