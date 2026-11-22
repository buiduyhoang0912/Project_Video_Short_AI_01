"""Chạy thử luồng xuyên suốt THẬT qua HTTP trên server đang chạy (Task T3D1DB4).

Khác với pytest (SQLite in-memory), script này gọi API của backend đang chạy với MySQL thật:
    Đăng ký -> đăng nhập -> gửi đơn bán hàng -> Admin duyệt -> tạo shop -> thêm sản phẩm/video
    -> người mua thêm giỏ -> đặt hàng -> Admin kiểm duyệt -> khoá/mở khoá -> dashboard.

Cách chạy (server đã bật, DB nên là DB trống riêng cho E2E):
    python e2e_live_flow.py --reset --base http://127.0.0.1:8001 --out docs/t3d1db4-slide-demo/e2e_live_results.json

Kết quả từng bước (PASS/FAIL) được in ra và ghi vào file JSON để cập nhật Test Log.
"""

import argparse
import json
import sys
import time
import uuid
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User

ASSETS = Path(__file__).parent / "docs" / "t3d1db4_assets"
PWD = "Password123!"

results: list[dict] = []


def check(case_id: str, desc: str, expected: str, ok: bool, actual: str) -> bool:
    results.append(
        {
            "id": case_id,
            "description": desc,
            "expected": expected,
            "actual": actual,
            "result": "PASS" if ok else "FAIL",
        }
    )
    print(f"[{'PASS' if ok else 'FAIL'}] {case_id} {desc} | mong đợi: {expected} | thực tế: {actual}")
    return ok


def hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--out", default="")
    ap.add_argument("--reset", action="store_true", help="Xoá & tạo lại bảng (chỉ DB có tên chứa 'e2e')")
    args = ap.parse_args()

    c = httpx.Client(base_url=args.base, timeout=30)
    run = uuid.uuid4().hex[:6]
    seller_u, buyer_u, buyer2_u, admin_u = (
        f"e2e_seller_{run}",
        f"e2e_buyer_{run}",
        f"e2e_buyer2_{run}",
        f"e2e_admin_{run}",
    )

    if args.reset:
        # Chỉ cho phép reset DB dành riêng cho E2E, tránh xoá nhầm dữ liệu thật.
        from app.core.config import settings
        from app.db.session import Base, engine

        if "e2e" not in settings.DB_NAME.lower():
            print(f"Từ chối --reset: DB '{settings.DB_NAME}' không phải DB E2E (tên phải chứa 'e2e').")
            return 2
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    # Admin không có API đăng ký (đúng thiết kế) -> tạo trực tiếp trong DB như script seed.
    with SessionLocal() as db:
        db.add(
            User(
                username=admin_u,
                email=f"{admin_u}@clipshop.ai",
                display_name="E2E Admin",
                password_hash=hash_password(PWD),
                role="ADMIN",
                status="ACTIVE",
            )
        )
        db.commit()

    # ============ 1. ĐĂNG KÝ / ĐĂNG NHẬP ============
    ids = {}
    for key, uname in (("seller", seller_u), ("buyer", buyer_u), ("buyer2", buyer2_u)):
        r = c.post(
            "/auth/register",
            json={"username": uname, "email": f"{uname}@clipshop.ai", "password": PWD, "display_name": f"Tên {uname}"},
        )
        ids[key] = r.json().get("id") if r.status_code == 201 else None
        check(f"E2E-01{key[0]}", f"Đăng ký tài khoản {key}", "201", r.status_code == 201, str(r.status_code))

    r = c.post("/auth/register", json={"username": seller_u, "email": "khac@clipshop.ai", "password": PWD, "display_name": "X"})
    check("E2E-02", "Đăng ký trùng username", "409", r.status_code == 409, str(r.status_code))
    r = c.post("/auth/register", json={"username": f"weak_{run}", "email": f"weak_{run}@x.com", "password": "123", "display_name": "X"})
    check("E2E-03", "Đăng ký mật khẩu quá ngắn", "422", r.status_code == 422, str(r.status_code))
    r = c.post(
        "/auth/register",
        json={"username": f"hack_{run}", "email": f"hack_{run}@x.com", "password": PWD, "display_name": "X", "role": "ADMIN"},
    )
    check("E2E-04", "Đăng ký cố ý gửi role=ADMIN (leo quyền)", "422 (bị từ chối)", r.status_code == 422, str(r.status_code))

    tokens = {}
    for key, uname in (("seller", seller_u), ("buyer", buyer_u), ("buyer2", buyer2_u), ("admin", admin_u)):
        r = c.post("/auth/login", json={"identifier": uname, "password": PWD})
        ok = r.status_code == 200 and "access_token" in r.json()
        tokens[key] = r.json().get("access_token") if ok else ""
        check(f"E2E-05{key[0]}", f"Đăng nhập {key}", "200 + access_token", ok, str(r.status_code))
    r = c.post("/auth/login", json={"identifier": buyer_u, "password": "SaiMatKhau1!"})
    check("E2E-06", "Đăng nhập sai mật khẩu", "401", r.status_code == 401, str(r.status_code))
    r = c.get("/auth/me", headers=hdr(tokens["buyer"]))
    check("E2E-07", "GET /auth/me với token hợp lệ", "200 role=USER", r.status_code == 200 and r.json().get("role") == "USER", f"{r.status_code} {r.json().get('role') if r.status_code == 200 else ''}")

    H = {k: hdr(v) for k, v in tokens.items()}

    # ============ 2. GỬI ĐƠN BÁN HÀNG -> ADMIN DUYỆT ============
    r = c.post("/api/shops", json={"name": "Shop Trái Phép"}, headers=H["seller"])
    check("E2E-08", "USER chưa được duyệt tạo shop", "403", r.status_code == 403, str(r.status_code))

    app_body = {"proposed_shop_name": f"Shop E2E {run}", "phone": "0987654321", "description": "Thời trang trẻ cho GenZ"}
    r = c.post("/api/seller-applications", json=app_body, headers=H["seller"])
    app_id = r.json().get("id") if r.status_code == 201 else None
    check("E2E-09", "Gửi đơn đăng ký bán hàng", "201 PENDING", r.status_code == 201 and r.json().get("status") == "PENDING", f"{r.status_code}")
    r = c.post("/api/seller-applications", json=app_body, headers=H["seller"])
    check("E2E-10", "Gửi đơn thứ 2 khi đã có đơn PENDING", "409", r.status_code == 409, str(r.status_code))

    r = c.get("/api/admin/seller-applications", headers=H["buyer"])
    check("E2E-11", "USER thường gọi API Admin (xem danh sách đơn)", "403", r.status_code == 403, str(r.status_code))
    r = c.get("/api/admin/seller-applications")
    check("E2E-12", "Không token gọi API Admin", "401", r.status_code == 401, str(r.status_code))
    r = c.patch(f"/api/admin/seller-applications/{app_id}/approve", headers=H["seller"])
    check("E2E-13", "Người nộp đơn tự duyệt đơn của mình", "403", r.status_code == 403, str(r.status_code))
    r = c.put(f"/api/seller-applications/{app_id}/approve", headers=H["seller"])
    check("E2E-14", "Người nộp đơn tự duyệt qua API /seller-applications (PUT)", "403", r.status_code == 403, str(r.status_code))

    r = c.get("/api/admin/seller-applications?status=PENDING", headers=H["admin"])
    check("E2E-15", "Admin xem danh sách đơn PENDING", "200, có đơn vừa gửi", r.status_code == 200 and any(a["id"] == app_id for a in r.json()), str(r.status_code))
    r = c.patch(f"/api/admin/seller-applications/{app_id}/reject", json={"rejection_reason": ""}, headers=H["admin"])
    check("E2E-16", "Admin từ chối không nhập lý do", "422", r.status_code == 422, str(r.status_code))
    r = c.patch(f"/api/admin/seller-applications/{app_id}/approve", headers=H["admin"])
    check("E2E-17", "Admin duyệt đơn", "200 APPROVED", r.status_code == 200 and r.json().get("status") == "APPROVED", str(r.status_code))
    r = c.patch(f"/api/admin/seller-applications/{app_id}/approve", headers=H["admin"])
    check("E2E-18", "Duyệt lại đơn đã duyệt", "409", r.status_code == 409, str(r.status_code))
    r = c.get("/auth/me", headers=H["seller"])
    check("E2E-19", "Sau duyệt role người nộp đơn = SELLER", "SELLER", r.json().get("role") == "SELLER", str(r.json().get("role")))

    # ============ 3. TẠO SHOP -> SẢN PHẨM -> VIDEO ============
    r = c.post("/api/shops", json={"name": f"Shop E2E {run}", "description": "Shop demo", "address": "Hà Nội"}, headers=H["seller"])
    shop_id = r.json().get("id") if r.status_code == 201 else None
    check("E2E-20", "Seller tạo shop", "201", r.status_code == 201, str(r.status_code))
    r = c.post("/api/shops", json={"name": "Shop thứ hai"}, headers=H["seller"])
    check("E2E-21", "Seller tạo shop thứ 2", "409", r.status_code == 409, str(r.status_code))

    cats = c.get("/api/categories").json()
    cat_id = cats[0]["id"] if cats else None
    check("E2E-22", "Lấy danh mục sản phẩm", "200, có danh mục", bool(cat_id), f"{len(cats)} danh mục")

    prods = {}
    for key, name, price, stock in (("p1", "Áo Hoodie Nỉ Unisex", 150000, 10), ("p2", "Mũ Lưỡi Trai Classic", 50000, 20), ("p3", "Tất Cổ Cao", 30000, 5)):
        r = c.post(
            "/api/products",
            json={"name": name, "description": f"{name} chính hãng", "price": price, "stock": stock, "category_id": cat_id},
            headers=H["seller"],
        )
        prods[key] = r.json().get("id") if r.status_code == 201 else None
        check(f"E2E-23{key[1]}", f"Seller thêm sản phẩm {name}", "201", r.status_code == 201, str(r.status_code))
    r = c.post("/api/products", json={"name": "Hàng lậu", "price": 1000, "stock": 1, "category_id": cat_id}, headers=H["buyer"])
    check("E2E-24", "USER thường thêm sản phẩm", "403", r.status_code == 403, str(r.status_code))
    r = c.post("/api/products", json={"name": "Giá âm", "price": -5, "stock": 1, "category_id": cat_id}, headers=H["seller"])
    check("E2E-25", "Thêm sản phẩm giá âm", "422", r.status_code == 422, str(r.status_code))

    vid_id = None
    with open(ASSETS / "demo_clip.mp4", "rb") as fv, open(ASSETS / "demo_thumb.jpg", "rb") as ft:
        r = c.post(
            "/api/videos",
            data={"title": f"Review Hoodie {run}", "description": "Video review #hoodie"},
            files={"video": ("demo_clip.mp4", fv, "video/mp4"), "thumbnail": ("demo_thumb.jpg", ft, "image/jpeg")},
            auth=(seller_u, PWD),
        )
    if r.status_code == 201:
        vid_id = r.json()["id"]
    check("E2E-26", "Seller đăng video (MP4 + ảnh bìa)", "201", r.status_code == 201, f"{r.status_code} {r.text[:80] if r.status_code != 201 else ''}")
    if vid_id:
        rv = c.get(r.json()["video_url"])
        check("E2E-27", "File video phát được qua /uploads", "200 video/mp4", rv.status_code == 200 and "video" in rv.headers.get("content-type", ""), f"{rv.status_code} {rv.headers.get('content-type')}")
    r = c.get("/api/videos/feed")
    feed_ids = [v["id"] for v in r.json().get("items", r.json().get("videos", []))] if r.status_code == 200 and isinstance(r.json(), dict) else []
    check("E2E-28", "Video mới có trong feed công khai", "200, có video", r.status_code == 200 and vid_id in feed_ids, f"{r.status_code}, feed={len(feed_ids)}")

    # ============ 4. NGƯỜI MUA: GIỎ HÀNG -> ĐẶT HÀNG ============
    r = c.get(f"/api/products/{prods['p1']}")
    check("E2E-29", "Khách xem chi tiết sản phẩm công khai", "200", r.status_code == 200, str(r.status_code))
    r = c.post("/api/cart/items", json={"product_id": prods["p1"], "quantity": 2}, headers=H["buyer"])
    check("E2E-30", "Buyer thêm sản phẩm 1 vào giỏ (x2)", "201", r.status_code == 201, str(r.status_code))
    r = c.post("/api/cart/items", json={"product_id": prods["p2"], "quantity": 1}, headers=H["buyer"])
    check("E2E-31", "Buyer thêm sản phẩm 2 vào giỏ (x1)", "201", r.status_code == 201, str(r.status_code))
    r = c.post("/api/cart/items", json={"product_id": prods["p3"], "quantity": 99}, headers=H["buyer"])
    check("E2E-32", "Thêm vượt tồn kho", "400/409", r.status_code in (400, 409, 422), str(r.status_code))
    r = c.post("/api/cart/items", json={"product_id": prods["p1"], "quantity": 1})
    check("E2E-33", "Thêm giỏ khi chưa đăng nhập", "401", r.status_code == 401, str(r.status_code))
    r = c.get("/api/cart", headers=H["buyer"])
    check("E2E-34", "Xem giỏ hàng", "200", r.status_code == 200, str(r.status_code))

    r = c.post(
        "/api/orders",
        json={"recipient_name": "Nguyễn Văn Mua", "recipient_phone": "0912345678", "recipient_address": "1 Đại Cồ Việt, Hà Nội", "payment_method": "SIMULATED"},
        headers=H["buyer"],
    )
    order1 = r.json() if r.status_code == 201 else {}
    order1_id = order1["orders"][0]["id"] if order1.get("orders") else None
    check("E2E-35", "Buyer đặt hàng (2×150k + 1×50k)", "201, tổng 350000", r.status_code == 201 and Decimal(str(order1.get("total_amount", 0))) == Decimal("350000"), f"{r.status_code} tổng={order1.get('total_amount')}")
    r = c.get(f"/api/products/{prods['p1']}")
    check("E2E-36", "Tồn kho bị trừ sau đặt hàng (10→8)", "stock=8", r.json().get("stock") == 8, f"stock={r.json().get('stock')}")
    r = c.get("/api/cart", headers=H["buyer"])
    cart_json = r.json()
    cart_empty = not (cart_json.get("groups") or cart_json.get("items") or cart_json.get("shops"))
    check("E2E-37", "Giỏ hàng được dọn sau đặt hàng", "giỏ rỗng", r.status_code == 200 and cart_empty, f"{r.status_code}")
    r = c.get(f"/api/orders/{order1_id}", headers=H["buyer2"])
    check("E2E-38", "Người mua khác xem đơn không phải của mình", "403/404", r.status_code in (403, 404), str(r.status_code))
    r = c.get("/api/shops/me/orders", headers=H["seller"])
    check("E2E-39", "Seller thấy đơn của shop mình", "200, có đơn", r.status_code == 200 and any(o["id"] == order1_id for o in r.json()), str(r.status_code))
    r = c.get("/api/shops/me/orders", headers=H["buyer"])
    check("E2E-40", "USER thường xem đơn của shop", "403", r.status_code == 403, str(r.status_code))

    # Đơn 2 để huỷ -> kiểm tra doanh thu không tính đơn huỷ
    c.post("/api/cart/items", json={"product_id": prods["p3"], "quantity": 2}, headers=H["buyer2"])
    r = c.post(
        "/api/orders",
        json={"recipient_name": "Trần Mua Hai", "recipient_phone": "0911111111", "recipient_address": "2 Tạ Quang Bửu, Hà Nội", "payment_method": "COD"},
        headers=H["buyer2"],
    )
    order2 = r.json() if r.status_code == 201 else {}
    order2_id = order2["orders"][0]["id"] if order2.get("orders") else None
    check("E2E-41", "Buyer 2 đặt đơn COD (2×30k)", "201", r.status_code == 201, f"{r.status_code} tổng={order2.get('total_amount')}")
    r = c.post(f"/api/shops/me/orders/{order2_id}/cancel", headers=H["seller"])
    check("E2E-42", "Seller huỷ đơn 2", "200 cancelled", r.status_code == 200 and r.json().get("status") == "cancelled", f"{r.status_code} {r.json().get('status') if r.status_code == 200 else r.text[:80]}")

    # ============ 5. ADMIN KIỂM DUYỆT ============
    r = c.patch(f"/api/admin/videos/{vid_id}/visibility", json={}, headers=H["admin"])
    check("E2E-43", "Admin gửi body rỗng vào /visibility", "422", r.status_code == 422, str(r.status_code))
    r = c.patch(f"/api/admin/videos/{vid_id}/visibility", json={"status": "HIDDEN", "reason": ""}, headers=H["admin"])
    check("E2E-44", "Admin ẩn video không có lý do", "422", r.status_code == 422, str(r.status_code))
    r = c.patch(f"/api/admin/videos/{vid_id}/visibility", json={"status": "HIDDEN", "reason": "Bản quyền âm thanh"}, headers=H["admin"])
    check("E2E-45", "Admin ẩn video kèm lý do", "200 HIDDEN", r.status_code == 200 and r.json().get("status") == "HIDDEN", str(r.status_code))
    r = c.get("/api/videos/feed")
    feed_ids = [v["id"] for v in r.json().get("items", r.json().get("videos", []))]
    check("E2E-46", "Video bị ẩn biến mất khỏi feed", "không còn trong feed", vid_id not in feed_ids, f"feed={len(feed_ids)}")
    r = c.patch(f"/api/videos/{vid_id}/status", json={"status": "VISIBLE"}, headers=H["seller"])
    check("E2E-47", "Chủ video tự bật lại video bị Admin ẩn", "403", r.status_code == 403, str(r.status_code))
    r = c.patch(f"/api/admin/videos/{vid_id}/show", headers=H["seller"])
    check("E2E-48", "Seller gọi API Admin bật video", "403", r.status_code == 403, str(r.status_code))

    # Video bị ẩn không được lộ qua bất kỳ đường công khai nào khác
    r = c.get(f"/api/videos/{vid_id}")
    dj = r.json() if r.status_code == 200 else {}
    check("E2E-48a", "Khách mở chi tiết video bị ẩn: chỉ thấy thông báo, không lộ video_url", "200, is_available=false, video_url=null", r.status_code == 200 and dj.get("is_available") is False and dj.get("video_url") is None, f"{r.status_code} available={dj.get('is_available')} url={dj.get('video_url')}")
    r = c.post(f"/api/videos/{vid_id}/views")
    check("E2E-48b", "Tăng lượt xem video bị ẩn", "404", r.status_code == 404, str(r.status_code))
    r = c.post(f"/api/videos/{vid_id}/likes", headers=H["buyer"])
    check("E2E-48c", "Thả tim video bị ẩn", "400", r.status_code == 400, str(r.status_code))
    r = c.get(f"/api/videos/{vid_id}/comments")
    check("E2E-48d", "Xem bình luận video bị ẩn", "400", r.status_code == 400, str(r.status_code))
    r = c.post(f"/api/videos/{vid_id}/comments", json={"content": "bình luận vào video bị ẩn"}, headers=H["buyer"])
    check("E2E-48d2", "Bình luận vào video bị ẩn", "400", r.status_code == 400, str(r.status_code))
    r = c.get(f"/api/videos/users/{ids['seller']}")
    body = json.dumps(r.json()) if r.status_code == 200 else ""
    check("E2E-48e", "Trang video của chủ kênh (khách xem) không có video bị ẩn", f"không chứa id {vid_id}", r.status_code == 200 and f'"id": {vid_id},' not in body, str(r.status_code))
    r = c.get("/api/search", params={"q": f"Review Hoodie {run}"})
    found = [v["id"] for v in r.json().get("videos", [])] if r.status_code == 200 else [-1]
    check("E2E-48f", "Tìm kiếm không trả video bị ẩn", "videos không chứa video bị ẩn", r.status_code == 200 and vid_id not in found, f"{r.status_code} kết quả={found}")
    r = c.get(f"/api/shops/{shop_id}/videos")
    body = json.dumps(r.json()) if r.status_code == 200 else ""
    check("E2E-48g", "Trang shop công khai không có video bị ẩn", "không thấy tiêu đề", r.status_code == 200 and f"Review Hoodie {run}" not in body, str(r.status_code))

    # Sản phẩm đã nằm trong giỏ nhưng bị Admin ẩn trước khi thanh toán
    stock_before = next((p["stock"] for p in c.get("/api/shops/me/products", headers=H["seller"]).json() if p["id"] == prods["p3"]), None)
    c.post("/api/cart/items", json={"product_id": prods["p3"], "quantity": 1}, headers=H["buyer"])
    rh = c.patch(f"/api/admin/products/{prods['p3']}/visibility", json={"status": "HIDDEN", "reason": "Kiểm tra giỏ hàng"}, headers=H["admin"])
    r = c.post(
        "/api/orders",
        json={"recipient_name": "Nguyễn Văn Mua", "recipient_phone": "0912345678", "recipient_address": "1 Đại Cồ Việt, Hà Nội", "payment_method": "COD"},
        headers=H["buyer"],
    )
    stock_p3 = c.get("/api/shops/me/products", headers=H["seller"]).json()
    p3_stock = next((p["stock"] for p in stock_p3 if p["id"] == prods["p3"]), None)
    check("E2E-48h", "Đặt hàng khi sản phẩm trong giỏ đã bị Admin ẩn", "bị chặn (4xx), tồn kho không đổi", rh.status_code == 200 and 400 <= r.status_code < 500 and p3_stock == stock_before, f"hide={rh.status_code} order={r.status_code} stock {stock_before}->{p3_stock}")
    c.patch(f"/api/admin/products/{prods['p3']}/show", headers=H["admin"])
    c.delete("/api/cart", headers=H["buyer"])

    r = c.patch(f"/api/admin/products/{prods['p2']}/visibility", json={"status": "HIDDEN", "reason": "Vi phạm nhãn hiệu"}, headers=H["admin"])
    check("E2E-49", "Admin ẩn sản phẩm kèm lý do", "200 HIDDEN", r.status_code == 200 and r.json().get("status") == "HIDDEN", str(r.status_code))
    r = c.get(f"/api/products/{prods['p2']}")
    check("E2E-50", "Khách xem sản phẩm bị ẩn", "404", r.status_code == 404, str(r.status_code))
    r = c.post("/api/cart/items", json={"product_id": prods["p2"], "quantity": 1}, headers=H["buyer"])
    check("E2E-51", "Thêm sản phẩm bị ẩn vào giỏ", "400", r.status_code == 400, str(r.status_code))
    r = c.patch(f"/api/products/{prods['p2']}", json={"status": "ACTIVE"}, headers=H["seller"])
    check("E2E-52", "Seller tự bật lại sản phẩm bị Admin ẩn (PATCH status)", "403", r.status_code == 403, str(r.status_code))
    r = c.put(f"/api/products/{prods['p2']}", json={"status": "ACTIVE"}, headers=H["seller"])
    check("E2E-53", "Seller tự bật lại sản phẩm bị Admin ẩn (PUT status)", "403", r.status_code == 403, str(r.status_code))
    r = c.put(f"/api/products/{prods['p2']}/hide", headers=H["seller"])
    st = c.get("/api/shops/me/products", headers=H["seller"]).json()
    p2_status = next((p["status"] for p in st if p["id"] == prods["p2"]), None)
    check("E2E-54", "Seller gọi /hide (toggle) trên sản phẩm bị Admin ẩn không làm hiện lại", "vẫn HIDDEN", p2_status == "HIDDEN", f"{r.status_code}, status={p2_status}")
    r = c.get("/api/admin/products?status=HIDDEN", headers=H["admin"])
    check("E2E-55", "Admin xem danh sách sản phẩm đã ẩn", "200, có sản phẩm", r.status_code == 200 and any(p["id"] == prods["p2"] for p in r.json()), str(r.status_code))

    r = c.patch(f"/api/admin/videos/{vid_id}/show", headers=H["admin"])
    check("E2E-56", "Admin bật lại video", "200 VISIBLE", r.status_code == 200 and r.json().get("status") == "VISIBLE", str(r.status_code))
    r = c.patch(f"/api/admin/products/{prods['p2']}/show", headers=H["admin"])
    check("E2E-57", "Admin bật lại sản phẩm", "200 ACTIVE", r.status_code == 200 and r.json().get("status") == "ACTIVE", str(r.status_code))
    r = c.get(f"/api/products/{prods['p2']}")
    check("E2E-58", "Sản phẩm xem lại được sau khi Admin bật", "200", r.status_code == 200, str(r.status_code))

    # ============ 6. KHOÁ / MỞ KHOÁ TÀI KHOẢN ============
    r = c.patch(f"/api/admin/users/{ids['buyer']}/lock", headers=H["buyer"])
    check("E2E-59", "USER thường tự khoá tài khoản qua API Admin", "403", r.status_code == 403, str(r.status_code))
    admin_id = c.get("/auth/me", headers=H["admin"]).json()["id"]
    r = c.patch(f"/api/admin/users/{admin_id}/lock", headers=H["admin"])
    check("E2E-60", "Admin tự khoá chính mình", "400", r.status_code == 400, str(r.status_code))
    r = c.patch(f"/api/admin/users/{ids['buyer']}/lock", headers=H["admin"])
    check("E2E-61", "Admin khoá buyer", "200 LOCKED", r.status_code == 200 and r.json().get("status") == "LOCKED", str(r.status_code))
    r = c.post("/auth/login", json={"identifier": buyer_u, "password": PWD})
    check("E2E-62", "Buyer bị khoá đăng nhập lại", "403", r.status_code == 403, str(r.status_code))
    r = c.get("/api/cart", headers=H["buyer"])
    check("E2E-63", "Buyer bị khoá dùng token cũ", "403", r.status_code == 403, str(r.status_code))
    r = c.patch(f"/api/admin/users/{ids['seller']}/lock", headers=H["admin"])
    check("E2E-64", "Admin khoá seller", "200 LOCKED", r.status_code == 200, str(r.status_code))
    with open(ASSETS / "demo_clip.mp4", "rb") as fv, open(ASSETS / "demo_thumb.jpg", "rb") as ft:
        r = c.post(
            "/api/videos",
            data={"title": "Video của seller bị khoá"},
            files={"video": ("demo_clip.mp4", fv, "video/mp4"), "thumbnail": ("demo_thumb.jpg", ft, "image/jpeg")},
            auth=(seller_u, PWD),
        )
    check("E2E-65", "Seller bị khoá đăng video", "401/403", r.status_code in (401, 403), str(r.status_code))
    r = c.post("/api/products", json={"name": "SP khi bị khoá", "price": 1000, "stock": 1, "category_id": cat_id}, headers=H["seller"])
    check("E2E-66", "Seller bị khoá thêm sản phẩm (token cũ)", "403", r.status_code == 403, str(r.status_code))
    r = c.get("/api/admin/users?search=" + buyer_u, headers=H["admin"])
    check("E2E-67", "Admin tìm tài khoản theo tên", "200, 1 kết quả", r.status_code == 200 and len(r.json()) == 1 and r.json()[0]["status"] == "LOCKED", str(r.status_code))
    for key in ("buyer", "seller"):
        r = c.patch(f"/api/admin/users/{ids[key]}/unlock", headers=H["admin"])
        check(f"E2E-68{key[0]}", f"Admin mở khoá {key}", "200 ACTIVE", r.status_code == 200 and r.json().get("status") == "ACTIVE", str(r.status_code))
    r = c.post("/auth/login", json={"identifier": buyer_u, "password": PWD})
    check("E2E-69", "Buyer đăng nhập lại sau khi mở khoá", "200", r.status_code == 200, str(r.status_code))
    r = c.get("/api/cart", headers=H["buyer"])
    check("E2E-70", "Token cũ dùng lại được sau mở khoá", "200", r.status_code == 200, str(r.status_code))

    # ============ 7. DASHBOARD ============
    # Seller xác nhận đơn 1 -> vẫn tính doanh thu 350.000; đơn 2 đã huỷ -> không tính.
    r0 = c.post(f"/api/shops/me/orders/{order1_id}/ship", headers=H["seller"])
    check("E2E-71a", "Seller giao đơn 1 (confirmed → shipping)", "200", r0.status_code == 200, str(r0.status_code))
    r = c.post(f"/api/shops/me/orders/{order1_id}/complete", headers=H["seller"])
    check("E2E-71", "Seller hoàn tất đơn 1 (shipping → completed)", "200", r.status_code == 200, f"{r.status_code} {r.text[:80] if r.status_code != 200 else ''}")
    r = c.get("/api/admin/dashboard?days=7", headers=H["admin"])
    dash = r.json() if r.status_code == 200 else {}
    s = dash.get("summary", {})
    check("E2E-72", "Dashboard trả về 200 với summary + daily", "200", r.status_code == 200 and "daily" in dash, str(r.status_code))
    check("E2E-73", "Doanh thu = 350.000 (đơn nhiều item không cộng trùng, bỏ đơn huỷ)", "350000", Decimal(str(s.get("total_revenue", -1))) == Decimal("350000"), f"{s.get('total_revenue')}")
    check("E2E-74", "Tổng đơn hàng (mọi trạng thái, gồm cả đơn huỷ)", "2", s.get("total_orders") == 2, f"{s.get('total_orders')}")
    check("E2E-75", "Tổng người dùng / người bán", "users=4, sellers=1", s.get("total_users") == 4 and s.get("total_sellers") == 1, f"users={s.get('total_users')} sellers={s.get('total_sellers')}")
    check("E2E-76", "Tổng video / sản phẩm", "videos=1, products=3", s.get("total_videos") == 1 and s.get("total_products") == 3, f"videos={s.get('total_videos')} products={s.get('total_products')}")
    daily = dash.get("daily", [])
    check("E2E-77", "Biểu đồ daily có đủ 7 điểm, điểm cuối = 350.000", "7 điểm, 350000", len(daily) == 7 and Decimal(str(daily[-1]["revenue"])) == Decimal("350000"), f"{len(daily)} điểm")
    r = c.get("/api/admin/dashboard", headers=H["buyer"])
    check("E2E-78", "USER thường xem dashboard", "403", r.status_code == 403, str(r.status_code))
    r = c.get("/api/admin/dashboard?from_date=2026-12-31&to_date=2026-01-01", headers=H["admin"])
    check("E2E-79", "Dashboard khoảng ngày ngược (from > to)", "400/422", r.status_code in (400, 422), str(r.status_code))

    # ============ 8. FRONTEND được phục vụ ============
    for i, page in enumerate(("index.html", "pages/login.html", "pages/register.html", "pages/admin.html", "pages/seller-center.html", "pages/feed.html", "pages/cart.html", "pages/product.html")):
        r = c.get("/" + page)
        check(f"E2E-8{i}", f"Frontend phục vụ /{page}", "200 text/html", r.status_code == 200 and "html" in r.headers.get("content-type", ""), str(r.status_code))

    total = len(results)
    passed = sum(1 for x in results if x["result"] == "PASS")
    print(f"\nTỔNG KẾT: {passed}/{total} PASS, {total - passed} FAIL")
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps({"run": run, "base": args.base, "total": total, "pass": passed, "fail": total - passed, "cases": results}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())


