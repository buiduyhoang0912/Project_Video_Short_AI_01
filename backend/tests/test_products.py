"""Test API CRUD sản phẩm, tồn kho và upload ảnh (Task T3D24C4 - Nguyễn Hoàng Văn).
Chạy: pytest (dùng SQLite in-memory, không cần MySQL).
"""

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import BIGINT, ENUM, INTEGER
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.db.session import Base, get_db
from app.main import app
from app.models.category import Category
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.shop import Shop
from app.models.user import User
from app.routers.products import PRODUCT_UPLOADS_DIR

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


def create_seller_with_shop(
    client: TestClient, db_session, username="seller_van", email="van@shop.com"
):
    r_reg = client.post(
        "/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "password123",
            "display_name": username,
        },
    )
    assert r_reg.status_code == 201
    user_id = r_reg.json()["id"]

    db = db_session()
    user = db.get(User, user_id)
    user.role = "SELLER"
    category = db.query(Category).first()
    if category is None:
        category = Category(name="Thời trang", description="Quần áo", status="ACTIVE")
        db.add(category)
    db.commit()
    db.refresh(category)
    category_id = category.id
    db.close()

    r_login = client.post(
        "/auth/login",
        json={"identifier": username, "password": "password123"},
    )
    token = r_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r_shop = client.post(
        "/api/shops",
        json={"name": f"Shop của {username}", "address": "Hà Nội"},
        headers=headers,
    )
    assert r_shop.status_code == 201
    shop_id = r_shop.json()["id"]

    return user_id, shop_id, category_id, headers


def make_image_bytes(color=(255, 0, 0), fmt="PNG") -> bytes:
    buf = BytesIO()
    img = Image.new("RGB", (32, 32), color=color)
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_create_update_hide_and_validate_price_stock(client, db_session):
    _, shop_id, category_id, headers = create_seller_with_shop(
        client, db_session
    )

    # 1. Giá <= 0 phải bị từ chối (422)
    r_zero_price = client.post(
        "/api/products",
        json={
            "category_id": category_id,
            "name": "Áo thun lỗi giá",
            "price": 0,
            "stock": 10,
        },
        headers=headers,
    )
    assert r_zero_price.status_code == 422

    # 2. Tồn kho < 0 phải bị từ chối (422)
    r_neg_stock = client.post(
        "/api/products",
        json={
            "category_id": category_id,
            "name": "Áo thun lỗi tồn kho",
            "price": 150000,
            "stock": -1,
        },
        headers=headers,
    )
    assert r_neg_stock.status_code == 422

    # 3. Tạo sản phẩm hợp lệ (giá > 0, tồn >= 0) -> 201
    r_create = client.post(
        "/api/products",
        json={
            "category_id": category_id,
            "name": "Áo Polo Cao Cấp",
            "description": "Chất liệu cotton 100%",
            "price": 199000,
            "stock": 0,
        },
        headers=headers,
    )
    assert r_create.status_code == 201
    product_data = r_create.json()
    product_id = product_data["id"]
    assert product_data["shop_id"] == shop_id
    assert float(product_data["price"]) == 199000.0
    assert product_data["stock"] == 0
    assert product_data["status"] == "ACTIVE"

    # 4. Sửa thông tin sản phẩm và cập nhật tồn kho
    r_update = client.put(
        f"/api/products/{product_id}",
        json={"name": "Áo Polo Nam Mới", "price": 220000, "stock": 25},
        headers=headers,
    )
    assert r_update.status_code == 200
    assert r_update.json()["name"] == "Áo Polo Nam Mới"
    assert r_update.json()["stock"] == 25

    r_stock = client.patch(
        f"/api/products/{product_id}/stock",
        json={"stock": 50},
        headers=headers,
    )
    assert r_stock.status_code == 200
    assert r_stock.json()["stock"] == 50

    # 5. Ẩn sản phẩm
    r_hide = client.patch(
        f"/api/products/{product_id}/hide",
        headers=headers,
    )
    assert r_hide.status_code == 200
    assert r_hide.json()["status"] == "HIDDEN"


def test_cannot_modify_other_shop_product(client, db_session):
    _, _, category_id, headers1 = create_seller_with_shop(
        client, db_session, "seller_a", "a@shop.com"
    )
    _, _, _, headers2 = create_seller_with_shop(
        client, db_session, "seller_b", "b@shop.com"
    )

    r_create = client.post(
        "/api/products",
        json={
            "category_id": category_id,
            "name": "Sản phẩm của Shop A",
            "price": 100000,
            "stock": 5,
        },
        headers=headers1,
    )
    product_id = r_create.json()["id"]

    # Seller B cố tình sửa hoặc ẩn sản phẩm của Seller A -> 403 Forbidden
    r_forbid_update = client.put(
        f"/api/products/{product_id}",
        json={"name": "Hack tên"},
        headers=headers2,
    )
    assert r_forbid_update.status_code == 403

    r_forbid_delete = client.delete(
        f"/api/products/{product_id}",
        headers=headers2,
    )
    assert r_forbid_delete.status_code == 403


def test_upload_multiple_images_and_shop_product_listing(client, db_session):
    _, shop_id, category_id, headers = create_seller_with_shop(
        client, db_session, "seller_img", "img@shop.com"
    )

    r_prod = client.post(
        "/api/products",
        json={
            "category_id": category_id,
            "name": "Giày Sneaker Trắng",
            "price": 350000,
            "stock": 12,
        },
        headers=headers,
    )
    product_id = r_prod.json()["id"]

    img1 = make_image_bytes((255, 0, 0), "PNG")
    img2 = make_image_bytes((0, 255, 0), "JPEG")

    # Upload nhiều ảnh cùng lúc
    r_upload = client.post(
        f"/api/products/{product_id}/images",
        files=[
            ("files", ("front.png", img1, "image/png")),
            ("files", ("side.jpg", img2, "image/jpeg")),
        ],
        headers=headers,
    )
    assert r_upload.status_code == 201
    uploaded = r_upload.json()
    assert len(uploaded) == 2
    assert uploaded[0]["is_primary"] is True
    assert uploaded[0]["sort_order"] == 0
    assert uploaded[0]["object_key"].startswith("/uploads/products/")
    assert uploaded[1]["is_primary"] is False
    assert uploaded[1]["sort_order"] == 1

    # Kiểm tra file đã thực sự được lưu vào thư mục uploads/products
    saved_files = []
    for item in uploaded:
        fname = item["object_key"].removeprefix("/uploads/products/")
        fpath = PRODUCT_UPLOADS_DIR / fname
        assert fpath.exists()
        saved_files.append(fpath)

    # API danh sách sản phẩm của shop trả về kèm danh sách ảnh
    r_shop_prods = client.get(f"/api/shops/{shop_id}/products")
    assert r_shop_prods.status_code == 200
    prods = r_shop_prods.json()
    assert len(prods) == 1
    assert len(prods[0]["images"]) == 2

    # Xoá cứng sản phẩm chưa có đơn -> tự động dọn cả file ảnh trong uploads/products
    r_del = client.delete(f"/api/products/{product_id}", headers=headers)
    assert r_del.status_code == 200
    assert r_del.json()["action"] == "deleted"
    for fpath in saved_files:
        assert not fpath.exists()


def test_product_with_order_only_hidden_not_hard_deleted(client, db_session):
    user_id, shop_id, category_id, headers = create_seller_with_shop(
        client, db_session, "seller_order", "order@shop.com"
    )

    # Tạo 2 sản phẩm: SP1 (có đơn hàng), SP2 (chưa có đơn hàng)
    r_p1 = client.post(
        "/api/products",
        json={
            "category_id": category_id,
            "name": "Sản phẩm đã có đơn",
            "price": 500000,
            "stock": 10,
        },
        headers=headers,
    )
    p1_id = r_p1.json()["id"]

    r_p2 = client.post(
        "/api/products",
        json={
            "category_id": category_id,
            "name": "Sản phẩm chưa có đơn",
            "price": 200000,
            "stock": 5,
        },
        headers=headers,
    )
    p2_id = r_p2.json()["id"]

    # Giả lập tạo 1 đơn hàng có chứa SP1 trong bảng order_items
    db = db_session()
    order = Order(
        buyer_id=user_id,
        shop_id=shop_id,
        total_amount=500000,
        recipient_name="Khách A",
        recipient_phone="0900111222",
        recipient_address="Hà Nội",
    )
    db.add(order)
    db.flush()
    db.add(
        OrderItem(
            order_id=order.id,
            product_id=p1_id,
            quantity=1,
            unit_price=500000,
        )
    )
    db.commit()
    db.close()

    # Gọi DELETE cho SP1 (đã có đơn) -> chỉ chuyển thành HIDDEN, không xoá cứng
    r_del_p1 = client.delete(f"/api/products/{p1_id}", headers=headers)
    assert r_del_p1.status_code == 200
    assert r_del_p1.json()["action"] == "hidden"
    assert r_del_p1.json()["product"]["status"] == "HIDDEN"

    # Kiểm tra trong DB SP1 vẫn tồn tại với status == HIDDEN
    db = db_session()
    assert db.get(Product, p1_id) is not None
    assert db.get(Product, p1_id).status == "HIDDEN"
    db.close()

    # Khách xem danh sách sản phẩm công khai của shop sẽ chỉ thấy SP2 (ACTIVE), không thấy SP1 (HIDDEN)
    r_public_list = client.get(f"/api/shops/{shop_id}/products")
    assert r_public_list.status_code == 200
    public_ids = [p["id"] for p in r_public_list.json()]
    assert p2_id in public_ids
    assert p1_id not in public_ids

    # Chủ shop xem danh sách sản phẩm của mình (/api/shops/me/products) thấy cả SP1 và SP2
    r_owner_list = client.get("/api/shops/me/products", headers=headers)
    assert r_owner_list.status_code == 200
    owner_ids = [p["id"] for p in r_owner_list.json()]
    assert p1_id in owner_ids and p2_id in owner_ids

    # Gọi DELETE cho SP2 (chưa có đơn) -> xoá cứng khỏi DB
    r_del_p2 = client.delete(f"/api/products/{p2_id}", headers=headers)
    assert r_del_p2.status_code == 200
    assert r_del_p2.json()["action"] == "deleted"

    db = db_session()
    assert db.get(Product, p2_id) is None
    db.close()


def test_products_unauthenticated_invalid_and_buyer_forbidden(
    client, db_session
):
    _, _, category_id, seller_headers = create_seller_with_shop(
        client, db_session, "seller_sec", "sec@shop.com"
    )

    # Tạo 1 sản phẩm hợp lệ
    r_prod = client.post(
        "/api/products",
        json={
            "category_id": category_id,
            "name": "Bàn phím cơ RGB",
            "price": 750000,
            "stock": 15,
        },
        headers=seller_headers,
    )
    assert r_prod.status_code == 201
    prod_id = r_prod.json()["id"]

    # 1. Chưa đăng nhập (401 Unauthorized)
    assert (
        client.post(
            "/api/products",
            json={
                "category_id": category_id,
                "name": "SP Lậu",
                "price": 10000,
                "stock": 1,
            },
        ).status_code
        == 401
    )
    assert (
        client.put(
            f"/api/products/{prod_id}", json={"name": "Sửa Lậu"}
        ).status_code
        == 401
    )
    assert (
        client.patch(
            f"/api/products/{prod_id}/stock", json={"stock": 99}
        ).status_code
        == 401
    )
    assert client.delete(f"/api/products/{prod_id}").status_code == 401
    assert client.get("/api/shops/me/products").status_code == 401

    # 2. Sai dữ liệu (400 / 404 / 422)
    # Danh mục không tồn tại -> 404
    r_bad_cat = client.post(
        "/api/products",
        json={
            "category_id": 99999,
            "name": "SP Sai Danh Mục",
            "price": 100000,
            "stock": 5,
        },
        headers=seller_headers,
    )
    assert r_bad_cat.status_code == 404

    # Upload file không phải định dạng ảnh cho sản phẩm -> 422
    r_bad_img = client.post(
        f"/api/products/{prod_id}/images",
        files=[("files", ("malware.exe", b"MZ-fake", "application/octet-stream"))],
        headers=seller_headers,
    )
    assert r_bad_img.status_code == 422

    # Xem sản phẩm không tồn tại -> 404
    assert client.get("/api/products/999999").status_code == 404

    # 3. Sai quyền (403 Forbidden): Tài khoản USER thường (chưa phải SELLER) cố tạo sản phẩm
    client.post(
        "/auth/register",
        json={
            "email": "buyer_only@shop.com",
            "username": "buyer_only",
            "password": "password123",
            "display_name": "Buyer Only",
        },
    )
    r_buyer_login = client.post(
        "/auth/login",
        json={"identifier": "buyer_only", "password": "password123"},
    )
    buyer_headers = {
        "Authorization": f"Bearer {r_buyer_login.json()['access_token']}"
    }
    r_buyer_create = client.post(
        "/api/products",
        json={
            "category_id": category_id,
            "name": "SP Của Buyer",
            "price": 100000,
            "stock": 1,
        },
        headers=buyer_headers,
    )
    assert r_buyer_create.status_code in (403, 404)

