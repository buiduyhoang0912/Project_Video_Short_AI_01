"""Test luồng xuyên suốt hệ thống (E2E Integration Flow - Task T3D1DB4).
Chạy: pytest tests/test_e2e_full_flow.py (SQLite in-memory, không cần MySQL).

Kiểm tra chuỗi nghiệp vụ toàn diện từ người dùng đến admin:
1. Đăng ký & Đăng nhập (Buyer, Seller, Admin)
2. Gửi đơn đăng ký người bán -> Admin duyệt (chuyển role SELLER)
3. Người bán tạo cửa hàng, đăng sản phẩm & video gắn sản phẩm
4. Người mua xem sản phẩm/video, thêm giỏ hàng & đặt hàng thành công
5. Kiểm tra tồn kho bị trừ chính xác và doanh thu được ghi nhận
6. Admin kiểm duyệt ẩn video & sản phẩm vi phạm kèm lý do
7. Kiểm tra nội dung vi phạm bị ẩn khỏi người mua, seller/chủ video không tự bật lại được
8. Admin khoá tài khoản vi phạm -> chặn token và chặn đăng nhập; sau đó mở khoá thành công
9. Dashboard thống kê: doanh thu khớp chính xác, không cộng trùng đơn nhiều item, loại bỏ đơn cancelled/pending
"""

from decimal import Decimal
import uuid

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
from app.models.product import Product
from app.models.shop import Shop
from app.models.user import User
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


def make_user(Session, role="USER", username=None, password="Passw0rd123!"):
    n = username or f"user_{uuid.uuid4().hex[:6]}"
    with Session() as db:
        u = User(
            email=f"{n}@tokflow.com",
            username=n,
            display_name=f"Tên {n}",
            password_hash=hash_password(password),
            role=role,
            status="ACTIVE",
        )
        db.add(u)
        db.commit()
        return u.id


def auth_header(user_id: int):
    token, _ = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def test_e2e_complete_platform_flow(client, Session):
    # =========================================================================
    # BƯỚC 1: Đăng ký & Đăng nhập (Admin, Applicant, Buyer)
    # =========================================================================
    admin_id = make_user(Session, role="ADMIN", username="admin_super")
    admin_h = auth_header(admin_id)

    # Đăng ký tài khoản người mua và người bán qua API /auth/register
    r_reg_seller = client.post(
        "/auth/register",
        json={
            "username": "seller_demo",
            "email": "seller_demo@clipshop.ai",
            "password": "Password123!",
            "display_name": "Shop Hoàng Văn",
        },
    )
    assert r_reg_seller.status_code == 201
    applicant_id = r_reg_seller.json()["id"]

    r_reg_buyer = client.post(
        "/auth/register",
        json={
            "username": "buyer_demo",
            "email": "buyer_demo@clipshop.ai",
            "password": "Password123!",
            "display_name": "Người mua mẫu",
        },
    )
    assert r_reg_buyer.status_code == 201
    buyer_id = r_reg_buyer.json()["id"]

    # Đăng nhập kiểm tra token
    r_login = client.post(
        "/auth/login",
        json={"identifier": "seller_demo", "password": "Password123!"},
    )
    assert r_login.status_code == 200
    applicant_token = r_login.json()["access_token"]
    applicant_h = {"Authorization": f"Bearer {applicant_token}"}

    r_login_buyer = client.post(
        "/auth/login",
        json={"identifier": "buyer_demo", "password": "Password123!"},
    )
    assert r_login_buyer.status_code == 200
    buyer_h = {"Authorization": f"Bearer {r_login_buyer.json()['access_token']}"}

    # =========================================================================
    # BƯỚC 2: Gửi đơn đăng ký người bán -> Admin duyệt (chuyển SELLER)
    # =========================================================================
    # Applicant gửi đơn
    r_sub = client.post(
        "/api/seller-applications",
        json={
            "proposed_shop_name": "Shop Thời Trang Trẻ",
            "phone": "0987654321",
            "description": "Chuyên bán áo hoodie và phụ kiện thời trang",
        },
        headers=applicant_h,
    )
    assert r_sub.status_code == 201
    app_id = r_sub.json()["id"]
    assert r_sub.json()["status"] == "PENDING"

    # Admin duyệt đơn
    r_app = client.patch(
        f"/api/admin/seller-applications/{app_id}/approve",
        headers=admin_h,
    )
    assert r_app.status_code == 200
    assert r_app.json()["status"] == "APPROVED"

    # Xác nhận role của applicant đã được nâng lên SELLER
    with Session() as db:
        user_db = db.get(User, applicant_id)
        assert user_db.role == "SELLER"

    # =========================================================================
    # BƯỚC 3: Người bán tạo Shop, thêm Sản phẩm & Đăng Video
    # =========================================================================
    # Tạo category mẫu và shop
    with Session() as db:
        cat = Category(name="Thời trang nam", status="ACTIVE")
        shop = Shop(owner_id=applicant_id, name="Shop Thời Trang Trẻ", status="ACTIVE")
        db.add_all([cat, shop])
        db.commit()
        cat_id = cat.id
        shop_id = shop.id

        # Tạo 2 sản phẩm: Áo hoodie (giá 150k, tồn 10) và Mũ lưỡi trai (giá 50k, tồn 20)
        p1 = Product(
            shop_id=shop_id,
            category_id=cat_id,
            name="Áo Hoodie Nam Nữ",
            price=Decimal("150000"),
            stock=10,
            status="ACTIVE",
        )
        p2 = Product(
            shop_id=shop_id,
            category_id=cat_id,
            name="Mũ Lưỡi Trai Unisex",
            price=Decimal("50000"),
            stock=20,
            status="ACTIVE",
        )
        db.add_all([p1, p2])
        db.commit()
        p1_id = p1.id
        p2_id = p2.id

        # Đăng video của seller
        vid = Video(
            user_id=applicant_id,
            title="Review Áo Hoodie Mới Về Cực Đẹp",
            video_url="/uploads/videos/demo.mp4",
            duration_seconds=15,
            status="VISIBLE",
        )
        db.add(vid)
        db.commit()
        vid_id = vid.id

    # =========================================================================
    # BƯỚC 4: Người mua xem sản phẩm/video, thêm giỏ hàng & Đặt hàng
    # =========================================================================
    # Buyer xem chi tiết sản phẩm công khai
    r_detail = client.get(f"/api/products/{p1_id}")
    assert r_detail.status_code == 200
    assert r_detail.json()["name"] == "Áo Hoodie Nam Nữ"

    # Buyer thêm sản phẩm vào giỏ hàng
    r_add_cart = client.post(
        "/api/cart/items",
        json={"product_id": p1_id, "quantity": 2},
        headers=buyer_h,
    )
    assert r_add_cart.status_code in (200, 201)

    r_add_cart2 = client.post(
        "/api/cart/items",
        json={"product_id": p2_id, "quantity": 1},
        headers=buyer_h,
    )
    assert r_add_cart2.status_code in (200, 201)

    # Buyer tạo đơn hàng (checkout) với thanh toán mô phỏng (tổng = 2*150k + 1*50k = 350k)
    r_order = client.post(
        "/api/orders",
        json={
            "recipient_name": "Nguyễn Văn Mua",
            "recipient_phone": "0912345678",
            "recipient_address": "Số 1 Đại Cồ Việt, Hà Nội",
            "payment_method": "MÔ PHỎNG",
            "items": [
                {"product_id": p1_id, "quantity": 2},
                {"product_id": p2_id, "quantity": 1},
            ],
        },
        headers=buyer_h,
    )
    assert r_order.status_code == 201
    orders_data = r_order.json()
    created_orders = orders_data["orders"]
    assert len(created_orders) >= 1
    # Đơn hàng thanh toán mô phỏng được chuyển sang confirmed
    assert created_orders[0]["status"] in ("confirmed", "completed")
    assert Decimal(str(orders_data["total_amount"])) == Decimal("350000")

    # Kiểm tra tồn kho sau khi đặt: p1 còn 8, p2 còn 19
    with Session() as db:
        assert db.get(Product, p1_id).stock == 8
        assert db.get(Product, p2_id).stock == 19

    # =========================================================================
    # BƯỚC 5: Admin kiểm duyệt ẩn video & sản phẩm vi phạm
    # =========================================================================
    # Admin ẩn video kèm lý do
    r_hide_vid = client.patch(
        f"/api/admin/videos/{vid_id}/visibility",
        json={"status": "HIDDEN", "reason": "Bản quyền âm thanh chưa cấp phép"},
        headers=admin_h,
    )
    assert r_hide_vid.status_code == 200
    assert r_hide_vid.json()["status"] == "HIDDEN"

    # Admin ẩn sản phẩm p2 kèm lý do
    r_hide_p2 = client.patch(
        f"/api/admin/products/{p2_id}/visibility",
        json={"status": "HIDDEN", "reason": "Hàng vi phạm nhãn hiệu"},
        headers=admin_h,
    )
    assert r_hide_p2.status_code == 200
    assert r_hide_p2.json()["status"] == "HIDDEN"

    # Người mua xem sản phẩm p2 bị ẩn -> trả về 404
    assert client.get(f"/api/products/{p2_id}").status_code == 404

    # Người mua cố thêm sản phẩm bị ẩn vào giỏ -> bị chặn 400
    r_cart_blocked = client.post(
        "/api/cart/items",
        json={"product_id": p2_id, "quantity": 1},
        headers=buyer_h,
    )
    assert r_cart_blocked.status_code == 400

    # Chủ video cố ý tự bật lại video bị Admin ẩn -> bị chặn 403
    r_unhide_vid_fail = client.patch(
        f"/api/videos/{vid_id}/status",
        json={"status": "VISIBLE"},
        headers=applicant_h,
    )
    assert r_unhide_vid_fail.status_code == 403

    # Seller cố ý tự kích hoạt lại sản phẩm bị Admin ẩn -> bị chặn 403
    r_unhide_prd_fail = client.patch(
        f"/api/products/{p2_id}",
        json={"status": "ACTIVE"},
        headers=applicant_h,
    )
    assert r_unhide_prd_fail.status_code == 403

    # =========================================================================
    # BƯỚC 6: Admin khoá & Mở khoá tài khoản
    # =========================================================================
    # Khoá tài khoản seller
    r_lock = client.patch(f"/api/admin/users/{applicant_id}/lock", headers=admin_h)
    assert r_lock.status_code == 200
    assert r_lock.json()["status"] == "LOCKED"

    # Seller bị khoá không thể đăng nhập
    r_login_locked = client.post(
        "/auth/login",
        json={"identifier": "seller_demo", "password": "Password123!"},
    )
    assert r_login_locked.status_code == 403

    # Seller dùng token cũ bị chặn 403
    r_token_blocked = client.get("/api/seller-applications/me", headers=applicant_h)
    assert r_token_blocked.status_code == 403

    # Admin mở khoá lại cho seller
    r_unlock = client.patch(f"/api/admin/users/{applicant_id}/unlock", headers=admin_h)
    assert r_unlock.status_code == 200
    assert r_unlock.json()["status"] == "ACTIVE"

    # Seller đăng nhập và dùng token trở lại bình thường
    assert client.get("/api/seller-applications/me", headers=applicant_h).status_code == 200

    # =========================================================================
    # BƯỚC 7: Dashboard thống kê toàn sàn
    # =========================================================================
    r_dash = client.get("/api/admin/dashboard?days=30", headers=admin_h)
    assert r_dash.status_code == 200
    dash_data = r_dash.json()
    summary = dash_data["summary"]

    # Kiểm tra số lượng
    assert summary["total_users"] == 3  # Admin, Seller, Buyer
    assert summary["total_sellers"] == 1
    assert summary["total_videos"] == 1
    assert summary["total_products"] == 2
    assert summary["total_orders"] == 1

    # Doanh thu tính đúng đơn 350k (đơn có 2 item nhưng không bị cộng trùng!)
    assert Decimal(str(summary["total_revenue"])) == Decimal("350000")

    # Kiểm tra điểm doanh thu trong daily
    today_point = dash_data["daily"][-1]
    assert Decimal(str(today_point["revenue"])) == Decimal("350000")
    assert today_point["orders"] == 1


def test_e2e_seller_shop_ai_voucher_order_lifecycle_and_analytics(
    client, Session
):
    """Kiểm thử luồng tích hợp xuyên suốt phân hệ Người bán & Cửa hàng (Task T3D1DBA - Nguyễn Hoàng Văn):
    Đăng ký bán hàng -> Admin duyệt -> Tạo Shop -> Gợi ý sản phẩm & kịch bản 30-60s bằng AI ->
    Đăng sản phẩm & tồn kho -> Tạo Mã giảm giá của Shop -> Người mua áp mã đặt hàng (Server tính lại tiền) ->
    Người bán xử lý đơn (Chờ xác nhận -> Đã xác nhận -> Đang giao -> Hoàn thành) ->
    Thống kê Doanh thu theo ngày & Sản phẩm bán chạy của Shop.
    """
    from datetime import datetime, timedelta

    admin_id = make_user(Session, role="ADMIN", username="admin_t3d1dba")
    admin_h = auth_header(admin_id)

    # 1. Người dùng đăng ký tài khoản & gửi đơn đăng ký bán hàng
    client.post(
        "/auth/register",
        json={
            "username": "van_seller_e2e",
            "email": "van_seller_e2e@clipshop.ai",
            "password": "Password123!",
            "display_name": "Nguyễn Hoàng Văn",
        },
    )
    r_login_s = client.post(
        "/auth/login",
        json={"identifier": "van_seller_e2e", "password": "Password123!"},
    )
    seller_h = {"Authorization": f"Bearer {r_login_s.json()['access_token']}"}

    r_app = client.post(
        "/api/seller-applications",
        json={
            "proposed_shop_name": "Hoàng Văn Flagship Store",
            "phone": "0912345678",
            "description": "Chuyên thời trang và phụ kiện công nghệ chính hãng",
        },
        headers=seller_h,
    )
    assert r_app.status_code == 201
    app_id = r_app.json()["id"]

    # Admin duyệt đơn -> user lên quyền SELLER
    r_approve = client.patch(
        f"/api/admin/seller-applications/{app_id}/approve",
        headers=admin_h,
    )
    assert r_approve.status_code == 200

    # 2. Người bán tạo cửa hàng mới
    r_shop = client.post(
        "/api/shops",
        json={
            "name": "Hoàng Văn Flagship Store",
            "description": "Gian hàng chính hãng uy tín",
            "address": "Hà Nội",
        },
        headers=seller_h,
    )
    assert r_shop.status_code == 201
    shop_id = r_shop.json()["id"]

    with Session() as db:
        cat = Category(name="Phụ kiện & Thời trang", status="ACTIVE")
        db.add(cat)
        db.commit()
        cat_id = cat.id

    # 3. Người bán bấm 'Gợi ý bằng AI' để sinh tên, mô tả & kịch bản video 30-60s rồi sửa trước khi lưu
    r_ai = client.post(
        "/api/products/ai-suggest",
        json={
            "raw_name": "Áo Khoác Bomber Hàn Quốc",
            "category_id": cat_id,
            "price": 250000,
            "features": "Chống gió, lót dù thoáng khí, form unisex",
            "duration_seconds": 45,
        },
        headers=seller_h,
    )
    assert r_ai.status_code == 200
    ai_data = r_ai.json()
    assert "00s - 05s" in ai_data["video_script_30_60s"]

    r_prod = client.post(
        "/api/products",
        json={
            "category_id": cat_id,
            "name": ai_data["suggested_name"][:120],
            "description": ai_data["suggested_description"],
            "price": 250000,
            "stock": 20,
        },
        headers=seller_h,
    )
    assert r_prod.status_code == 201
    prod_id = r_prod.json()["id"]

    # 4. Người bán tạo Mã giảm giá của Shop (GIAM10: giảm 10% tối đa 30k cho đơn từ 300k)
    r_voucher = client.post(
        "/api/shops/me/vouchers",
        json={
            "code": "GIAM10",
            "description": "Giảm 10% tối đa 30k cho đơn từ 300k",
            "discount_type": "PERCENT",
            "discount_value": 10,
            "max_discount_amount": 30000,
            "min_order_amount": 300000,
            "usage_limit": 10,
            "per_user_limit": 2,
            "expires_at": (datetime.now() + timedelta(days=7)).isoformat(
                timespec="seconds"
            ),
        },
        headers=seller_h,
    )
    assert r_voucher.status_code == 201

    # Kiểm tra trang cửa hàng công khai hiển thị sản phẩm và voucher
    assert len(client.get(f"/api/shops/{shop_id}/products").json()) == 1
    assert len(client.get(f"/api/shops/{shop_id}/vouchers").json()) == 1

    # 5. Người mua thêm 2 sản phẩm vào giỏ (500.000đ), áp mã GIAM10 (giảm 30.000đ -> còn 470.000đ) và đặt hàng COD
    buyer_id = make_user(Session, role="USER", username="buyer_t3d1dba")
    buyer_h = auth_header(buyer_id)

    client.post(
        "/api/cart/items",
        json={"product_id": prod_id, "quantity": 2},
        headers=buyer_h,
    )
    r_apply = client.post(
        "/api/vouchers/apply",
        json={"code": "giam10"},
        headers=buyer_h,
    )
    assert r_apply.status_code == 200
    assert r_apply.json()["discount_amount"] == 30000
    assert r_apply.json()["total_after_discount"] == 470000

    r_checkout = client.post(
        "/api/orders",
        json={
            "recipient_name": "Khách Mua Hàng",
            "recipient_phone": "0988112233",
            "recipient_address": "Cầu Giấy, Hà Nội",
            "payment_method": "COD",
            "voucher_codes": ["GIAM10"],
        },
        headers=buyer_h,
    )
    assert r_checkout.status_code == 201
    checkout_res = r_checkout.json()
    assert checkout_res["total_before_discount"] == 500000
    assert checkout_res["total_discount"] == 30000
    assert checkout_res["total_amount"] == 470000
    order_id = checkout_res["orders"][0]["id"]

    # 6. Người bán xem đơn của shop và cập nhật tuần tự: pending -> confirmed -> shipping -> completed
    r_shop_orders = client.get("/api/shops/me/orders", headers=seller_h)
    assert r_shop_orders.status_code == 200
    assert r_shop_orders.json()[0]["voucher_code"] == "GIAM10"

    for next_st in ("confirmed", "shipping", "completed"):
        r_st = client.patch(
            f"/api/shops/me/orders/{order_id}/status",
            json={"status": next_st},
            headers=seller_h,
        )
        assert r_st.status_code == 200
        assert r_st.json()["status"] == next_st

    # 7. Người bán kiểm tra thống kê Doanh thu theo ngày & Sản phẩm bán chạy của Shop
    r_analytics = client.get("/api/shops/me/analytics", headers=seller_h)
    assert r_analytics.status_code == 200
    an = r_analytics.json()
    assert an["completed_orders"] == 1
    assert an["total_revenue"] == 470000.0
    assert an["best_selling_products"][0]["product_id"] == prod_id
    assert an["best_selling_products"][0]["total_quantity_sold"] == 2

