"""Tạo dữ liệu mẫu sẵn sàng cho buổi bảo vệ & demo (Task T3D1DB4).
Chạy: python app/seed_demo_flow.py

Tài khoản được tạo (mật khẩu chung: Password123!):
- admin01 (ADMIN)           -> Đăng nhập trang Admin (pages/admin.html)
- seller_candidate (USER)    -> Đang có 1 đơn PENDING chờ Admin duyệt
- seller_active (SELLER)     -> Đang có 1 Shop, 2 sản phẩm, 1 video để demo kiểm duyệt
- user_normal (USER)         -> Tài khoản đang ACTIVE để demo tìm kiếm & bấm khoá
- user_locked (USER)         -> Tài khoản đang LOCKED để demo bấm mở khoá
- buyer_sample (USER)        -> Tài khoản người mua có các đơn hàng confirmed và completed
"""

import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

# Đảm bảo import được package app khi chạy trực tiếp `python app/seed_demo_flow.py`
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.main import ensure_schema_columns
from app.models.category import Category
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.seller_application import SellerApplication
from app.models.shop import Shop
from app.models.user import User, utc_now
from app.models.video import Video
from app.models.voucher import ShopVoucher


def seed_demo():
    print("[Seed] Đang khởi tạo dữ liệu mẫu cho demo T3D1DB4...")
    Base.metadata.create_all(bind=engine)
    ensure_schema_columns(engine)
    now = utc_now()
    default_pwd = hash_password("Password123!")

    with SessionLocal() as db:
        # 1. Admin
        admin = db.scalar(select(User).where(User.username == "admin01"))
        if not admin:
            admin = User(
                username="admin01",
                email="admin01@clipshop.ai",
                display_name="Quản Trị Viên Hệ Thống",
                password_hash=default_pwd,
                role="ADMIN",
                status="ACTIVE",
            )
            db.add(admin)
            db.flush()
            print(" -> Tạo tài khoản ADMIN: admin01 / Password123!")

        # 2. Seller Candidate (có đơn PENDING)
        cand = db.scalar(select(User).where(User.username == "seller_candidate"))
        if not cand:
            cand = User(
                username="seller_candidate",
                email="candidate@clipshop.ai",
                display_name="Hoàng Văn Candidate",
                password_hash=default_pwd,
                role="USER",
                status="ACTIVE",
            )
            db.add(cand)
            db.flush()

            app_pending = SellerApplication(
                user_id=cand.id,
                proposed_shop_name="GenZ Fashion Official",
                phone="0988776655",
                description="Cửa hàng thời trang phong cách đường phố dành cho giới trẻ",
                status="PENDING",
            )
            db.add(app_pending)
            print(" -> Tạo ứng viên đăng ký bán hàng: seller_candidate (đơn PENDING)")

        # 3. Seller Active (có Shop, Sản phẩm, Video)
        seller = db.scalar(select(User).where(User.username == "seller_active"))
        if not seller:
            seller = User(
                username="seller_active",
                email="seller_active@clipshop.ai",
                display_name="Shop Hoàng Văn",
                password_hash=default_pwd,
                role="SELLER",
                status="ACTIVE",
            )
            db.add(seller)
            db.flush()

            # Shop
            shop = Shop(
                owner_id=seller.id,
                name="Shop Hoàng Văn Studio",
                description="Thời trang & Phụ kiện cao cấp",
                address="Hà Nội, Việt Nam",
                status="ACTIVE",
            )
            db.add(shop)
            db.flush()

            # Category
            cat = db.scalar(select(Category).where(Category.name == "Thời trang"))
            if not cat:
                cat = Category(name="Thời trang", status="ACTIVE")
                db.add(cat)
                db.flush()

            # Products
            p1 = Product(
                shop_id=shop.id,
                category_id=cat.id,
                name="Áo Hoodie Nỉ Bông Unisex",
                price=Decimal("199000"),
                stock=50,
                status="ACTIVE",
            )
            p2 = Product(
                shop_id=shop.id,
                category_id=cat.id,
                name="Mũ Lưỡi Trai Classic (Hàng Cấm Vi Phạm)",
                price=Decimal("79000"),
                stock=20,
                status="ACTIVE",
            )
            db.add_all([p1, p2])
            db.flush()

            # Video
            vid = Video(
                user_id=seller.id,
                title="Review Áo Hoodie Mới Về Đẹp Hết Nấc",
                description="Chiếc áo cực hot trong mùa đông năm nay #hoodie #fashion",
                video_url="/uploads/videos/sample.mp4",
                duration_seconds=18,
                view_count=1250,
                status="VISIBLE",
            )
            db.add(vid)
            print(" -> Tạo seller_active: có shop, 2 sản phẩm và 1 video")

        # 3b. Mã giảm giá mẫu cho Shop Hoàng Văn Studio (Task T3D2BFB / T3D1DBA)
        shop_for_voucher = db.scalar(select(Shop).limit(1))
        if shop_for_voucher:
            existing_v1 = db.scalar(
                select(ShopVoucher).where(
                    ShopVoucher.shop_id == shop_for_voucher.id,
                    ShopVoucher.code == "GIAM10",
                )
            )
            if not existing_v1:
                db.add_all(
                    [
                        ShopVoucher(
                            shop_id=shop_for_voucher.id,
                            code="GIAM10",
                            description="Giảm 10% tối đa 30.000đ cho đơn từ 150.000đ",
                            discount_type="PERCENT",
                            discount_value=Decimal("10"),
                            max_discount_amount=Decimal("30000"),
                            min_order_amount=Decimal("150000"),
                            usage_limit=50,
                            used_count=0,
                            per_user_limit=5,
                            expires_at=now + timedelta(days=14),
                            status="ACTIVE",
                        ),
                        ShopVoucher(
                            shop_id=shop_for_voucher.id,
                            code="HOANGVAN50K",
                            description="Giảm ngay 50.000đ cho đơn từ 300.000đ",
                            discount_type="FIXED",
                            discount_value=Decimal("50000"),
                            max_discount_amount=None,
                            min_order_amount=Decimal("300000"),
                            usage_limit=30,
                            used_count=0,
                            per_user_limit=3,
                            expires_at=now + timedelta(days=14),
                            status="ACTIVE",
                        ),
                    ]
                )
                print(" -> Tạo 2 mã giảm giá mẫu của shop: GIAM10 và HOANGVAN50K")

        # 4. User Normal (để demo khoá)
        u_norm = db.scalar(select(User).where(User.username == "user_normal"))
        if not u_norm:
            u_norm = User(
                username="user_normal",
                email="user_normal@clipshop.ai",
                display_name="Trần Văn Thường",
                password_hash=default_pwd,
                role="USER",
                status="ACTIVE",
            )
            db.add(u_norm)
            print(" -> Tạo user_normal (ACTIVE để test khoá)")

        # 5. User Locked (để demo mở khoá)
        u_lock = db.scalar(select(User).where(User.username == "user_locked"))
        if not u_lock:
            u_lock = User(
                username="user_locked",
                email="user_locked@clipshop.ai",
                display_name="Lê Vi Phạm (Đang bị khoá)",
                password_hash=default_pwd,
                role="USER",
                status="LOCKED",
            )
            db.add(u_lock)
            print(" -> Tạo user_locked (LOCKED để test mở khoá)")

        # 6. Đơn hàng mẫu cho Dashboard
        buyer = db.scalar(select(User).where(User.username == "buyer_sample"))
        if not buyer:
            buyer = User(
                username="buyer_sample",
                email="buyer_sample@clipshop.ai",
                display_name="Người Mua Chăm Chỉ",
                password_hash=default_pwd,
                role="USER",
                status="ACTIVE",
            )
            db.add(buyer)
            db.flush()

            # Tạo 3 đơn hàng ở các ngày khác nhau để vẽ biểu đồ
            shop_record = db.scalar(select(Shop).limit(1))
            if shop_record:
                # Đơn 1 (hôm nay): completed (398,000)
                o1 = Order(
                    buyer_id=buyer.id,
                    shop_id=shop_record.id,
                    total_amount=Decimal("398000"),
                    payment_method="MÔ PHỎNG",
                    status="completed",
                    recipient_name="Người Mua Chăm Chỉ",
                    recipient_phone="0911223344",
                    recipient_address="Hà Nội",
                    created_at=now,
                )
                # Đơn 2 (hôm qua): confirmed (199,000)
                o2 = Order(
                    buyer_id=buyer.id,
                    shop_id=shop_record.id,
                    total_amount=Decimal("199000"),
                    payment_method="MÔ PHỎNG",
                    status="confirmed",
                    recipient_name="Người Mua Chăm Chỉ",
                    recipient_phone="0911223344",
                    recipient_address="Hà Nội",
                    created_at=now - timedelta(days=1),
                )
                # Đơn 3 (2 ngày trước): cancelled (999,000 - không tính vào doanh thu)
                o3 = Order(
                    buyer_id=buyer.id,
                    shop_id=shop_record.id,
                    total_amount=Decimal("999000"),
                    payment_method="COD",
                    status="cancelled",
                    recipient_name="Người Mua Chăm Chỉ",
                    recipient_phone="0911223344",
                    recipient_address="Hà Nội",
                    created_at=now - timedelta(days=2),
                )
                db.add_all([o1, o2, o3])
                print(" -> Tạo 3 đơn hàng mẫu (2 đơn thành công tính doanh thu, 1 đơn huỷ)")

        db.commit()
    print("[Seed] Khởi tạo hoàn tất! Dữ liệu demo đã sẵn sàng.")


if __name__ == "__main__":
    seed_demo()
