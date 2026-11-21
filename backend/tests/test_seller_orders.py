"""Test API người bán quản lý đơn hàng của shop, doanh thu theo ngày và sản phẩm bán chạy."""

from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import BIGINT, ENUM, INTEGER
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.core.security import create_access_token, hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models.category import Category
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.shop import Shop
from app.models.user import User


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


@pytest.fixture()
def seed_shop_orders(db_session):
    db = db_session()

    seller1 = User(
        id=1,
        email="seller1@shop.com",
        username="seller1",
        password_hash=hash_password("password123"),
        display_name="Seller 1",
        role="SELLER",
        status="ACTIVE",
    )
    seller2 = User(
        id=2,
        email="seller2@shop.com",
        username="seller2",
        password_hash=hash_password("password123"),
        display_name="Seller 2",
        role="SELLER",
        status="ACTIVE",
    )
    buyer = User(
        id=3,
        email="buyer@shop.com",
        username="buyer1",
        password_hash=hash_password("password123"),
        display_name="Buyer 1",
        role="USER",
        status="ACTIVE",
    )
    shop1 = Shop(id=1, owner_id=1, name="Shop Hoàng Văn", status="ACTIVE")
    shop2 = Shop(id=2, owner_id=2, name="Shop Người Khác", status="ACTIVE")
    cat = Category(id=1, name="Thời trang", status="ACTIVE")

    p1 = Product(
        id=1,
        shop_id=1,
        category_id=1,
        name="Áo Hoodie Nỉ",
        price=Decimal("250000"),
        stock=10,
        sold_count=3,
        status="ACTIVE",
    )
    p2 = Product(
        id=2,
        shop_id=1,
        category_id=1,
        name="Quần Jogger Kaki",
        price=Decimal("300000"),
        stock=8,
        sold_count=1,
        status="ACTIVE",
    )

    # Đơn 1: pending (Chờ xác nhận) - ngày 2026-11-19: 2 Áo Hoodie = 500k
    o1 = Order(
        id=1,
        buyer_id=3,
        shop_id=1,
        total_amount=Decimal("500000"),
        payment_method="COD",
        status="pending",
        recipient_name="Nguyễn Văn Khách",
        recipient_phone="0911222333",
        recipient_address="Hà Nội",
        created_at=datetime(2026, 11, 19, 10, 0, 0),
    )
    oi1 = OrderItem(
        id=1,
        order_id=1,
        product_id=1,
        quantity=2,
        unit_price=Decimal("250000"),
    )

    # Đơn 2: pending (Sẽ bị huỷ) - ngày 2026-11-20: 1 Áo Hoodie + 1 Quần Jogger = 550k
    o2 = Order(
        id=2,
        buyer_id=3,
        shop_id=1,
        total_amount=Decimal("550000"),
        payment_method="COD",
        status="pending",
        recipient_name="Trần Thị Mua",
        recipient_phone="0988777666",
        recipient_address="Đà Nẵng",
        created_at=datetime(2026, 11, 20, 14, 30, 0),
    )
    oi2_a = OrderItem(
        id=2,
        order_id=2,
        product_id=1,
        quantity=1,
        unit_price=Decimal("250000"),
    )
    oi2_b = OrderItem(
        id=3,
        order_id=2,
        product_id=2,
        quantity=1,
        unit_price=Decimal("300000"),
    )

    db.add_all(
        [seller1, seller2, buyer, shop1, shop2, cat, p1, p2, o1, oi1, o2, oi2_a, oi2_b]
    )
    db.commit()

    t1, _ = create_access_token(1)
    t2, _ = create_access_token(2)
    db.close()

    return {
        "seller1_headers": {"Authorization": f"Bearer {t1}"},
        "seller2_headers": {"Authorization": f"Bearer {t2}"},
    }


def test_seller_order_lifecycle_pending_to_completed(client, seed_shop_orders):
    h1 = seed_shop_orders["seller1_headers"]

    # 1. Xem danh sách đơn của shop
    r_list = client.get("/api/shops/me/orders", headers=h1)
    assert r_list.status_code == 200
    assert len(r_list.json()) == 2

    # 2. Không được nhảy cóc từ pending -> shipping hoặc pending -> completed
    r_bad_jump = client.patch(
        "/api/shops/me/orders/1/status",
        json={"status": "shipping"},
        headers=h1,
    )
    assert r_bad_jump.status_code == 400

    # 3. Bước 1: Chờ xác nhận (pending) -> Đã xác nhận (confirmed)
    r_confirm = client.patch(
        "/api/shops/me/orders/1/status",
        json={"status": "confirmed"},
        headers=h1,
    )
    assert r_confirm.status_code == 200
    assert r_confirm.json()["status"] == "confirmed"

    # 4. Bước 2: Đã xác nhận (confirmed) -> Đang giao (shipping)
    r_ship = client.patch(
        "/api/shops/me/orders/1/status",
        json={"status": "shipping"},
        headers=h1,
    )
    assert r_ship.status_code == 200
    assert r_ship.json()["status"] == "shipping"

    # Khi đang giao (shipping) thì không được huỷ đơn
    r_cancel_shipping = client.patch(
        "/api/shops/me/orders/1/status",
        json={"status": "cancelled"},
        headers=h1,
    )
    assert r_cancel_shipping.status_code == 400

    # 5. Bước 3: Đang giao (shipping) -> Hoàn thành (completed)
    r_complete = client.patch(
        "/api/shops/me/orders/1/status",
        json={"status": "completed"},
        headers=h1,
    )
    assert r_complete.status_code == 200
    assert r_complete.json()["status"] == "completed"


def test_cancel_order_restores_stock_and_other_seller_forbidden(
    client, seed_shop_orders, db_session
):
    h1 = seed_shop_orders["seller1_headers"]
    h2 = seed_shop_orders["seller2_headers"]

    # Seller 2 không được phép sửa đơn #2 của Shop 1 -> 403 Forbidden
    r_forbid = client.patch(
        "/api/shops/me/orders/2/status",
        json={"status": "confirmed"},
        headers=h2,
    )
    assert r_forbid.status_code == 403

    # Seller 1 huỷ đơn #2 (gồm 1 SP1 và 1 SP2) -> hoàn trả tồn kho
    r_cancel = client.patch(
        "/api/shops/me/orders/2/status",
        json={"status": "cancelled"},
        headers=h1,
    )
    assert r_cancel.status_code == 200
    assert r_cancel.json()["status"] == "cancelled"

    db = db_session()
    p1 = db.get(Product, 1)
    p2 = db.get(Product, 2)
    assert p1.stock == 11  # 10 + 1
    assert p2.stock == 9   # 8 + 1
    db.close()


def test_daily_revenue_and_best_selling_products(client, seed_shop_orders):
    h1 = seed_shop_orders["seller1_headers"]

    # Chuyển đơn #1 (500.000đ, 2 Áo Hoodie, ngày 2026-11-19) sang Hoàn thành
    client.post("/api/shops/me/orders/1/confirm", headers=h1)
    client.post("/api/shops/me/orders/1/ship", headers=h1)
    client.post("/api/shops/me/orders/1/complete", headers=h1)

    # Huỷ đơn #2 (ngày 2026-11-20)
    client.post("/api/shops/me/orders/2/cancel", headers=h1)

    # Kiểm tra thống kê tổng hợp, doanh thu theo ngày và sản phẩm bán chạy
    r_analytics = client.get("/api/shops/me/analytics", headers=h1)
    assert r_analytics.status_code == 200
    data = r_analytics.json()

    assert data["total_orders"] == 2
    assert data["completed_orders"] == 1
    assert data["cancelled_orders"] == 1
    assert data["total_revenue"] == 500000.0

    # Doanh thu theo ngày
    daily = {d["date"]: d for d in data["daily_revenue"]}
    assert daily["2026-11-19"]["revenue"] == 500000.0
    assert daily["2026-11-19"]["completed_orders"] == 1
    assert daily["2026-11-20"]["revenue"] == 0.0

    # Sản phẩm bán chạy (Đơn #2 đã huỷ nên chỉ tính 2 Áo Hoodie từ Đơn #1)
    best = data["best_selling_products"]
    assert len(best) == 1
    assert best[0]["product_id"] == 1
    assert best[0]["product_name"] == "Áo Hoodie Nỉ"
    assert best[0]["total_quantity_sold"] == 2
    assert best[0]["total_revenue"] == 500000.0


def test_seller_orders_unauthenticated_invalid_and_forbidden(
    client, seed_shop_orders
):
    h1 = seed_shop_orders["seller1_headers"]
    h2 = seed_shop_orders["seller2_headers"]

    # 1. Chưa đăng nhập (401 Unauthorized)
    assert client.get("/api/shops/me/orders").status_code == 401
    assert (
        client.patch(
            "/api/shops/me/orders/1/status", json={"status": "confirmed"}
        ).status_code
        == 401
    )
    assert client.get("/api/shops/me/analytics").status_code == 401
    assert client.get("/api/shops/me/revenue-daily").status_code == 401
    assert client.get("/api/shops/me/best-sellers").status_code == 401

    # 2. Sai dữ liệu (422 / 404)
    r_invalid_status = client.patch(
        "/api/shops/me/orders/1/status",
        json={"status": "invalid_state"},
        headers=h1,
    )
    assert r_invalid_status.status_code == 422

    r_not_found = client.patch(
        "/api/shops/me/orders/999999/status",
        json={"status": "confirmed"},
        headers=h1,
    )
    assert r_not_found.status_code == 404

    # 3. Sai quyền (403 Forbidden): Seller 2 gọi các endpoint xác nhận/giao/hoàn thành trên đơn của Shop 1
    assert (
        client.post("/api/shops/me/orders/1/confirm", headers=h2).status_code
        == 403
    )
    assert (
        client.post("/api/shops/me/orders/1/ship", headers=h2).status_code
        == 403
    )
    assert (
        client.post("/api/shops/me/orders/1/complete", headers=h2).status_code
        == 403
    )
    assert (
        client.post("/api/shops/me/orders/1/cancel", headers=h2).status_code
        == 403
    )

