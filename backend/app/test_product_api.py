"""Unit tests cho API Sản phẩm theo yêu cầu task T3D2839:

1. Chỉ sản phẩm ACTIVE của shop đang hoạt động (ACTIVE).
2. Tìm theo tên (search by keyword).
3. Lọc danh mục, khoảng giá, shop.
4. Sắp xếp: giá (tăng/giảm), mới nhất, bán chạy.
5. Phân trang: total, page, page_size, total_pages, items.
6. Chi tiết: kèm ảnh, tồn kho, shop, video có gắn sản phẩm.
"""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.crud.product import get_product_detail, get_products
from app.db.session import Base
from app.models.category import Category
from app.models.product import Product, ProductImage
from app.models.shop import Shop
from app.models.user import User
from app.models.video import Video, VideoProduct
from app.schemas.product import ProductSortBy


@pytest.fixture
def db_session():
    # SQLite in-memory database để chạy test độc lập
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # 1. User
        u = User(id=1, email="seller@test.com", username="seller1", password_hash="hash", display_name="Seller")
        session.add(u)
        session.commit()

        # 2. Shop: Shop 1 (ACTIVE), Shop 2 (INACTIVE)
        shop_active = Shop(id=1, owner_id=1, name="Shop Hoạt Động", status="ACTIVE", description="Mô tả shop")
        shop_inactive = Shop(id=2, owner_id=1, name="Shop Đã Tắt", status="INACTIVE", description="Shop tạm dừng")
        session.add_all([shop_active, shop_inactive])
        session.commit()

        # 3. Category: Cat 1 (Áo), Cat 2 (Quần)
        cat_shirt = Category(id=1, name="Áo thời trang")
        cat_pants = Category(id=2, name="Quần jean")
        session.add_all([cat_shirt, cat_pants])
        session.commit()

        # 4. Products:
        # P1: ACTIVE, Shop 1 (ACTIVE), Cat 1, price 100k, stock 10, sold 50, newest
        now = datetime.now()
        p1 = Product(
            id=1, shop_id=1, category_id=1, name="Áo thun phong cách",
            price=Decimal("100000"), stock=10, sold_count=50, status="ACTIVE",
            created_at=now,
        )
        # P2: ACTIVE, Shop 1 (ACTIVE), Cat 1, price 200k, stock 20, sold 100 (bán chạy nhất), older
        p2 = Product(
            id=2, shop_id=1, category_id=1, name="Áo sơ mi nam",
            price=Decimal("200000"), stock=20, sold_count=100, status="ACTIVE",
            created_at=now - timedelta(days=2),
        )
        # P3: ACTIVE, Shop 1 (ACTIVE), Cat 2, price 300k, stock 5, sold 10, oldest
        p3 = Product(
            id=3, shop_id=1, category_id=2, name="Quần jean rách",
            price=Decimal("300000"), stock=5, sold_count=10, status="ACTIVE",
            created_at=now - timedelta(days=5),
        )
        # P4: INACTIVE, Shop 1 (ACTIVE) -> KHÔNG ĐƯỢC HIỂN THỊ
        p4 = Product(
            id=4, shop_id=1, category_id=1, name="Áo len (ngừng bán)",
            price=Decimal("150000"), stock=0, sold_count=0, status="INACTIVE",
            created_at=now,
        )
        # P5: ACTIVE, Shop 2 (INACTIVE) -> KHÔNG ĐƯỢC HIỂN THỊ (shop ngừng hoạt động)
        p5 = Product(
            id=5, shop_id=2, category_id=2, name="Quần short (shop đóng cửa)",
            price=Decimal("80000"), stock=15, sold_count=30, status="ACTIVE",
            created_at=now,
        )
        session.add_all([p1, p2, p3, p4, p5])
        session.commit()

        # 5. Ảnh sản phẩm cho P1
        img1 = ProductImage(id=1, product_id=1, object_key="https://img1.jpg", is_primary=True, sort_order=1)
        img2 = ProductImage(id=2, product_id=1, object_key="https://img2.jpg", is_primary=False, sort_order=2)
        session.add_all([img1, img2])

        # 6. Video gắn kèm P1
        v1 = Video(
            id=1, user_id=1, title="Review áo thun", video_url="https://video1.mp4",
            duration_seconds=30, view_count=1000, status="VISIBLE"
        )
        session.add(v1)
        session.commit()
        vp1 = VideoProduct(video_id=1, product_id=1)
        session.add(vp1)
        session.commit()

        yield session


def test_only_active_products_of_active_shops(db_session):
    """1. Chỉ lấy sản phẩm ACTIVE của shop đang hoạt động."""
    res = get_products(db_session)
    product_ids = [item.id for item in res.items]

    # P1, P2, P3 phải có mặt
    assert 1 in product_ids
    assert 2 in product_ids
    assert 3 in product_ids
    # P4 (product INACTIVE) và P5 (shop INACTIVE) KHÔNG được xuất hiện
    assert 4 not in product_ids
    assert 5 not in product_ids
    assert res.total == 3


def test_search_by_name(db_session):
    """2. Tìm kiếm theo tên."""
    res = get_products(db_session, keyword="sơ mi")
    assert res.total == 1
    assert res.items[0].id == 2
    assert res.items[0].name == "Áo sơ mi nam"


def test_filter_by_category_price_shop(db_session):
    """3. Lọc theo danh mục, khoảng giá, shop."""
    # Lọc danh mục = 2 (Quần)
    res_cat = get_products(db_session, category_id=2)
    assert res_cat.total == 1
    assert res_cat.items[0].id == 3

    # Lọc khoảng giá: 150.000 đến 250.000 (chỉ có P2: 200k)
    res_price = get_products(db_session, min_price=150000, max_price=250000)
    assert res_price.total == 1
    assert res_price.items[0].id == 2

    # Lọc theo shop_id = 1
    res_shop = get_products(db_session, shop_id=1)
    assert res_shop.total == 3

    # Lọc shop_id = 2 (shop inactive) -> 0 kết quả
    res_shop_inactive = get_products(db_session, shop_id=2)
    assert res_shop_inactive.total == 0


def test_sorting(db_session):
    """4. Sắp xếp giá tăng, giá giảm, mới nhất, bán chạy."""
    # Giá tăng dần: P1 (100k) -> P2 (200k) -> P3 (300k)
    res_asc = get_products(db_session, sort_by=ProductSortBy.PRICE_ASC)
    assert [x.id for x in res_asc.items] == [1, 2, 3]

    # Giá giảm dần: P3 (300k) -> P2 (200k) -> P1 (100k)
    res_desc = get_products(db_session, sort_by=ProductSortBy.PRICE_DESC)
    assert [x.id for x in res_desc.items] == [3, 2, 1]

    # Bán chạy: P2 (100 sold) -> P1 (50 sold) -> P3 (10 sold)
    res_best = get_products(db_session, sort_by=ProductSortBy.BEST_SELLING)
    assert [x.id for x in res_best.items] == [2, 1, 3]

    # Mới nhất: P1 (now) -> P2 (now - 2 days) -> P3 (now - 5 days)
    res_newest = get_products(db_session, sort_by=ProductSortBy.NEWEST)
    assert [x.id for x in res_newest.items] == [1, 2, 3]


def test_pagination(db_session):
    """5. Phân trang."""
    res_p1 = get_products(db_session, page=1, page_size=2)
    assert res_p1.total == 3
    assert res_p1.page == 1
    assert res_p1.page_size == 2
    assert res_p1.total_pages == 2
    assert len(res_p1.items) == 2

    res_p2 = get_products(db_session, page=2, page_size=2)
    assert len(res_p2.items) == 1


def test_product_detail_with_images_stock_shop_videos(db_session):
    """6. Chi tiết kèm ảnh, tồn, shop, video có gắn sản phẩm."""
    p1 = get_product_detail(db_session, product_id=1)
    assert p1 is not None
    assert p1.name == "Áo thun phong cách"
    assert p1.stock == 10  # Tồn kho

    # Shop
    assert p1.shop is not None
    assert p1.shop.name == "Shop Hoạt Động"
    assert p1.shop.status == "ACTIVE"

    # Images
    assert len(p1.images) == 2
    assert p1.images[0].image_url == "https://img1.jpg"

    # Videos có gắn sản phẩm
    assert len(p1.videos) == 1
    assert p1.videos[0].title == "Review áo thun"


def test_product_detail_inactive_returns_none(db_session):
    """Chi tiết sản phẩm INACTIVE hoặc của shop INACTIVE trả về None (404)."""
    p4 = get_product_detail(db_session, product_id=4)  # Product inactive
    assert p4 is None

    p5 = get_product_detail(db_session, product_id=5)  # Shop inactive
    assert p5 is None
