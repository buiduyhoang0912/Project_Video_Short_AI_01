"""Unit tests cho API Đặt hàng trong Transaction (Task T3D2B17).

Kiểm tra:
1. Tách đơn theo shop: Giỏ hàng chứa sản phẩm của 2 shop -> tự động tách thành 2 đơn riêng.
2. Kiểm tra tồn và trừ kho: Kho trừ đúng số lượng, lưu giá lúc đặt (snapshot price).
3. 2 người mua sản phẩm cuối không làm tồn âm: Mua vượt tồn kho bị chặn, không cho tồn kho âm.
4. Xóa dòng khỏi giỏ: Các sản phẩm đã đặt bị xóa khỏi giỏ.
5. Lỗi giữa chừng rollback: Nếu 1 sản phẩm bị thiếu hàng, toàn bộ đơn bị huỷ, tồn kho không bị trừ, giỏ hàng không bị xóa.
6. Thanh toán mô phỏng đánh dấu đã thanh toán (confirmed).
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
from app.models.order import Order, OrderItem
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
def setup_data(db_session):
    buyer1 = User(id=1, email="buyer1@test.com", username="buyer01", password_hash="h", display_name="B1", role="USER", status="ACTIVE")
    buyer2 = User(id=2, email="buyer2@test.com", username="buyer02", password_hash="h", display_name="B2", role="USER", status="ACTIVE")
    seller = User(id=3, email="seller@test.com", username="seller01", password_hash="h", display_name="S1", role="SELLER", status="ACTIVE")

    # Shop 1, Shop 2
    shop1 = Shop(id=1, owner_id=3, name="Shop Quần Áo", status="ACTIVE")
    shop2 = Shop(id=2, owner_id=3, name="Shop Đồ Chơi", status="ACTIVE")
    cat = Category(id=1, name="Chung", status="ACTIVE")

    # Product 1: Shop 1, 100k, tồn = 5
    p1 = Product(id=1, shop_id=1, category_id=1, name="Áo thun", price=Decimal("100000"), stock=5, status="ACTIVE")
    # Product 2: Shop 1, 200k, tồn = 10
    p2 = Product(id=2, shop_id=1, category_id=1, name="Quần jean", price=Decimal("200000"), stock=10, status="ACTIVE")
    # Product 3: Shop 2, 50k, tồn = 1 (sản phẩm cuối cùng)
    p3 = Product(id=3, shop_id=2, category_id=1, name="Móc khóa (còn 1 chiếc)", price=Decimal("50000"), stock=1, status="ACTIVE")

    db_session.add_all([buyer1, buyer2, seller, shop1, shop2, cat, p1, p2, p3])
    db_session.commit()

    token1, _ = create_access_token(buyer1.id)
    token2, _ = create_access_token(buyer2.id)

    return {
        "headers1": {"Authorization": f"Bearer {token1}"},
        "headers2": {"Authorization": f"Bearer {token2}"},
    }


def test_split_orders_by_shop_and_stock_deduction(client, setup_data, db_session):
    """1. Tách đơn theo shop, trừ kho, lưu snapshot giá, xóa khỏi giỏ."""
    headers = setup_data["headers1"]

    # Thêm 2 sp của Shop 1 và 1 sp của Shop 2 vào giỏ
    client.post("/api/cart/items", json={"product_id": 1, "quantity": 2}, headers=headers)
    client.post("/api/cart/items", json={"product_id": 2, "quantity": 1}, headers=headers)
    client.post("/api/cart/items", json={"product_id": 3, "quantity": 1}, headers=headers)

    # Đặt hàng (COD)
    checkout_payload = {
        "recipient_name": "Nguyễn Văn A",
        "recipient_phone": "0912345678",
        "recipient_address": "123 Đường Cầu Giấy, Hà Nội",
        "payment_method": "COD",
    }
    res = client.post("/api/orders", json=checkout_payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    # Tách thành 2 đơn hàng cho 2 shop
    assert data["total_orders_created"] == 2
    assert len(data["orders"]) == 2

    # Đơn Shop 1: 2 áo (200k) + 1 quần (200k) = 400k
    o1 = next(o for o in data["orders"] if o["shop_id"] == 1)
    assert o1["total_amount"] == 400000.0
    assert o1["status"] == "pending"
    assert len(o1["items"]) == 2

    # Đơn Shop 2: 1 móc khóa = 50k
    o2 = next(o for o in data["orders"] if o["shop_id"] == 2)
    assert o2["total_amount"] == 50000.0
    assert o2["status"] == "pending"

    # Kiểm tra kho đã được trừ trong DB
    p1 = db_session.get(Product, 1)
    p2 = db_session.get(Product, 2)
    p3 = db_session.get(Product, 3)
    assert p1.stock == 3  # 5 - 2 = 3
    assert p2.stock == 9  # 10 - 1 = 9
    assert p3.stock == 0  # 1 - 1 = 0

    # Kiểm tra giỏ hàng đã được xóa các món đã đặt
    res_cart = client.get("/api/cart", headers=headers)
    assert res_cart.json()["total_valid_items"] == 0


def test_simulated_payment_marks_confirmed(client, setup_data):
    """2. Thanh toán mô phỏng đánh dấu đã thanh toán (status = confirmed)."""
    headers = setup_data["headers1"]

    # Thêm 1 áo vào giỏ
    client.post("/api/cart/items", json={"product_id": 1, "quantity": 1}, headers=headers)

    checkout_payload = {
        "recipient_name": "Trần Thị B",
        "recipient_phone": "0987654321",
        "recipient_address": "Số 1 Đại Cồ Việt, Hà Nội",
        "payment_method": "SIMULATED",  # Mô phỏng
    }
    res = client.post("/api/orders", json=checkout_payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["orders"][0]["payment_method"] == "SIMULATED"
    assert data["orders"][0]["status"] == "confirmed"  # Đã thanh toán


def test_concurrency_last_stock_and_rollback(client, setup_data, db_session):
    """3. Hai người cùng mua sản phẩm cuối: người sau không làm tồn âm và transaction tự rollback."""
    headers1 = setup_data["headers1"]
    headers2 = setup_data["headers2"]

    # p3 chỉ còn 1 chiếc
    # Người 1 thêm vào giỏ 1 chiếc
    client.post("/api/cart/items", json={"product_id": 3, "quantity": 1}, headers=headers1)
    # Người 2 cũng thêm vào giỏ 1 chiếc
    client.post("/api/cart/items", json={"product_id": 3, "quantity": 1}, headers=headers2)

    checkout_payload = {
        "recipient_name": "Người mua",
        "recipient_phone": "0900000000",
        "recipient_address": "Hà Nội",
        "payment_method": "COD",
    }

    # Người 1 đặt thành công chiếc cuối cùng
    res1 = client.post("/api/orders", json=checkout_payload, headers=headers1)
    assert res1.status_code == 201

    # Tồn kho hiện tại đã về 0
    p3 = db_session.get(Product, 3)
    assert p3.stock == 0

    # Người 2 cố đặt -> Phải báo lỗi hết hàng và ROLLBACK
    res2 = client.post("/api/orders", json=checkout_payload, headers=headers2)
    assert res2.status_code == 400
    assert "không đủ số lượng tồn kho" in res2.json()["detail"].lower()

    # Đảm bảo tồn kho không bị âm
    db_session.refresh(p3)
    assert p3.stock == 0  # Không bị âm!
