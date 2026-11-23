"""Unit test cho tính năng huỷ đơn hàng và hoàn tồn kho (Task T3D2B93).

Yêu cầu:
- API danh sách đơn theo trạng thái (filter status)
- Chi tiết đơn có dòng thời gian trạng thái (timeline)
- Huỷ khi còn Chờ xác nhận (PENDING) và hoàn tồn đúng một lần
- Huỷ khi không phải PENDING bị chặn (400)
- Huỷ lại lần 2 bị chặn (400)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.session import Base, get_db
from app.main import app
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


def create_mock_user(db, email="buyer@test.com", username="buyer1", role="user"):
    u = User(
        email=email,
        username=username,
        hashed_password="pw",
        role=role,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def create_mock_shop(db, owner_id):
    shop = Shop(
        name="Test Shop",
        owner_id=owner_id,
        is_active=True,
    )
    db.add(shop)
    db.commit()
    db.refresh(shop)
    return shop


def create_mock_product(db, shop_id, name="Test Product", stock=10, price=50000.0):
    prod = Product(
        name=name,
        price=price,
        stock=stock,
        shop_id=shop_id,
        status="ACTIVE",
        sold_count=0,
    )
    db.add(prod)
    db.commit()
    db.refresh(prod)
    return prod


def test_cancel_order_pending_success_and_restock(client, db_session):
    """Test huỷ đơn hàng PENDING thành công và hoàn tồn kho chính xác."""
    seller = create_mock_user(db_session, "seller@test.com", "seller1", "seller")
    buyer = create_mock_user(db_session, "buyer@test.com", "buyer1", "user")
    shop = create_mock_shop(db_session, seller.id)
    prod = create_mock_product(db_session, shop.id, stock=5)

    order = Order(
        buyer_id=buyer.id,
        shop_id=shop.id,
        total_amount=100000.0,
        payment_method="COD",
        status="PENDING",
        recipient_name="Buyer",
        recipient_phone="0912345678",
        recipient_address="Hanoi",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    item = OrderItem(
        order_id=order.id,
        product_id=prod.id,
        quantity=3,
        unit_price=50000.0,
    )
    db_session.add(item)
    db_session.commit()

    token = create_access_token({"sub": str(buyer.id), "user_id": buyer.id, "email": buyer.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Gọi API huỷ đơn
    res = client.post(f"/api/orders/{order.id}/cancel", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "CANCELLED"
    assert data["restocked_items_count"] == 1

    # Kiểm tra tồn kho đã được cộng lại: 5 + 3 = 8
    db_session.refresh(prod)
    assert prod.stock == 8

    # Kiểm tra đơn hàng có status = CANCELLED
    db_session.refresh(order)
    assert order.status == "CANCELLED"


def test_cannot_cancel_non_pending_order(client, db_session):
    """Test không thể huỷ đơn khi đơn không còn ở trạng thái PENDING."""
    seller = create_mock_user(db_session, "seller2@test.com", "seller2", "seller")
    buyer = create_mock_user(db_session, "buyer2@test.com", "buyer2", "user")
    shop = create_mock_shop(db_session, seller.id)
    prod = create_mock_product(db_session, shop.id, stock=10)

    order = Order(
        buyer_id=buyer.id,
        shop_id=shop.id,
        total_amount=50000.0,
        payment_method="SIMULATED",
        status="CONFIRMED",
        recipient_name="Buyer",
        recipient_phone="0912345678",
        recipient_address="Hanoi",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    token = create_access_token({"sub": str(buyer.id), "user_id": buyer.id, "email": buyer.email})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(f"/api/orders/{order.id}/cancel", headers=headers)
    assert res.status_code == 400
    assert "PENDING" in res.json()["detail"]


def test_cannot_cancel_twice(client, db_session):
    """Test huỷ lại lần 2 bị từ chối và không hoàn tồn lặp lại."""
    seller = create_mock_user(db_session, "seller3@test.com", "seller3", "seller")
    buyer = create_mock_user(db_session, "buyer3@test.com", "buyer3", "user")
    shop = create_mock_shop(db_session, seller.id)
    prod = create_mock_product(db_session, shop.id, stock=10)

    order = Order(
        buyer_id=buyer.id,
        shop_id=shop.id,
        total_amount=50000.0,
        payment_method="COD",
        status="PENDING",
        recipient_name="Buyer",
        recipient_phone="0912345678",
        recipient_address="Hanoi",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    item = OrderItem(order_id=order.id, product_id=prod.id, quantity=2, unit_price=50000.0)
    db_session.add(item)
    db_session.commit()

    token = create_access_token({"sub": str(buyer.id), "user_id": buyer.id, "email": buyer.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Lần 1: huỷ thành công
    res1 = client.post(f"/api/orders/{order.id}/cancel", headers=headers)
    assert res1.status_code == 200
    db_session.refresh(prod)
    assert prod.stock == 12

    # Lần 2: huỷ lại báo lỗi 400 và tồn kho vẫn là 12
    res2 = client.post(f"/api/orders/{order.id}/cancel", headers=headers)
    assert res2.status_code == 400
    db_session.refresh(prod)
    assert prod.stock == 12
