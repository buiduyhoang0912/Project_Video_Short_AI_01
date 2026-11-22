"""Schema dữ liệu cho Sản phẩm (Product), Ảnh, Shop, Video gắn kèm và Phân trang."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product_image import ProductImageOut as SellerProductImageOut


class ProductSortBy(str, enum.Enum):
    PRICE_ASC = "price_asc"          # Giá tăng dần
    PRICE_DESC = "price_desc"        # Giá giảm dần
    NEWEST = "newest"                # Mới nhất
    BEST_SELLING = "best_selling"    # Bán chạy


# --- Sub-schemas ---
class ShopBriefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    logo_url: str | None = None
    description: str | None = None
    status: str


class CategoryBriefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    icon_url: str | None = None


class ProductImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int | None = None
    object_key: str | None = None
    image_url: str | None = None
    is_primary: bool = False
    sort_order: int = 0
    display_order: int = 0
    created_at: datetime | None = None


class VideoBriefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    video_url: str
    thumbnail_url: str | None = None
    duration_seconds: int = 0
    view_count: int = 0


# --- Base & Create/Update ---
class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=200, examples=["Áo thun phong cách"])
    description: str | None = Field(default=None, examples=["Chất liệu cotton thoáng mát"])
    price: Decimal = Field(gt=0, examples=[150000])
    stock: int = Field(default=0, ge=0, description="Số lượng tồn kho", examples=[50])
    category_id: int = Field(..., examples=[1])
    thumbnail_url: str | None = Field(default=None, examples=["https://example.com/thumb.jpg"])


class ProductCreate(ProductBase):
    shop_id: int | None = Field(default=None, examples=[1])
    status: str = Field(default="ACTIVE", examples=["ACTIVE"])


class ProductUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    thumbnail_url: str | None = None
    status: Literal["ACTIVE", "HIDDEN", "INACTIVE"] | None = None


class ProductStockUpdate(BaseModel):
    stock: int = Field(ge=0)


class ProductAiSuggestRequest(BaseModel):
    raw_name: str = Field(
        min_length=1,
        max_length=200,
        description="Tên sản phẩm thô hoặc ý tưởng sản phẩm",
    )
    category_id: int | None = None
    category_name: str | None = Field(default=None, max_length=100)
    price: Decimal | float | None = Field(default=None, ge=0)
    features: str | None = Field(
        default=None,
        max_length=1000,
        description="Đặc điểm nổi bật hoặc ghi chú thêm của người bán",
    )
    duration_seconds: int = Field(
        default=45,
        ge=30,
        le=60,
        description="Thời lượng kịch bản video ngắn (30-60 giây)",
    )


class ProductAiSuggestResponse(BaseModel):
    suggested_name: str
    alternative_names: list[str] = Field(default_factory=list)
    suggested_description: str
    video_script_30_60s: str
    suggested_hashtags: list[str] = Field(default_factory=list)
    provider: str = "clipshop-ai"


# --- Output Schemas ---
class ProductListItemOut(BaseModel):
    """Item trả về trong danh sách sản phẩm (tìm kiếm / lọc / phân trang)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_id: int
    shop_name: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    name: str
    price: float
    stock: int
    sold_count: int = 0
    thumbnail_url: str | None = None
    status: str
    created_at: datetime


class ProductListResponse(BaseModel):
    """Kết quả phân trang danh sách sản phẩm."""
    items: list[ProductListItemOut]
    total: int = Field(..., description="Tổng số sản phẩm thoả mãn điều kiện")
    page: int = Field(..., ge=1, description="Trang hiện tại")
    page_size: int = Field(..., ge=1, description="Số lượng mỗi trang")
    total_pages: int = Field(..., description="Tổng số trang")


class ProductDetailOut(BaseModel):
    """Chi tiết sản phẩm kèm ảnh, tồn, shop, video có gắn sản phẩm."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    price: float
    stock: int = Field(..., description="Số lượng tồn kho")
    sold_count: int = Field(default=0, description="Đã bán")
    thumbnail_url: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime | None = None

    # Thông tin Shop
    shop: ShopBriefOut | None = None

    # Thông tin Danh mục
    category: CategoryBriefOut | None = None

    # Danh sách ảnh
    images: list[ProductImageOut] = Field(default_factory=list)

    # Danh sách video có gắn sản phẩm
    videos: list[VideoBriefOut] = Field(default_factory=list)


class ProductOut(BaseModel):
    id: int
    shop_id: int
    category_id: int
    name: str
    description: str | None = None
    price: Decimal
    stock: int
    status: str
    created_at: datetime
    images: list[SellerProductImageOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
