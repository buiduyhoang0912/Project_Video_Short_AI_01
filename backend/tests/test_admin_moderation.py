"""Test kiểm duyệt video/sản phẩm và dashboard Admin (T3D201D).
Chạy: pytest tests/test_admin_moderation.py (SQLite in-memory, không cần MySQL).
"""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
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
from app.models.user import User, utc_now
from app.models.video import Video


@pytest.fixture()
def Session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine)
    engine.dispose()


@pytest.fixture()
def client(Session):
    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(Session, role="USER"):
    n = uuid.uuid4().hex[:8]
    with Session() as db:
        u = User(
            email=f"{n}@t.com", username=n, display_name=f"Ten {n}",
            password_hash=hash_password("Passw0rd!"), role=role,
        )
        db.add(u)
        db.commit()
        return u.id


def auth(uid):
    token, _ = create_access_token(uid)
    return {"Authorization": f"Bearer {token}"}


def make_video(Session, owner_id, title="Video vi phạm"):
    with Session() as db:
        v = Video(user_id=owner_id, title=title, video_url="/uploads/videos/a.mp4",
                  duration_seconds=10)
        db.add(v)
        db.commit()
        return v.id


def make_shop_product(Session, owner_id, name="Áo thun"):
    with Session() as db:
        shop = Shop(owner_id=owner_id, name="Shop X")
        cat = Category(name=f"Cat {uuid.uuid4().hex[:4]}")
        db.add_all([shop, cat])
        db.flush()
        p = Product(shop_id=shop.id, category_id=cat.id, name=name,
                    price=Decimal("100000"), stock=5)
        db.add(p)
        db.commit()
        return p.id, shop.id


def make_order(Session, buyer, shop, amount, status, when=None, items_count=1):
    with Session() as db:
        o = Order(buyer_id=buyer, shop_id=shop, total_amount=Decimal(amount),
                  status=status, recipient_name="A", recipient_phone="0900000000",
                  recipient_address="HN")
        if when:
            o.created_at = when
        db.add(o)
        db.flush()
        for _ in range(items_count):
            item = OrderItem(order_id=o.id, product_id=1, quantity=1, unit_price=Decimal("50000"))
            db.add(item)
        db.commit()


CALLS = [
    ("get", "/api/admin/videos"),
    ("patch", "/api/admin/videos/1/visibility"),
    ("patch", "/api/admin/videos/1/hide"),
    ("patch", "/api/admin/videos/1/show"),
    ("get", "/api/admin/products"),
    ("patch", "/api/admin/products/1/visibility"),
    ("patch", "/api/admin/products/1/hide"),
    ("patch", "/api/admin/products/1/show"),
    ("get", "/api/admin/dashboard"),
    ("get", "/api/admin/dashboard/summary"),
    ("get", "/api/admin/dashboard/daily"),
]


@pytest.mark.parametrize("method,url", CALLS)
def test_only_admin(client, Session, method, url):
    assert getattr(client, method)(url).status_code == 401
    for role in ("USER", "SELLER"):
        uid = make_user(Session, role)
        assert getattr(client, method)(url, headers=auth(uid)).status_code == 403


# ---------- Video ----------
def test_hide_video_requires_reason_and_hides_publicly(client, Session):
    admin = make_user(Session, "ADMIN")
    owner = make_user(Session)
    vid = make_video(Session, owner)
    h = auth(admin)
    url = f"/api/admin/videos/{vid}/hide"

    assert client.patch(url, json={}, headers=h).status_code == 422
    assert client.patch(url, json={"reason": "  "}, headers=h).status_code == 422
    with Session() as db:
        assert db.get(Video, vid).status == "VISIBLE"

    r = client.patch(url, json={"reason": "Nội dung phản cảm"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "HIDDEN"
    assert r.json()["moderation_reason"] == "Nội dung phản cảm"
    with Session() as db:
        v = db.get(Video, vid)
        assert v.status == "HIDDEN" and v.moderated_by == admin and v.moderated_at

    assert client.patch(url, json={"reason": "x"}, headers=h).status_code == 409
    hidden = client.get("/api/admin/videos?status=HIDDEN", headers=h).json()
    assert [x["id"] for x in hidden] == [vid]
    assert client.get("/api/admin/videos?status=VISIBLE", headers=h).json() == []

    r = client.patch(f"/api/admin/videos/{vid}/show", headers=h)
    assert r.status_code == 200 and r.json()["status"] == "VISIBLE"
    assert r.json()["moderation_reason"] is None
    assert client.patch(f"/api/admin/videos/{vid}/show", headers=h).status_code == 409
    assert client.patch("/api/admin/videos/9999/hide", json={"reason": "x"}, headers=h).status_code == 404


def test_video_visibility_endpoint(client, Session):
    admin = make_user(Session, "ADMIN")
    owner = make_user(Session)
    vid = make_video(Session, owner)
    h = auth(admin)
    url = f"/api/admin/videos/{vid}/visibility"

    # Body rỗng {} -> 422
    assert client.patch(url, json={}, headers=h).status_code == 422

    # Mâu thuẫn status=VISIBLE nhưng is_visible=false -> 422
    assert client.patch(url, json={"status": "VISIBLE", "is_visible": False}, headers=h).status_code == 422

    # Ẩn không có lý do -> 422
    r = client.patch(url, json={"status": "HIDDEN"}, headers=h)
    assert r.status_code == 422

    # Ẩn có lý do -> 200
    r = client.patch(url, json={"status": "HIDDEN", "reason": "Bản quyền"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "HIDDEN"

    # Hiện lại qua visibility
    r = client.patch(url, json={"status": "VISIBLE"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "VISIBLE"


def test_video_owner_cannot_unhide_moderated_video(client, Session):
    """Chủ video KHÔNG thể tự chuyển video sang VISIBLE khi đang bị Admin ẩn do vi phạm."""
    admin = make_user(Session, "ADMIN")
    owner = make_user(Session)
    vid = make_video(Session, owner)

    # 1. Admin ẩn video do vi phạm
    r_hide = client.patch(
        f"/api/admin/videos/{vid}/visibility",
        json={"status": "HIDDEN", "reason": "Nội dung phản cảm"},
        headers=auth(admin),
    )
    assert r_hide.status_code == 200

    # 2. Chủ video cố gắng gọi PATCH /api/videos/{vid}/status để tự bật lại VISIBLE -> Bị chặn 403
    r_owner = client.patch(
        f"/api/videos/{vid}/status",
        json={"status": "VISIBLE"},
        headers=auth(owner),
    )
    assert r_owner.status_code == 403
    assert "Admin ẩn" in r_owner.json()["detail"]

    # Trạng thái trong DB vẫn phải là HIDDEN
    with Session() as db:
        v = db.get(Video, vid)
        assert v.status == "HIDDEN"
        assert v.moderated_at is not None

    # 3. Chỉ Admin mới có quyền gỡ ẩn video này
    r_admin_unhide = client.patch(
        f"/api/videos/{vid}/status",
        json={"status": "VISIBLE"},
        headers=auth(admin),
    )
    assert r_admin_unhide.status_code == 200
    assert r_admin_unhide.json()["status"] == "VISIBLE"

    # Sau khi Admin gỡ ẩn, cờ moderated_at được reset và chủ video có thể quản lý lại bình thường
    with Session() as db:
        v = db.get(Video, vid)
        assert v.status == "VISIBLE"
        assert v.moderated_at is None


def test_search_videos(client, Session):
    admin = make_user(Session, "ADMIN")
    owner = make_user(Session)
    make_video(Session, owner, "Review son")
    make_video(Session, owner, "Nấu ăn")
    r = client.get("/api/admin/videos?search=son", headers=auth(admin)).json()
    assert [x["title"] for x in r] == ["Review son"]


# ---------- Sản phẩm ----------
def test_hide_product_requires_reason_and_seller_cannot_unhide(client, Session):
    admin = make_user(Session, "ADMIN")
    seller = make_user(Session, "SELLER")
    pid, _ = make_shop_product(Session, seller)
    h = auth(admin)
    url = f"/api/admin/products/{pid}/hide"

    assert client.patch(url, json={}, headers=h).status_code == 422
    r = client.patch(url, json={"reason": "Hàng cấm"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "HIDDEN"
    with Session() as db:
        p = db.get(Product, pid)
        assert p.status == "HIDDEN" and p.moderation_reason == "Hàng cấm"
    assert client.patch(url, json={"reason": "x"}, headers=h).status_code == 409

    # Sản phẩm bị ẩn không còn trong chi tiết công khai
    assert client.get(f"/api/products/{pid}").status_code == 404

    # Người bán không tự bật lại được
    r = client.patch(f"/api/products/{pid}", json={"status": "ACTIVE"}, headers=auth(seller))
    assert r.status_code == 403
    with Session() as db:
        assert db.get(Product, pid).status == "HIDDEN"

    r = client.patch(f"/api/admin/products/{pid}/show", headers=h)
    assert r.status_code == 200 and r.json()["status"] == "ACTIVE"
    assert client.get(f"/api/products/{pid}").status_code == 200
    assert client.patch(f"/api/admin/products/{pid}/show", headers=h).status_code == 409


def test_product_visibility_endpoint(client, Session):
    admin = make_user(Session, "ADMIN")
    seller = make_user(Session, "SELLER")
    pid, _ = make_shop_product(Session, seller)
    h = auth(admin)
    url = f"/api/admin/products/{pid}/visibility"

    # Body rỗng {} -> 422
    assert client.patch(url, json={}, headers=h).status_code == 422

    # Mâu thuẫn status=ACTIVE nhưng is_visible=false -> 422
    assert client.patch(url, json={"status": "ACTIVE", "is_visible": False}, headers=h).status_code == 422

    # Ẩn không có lý do -> 422
    assert client.patch(url, json={"status": "HIDDEN"}, headers=h).status_code == 422

    # Ẩn có lý do -> 200
    r = client.patch(url, json={"status": "HIDDEN", "reason": "Gian lận"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "HIDDEN"

    # Hiện lại
    r = client.patch(url, json={"status": "ACTIVE"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "ACTIVE"


def test_list_products_filter_and_search(client, Session):
    admin = make_user(Session, "ADMIN")
    seller = make_user(Session, "SELLER")
    pid, _ = make_shop_product(Session, seller, "Áo khoác")
    h = auth(admin)
    assert [x["id"] for x in client.get("/api/admin/products?search=khoác", headers=h).json()] == [pid]
    assert client.get("/api/admin/products?search=khongco", headers=h).json() == []
    assert client.get("/api/admin/products?status=HIDDEN", headers=h).json() == []
    assert client.get("/api/admin/products?status=XYZ", headers=h).status_code == 422


# ---------- Dashboard ----------
def test_dashboard_summary_and_daily(client, Session):
    admin = make_user(Session, "ADMIN")
    seller = make_user(Session, "SELLER")
    buyer = make_user(Session)
    make_video(Session, buyer)
    _, shop = make_shop_product(Session, seller)
    now = utc_now()
    # Đơn có 3 items nhưng tổng tiền là 100000 -> chỉ được tính 100000 một lần duy nhất!
    make_order(Session, buyer, shop, "100000", "completed", now, items_count=3)
    make_order(Session, buyer, shop, "50000", "confirmed", now - timedelta(days=1), items_count=2)
    make_order(Session, buyer, shop, "999999", "cancelled", now)  # Không tính vào doanh thu
    make_order(Session, buyer, shop, "777777", "pending", now)    # Chưa xác nhận -> chưa tính doanh thu
    h = auth(admin)

    # 1. GET /api/admin/dashboard
    dash = client.get("/api/admin/dashboard?days=7", headers=h).json()
    assert "summary" in dash and "daily" in dash
    s = dash["summary"]
    assert s["total_users"] == 3
    assert s["total_sellers"] == 1
    assert s["total_videos"] == 1
    assert s["total_products"] == 1
    assert s["total_orders"] == 4
    # Doanh thu = 100000 + 50000 = 150000 (không bị nhân đôi dù có nhiều items)
    assert Decimal(str(s["total_revenue"])) == Decimal("150000")

    # 2. Test range Từ ngày - Đến ngày
    start_str = (now - timedelta(days=2)).date().isoformat()
    end_str = now.date().isoformat()
    dash_range = client.get(f"/api/admin/dashboard?from_date={start_str}&to_date={end_str}", headers=h).json()
    assert len(dash_range["daily"]) == 3
    assert dash_range["from_date"] == start_str
    assert dash_range["to_date"] == end_str

    # 3. Lỗi ngày không hợp lệ
    assert client.get(f"/api/admin/dashboard?from_date={end_str}&to_date={start_str}", headers=h).status_code == 400
    assert client.get("/api/admin/dashboard?from_date=abc&to_date=def", headers=h).status_code == 400
