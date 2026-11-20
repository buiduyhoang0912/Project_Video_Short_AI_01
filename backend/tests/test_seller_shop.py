"""Test API đơn đăng ký bán hàng và cửa hàng (Task T3D24AA).
Chạy: pytest (dùng SQLite in-memory, không cần MySQL).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import BIGINT, ENUM, INTEGER
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.db.session import Base, get_db
from app.main import app
from app.models.shop import Shop
from app.models.user import User

# Bổ sung relationship còn thiếu giữa order/cart và User/Shop khi chạy test
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


def register_and_login(client, username="seller1", email="s1@example.com"):
    r = client.post(
        "/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "password123",
            "display_name": username.capitalize(),
        },
    )
    assert r.status_code == 201
    user_id = r.json()["id"]

    r_login = client.post(
        "/auth/login",
        json={"identifier": username, "password": "password123"},
    )
    assert r_login.status_code == 200
    token = r_login.json()["access_token"]
    return user_id, {"Authorization": f"Bearer {token}"}


def make_admin(db_session, user_id: int):
    db = db_session()
    user = db.get(User, user_id)
    user.role = "ADMIN"
    db.commit()
    db.close()


def test_submit_application_and_single_pending_limit(client):
    _, headers = register_and_login(client)
    payload = {
        "proposed_shop_name": "Shop Thời Trang Văn",
        "phone": "0912345678",
        "description": "Chuyên quần áo nam nữ chất lượng cao",
    }

    # Gửi đơn lần 1 -> 201 Created
    r1 = client.post("/api/seller-applications", json=payload, headers=headers)
    assert r1.status_code == 201
    data = r1.json()
    assert data["status"] == "PENDING"
    assert data["proposed_shop_name"] == "Shop Thời Trang Văn"

    # Gửi đơn lần 2 khi đơn đầu đang PENDING -> 409 Conflict
    r2 = client.post("/api/seller-applications", json=payload, headers=headers)
    assert r2.status_code == 409


def test_cannot_create_shop_before_admin_approval(client):
    _, headers = register_and_login(client)

    # Chưa gửi đơn / chưa được duyệt mà tạo shop -> 403 Forbidden
    r = client.post(
        "/api/shops",
        json={"name": "Shop Chưa Duyệt", "description": "Mô tả"},
        headers=headers,
    )
    assert r.status_code == 403


def test_full_flow_approve_then_create_update_and_view_public_shop(
    client, db_session
):
    _, user_headers = register_and_login(client, "van_user", "van@example.com")
    admin_id, admin_headers = register_and_login(
        client, "admin_user", "admin@example.com"
    )
    make_admin(db_session, admin_id)

    # 1. Người dùng gửi đơn đăng ký bán hàng
    r_app = client.post(
        "/api/seller-applications",
        json={
            "proposed_shop_name": "ClipShop Official",
            "phone": "0987654321",
            "description": "Cửa hàng phụ kiện công nghệ",
        },
        headers=user_headers,
    )
    assert r_app.status_code == 201
    app_id = r_app.json()["id"]

    # 2. Admin duyệt đơn
    r_approve = client.put(
        f"/api/seller-applications/{app_id}/approve",
        headers=admin_headers,
    )
    assert r_approve.status_code == 200
    assert r_approve.json()["status"] == "APPROVED"
    assert r_approve.json()["reviewed_by"] == admin_id

    # Kiểm tra role của user đã chuyển thành SELLER
    r_me = client.get("/auth/me", headers=user_headers)
    assert r_me.json()["role"] == "SELLER"

    # 3. Sau khi Admin duyệt, người bán tạo cửa hàng
    r_shop = client.post(
        "/api/shops",
        json={
            "name": "ClipShop Official",
            "description": "Phụ kiện chính hãng",
            "address": "Hà Nội",
        },
        headers=user_headers,
    )
    assert r_shop.status_code == 201
    shop_data = r_shop.json()
    shop_id = shop_data["id"]
    assert shop_data["name"] == "ClipShop Official"
    assert shop_data["status"] == "ACTIVE"

    # Mỗi người bán chỉ được tạo 1 cửa hàng -> tạo thêm sẽ báo 409
    r_dup_shop = client.post(
        "/api/shops",
        json={"name": "Shop Thứ 2"},
        headers=user_headers,
    )
    assert r_dup_shop.status_code == 409

    # 4. Người bán sửa thông tin cửa hàng
    r_update = client.put(
        f"/api/shops/{shop_id}",
        json={
            "name": "ClipShop Official VN",
            "address": "Cầu Giấy, Hà Nội",
        },
        headers=user_headers,
    )
    assert r_update.status_code == 200
    assert r_update.json()["name"] == "ClipShop Official VN"
    assert r_update.json()["address"] == "Cầu Giấy, Hà Nội"

    # 5. Xem thông tin cửa hàng công khai (không cần đăng nhập)
    r_public_detail = client.get(f"/api/shops/{shop_id}")
    assert r_public_detail.status_code == 200
    assert r_public_detail.json()["name"] == "ClipShop Official VN"

    r_public_list = client.get("/api/shops?q=ClipShop")
    assert r_public_list.status_code == 200
    assert len(r_public_list.json()) == 1


def test_reject_application_then_can_resubmit(client, db_session):
    _, user_headers = register_and_login(client, "user2", "u2@example.com")
    admin_id, admin_headers = register_and_login(
        client, "admin2", "a2@example.com"
    )
    make_admin(db_session, admin_id)

    # Gửi đơn lần 1
    r1 = client.post(
        "/api/seller-applications",
        json={
            "proposed_shop_name": "Shop A",
            "phone": "0911222333",
            "description": "Mô tả shop A",
        },
        headers=user_headers,
    )
    app_id = r1.json()["id"]

    # Admin từ chối đơn
    r_reject = client.put(
        f"/api/seller-applications/{app_id}/reject",
        json={"rejection_reason": "Thông tin mô tả chưa rõ ràng"},
        headers=admin_headers,
    )
    assert r_reject.status_code == 200
    assert r_reject.json()["status"] == "REJECTED"

    # Sau khi bị từ chối (không còn đơn PENDING), người dùng có thể gửi lại đơn mới
    r2 = client.post(
        "/api/seller-applications",
        json={
            "proposed_shop_name": "Shop A Mới",
            "phone": "0911222333",
            "description": "Mô tả chi tiết rõ ràng hơn",
        },
        headers=user_headers,
    )
    assert r2.status_code == 201
    assert r2.json()["status"] == "PENDING"


def test_shop_logo_upload_and_public_shop_videos(client, db_session):
    from io import BytesIO
    from PIL import Image
    from app.models.video import Video
    from app.routers.shops import SHOP_UPLOADS_DIR

    user_id, user_headers = register_and_login(
        client, "seller_video", "sv@example.com"
    )
    client.post("/api/seller-applications/quick-setup", headers=user_headers)

    r_me_shop = client.get("/api/shops/me", headers=user_headers)
    assert r_me_shop.status_code == 200
    shop_id = r_me_shop.json()["id"]

    # 1. Upload logo cửa hàng
    buf = BytesIO()
    Image.new("RGB", (48, 48), color=(0, 128, 255)).save(buf, format="PNG")
    r_logo = client.post(
        f"/api/shops/{shop_id}/logo",
        files={"file": ("logo.png", buf.getvalue(), "image/png")},
        headers=user_headers,
    )
    assert r_logo.status_code == 200
    avatar_key = r_logo.json()["avatar_key"]
    assert avatar_key.startswith("/uploads/shops/")

    fname = avatar_key.removeprefix("/uploads/shops/")
    fpath = SHOP_UPLOADS_DIR / fname
    assert fpath.exists()
    fpath.unlink(missing_ok=True)

    # 2. Tạo video công khai của chủ shop và kiểm tra GET /api/shops/{shop_id}/videos
    db = db_session()
    db.add(
        Video(
            user_id=user_id,
            title="Video giới thiệu sản phẩm của Shop",
            description="Review thực tế tại cửa hàng",
            video_url="/uploads/videos/demo.mp4",
            thumbnail_url="/uploads/thumbnails/demo.jpg",
            duration_seconds=25,
            view_count=12,
            status="VISIBLE",
        )
    )
    db.commit()
    db.close()

    r_videos = client.get(f"/api/shops/{shop_id}/videos")
    assert r_videos.status_code == 200
    videos = r_videos.json()
    assert len(videos) == 1
    assert videos[0]["title"] == "Video giới thiệu sản phẩm của Shop"
    assert videos[0]["view_count"] == 12


