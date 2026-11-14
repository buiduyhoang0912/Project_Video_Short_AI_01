"""CRUD cho bảng products, shop, category, product_images và video_products.

Đảm bảo các nghiệp vụ:
- Chỉ lấy sản phẩm ACTIVE của shop đang hoạt động (ACTIVE).
- Tìm kiếm theo tên.
- Lọc theo danh mục, khoảng giá (min_price, max_price), shop.
- Sắp xếp: giá tăng/giảm, mới nhất, bán chạy.
- Phân trang (total, page, page_size, total_pages, items).
- Xem chi tiết sản phẩm kèm ảnh, tồn kho, thông tin shop, và video có gắn sản phẩm.
"""
import math
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.category import Category
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.shop import Shop
from app.models.video import Video, VideoProduct
from app.schemas.product import (
    ProductCreate,
    ProductListItemOut,
    ProductListResponse,
    ProductSortBy,
    ProductUpdate,
)


def get_products(
    db: Session,
    *,
    keyword: str | None = None,
    category_id: int | None = None,
    min_price: Decimal | float | None = None,
    max_price: Decimal | float | None = None,
    shop_id: int | None = None,
    sort_by: ProductSortBy | str = ProductSortBy.NEWEST,
    page: int = 1,
    page_size: int = 10,
) -> ProductListResponse:
    """Lấy danh sách sản phẩm theo bộ lọc, phân trang và sắp xếp."""
    # 1. Base query: Chỉ sản phẩm ACTIVE của shop đang hoạt động (ACTIVE)
    stmt = (
        select(Product, Shop.name.label("shop_name"), Category.name.label("category_name"))
        .join(Shop, Product.shop_id == Shop.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(
            func.upper(Product.status) == "ACTIVE",
            func.upper(Shop.status) == "ACTIVE",
        )
    )

    # 2. Tìm theo tên
    if keyword and keyword.strip():
        search_kw = f"%{keyword.strip()}%"
        stmt = stmt.where(Product.name.ilike(search_kw))

    # 3. Lọc danh mục
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)

    # 4. Lọc khoảng giá
    if min_price is not None:
        stmt = stmt.where(Product.price >= Decimal(str(min_price)))
    if max_price is not None:
        stmt = stmt.where(Product.price <= Decimal(str(max_price)))

    # 5. Lọc theo shop
    if shop_id is not None:
        stmt = stmt.where(Product.shop_id == shop_id)

    # 6. Đếm tổng số kết quả (trước khi phân trang)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = db.scalar(count_stmt) or 0

    # 7. Sắp xếp giá / mới nhất / bán chạy
    sort_key = sort_by.value if isinstance(sort_by, ProductSortBy) else sort_by
    if sort_key == ProductSortBy.PRICE_ASC.value:
        stmt = stmt.order_by(Product.price.asc(), Product.id.desc())
    elif sort_key == ProductSortBy.PRICE_DESC.value:
        stmt = stmt.order_by(Product.price.desc(), Product.id.desc())
    elif sort_key == ProductSortBy.BEST_SELLING.value:
        stmt = stmt.order_by(Product.sold_count.desc(), Product.id.desc())
    else:  # Mặc định: mới nhất (newest)
        stmt = stmt.order_by(Product.created_at.desc(), Product.id.desc())

    # 8. Phân trang
    safe_page = max(page, 1)
    safe_page_size = max(min(page_size, 100), 1)
    offset = (safe_page - 1) * safe_page_size
    stmt = stmt.offset(offset).limit(safe_page_size)

    results = db.execute(stmt).all()

    items: list[ProductListItemOut] = []
    for product_obj, shop_name, category_name in results:
        items.append(
            ProductListItemOut(
                id=product_obj.id,
                shop_id=product_obj.shop_id,
                shop_name=shop_name,
                category_id=product_obj.category_id,
                category_name=category_name,
                name=product_obj.name,
                price=float(product_obj.price),
                stock=product_obj.stock,
                sold_count=product_obj.sold_count,
                thumbnail_url=product_obj.thumbnail_url,
                status=product_obj.status,
                created_at=product_obj.created_at,
            )
        )

    total_pages = math.ceil(total / safe_page_size) if total > 0 else 0

    return ProductListResponse(
        items=items,
        total=total,
        page=safe_page,
        page_size=safe_page_size,
        total_pages=total_pages,
    )


def get_product_detail(db: Session, product_id: int) -> Product | None:
    """Lấy chi tiết 1 sản phẩm: kèm ảnh, tồn kho, shop, và video có gắn sản phẩm.

    Chỉ trả về nếu sản phẩm ACTIVE và shop đang hoạt động (ACTIVE).
    """
    stmt = (
        select(Product)
        .options(
            joinedload(Product.shop),
            joinedload(Product.category),
            selectinload(Product.images),
            selectinload(Product.videos),
        )
        .join(Shop, Product.shop_id == Shop.id)
        .where(
            Product.id == product_id,
            func.upper(Product.status) == "ACTIVE",
            func.upper(Shop.status) == "ACTIVE",
        )
    )
    return db.scalar(stmt)


def create_product(db: Session, data: ProductCreate) -> Product:
    """Tạo sản phẩm mới."""
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product: Product, data: ProductUpdate) -> Product:
    """Cập nhật thông tin sản phẩm."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


def add_product_image(
    db: Session, product_id: int, image_url: str, is_primary: bool = False, display_order: int = 0
) -> ProductImage:
    """Thêm ảnh cho sản phẩm."""
    img = ProductImage(
        product_id=product_id,
        object_key=image_url,
        is_primary=is_primary,
        sort_order=display_order,
    )
    db.add(img)
    db.commit()
    db.refresh(img)
    return img


def link_product_to_video(db: Session, product_id: int, video_id: int) -> VideoProduct:
    """Gắn sản phẩm vào video."""
    vp = VideoProduct(product_id=product_id, video_id=video_id)
    db.add(vp)
    db.commit()
    return vp
