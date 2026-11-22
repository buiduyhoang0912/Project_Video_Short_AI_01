"""Test tính năng gắn sản phẩm vào video (Task T3D2296 - Phạm Công Khải Hoàn).
Chạy: pytest backend/tests/test_video_products.py (dùng SQLite in-memory).
"""

from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import BIGINT, ENUM, INTEGER
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.core.security import create_access_token, hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models.category import Category
from app.models.product import Product
from app.models.shop import Shop
from app.models.user import User
from app.models.video import Video, VideoProduct

# Bổ sung relationship còn thiếu khi chạy test với SQLite
if not hasattr(User, "addresses"):
    User.addresses = relationship("Address", back_populates="user")
if not hasattr(User, "orders"):
    User.orders = relationship("Order", back_populates="buyer")
if not hasattr(User, "cart"):
    User.cart = relationship("Cart", back_populates="user", uselist=False)
if not hasattr(Shop, "orders"):
    Shop.orders = relationship("Order", back_populates="shop")


@compiles(BIGINT, "sqlite")
def _bigint_sqlite(t, c, **k):
    return "INTEGER"


@compiles(INTEGER, "sqlite")
def _int_sqlite(t, c, **k):
    return "INTEGER"


@compiles(ENUM, "sqlite")
def _enum_sqlite(t, c, **k):
    return "VARCHAR(50)"


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    yield Session
    engine.dispose()


@pytest.fixture()
def client(db_session):
    def override():
        db = db_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_seller(db, username: str, email: str) -> tuple[User, Shop, str]:
    user = User(
        username=username,
        email=email,
        display_name=username,
        password_hash=hash_password("password123"),
        role="SELLER",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    shop = Shop(
        owner_id=user.id,
        name=f"Shop {username}",
        description="Shop test",
        status="ACTIVE",
    )
    db.add(shop)
    db.commit()
    db.refresh(shop)

    token, _ = create_access_token(user.id)
    return user, shop, token


def make_product(db, shop_id: int, category_id: int, name: str, price: float = 100000.0) -> Product:
    p = Product(
        shop_id=shop_id,
        category_id=category_id,
        name=name,
        price=Decimal(str(price)),
        stock=100,
        status="ACTIVE",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def make_video(db, user_id: int, title: str) -> Video:
    v = Video(
        user_id=user_id,
        title=title,
        description="Mô tả video",
        video_url="/uploads/video.mp4",
        thumbnail_url="/uploads/thumb.jpg",
        duration_seconds=60,
        status="VISIBLE",
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def test_set_video_products_success(client, db_session):
    """Người bán gắn tối đa 3 sản phẩm vào video của mình."""
    db = db_session()
    user, shop, token = make_seller(db, "seller1", "seller1@test.com")
    cat = Category(name="Thời trang")
    db.add(cat)
    db.commit()
    db.refresh(cat)

    p1 = make_product(db, shop.id, cat.id, "Áo sơ mi trắng", 150000)
    p2 = make_product(db, shop.id, cat.id, "Quần tây đen", 250000)
    p3 = make_product(db, shop.id, cat.id, "Thắt lưng da", 90000)
    video = make_video(db, user.id, "Video phối đồ công sở")
    vid = video.id
    pid1, pid2, pid3 = p1.id, p2.id, p3.id
    db.close()

    headers = {"Authorization": f"Bearer {token}"}
    res = client.post(
        f"/api/videos/{vid}/products",
        json={"product_ids": [pid1, pid2, pid3]},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    names = [p["name"] for p in data]
    assert "Áo sơ mi trắng" in names
    assert "Quần tây đen" in names
    assert "Thắt lưng da" in names

    # Kiểm tra lấy danh sách sản phẩm qua GET /api/videos/{video_id}/products
    res_get = client.get(f"/api/videos/{vid}/products")
    assert res_get.status_code == 200
    assert len(res_get.json()) == 3


def test_set_video_products_limit_3(client, db_session):
    """Không được gắn quá 3 sản phẩm vào 1 video."""
    db = db_session()
    user, shop, token = make_seller(db, "seller2", "seller2@test.com")
    cat = Category(name="Mỹ phẩm")
    db.add(cat)
    db.commit()
    db.refresh(cat)

    pids = [
        make_product(db, shop.id, cat.id, f"Sản phẩm {i}", 100000).id
        for i in range(4)
    ]
    video = make_video(db, user.id, "Video review mỹ phẩm")
    vid = video.id
    db.close()

    headers = {"Authorization": f"Bearer {token}"}
    res = client.post(
        f"/api/videos/{vid}/products",
        json={"product_ids": pids},
        headers=headers,
    )
    # Lỗi 400 hoặc 422 vì vượt quá 3 sản phẩm
    assert res.status_code in (400, 422)


def test_set_video_products_not_owned_product(client, db_session):
    """Không được gắn sản phẩm thuộc shop của người khác."""
    db = db_session()
    user1, shop1, token1 = make_seller(db, "seller_a", "seller_a@test.com")
    _, shop2, _ = make_seller(db, "seller_b", "seller_b@test.com")
    cat = Category(name="Gia dụng")
    db.add(cat)
    db.commit()
    db.refresh(cat)

    p_other = make_product(db, shop2.id, cat.id, "Nồi cơm điện", 500000)
    video = make_video(db, user1.id, "Video của shop A")
    vid = video.id
    other_pid = p_other.id
    db.close()

    headers = {"Authorization": f"Bearer {token1}"}
    res = client.post(
        f"/api/videos/{vid}/products",
        json={"product_ids": [other_pid]},
        headers=headers,
    )
    assert res.status_code == 400
    assert "cửa hàng của bạn" in res.json()["detail"]


def test_video_detail_includes_products(client, db_session):
    """Trang chi tiết video (/video/{id}) trả về danh sách products được gắn."""
    db = db_session()
    user, shop, token = make_seller(db, "seller3", "seller3@test.com")
    cat = Category(name="Giày dép")
    db.add(cat)
    db.commit()
    db.refresh(cat)

    p1 = make_product(db, shop.id, cat.id, "Giày thể thao Sneaker", 350000)
    video = make_video(db, user.id, "Video trên chân Sneaker")
    link = VideoProduct(video_id=video.id, product_id=p1.id)
    db.add(link)
    db.commit()
    vid = video.id
    db.close()

    res = client.get(f"/api/video/{vid}")
    assert res.status_code == 200
    data = res.json()
    assert "products" in data
    assert len(data["products"]) == 1
    assert data["products"][0]["name"] == "Giày thể thao Sneaker"
