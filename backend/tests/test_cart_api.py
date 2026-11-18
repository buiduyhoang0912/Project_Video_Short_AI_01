"""Unit tests cho API Giỏ hàng (Task T3D2853).

Kiểm tra:
1. Thêm sản phẩm vào giỏ (cộng dồn số lượng nếu đã có).
2. Sửa số lượng (kiểm tra không vượt quá tồn kho).
3. Xoá sản phẩm khỏi giỏ và làm trống giỏ.
4. Xem giỏ hàng nhóm theo shop.
5. Tạm tính tính chuẩn xác tại server.
6. Chặn sản phẩm đã ẩn (không ACTIVE) hoặc cửa hàng đã ẩn.
"""
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.session import Base, get_db
from app.main import app
from app.models.category import Category
from app.models.product import Product
from app.models.shop import Shop
from app.models.user import User


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def sample_data(db_session):
    # User 1 (buyer)
    user = User(
        id=1,
        email="buyer@clipshop.vn",
        username="buyer01",
        password_hash="fake_hash",
        display_name="Người Mua 01",
        role="USER",
        status="ACTIVE",
    )
    # User 2 (seller)
    seller = User(
        id=2,
        email="seller@clipshop.vn",
        username="seller01",
        password_hash="fake_hash",
        display_name="Chủ Shop 01",
        role="SELLER",
        status="ACTIVE",
    )
    # Shop 1 (ACTIVE), Shop 2 (ACTIVE)
    shop1 = Shop(id=1, owner_id=2, name="Shop Thời Trang", status="ACTIVE")
    shop2 = Shop(id=2, owner_id=2, name="Shop Đồ Điện Tử", status="ACTIVE")
    cat = Category(id=1, name="Chung", status="ACTIVE")

    # Product 1: Shop 1, price 100k, stock 10, ACTIVE
    p1 = Product(id=1, shop_id=1, category_id=1, name="Áo thun", price=Decimal("100000"), stock=10, status="ACTIVE")
    # Product 2: Shop 1, price 200k, stock 5, ACTIVE
    p2 = Product(id=2, shop_id=1, category_id=1, name="Quần jean", price=Decimal("200000"), stock=5, status="ACTIVE")
    # Product 3: Shop 2, price 500k, stock 8, ACTIVE
    p3 = Product(id=3, shop_id=2, category_id=1, name="Tai nghe", price=Decimal("500000"), stock=8, status="ACTIVE")
    # Product 4: Shop 1, price 150k, stock 20, INACTIVE (đã ẩn)
    p4 = Product(id=4, shop_id=1, category_id=1, name="Áo lỗi (Ẩn)", price=Decimal("150000"), stock=20, status="INACTIVE")

    db_session.add_all([user, seller, shop1, shop2, cat, p1, p2, p3, p4])
    db_session.commit()

    token, _ = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}
    return {"user": user, "headers": headers, "p1": p1, "p2": p2, "p3": p3, "p4": p4}


def test_add_to_cart_cumulative_and_stock_limit(client, sample_data):
    """1. Thêm vào giỏ (cộng dồn) & kiểm tra không vượt tồn kho."""
    headers = sample_data["headers"]

    # Thêm lần 1: 3 chiếc p1 (tồn 10) -> OK
    res = client.post("/api/cart/items", json={"product_id": 1, "quantity": 3}, headers=headers)
    assert res.status_code == 201
    assert res.json()["quantity"] == 3

    # Thêm lần 2: thêm 4 chiếc p1 -> cộng dồn thành 7 -> OK
    res = client.post("/api/cart/items", json={"product_id": 1, "quantity": 4}, headers=headers)
    assert res.status_code == 201
    assert res.json()["quantity"] == 7

    # Thêm lần 3: thêm 5 chiếc p1 -> tổng 7 + 5 = 12 > 10 (vượt tồn) -> 400
    res = client.post("/api/cart/items", json={"product_id": 1, "quantity": 5}, headers=headers)
    assert res.status_code == 400
    assert "vượt quá" in res.json()["detail"].lower()


def test_add_hidden_product_blocked(client, sample_data):
    """2. Chặn thêm sản phẩm đã ẩn."""
    headers = sample_data["headers"]
    # p4 có status = INACTIVE (đã ẩn)
    res = client.post("/api/cart/items", json={"product_id": 4, "quantity": 1}, headers=headers)
    assert res.status_code == 400
    assert "bị ẩn" in res.json()["detail"].lower()


def test_update_quantity_and_stock_limit(client, sample_data):
    """3. Sửa số lượng (không vượt tồn)."""
    headers = sample_data["headers"]

    # Thêm 2 chiếc p2 (tồn 5)
    res = client.post("/api/cart/items", json={"product_id": 2, "quantity": 2}, headers=headers)
    item_id = res.json()["cart_item_id"]

    # Sửa lên 5 chiếc (bằng tồn kho) -> OK
    res_up = client.put(f"/api/cart/items/{item_id}", json={"quantity": 5}, headers=headers)
    assert res_up.status_code == 200
    assert res_up.json()["quantity"] == 5

    # Sửa lên 6 chiếc (vượt tồn) -> 400
    res_err = client.put(f"/api/cart/items/{item_id}", json={"quantity": 6}, headers=headers)
    assert res_err.status_code == 400


def test_delete_cart_item(client, sample_data):
    """4. Xoá sản phẩm khỏi giỏ hàng."""
    headers = sample_data["headers"]

    res = client.post("/api/cart/items", json={"product_id": 1, "quantity": 2}, headers=headers)
    item_id = res.json()["cart_item_id"]

    # Xoá item
    res_del = client.delete(f"/api/cart/items/{item_id}", headers=headers)
    assert res_del.status_code == 200

    # Giỏ rỗng
    res_cart = client.get("/api/cart", headers=headers)
    assert res_cart.json()["total_valid_items"] == 0
    assert res_cart.json()["subtotal"] == 0.0


def test_view_cart_grouped_by_shop_and_server_subtotal(client, sample_data):
    """5. Xem giỏ nhóm theo shop & tính tạm tính ở server."""
    headers = sample_data["headers"]

    # Thêm p1 (Shop 1): 2 chiếc * 100k = 200k
    client.post("/api/cart/items", json={"product_id": 1, "quantity": 2}, headers=headers)
    # Thêm p2 (Shop 1): 1 chiếc * 200k = 200k
    client.post("/api/cart/items", json={"product_id": 2, "quantity": 1}, headers=headers)
    # Thêm p3 (Shop 2): 2 chiếc * 500k = 1000k
    client.post("/api/cart/items", json={"product_id": 3, "quantity": 2}, headers=headers)

    res = client.get("/api/cart", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Nhóm thành 2 shop
    assert len(data["shops"]) == 2

    # Shop 1: 2 items, subtotal = 400k
    shop1_group = next(s for s in data["shops"] if s["shop_id"] == 1)
    assert len(shop1_group["items"]) == 2
    assert shop1_group["shop_subtotal"] == 400000.0

    # Shop 2: 1 item, subtotal = 1000k
    shop2_group = next(s for s in data["shops"] if s["shop_id"] == 2)
    assert len(shop2_group["items"]) == 1
    assert shop2_group["shop_subtotal"] == 1000000.0

    # Tổng giỏ: 200k + 200k + 1000k = 1400k
    assert data["subtotal"] == 1400000.0
    assert data["total_valid_items"] == 5
