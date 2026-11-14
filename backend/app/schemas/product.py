"""Schema dữ liệu cho Sản phẩm (Product), Ảnh, Shop, Video gắn kèm và Phân trang."""
import enum
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


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
    image_url: str
    is_primary: bool = False
    display_order: int = 0


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
    name: str = Field(min_length=1, max_length=255, examples=["Áo thun phong cách"])
    description: str | None = Field(default=None, examples=["Chất liệu cotton thoáng mát"])
    price: Decimal = Field(default=Decimal("0"), ge=0, examples=[150000])
    stock: int = Field(default=0, ge=0, description="Số lượng tồn kho", examples=[50])
    category_id: int | None = Field(default=None, examples=[1])
    thumbnail_url: str | None = Field(default=None, examples=["https://example.com/thumb.jpg"])


class ProductCreate(ProductBase):
    shop_id: int = Field(..., examples=[1])
    status: str = Field(default="ACTIVE", examples=["ACTIVE"])


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    category_id: int | None = None
    thumbnail_url: str | None = None
    status: str | None = None


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
    sold_count: int
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
    sold_count: int = Field(..., description="Đã bán")
    thumbnail_url: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    # Thông tin Shop
    shop: ShopBriefOut

    # Thông tin Danh mục
    category: CategoryBriefOut | None = None

    # Danh sách ảnh
    images: list[ProductImageOut] = []

    # Danh sách video có gắn sản phẩm
    videos: list[VideoBriefOut] = []


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

    model_config = ConfigDict(from_attributes=True)
