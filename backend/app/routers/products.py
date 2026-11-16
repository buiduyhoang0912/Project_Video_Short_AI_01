"""API cho Sản phẩm (Products). Đường dẫn: /api/products

Yêu cầu nghiệp vụ:
- Chỉ sản phẩm ACTIVE của shop đang hoạt động.
- Tìm kiếm theo tên (?q=...).
- Lọc theo: danh mục (?category_id=...), khoảng giá (?min_price=...&max_price=...), shop (?shop_id=...).
- Sắp xếp: giá (price_asc, price_desc), mới nhất (newest), bán chạy (best_selling).
- Phân trang: ?page=1&page_size=10 (trả về danh sách cùng total, page, page_size, total_pages).
- Xem chi tiết: GET /api/products/{id} kèm ảnh, tồn kho, shop, video có gắn sản phẩm.
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud import product as product_crud
from app.db.session import get_db
from app.schemas.product import (
    ProductCreate,
    ProductDetailOut,
    ProductListResponse,
    ProductSortBy,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=ProductListResponse, summary="Danh sách sản phẩm (tìm kiếm, lọc, sắp xếp, phân trang)")
def list_products(
    q: str | None = Query(None, description="Tìm theo tên sản phẩm"),
    category_id: int | None = Query(None, description="Lọc theo danh mục"),
    min_price: Decimal | None = Query(None, ge=0, description="Giá tối thiểu"),
    max_price: Decimal | None = Query(None, ge=0, description="Giá tối đa"),
    shop_id: int | None = Query(None, description="Lọc theo shop"),
    sort_by: ProductSortBy = Query(
        ProductSortBy.NEWEST,
        description="Sắp xếp: price_asc (giá tăng), price_desc (giá giảm), newest (mới nhất), best_selling (bán chạy)",
    ),
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    page_size: int = Query(10, ge=1, le=100, description="Số sản phẩm mỗi trang"),
    db: Session = Depends(get_db),
):
    """Lấy danh sách sản phẩm:

    - Chỉ trả về sản phẩm ACTIVE của shop đang hoạt động (ACTIVE).
    - Hỗ trợ tìm theo tên, lọc theo danh mục, khoảng giá, shop.
    - Sắp xếp theo giá, mới nhất hoặc bán chạy.
    - Phân trang đầy đủ (items, total, page, page_size, total_pages).
    """
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price không được lớn hơn max_price",
        )

    return product_crud.get_products(
        db,
        keyword=q,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        shop_id=shop_id,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )


@router.get("/{product_id}", response_model=ProductDetailOut, summary="Chi tiết sản phẩm kèm ảnh, tồn, shop, video")
def get_product_detail(
    product_id: int,
    db: Session = Depends(get_db),
):
    """Lấy chi tiết 1 sản phẩm:

    - Kèm danh sách ảnh (images).
    - Tồn kho (stock).
    - Thông tin shop bán sản phẩm (shop).
    - Danh sách video có gắn sản phẩm này (videos).
    - Trả về 404 nếu sản phẩm không tồn tại hoặc shop/sản phẩm không ở trạng thái ACTIVE.
    """
    product = product_crud.get_product_detail(db, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sản phẩm id={product_id} hoặc sản phẩm/shop không còn hoạt động.",
        )
    return product


@router.post("", response_model=ProductDetailOut, status_code=status.HTTP_201_CREATED, summary="Tạo sản phẩm mới (hỗ trợ test)")
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
):
    """Endpoint tạo sản phẩm mới cho shop."""
    product = product_crud.create_product(db, data)
    return product_crud.get_product_detail(db, product.id)
