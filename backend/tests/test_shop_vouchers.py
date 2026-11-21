"""Test Task T3D2BFB - [Bonus] Mã giảm giá của shop.

- Người bán tạo mã (phần trăm / số tiền, đơn tối thiểu, hạn dùng, số lượt)
- Người mua nhập mã khi thanh toán, server kiểm tra và tính lại tiền
Chạy: pytest tests/test_shop_vouchers.py -v (SQLite in-memory, không cần MySQL)
"""

from datetime import datetime, timedelta
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
from app.models.order import Order
from app.models.product import Product
from app.models.shop import Shop
from app.models.user import User
from app.models.voucher import ShopVoucher, VoucherUsage


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


def _user(uid, username, role):
    return User(
        id=uid,
        email=f"{username}@shop.com",
        username=username,
        password_hash=hash_password("password123"),
        display_name=username,
        role=role,
        status="ACTIVE",
    )


@pytest.fixture()
def seed(db_session):
    db = db_session()
    db.add_all(
        [
            _user(1, "seller1", "SELLER"),
            _user(2, "seller2", "SELLER"),
            _user(3, "buyer1", "USER"),
            _user(4, "buyer2", "USER"),
            Shop(id=1, owner_id=1, name="Shop Hoàng Văn", status="ACTIVE"),
            Shop(id=2, owner_id=2, name="Shop Người Khác", status="ACTIVE"),
            Category(id=1, name="Thời trang", status="ACTIVE"),
            Product(id=1, shop_id=1, category_id=1, name="Áo Hoodie Nỉ",
                    price=Decimal("250000"), stock=50, status="ACTIVE"),
            Product(id=2, shop_id=2, category_id=1, name="Quần Jogger",
                    price=Decimal("300000"), stock=50, status="ACTIVE"),
        ]
    )
    db.commit()
    db.close()
    headers = {}
    for uid, name in [(1, "seller1"), (2, "seller2"), (3, "buyer1"), (4, "buyer2")]:
        token, _ = create_access_token(uid)
        headers[name] = {"Authorization": f"Bearer {token}"}
    return headers


def _future(days=7):
    return (datetime.now() + timedelta(days=days)).isoformat(timespec="seconds")


def _voucher_payload(**overrides):
    data = {
        "code": "giam10",
        "description": "Giảm 10% tối đa 30k cho đơn từ 300k",
        "discount_type": "PERCENT",
        "discount_value": 10,
        "max_discount_amount": 30000,
        "min_order_amount": 300000,
        "usage_limit": 2,
        "per_user_limit": 1,
        "expires_at": _future(),
    }
    data.update(overrides)
    return data


def _checkout(client, headers, codes=None):
    body = {
        "recipient_name": "Nguyễn Văn Khách",
        "recipient_phone": "0911222333",
        "recipient_address": "Hà Nội",
        "payment_method": "COD",
    }
    if codes is not None:
        body["voucher_codes"] = codes
    return client.post("/api/orders", json=body, headers=headers)


# ---------------- 1. Người bán tạo / quản lý mã ----------------

def test_seller_create_list_update_and_delete_voucher(client, seed):
    h1 = seed["seller1"]

    r = client.post("/api/shops/me/vouchers", json=_voucher_payload(), headers=h1)
    assert r.status_code == 201
    v = r.json()
    assert v["code"] == "GIAM10"  # tự viết hoa
    assert v["discount_type"] == "PERCENT"
    assert v["state"] == "ACTIVE"
    assert v["remaining_uses"] == 2

    # Trùng mã trong cùng shop -> 409
    assert client.post(
        "/api/shops/me/vouchers", json=_voucher_payload(), headers=h1
    ).status_code == 409

    # Shop khác được phép dùng cùng tên mã
    assert client.post(
        "/api/shops/me/vouchers", json=_voucher_payload(), headers=seed["seller2"]
    ).status_code == 201

    # Mã giảm số tiền cố định
    r_fixed = client.post(
        "/api/shops/me/vouchers",
        json=_voucher_payload(code="FREESHIP-50K", discount_type="FIXED",
                              discount_value=50000, min_order_amount=0),
        headers=h1,
    )
    assert r_fixed.status_code == 201
    assert r_fixed.json()["max_discount_amount"] is None

    r_list = client.get("/api/shops/me/vouchers", headers=h1)
    assert r_list.status_code == 200
    assert {x["code"] for x in r_list.json()} == {"GIAM10", "FREESHIP-50K"}

    # Sửa: tắt mã
    r_off = client.put(f"/api/shops/me/vouchers/{v['id']}",
                       json={"status": "INACTIVE"}, headers=h1)
    assert r_off.status_code == 200
    assert r_off.json()["state"] == "INACTIVE"

    # Xoá mã chưa dùng -> xoá hẳn
    r_del = client.delete(f"/api/shops/me/vouchers/{r_fixed.json()['id']}", headers=h1)
    assert r_del.status_code == 200
    assert r_del.json()["action"] == "deleted"

    # Mã công khai chỉ hiện mã còn hiệu lực (GIAM10 đã tắt)
    assert client.get("/api/shops/1/vouchers").json() == []


def test_create_voucher_invalid_data_returns_422(client, seed):
    h1 = seed["seller1"]
    bad_payloads = [
        _voucher_payload(discount_value=150),  # % > 100
        _voucher_payload(discount_value=0),  # giá trị <= 0
        _voucher_payload(expires_at=(datetime.now() - timedelta(days=1)).isoformat()),
        _voucher_payload(usage_limit=0),  # số lượt < 1
        _voucher_payload(min_order_amount=-1),
        _voucher_payload(code="GIẢM 10"),  # có dấu, khoảng trắng
        _voucher_payload(starts_at=_future(10), expires_at=_future(5)),
        _voucher_payload(per_user_limit=5, usage_limit=2),
    ]
    for payload in bad_payloads:
        r = client.post("/api/shops/me/vouchers", json=payload, headers=h1)
        assert r.status_code == 422, payload


def test_voucher_unauthenticated_and_wrong_permission(client, seed, db_session):
    # Chưa đăng nhập -> 401
    assert client.get("/api/shops/me/vouchers").status_code == 401
    assert client.post("/api/shops/me/vouchers", json=_voucher_payload()).status_code == 401
    assert client.post("/api/vouchers/apply", json={"code": "GIAM10"}).status_code == 401

    # Người mua (USER) không được tạo mã -> 403
    assert client.post(
        "/api/shops/me/vouchers", json=_voucher_payload(), headers=seed["buyer1"]
    ).status_code == 403

    # Seller 2 sửa / xoá mã của Shop 1 -> 403
    vid = client.post(
        "/api/shops/me/vouchers", json=_voucher_payload(), headers=seed["seller1"]
    ).json()["id"]
    assert client.put(f"/api/shops/me/vouchers/{vid}", json={"status": "INACTIVE"},
                      headers=seed["seller2"]).status_code == 403
    assert client.delete(f"/api/shops/me/vouchers/{vid}",
                         headers=seed["seller2"]).status_code == 403
    assert client.put("/api/shops/me/vouchers/99999", json={"status": "INACTIVE"},
                      headers=seed["seller1"]).status_code == 404


# ---------------- 2. Người mua áp mã: server kiểm tra & tính tiền ----------------

def test_apply_voucher_preview_calculates_discount_on_server(client, seed, db_session):
    client.post("/api/shops/me/vouchers", json=_voucher_payload(), headers=seed["seller1"])
    client.post(
        "/api/shops/me/vouchers",
        json=_voucher_payload(code="GIAM50K", discount_type="FIXED",
                              discount_value=50000, min_order_amount=600000),
        headers=seed["seller1"],
    )
    hb = seed["buyer1"]
    # Giỏ: 2 x Áo Hoodie (Shop 1) = 500.000đ
    client.post("/api/cart/items", json={"product_id": 1, "quantity": 2}, headers=hb)

    # 10% của 500k = 50k nhưng tối đa 30k -> giảm 30k, còn 470k
    r = client.post("/api/vouchers/apply", json={"code": " giam10 "}, headers=hb)
    assert r.status_code == 200
    data = r.json()
    assert data["shop_id"] == 1
    assert data["subtotal"] == 500000
    assert data["discount_amount"] == 30000
    assert data["total_after_discount"] == 470000

    # Chưa đủ đơn tối thiểu 600k -> 400
    r_min = client.post("/api/vouchers/apply", json={"code": "GIAM50K"}, headers=hb)
    assert r_min.status_code == 400
    assert "600.000đ" in r_min.json()["detail"]

    # Mã không tồn tại -> 404
    assert client.post("/api/vouchers/apply", json={"code": "KHONGCO"},
                       headers=hb).status_code == 404

    # Mã của Shop 2 nhưng giỏ chỉ có hàng Shop 1 -> 400
    client.post(
        "/api/shops/me/vouchers", json=_voucher_payload(code="SHOP2SALE"),
        headers=seed["seller2"],
    )
    assert client.post("/api/vouchers/apply", json={"code": "SHOP2SALE"},
                       headers=hb).status_code == 400

    # Mã hết hạn / chưa đến ngày -> 400
    db = db_session()
    db.add_all([
        ShopVoucher(shop_id=1, code="HETHAN", discount_type="FIXED",
                    discount_value=Decimal("10000"), min_order_amount=0,
                    usage_limit=5, used_count=0, per_user_limit=1,
                    expires_at=datetime.now() - timedelta(hours=1), status="ACTIVE"),
        ShopVoucher(shop_id=1, code="SAPTOI", discount_type="FIXED",
                    discount_value=Decimal("10000"), min_order_amount=0,
                    usage_limit=5, used_count=0, per_user_limit=1,
                    starts_at=datetime.now() + timedelta(days=1),
                    expires_at=datetime.now() + timedelta(days=3), status="ACTIVE"),
    ])
    db.commit()
    db.close()
    r_exp = client.post("/api/vouchers/apply", json={"code": "HETHAN"}, headers=hb)
    assert r_exp.status_code == 400 and "hết hạn" in r_exp.json()["detail"]
    r_up = client.post("/api/vouchers/apply", json={"code": "SAPTOI"}, headers=hb)
    assert r_up.status_code == 400 and "chưa đến" in r_up.json()["detail"]


def test_checkout_with_voucher_recalculates_total_and_limits_usage(
    client, seed, db_session
):
    client.post("/api/shops/me/vouchers", json=_voucher_payload(), headers=seed["seller1"])
    hb1, hb2 = seed["buyer1"], seed["buyer2"]

    # Buyer 1: giỏ có hàng của 2 shop, áp mã GIAM10 của Shop 1
    client.post("/api/cart/items", json={"product_id": 1, "quantity": 2}, headers=hb1)
    client.post("/api/cart/items", json={"product_id": 2, "quantity": 1}, headers=hb1)
    r = _checkout(client, hb1, ["giam10"])
    assert r.status_code == 201
    data = r.json()
    assert data["total_before_discount"] == 800000
    assert data["total_discount"] == 30000
    assert data["total_amount"] == 770000
    orders = {o["shop_id"]: o for o in data["orders"]}
    assert orders[1]["voucher_code"] == "GIAM10"
    assert orders[1]["subtotal_amount"] == 500000
    assert orders[1]["discount_amount"] == 30000
    assert orders[1]["total_amount"] == 470000
    assert orders[2]["discount_amount"] == 0
    assert orders[2]["total_amount"] == 300000

    # Lịch sử đơn của người mua cũng hiện mã đã dùng
    my_orders = client.get("/api/orders", headers=hb1).json()
    assert any(o["voucher_code"] == "GIAM10" for o in my_orders)

    # Buyer 1 dùng lại lần 2 -> vượt giới hạn mỗi người (1 lượt) -> 400, đơn KHÔNG được tạo
    client.post("/api/cart/items", json={"product_id": 1, "quantity": 2}, headers=hb1)
    r_again = _checkout(client, hb1, ["GIAM10"])
    assert r_again.status_code == 400
    db = db_session()
    assert db.query(Order).filter(Order.buyer_id == 3).count() == 2  # rollback, không có đơn mới
    assert db.get(Product, 1).stock == 48  # tồn kho không bị trừ lần 2
    db.close()

    # Buyer 2 dùng lượt cuối cùng (usage_limit = 2)
    client.post("/api/cart/items", json={"product_id": 1, "quantity": 2}, headers=hb2)
    r_b2 = _checkout(client, hb2, ["GIAM10"])
    assert r_b2.status_code == 201
    order_b2_id = r_b2.json()["orders"][0]["id"]

    db = db_session()
    voucher = db.query(ShopVoucher).filter_by(shop_id=1, code="GIAM10").one()
    assert voucher.used_count == 2
    assert db.query(VoucherUsage).count() == 2
    db.close()

    # Hết lượt -> mã hiện trạng thái USED_UP
    v_list = client.get("/api/shops/me/vouchers", headers=seed["seller1"]).json()
    assert v_list[0]["state"] == "USED_UP"

    # Người bán huỷ đơn của Buyer 2 -> trả lại 1 lượt dùng mã
    r_cancel = client.post(f"/api/shops/me/orders/{order_b2_id}/cancel",
                           headers=seed["seller1"])
    assert r_cancel.status_code == 200
    db = db_session()
    voucher = db.query(ShopVoucher).filter_by(shop_id=1, code="GIAM10").one()
    assert voucher.used_count == 1
    db.close()

    # Mã đã có đơn dùng -> xoá thì chỉ chuyển sang INACTIVE
    r_del = client.delete(f"/api/shops/me/vouchers/{voucher.id}", headers=seed["seller1"])
    assert r_del.json()["action"] == "deactivated"


def test_checkout_rejects_invalid_or_foreign_voucher(client, seed):
    hb = seed["buyer1"]
    client.post("/api/cart/items", json={"product_id": 1, "quantity": 1}, headers=hb)

    # Mã không tồn tại -> 404, đơn không được tạo
    assert _checkout(client, hb, ["KHONGCO"]).status_code == 404

    # Mã của shop không có trong đơn -> 400
    client.post("/api/shops/me/vouchers", json=_voucher_payload(code="SHOP2SALE"),
                headers=seed["seller2"])
    assert _checkout(client, hb, ["SHOP2SALE"]).status_code == 400

    # Chưa đủ đơn tối thiểu (250k < 300k) -> 400
    client.post("/api/shops/me/vouchers", json=_voucher_payload(), headers=seed["seller1"])
    assert _checkout(client, hb, ["GIAM10"]).status_code == 400

    # Giỏ vẫn còn nguyên sau các lần thất bại, đặt không mã vẫn thành công
    r_ok = _checkout(client, hb)
    assert r_ok.status_code == 201
    assert r_ok.json()["total_amount"] == 250000
    assert r_ok.json()["total_discount"] == 0
