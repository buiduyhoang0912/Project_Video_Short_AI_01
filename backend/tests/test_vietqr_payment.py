"""Unit test cho tính năng thanh toán chuyển khoản bằng mã QR VietQR (Task T3D2C15).

Yêu cầu:
- Phương thức chuyển khoản hiển thị QR VietQR theo số tài khoản của shop, số tiền và nội dung = mã đơn (DH{id})
- Người bán xác nhận đã nhận tiền chuyển khoản -> chuyển trạng thái confirmed
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


def create_user(db, email, username, role="user"):
    u = User(email=email, username=username, hashed_password="pw", role=role, is_active=True)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_vietqr_generation_and_seller_confirmation(client, db_session):
    """Test đặt hàng BANK_TRANSFER sinh mã VietQR và seller xác nhận đã nhận tiền."""
    seller = create_user(db_session, "seller_qr@test.com", "seller_qr", "seller")
    buyer = create_user(db_session, "buyer_qr@test.com", "buyer_qr", "user")

    # Shop có thông tin ngân hàng VietQR
    shop = Shop(
        name="Cửa Hàng Công Nghệ",
        owner_id=seller.id,
        is_active=True,
        bank_name="MB",
        bank_account_number="0988776655",
        bank_account_holder="NGUYEN VAN A",
    )
    db_session.add(shop)
    db_session.commit()
    db_session.refresh(shop)

    prod = Product(
        name="Tai nghe Bluetooth",
        price=250000.0,
        stock=10,
        shop_id=shop.id,
        status="ACTIVE",
    )
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)

    # Thêm vào giỏ
    cart = Cart(user_id=buyer.id)
    db_session.add(cart)
    db_session.commit()
    db_session.refresh(cart)

    c_item = CartItem(cart_id=cart.id, product_id=prod.id, quantity=1)
    db_session.add(c_item)
    db_session.commit()

    buyer_token = create_access_token({"sub": str(buyer.id), "user_id": buyer.id, "email": buyer.email})
    seller_token = create_access_token({"sub": str(seller.id), "user_id": seller.id, "email": seller.email, "role": "seller"})

    # 1. Buyer đặt hàng bằng BANK_TRANSFER
    checkout_payload = {
        "recipient_name": "Nguyễn Mua Hàng",
        "recipient_phone": "0912345678",
        "recipient_address": "123 Đường Cầu Giấy, Hà Nội",
        "payment_method": "BANK_TRANSFER",
    }
    res = client.post(
        "/api/orders",
        json=checkout_payload,
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["total_orders_created"] == 1
    order_out = data["orders"][0]
    assert order_out["payment_method"] == "BANK_TRANSFER"
    assert order_out["bank_name"] == "MB"
    assert order_out["bank_account_number"] == "0988776655"
    assert "vietqr.io" in order_out["vietqr_url"]
    assert f"DH{order_out['id']}" in order_out["vietqr_url"]

    order_id = order_out["id"]

    # 2. Seller gọi API xác nhận đã nhận tiền (/confirm-payment)
    confirm_res = client.post(
        f"/api/shops/me/orders/{order_id}/confirm-payment",
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert confirm_res.status_code == 200
    confirm_data = confirm_res.json()
    assert confirm_data["status"] == "confirmed"
    assert confirm_data["payment_status"] == "PAID"
