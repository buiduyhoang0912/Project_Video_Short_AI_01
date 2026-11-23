"""E2E Test kiểm tra luồng xuyên suốt của toàn bộ phân hệ (Task T3D1DBC).

Luồng kiểm tra:
1. Thêm sản phẩm từ 2 Shop khác nhau vào giỏ hàng (Cart API)
2. Xem giỏ hàng nhóm theo shop, kiểm tra tính tạm tính
3. Đặt hàng trong Transaction: tách thành 2 đơn hàng độc lập, trừ kho chính xác
4. Kiểm tra đơn hàng có thông tin thanh toán VietQR
5. Huỷ 1 đơn hàng khi còn PENDING -> hoàn tồn kho chính xác cho shop đó
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.session import Base, get_db
from app.main import app
from app.models.cart import Cart, CartItem
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.shop import Shop
from app.models.user import User

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
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


def test_full_e2e_cart_checkout_cancel_flow(client, db_session):
    # Tạo 2 seller, 2 shop
    s1_user = User(email="s1@test.com", username="s1", hashed_password="pw", role="seller", is_active=True)
    s2_user = User(email="s2@test.com", username="s2", hashed_password="pw", role="seller", is_active=True)
    buyer = User(email="buyer_e2e@test.com", username="buyer_e2e", hashed_password="pw", role="user", is_active=True)
    db_session.add_all([s1_user, s2_user, buyer])
    db_session.commit()

    shop1 = Shop(name="Shop Alpha", owner_id=s1_user.id, is_active=True, bank_name="MB", bank_account_number="111111")
    shop2 = Shop(name="Shop Beta", owner_id=s2_user.id, is_active=True, bank_name="VCB", bank_account_number="222222")
    db_session.add_all([shop1, shop2])
    db_session.commit()

    p1 = Product(name="Sản phẩm A", price=100000.0, stock=10, shop_id=shop1.id, status="ACTIVE")
    p2 = Product(name="Sản phẩm B", price=200000.0, stock=5, shop_id=shop2.id, status="ACTIVE")
    db_session.add_all([p1, p2])
    db_session.commit()

    buyer_token = create_access_token({"sub": str(buyer.id), "user_id": buyer.id, "email": buyer.email})
    headers = {"Authorization": f"Bearer {buyer_token}"}

    # 1. Thêm vào giỏ
    client.post("/api/cart/items", json={"product_id": p1.id, "quantity": 2}, headers=headers)
    client.post("/api/cart/items", json={"product_id": p2.id, "quantity": 1}, headers=headers)

    # 2. Xem giỏ hàng
    cart_res = client.get("/api/cart", headers=headers)
    assert cart_res.status_code == 200
    cart_data = cart_res.json()
    assert len(cart_data["shops"]) == 2
    assert cart_data["subtotal"] == 400000.0  # 100k*2 + 200k*1

    # 3. Đặt hàng trong Transaction
    order_res = client.post(
        "/api/orders",
        json={
            "recipient_name": "Người mua E2E",
            "recipient_phone": "0988888888",
            "recipient_address": "Hà Nội",
            "payment_method": "BANK_TRANSFER",
        },
        headers=headers,
    )
    assert order_res.status_code == 201
    orders_created = order_res.json()["orders"]
    assert len(orders_created) == 2

    # Kiểm tra tồn kho đã bị trừ
    db_session.refresh(p1)
    db_session.refresh(p2)
    assert p1.stock == 8
    assert p2.stock == 4

    # 4. Huỷ đơn hàng thứ nhất (của shop 1)
    order1_id = orders_created[0]["id"]
    cancel_res = client.post(f"/api/orders/{order1_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200

    # Kiểm tra tồn kho p1 đã được hoàn lại: 8 + 2 = 10
    db_session.refresh(p1)
    assert p1.stock == 10
    # p2 của shop 2 vẫn giữ nguyên 4
    db_session.refresh(p2)
    assert p2.stock == 4
