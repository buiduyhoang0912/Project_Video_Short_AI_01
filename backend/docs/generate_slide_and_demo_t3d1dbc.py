"""Script sinh file PowerPoint (.pptx) và kịch bản Demo bảo vệ (.md) cho Task T3D1DBC:
[Hoàn thiện] Ghép nối toàn hệ thống, sửa bug, slide và demo - Hoàng Phúc Hiếu (SV1500).
Module: Giỏ hàng, Đặt hàng trong Transaction, Quản lý đơn hàng & Huỷ đơn hoàn tồn, Thanh toán VietQR, UI Cửa hàng & Chi tiết sản phẩm.
"""

import shutil
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

DOCS_DIR = Path(__file__).resolve().parent
ROOT_DIR = DOCS_DIR.parent.parent

SLIDES_DATA = [
    {
        "title": "BÁO CÁO BẢO VỆ DỰ ÁN: CLIPSHOP AI",
        "subtitle": "Module Giỏ hàng, Đặt hàng Transaction, Quản lý & Huỷ đơn hoàn tồn, Thanh toán VietQR\nSinh viên thực hiện: Hoàng Phúc Hiếu (SV1500) · Mã Task: T3D1DBC",
        "bullets": [
            "Đề tài: Nền tảng Video ngắn kết hợp Thương mại điện tử & Trợ lý Mua sắm AI (ClipShop AI)",
            "Vai trò cá nhân: Phụ trách toàn bộ phân hệ Giỏ hàng (Cart), Đặt hàng trong Transaction (Order), Quản lý đơn hàng của tôi & Huỷ đơn hoàn tồn, Thanh toán VietQR & Giao diện Shop công khai",
            "Công nghệ sử dụng: FastAPI, SQLAlchemy 2.0 (Transaction & Concurrency Lock), MySQL, Pydantic v2, VietQR API, HTML5/CSS3/Vanilla JS (Axios)",
            "Trạng thái tích hợp: Đã ghép nối xuyên suốt từ Xem Shop -> Thêm giỏ -> Áp mã -> Đặt hàng Transaction -> Thanh toán VietQR -> Quản lý & Huỷ đơn",
        ],
    },
    {
        "title": "1. TỔNG QUAN CÁC TASK ĐẢM NHẬN (SPRINT 1 - 3)",
        "subtitle": "Hoàng Phúc Hiếu (SV1500) — 6 Task chức năng cốt lõi & kiểm thử hoàn thiện",
        "bullets": [
            "1. T3D2839 & T3D2B47: API & Giao diện Trang Shop dạng lưới có tìm kiếm, lọc danh mục/giá, sắp xếp giá/bán chạy, phân trang & Trang chi tiết sản phẩm kèm gallery ảnh, tồn kho, thêm giỏ/mua ngay",
            "2. T3D2853 & T3D2B79: API Giỏ hàng nhóm theo shop, tính tạm tính tại server, chặn sản phẩm ẩn/hết hàng & Giao diện giỏ hàng tăng/giảm/xoá, sổ địa chỉ đã lưu, chọn COD/mô phỏng",
            "3. T3D2B17: API Đặt hàng trong Transaction: Tách đơn theo shop, trừ kho, lưu giá snapshot, xoá giỏ hàng trong 1 transaction, tự động rollback khi lỗi & khoá SELECT FOR UPDATE chống tồn âm",
            "4. T3D2B93: API & Giao diện Đơn hàng của tôi: Lọc theo trạng thái, xem chi tiết kèm Dòng thời gian trạng thái (Timeline trực quan) & Huỷ đơn khi Chờ xác nhận hoàn tồn đúng 1 lần",
            "5. T3D2C15 (Bonus): Thanh toán chuyển khoản tự động sinh mã VietQR theo tài khoản Shop và mã đơn DH{id}; Người bán xác nhận đã nhận tiền chuyển khoản",
            "6. T3D1D74 & T3D1DBC: Bộ 25 Test Cases (100% Pass), kịch bản demo bảo vệ, slide trình chiếu & ghép nối toàn bộ luồng hệ thống",
        ],
    },
    {
        "title": "2. THIẾT KẾ CƠ SỞ DỮ LIỆU PHÂN HỆ CART & ORDER",
        "subtitle": "Các bảng dữ liệu chuẩn hoá với ràng buộc toàn vẹn & Transaction ACID",
        "bullets": [
            "Bảng 'carts' & 'cart_items': Quản lý giỏ hàng của từng User, lưu product_id, quantity; cascade xoá khi user bị xoá",
            "Bảng 'orders': Lưu thông tin đơn hàng tách riêng theo từng shop (buyer_id, shop_id, total_amount, payment_method, status, recipient_info, bank info)",
            "Bảng 'order_items': Lưu chi tiết từng mặt hàng trong đơn kèm unit_price snapshot tại thời điểm đặt (bảo vệ giá chốt, không bị ảnh hưởng nếu seller đổi giá sau đó)",
            "Trạng thái đơn hàng chuẩn: PENDING (Chờ xác nhận) -> CONFIRMED (Đã xác nhận) -> SHIPPED (Đang vận chuyển) -> DELIVERED (Hoàn thành) / CANCELLED (Đã huỷ)",
            "Khoá Concurrency: Sử dụng with_for_update() trên Product khi thanh toán và khi huỷ đơn để đảm bảo dữ liệu kho luôn chính xác tuyệt đối",
        ],
    },
    {
        "title": "3. KỸ THUẬT ĐẶT HÀNG TRANSACTION & CHỐNG TỒN ÂM",
        "subtitle": "Giải quyết bài toán Concurrency và tính toàn vẹn dữ liệu (Task T3D2B17)",
        "bullets": [
            "Tách đơn theo từng Shop: Khi giỏ có sản phẩm từ N shop, hệ thống tự động tách thành N đơn hàng độc lập, mỗi đơn có mã đơn và người bán quản lý riêng",
            "Atomic Transaction: Toàn bộ quá trình kiểm tra kho -> trừ kho -> tạo đơn -> xoá giỏ diễn ra trong 1 transaction duy nhất. Bất kỳ lỗi nào phát sinh đều tự động Rollback 100%",
            "Chống tồn âm (Race Condition): Khi sản phẩm chỉ còn 1 cái và nhiều người mua đồng thời, lệnh SELECT ... FOR UPDATE khoá dòng sản phẩm trong DB: chỉ người đầu tiên mua thành công, người thứ 2 bị chặn",
            "Thanh toán mô phỏng (SIMULATED): Tự động đánh dấu đơn đã thanh toán (payment_status = 'PAID') và chuyển trạng thái 'CONFIRMED' ngay khi đặt",
        ],
    },
    {
        "title": "4. QUẢN LÝ ĐƠN HÀNG, STATUS TIMELINE & HUỶ ĐƠN HOÀN TỒN",
        "subtitle": "Trải nghiệm người dùng minh bạch và quy tắc nghiệp vụ chặt chẽ (Task T3D2B93)",
        "bullets": [
            "Bộ lọc đa trạng thái: Dễ dàng xem danh sách đơn theo Tất cả, Chờ xác nhận, Đã xác nhận, Đang vận chuyển, Hoàn thành, Đã huỷ",
            "Dòng thời gian trạng thái (Timeline): Giao diện hiển thị trực quan các mốc thời gian: Đặt hàng thành công -> Chờ xác nhận -> Đã xác nhận -> Đang vận chuyển -> Giao thành công / Huỷ",
            "Quy tắc huỷ đơn: Người mua chỉ được phép huỷ khi đơn ở trạng thái PENDING. Khi đã CONFIRMED hoặc SHIPPED, hệ thống từ chối huỷ (HTTP 400)",
            "Hoàn tồn đúng một lần: Khi huỷ đơn, hệ thống dùng Transaction khoá Product và cộng lại stock += quantity đúng 1 lần; nếu gọi huỷ lại lần 2 sẽ bị chặn không hoàn tồn lặp lại",
        ],
    },
    {
        "title": "5. THANH TOÁN CHUYỂN KHOẢN MÃ QR VIETQR (BONUS)",
        "subtitle": "Tích hợp chuẩn VietQR và xác nhận thanh toán phía người bán (Task T3D2C15)",
        "bullets": [
            "Tự động sinh mã VietQR: Dựa trên ngân hàng, số tài khoản của Shop, số tiền chính xác và cú pháp nội dung 'DH{order_id}'",
            "Giao diện Popup VietQR: Hiển thị ảnh mã QR VietQR chất lượng cao, STK, tên chủ tài khoản, số tiền và nút sao chép tiện lợi",
            "Quy trình xác nhận phía Seller: Người bán xem đơn hàng trong Seller Center, thấy đơn chuyển khoản kèm mã chuyển tiền; bấm 'Xác nhận đã nhận tiền' để kích hoạt đơn sang trạng thái CONFIRMED",
            "Bảo mật quyền hạn: Chỉ chủ sở hữu Shop mới có quyền gọi API xác nhận đã nhận tiền của đơn hàng thuộc shop mình",
        ],
    },
    {
        "title": "6. KẾT QUẢ KIỂM THỬ (TEST REPORT) & TỔNG KẾT",
        "subtitle": "25 Test Cases hoàn thành với tỉ lệ Đạt 100% · Không có bug tồn đọng",
        "bullets": [
            "Kiểm thử đầy đủ các khía cạnh: Đúng dữ liệu (Happy case), Sai dữ liệu (Boundary & Validation), Chưa đăng nhập (Auth 401), Sai quyền (Permission 403/404), Concurrency Lock",
            "Module Giỏ hàng: 8/8 Test Cases PASS",
            "Module Đặt hàng Transaction & Chống tồn âm: 5/5 Test Cases PASS",
            "Module Quản lý đơn hàng & Huỷ đơn hoàn tồn: 6/6 Test Cases PASS",
            "Module Thanh toán VietQR & UI Shop/Sản phẩm: 6/6 Test Cases PASS",
            "Ghép nối hệ thống: Khớp nối hoàn hảo với phân hệ Video (Khai Hoan), Social (Quang Huy), Seller (Hoang Van) và Auth/Admin (Duy Hoang)",
        ],
    },
    {
        "title": "7. KỊCH BẢN DEMO BẢO VỆ ĐỀ TÀI",
        "subtitle": "Luồng Demo trực tiếp 5 phút thuyết phục Hội đồng chấm",
        "bullets": [
            "Bước 1: Đăng nhập tài khoản Người mua -> Vào trang Cửa hàng (shop-public.html) -> Lọc danh mục, tìm kiếm và xem chi tiết sản phẩm",
            "Bước 2: Chọn số lượng, bấm 'Thêm vào giỏ hàng' cho 2 sản phẩm từ 2 Shop khác nhau -> Chuyển vào Giỏ hàng (cart.html)",
            "Bước 3: Xem giỏ hàng nhóm theo 2 Shop; chọn địa chỉ từ 'Sổ địa chỉ đã lưu'; chọn thanh toán 'Chuyển khoản VietQR' -> Bấm Đặt hàng",
            "Bước 4: Hệ thống tự động tách thành 2 đơn hàng, trừ tồn kho trong 1 Transaction và hiển thị Popup mã VietQR kèm nội dung DH{id}",
            "Bước 5: Vào 'Đơn hàng của tôi' (orders.html) -> Xem Timeline dòng thời gian trạng thái -> Thử nghiệm tính năng 'Huỷ đơn hàng' và chứng minh tồn kho được hoàn lại ngay lập tức",
            "Bước 6: Đăng nhập tài khoản Seller -> Vào Quản lý đơn hàng -> Bấm 'Xác nhận đã nhận tiền (VietQR)' hoàn tất chu trình",
        ],
    },
]


def create_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    COLOR_BG = RGBColor(248, 250, 252)
    COLOR_PRIMARY = RGBColor(30, 58, 138)  # Deep Navy
    COLOR_ACCENT = RGBColor(37, 99, 235)   # Royal Blue
    COLOR_TEXT = RGBColor(30, 41, 59)
    COLOR_MUTED = RGBColor(100, 116, 139)
    COLOR_CARD = RGBColor(255, 255, 255)

    blank_layout = prs.slide_layouts[6]

    for idx, slide_info in enumerate(SLIDES_DATA):
        slide = prs.slides.add_slide(blank_layout)

        # Background shape
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = COLOR_BG
        bg.line.fill.background()

        # Top banner bar
        top_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.18))
        top_bar.fill.solid()
        top_bar.fill.fore_color.rgb = COLOR_ACCENT
        top_bar.line.fill.background()

        # Title Box
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(1.3))
        tf = title_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p_title = tf.paragraphs[0]
        p_title.text = slide_info["title"]
        p_title.font.name = "Segoe UI"
        p_title.font.size = Pt(24)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_PRIMARY

        p_sub = tf.add_paragraph()
        p_sub.text = slide_info["subtitle"]
        p_sub.font.name = "Segoe UI"
        p_sub.font.size = Pt(13)
        p_sub.font.color.rgb = COLOR_MUTED
        p_sub.space_before = Pt(4)

        # Content Card
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(0.8),
            Inches(1.85),
            Inches(11.733),
            Inches(5.0),
        )
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_CARD
        card.line.color.rgb = RGBColor(226, 232, 240)
        card.line.width = Pt(1.5)

        # Content Text Box inside Card
        content_box = slide.shapes.add_textbox(
            Inches(1.1),
            Inches(2.05),
            Inches(11.133),
            Inches(4.6),
        )
        ctf = content_box.text_frame
        ctf.word_wrap = True
        ctf.margin_left = ctf.margin_top = ctf.margin_right = ctf.margin_bottom = 0

        for b_idx, bullet in enumerate(slide_info["bullets"]):
            p = ctf.add_paragraph() if b_idx > 0 else ctf.paragraphs[0]
            p.text = f"•  {bullet}"
            p.font.name = "Segoe UI"
            p.font.size = Pt(14)
            p.font.color.rgb = COLOR_TEXT
            p.space_after = Pt(14)
            p.line_spacing = 1.25

        # Footer page number
        footer_box = slide.shapes.add_textbox(Inches(11.5), Inches(7.0), Inches(1.5), Inches(0.4))
        ftf = footer_box.text_frame
        fp = ftf.paragraphs[0]
        fp.text = f"Trang {idx + 1} / {len(SLIDES_DATA)}"
        fp.font.name = "Segoe UI"
        fp.font.size = Pt(10)
        fp.font.color.rgb = COLOR_MUTED
        fp.alignment = PP_ALIGN.RIGHT

    pptx_path = DOCS_DIR / "T3D1DBC_Slide_BaoVe_HoangPhucHieu_SV1500.pptx"
    prs.save(pptx_path)
    print(f"✅ Đã tạo PowerPoint: {pptx_path}")

    # Copy ra thư mục gốc
    root_pptx = ROOT_DIR / "T3D1DBC_Slide_BaoVe_HoangPhucHieu_SV1500.pptx"
    shutil.copy2(pptx_path, root_pptx)
    print(f"✅ Đã copy slide ra root: {root_pptx}")


def create_demo_script():
    md_path = DOCS_DIR / "T3D1DBC_KichBan_Demo_Va_Slide_HoangPhucHieu_SV1500.md"
    content = """# KỊCH BẢN DEMO BẢO VỆ ĐỀ TÀI & NỘI DUNG SLIDE TRÌNH CHIẾU
**Dự án:** ClipShop AI - Nền tảng Video ngắn kết hợp E-Commerce & Trợ lý AI  
**Sinh viên phụ trách:** Hoàng Phúc Hiếu (SV1500)  
**Mã Task:** `T3D1DBC` (Ghép nối toàn hệ thống, sửa bug, slide và demo)  
**Sprint:** Sprint 3 (18/11 - 24/11/2026)

---

## 🎯 PHÂN HỆ ĐẢM NHẬN & CHỨC NĂNG CỐT LÕI
1. **Trang Cửa hàng & Chi tiết sản phẩm (T3D2839, T3D2B47):** Lưới sản phẩm, tìm kiếm từ khoá, lọc danh mục, lọc khoảng giá, sắp xếp theo giá / bán chạy, xem gallery ảnh sản phẩm, số lượng tồn và nút thêm giỏ / mua ngay.
2. **Giỏ hàng & Sổ địa chỉ (T3D2853, T3D2B79):** Nhóm sản phẩm theo từng Shop, tăng/giảm/xoá trong giới hạn kho, báo lỗi hết hàng, chọn địa chỉ từ Sổ địa chỉ đã lưu hoặc lưu địa chỉ mới.
3. **Đặt hàng trong Transaction (T3D2B17):** Tách đơn theo từng shop, trừ tồn kho, lưu giá snapshot, dọn giỏ hàng trong 1 Transaction ACID duy nhất; tự động Rollback khi lỗi; khoá `SELECT FOR UPDATE` chống tồn âm khi nhiều người cùng mua.
4. **Quản lý đơn hàng của tôi & Huỷ đơn hoàn tồn (T3D2B93):** Lọc đơn theo trạng thái (PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED), xem chi tiết kèm Dòng thời gian trạng thái (Status Timeline trực quan); huỷ đơn hàng khi còn Chờ xác nhận và hoàn tồn kho đúng 1 lần.
5. **Thanh toán chuyển khoản QR VietQR (T3D2C15 - Bonus):** Tự động sinh mã VietQR chuẩn theo STK shop, số tiền và mã đơn DH{id}; người bán xác nhận đã nhận tiền chuyển khoản để kích hoạt đơn.

---

## 🎬 KỊCH BẢN DEMO CHI TIẾT (5 PHÚT DÀNH CHO HỘI ĐỒNG BẢO VỆ)

### 📌 Phần 1: Khám phá Cửa hàng & Thêm sản phẩm vào giỏ (1 phút)
1. Đăng nhập tài khoản người mua (ví dụ `buyer1@gmail.com`).
2. Điều hướng tới trang **Cửa hàng** (`frontend/pages/shop-public.html`).
3. Demo thanh lọc:
   - Nhập từ khoá tìm kiếm (ví dụ "Áo", "Tai nghe").
   - Lọc theo danh mục và nhập khoảng giá.
   - Sắp xếp theo "Bán chạy nhất" hoặc "Giá tăng dần".
4. Bấm vào 1 sản phẩm để vào trang **Chi tiết sản phẩm** (`product.html?id=...`):
   - Xem Gallery ảnh (bấm đổi giữa các ảnh thumbnail).
   - Xem tồn kho thực tế, tăng số lượng lên 2.
   - Bấm nút "🛒 Thêm vào giỏ hàng".
5. Quay lại shop và thêm tiếp 1 sản phẩm của Shop khác vào giỏ để chứng minh tính năng giỏ hàng đa shop.

### 📌 Phần 2: Trải nghiệm Giỏ hàng & Sổ địa chỉ giao hàng (1.5 phút)
1. Mở trang **Giỏ hàng** (`frontend/pages/cart.html`).
2. Chỉ rõ giao diện đã nhóm các mặt hàng theo 2 Shop riêng biệt kèm tạm tính từng shop.
3. Demo tăng / giảm số lượng; chú ý nút `+` bị khoá khi số lượng đạt giới hạn tồn kho thực tế.
4. Demo tính năng **Sổ địa chỉ đã lưu (Address Book)**:
   - Bấm vào chip địa chỉ đã lưu -> tự động điền nhanh Họ tên, SĐT, Địa chỉ.
   - Hoặc nhập địa chỉ mới và giữ tick "Lưu vào sổ địa chỉ để dùng lần sau".
5. Chọn phương thức thanh toán: **"Chuyển khoản ngân hàng quét mã VietQR"**.
6. Bấm nút **"✅ Đặt hàng ngay"**.

### 📌 Phần 3: Đặt hàng Transaction & Thanh toán VietQR (1.5 phút)
1. Hệ thống thực hiện Transaction:
   - Tách thành 2 đơn hàng cho 2 shop.
   - Trừ kho sản phẩm chính xác.
   - Dọn sạch các món đã đặt khỏi giỏ hàng.
2. **Popup Modal VietQR tự động xuất hiện:**
   - Hiển thị mã QR VietQR chuẩn tạo từ ngân hàng Shop.
   - Hiển thị đúng số tài khoản, tên chủ shop, số tiền và nội dung chuyển tiền `DH{order_id}`.
   - Demo nút "Tôi đã chuyển khoản xong".

### 📌 Phần 4: Quản lý Đơn hàng, Xem Timeline & Huỷ đơn hoàn tồn (1 phút)
1. Điều hướng tới trang **Đơn hàng của tôi** (`frontend/pages/orders.html`).
2. Demo các tab lọc trạng thái: *Tất cả*, *Chờ xác nhận*, *Đã xác nhận*, *Đã huỷ*.
3. Bấm nút **"⏱️ Chi tiết & Timeline"** của đơn hàng vừa tạo:
   - Hội đồng thấy dòng thời gian trực quan: *Đặt hàng thành công -> Chờ xác nhận -> Đã xác nhận -> Đang vận chuyển -> Hoàn thành*.
4. Bấm nút **"🚫 Huỷ đơn hàng"** trên đơn đang ở trạng thái Chờ xác nhận:
   - Xác nhận hộp thoại huỷ đơn.
   - Đơn chuyển sang trạng thái **"ĐÃ HUỶ"** màu đỏ.
   - Chứng minh tồn kho của sản phẩm trong kho được cộng hoàn lại ngay lập tức!
   - Thử bấm huỷ lại lần 2 -> hệ thống chặn và báo lỗi, không bao giờ hoàn tồn lặp lại.

---

## 🏆 KẾT LUẬN & ĐÓNG GÓP CHO ĐỀ TÀI
- Toàn bộ 5 task trong Sprint 3 và các task Sprint trước của sinh viên Hoàng Phúc Hiếu đều hoàn thành 100% với chất lượng cao.
- Không gây bất kỳ xung đột nào đến bài của các thành viên khác trong nhóm.
- Đã kiểm thử tự động và thủ công 25/25 test case đạt chuẩn.
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Đã tạo kịch bản demo: {md_path}")


if __name__ == "__main__":
    create_presentation()
    create_demo_script()
