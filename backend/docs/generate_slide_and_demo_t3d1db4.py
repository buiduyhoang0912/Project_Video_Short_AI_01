"""Script sinh file PowerPoint (.pptx) và cập nhật tài liệu Slide, Kịch bản Demo cho Task T3D1DB4:
T3D1DB4: tích hợp hệ thống, sửa lỗi và chuẩn bị demo - Bùi Duy Hoàng (B25DTCN093).
"""

from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
DOCS_DIR = ROOT_DIR / "docs" / "t3d1db4-slide-demo"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

SLIDES_DATA = [
    {
        "title": "BÁO CÁO BẢO VỆ DỰ ÁN: CLIPSHOP AI (TOKFLOW)",
        "subtitle": "Phân hệ Quản trị Admin, Kiểm duyệt nội dung & Kiểm thử Tích hợp Toàn hệ thống\nSinh viên thực hiện: BÙI DUY HOÀNG (B25DTCN093) · Task hoàn thiện: T3D1DB4",
        "bullets": [
            "Đề tài: Nền tảng Video ngắn kết hợp Thương mại điện tử & Trợ lý AI (ClipShop AI / TokFlow)",
            "Vai trò phụ trách chính:",
            "  • T3D2003: Phân quyền & Quản trị tài khoản, Xét duyệt người bán (USER -> SELLER), Khoá/Mở khoá tài khoản",
            "  • T3D201D: Kiểm duyệt video & sản phẩm vi phạm (Ẩn/Hiện kèm lý do), Dashboard thống kê thời gian thực Chart.js",
            "  • T3D1D6C: Thiết kế tài liệu kiểm thử toàn diện (52 Test Cases, 55 Test Logs, Bug Log quản lý 5 lỗi phát hiện)",
            "  • T3D1DB4: Tích hợp luồng xuyên suốt E2E từ Đăng ký -> Mua hàng -> Kiểm duyệt -> Thống kê; khắc phục triệt để lỗi tích hợp",
            "Công nghệ áp dụng: Python FastAPI, SQLAlchemy 2.0, MySQL 8, PyJWT, Chart.js, HTML5/CSS3/Vanilla JS (Axios), Pytest",
        ],
    },
    {
        "title": "1. DUYỆT NGƯỜI BÁN & QUẢN LÝ TÀI KHOẢN (TASK T3D2003)",
        "subtitle": "Kiến trúc phân quyền RBAC đa tầng, kiểm soát phiên và đảm bảo tính nhất quán dữ liệu",
        "bullets": [
            "Quy trình xét duyệt đơn bán hàng chuẩn nghiệp vụ (/api/admin/seller-applications):",
            "  • Giao dịch nguyên tử (Atomic Transaction): Cập nhật trạng thái đơn APPROVED và nâng cấp role USER -> SELLER trong cùng transaction, tự rollback nếu lỗi",
            "  • Validate từ chối nghiêm ngặt: Bắt buộc lý do từ chối (REJECTED), chặn chuỗi khoảng trắng hoặc bỏ trống",
            "  • Chống xử lý trùng lặp (Idempotent): Đơn đã duyệt hoặc từ chối bị khóa, trả về 409 Conflict nếu cố thao tác lại",
            "Quản lý tài khoản người dùng thời gian thực (/api/admin/users):",
            "  • Chặn tức thời khi bị khoá (status = LOCKED): Người dùng bị từ chối đăng nhập ngay lập tức",
            "  • Vô hiệu hóa token cũ lưu hành: get_current_user đọc trạng thái user từ DB trong mỗi request, chặn 403 Forbidden mọi token cũ",
            "  • An toàn bảo mật: Chặn Admin tự khoá tài khoản của chính mình (400 Bad Request), escape ký tự wildcard (% và _) trong tìm kiếm",
        ],
    },
    {
        "title": "2. KIỂM DUYỆT VIDEO VÀ SẢN PHẨM VI PHẠM (TASK T3D201D)",
        "subtitle": "Cơ chế kiểm duyệt hai chiều, bảo vệ người tiêu dùng và ngăn chặn lạm quyền",
        "bullets": [
            "Quy trình ẩn nội dung vi phạm (/api/admin/videos & /api/admin/products):",
            "  • Bắt buộc lý do vi phạm: Khi Admin chọn Ẩn (HIDDEN), bắt buộc nhập lý do chi tiết; lưu kèm ID Admin và thời điểm moderated_at",
            "  • Tác động tức thì phía người mua: Video vi phạm biến mất khỏi Feed công khai; Sản phẩm vi phạm bị trả về 404 và giỏ hàng chặn thêm (400)",
            "Chốt chặn chống chủ nội dung tự ý hiển thị lại (Bảo mật chéo):",
            "  • Sản phẩm: Seller cố tình gọi PUT/PATCH /api/products/{id} để đổi trạng thái ACTIVE sẽ bị chặn 403 Forbidden",
            "  • Video: Chủ video gọi /api/videos/{id}/status để đổi VISIBLE sẽ bị chặn 403 Forbidden nếu cờ moderated_at còn hiệu lực",
            "  • Tương tác trên video ẩn: Chặn toàn bộ hành vi Like, Comment và Xem bình luận trên video vi phạm (trả về 400 Bad Request)",
            "Gỡ ẩn an toàn: Chỉ duy nhất Quản trị viên (ADMIN) mới có quyền mở lại nội dung sau khi chủ shop/kênh giải trình thành công",
        ],
    },
    {
        "title": "3. DASHBOARD THỐNG KÊ & TÍNH TOÁN DOANH THU CHART.JS",
        "subtitle": "6 Thẻ chỉ số nền tảng thời gian thực và 3 biểu đồ trực quan hóa dữ liệu chính xác",
        "bullets": [
            "6 Thẻ chỉ số tổng quan (Real-time Metric Cards):",
            "  • Người dùng (Users), Người bán (Sellers), Tổng Video, Tổng Sản phẩm, Tổng Đơn hàng, Doanh thu toàn sàn",
            "Quy tắc tính toán doanh thu chuẩn xác (Financial Integrity):",
            "  • Trạng thái hợp lệ: Chỉ tính các đơn đã xác nhận (confirmed), đang giao (shipping) hoặc đã hoàn tất (completed)",
            "  • Loại trừ đơn rác: Hoàn toàn loại bỏ đơn chờ thanh toán (pending) và đơn đã hủy (cancelled)",
            "  • Chống cộng trùng (Zero Double-Counting): Tính SUM(total_amount) trực tiếp trên bảng orders, không join nhân bản theo order_items",
            "3 Biểu đồ Chart.js trực quan theo khoảng thời gian linh hoạt:",
            "  • Biểu đồ đường Doanh thu theo ngày (₫), Biểu đồ cột Số đơn hàng, Biểu đồ kép Người dùng & Video mới",
            "  • Bộ lọc linh hoạt: 7 ngày, 14 ngày, 30 ngày, 90 ngày hoặc tùy chọn Từ ngày - Đến ngày (validate logic ngày bắt đầu <= ngày kết thúc)",
        ],
    },
    {
        "title": "4. BUG PHÁT HIỆN TRONG QUÁ TRÌNH TÍCH HỢP & CÁCH SỬA",
        "subtitle": "5 Lỗi nghiệp vụ & bảo mật quan trọng được phát hiện sớm, sửa triệt để và kiểm thử hồi quy",
        "bullets": [
            "BUG-01 (High): Chủ video tự bật lại video bị Admin ẩn qua API cũ /api/videos/{id}/status",
            "  -> Khắc phục: Kiểm tra video.moderated_at IS NOT NULL; chặn 403 Forbidden với mọi non-admin. (PASS)",
            "BUG-02 (Medium): Request body rỗng {} gửi tới /visibility tự động kích hoạt nhánh gỡ ẩn",
            "  -> Khắc phục: Dùng Pydantic model_validator(mode='after') và extra='forbid', bắt lỗi 422 nếu thiếu trường. (PASS)",
            "BUG-03 (Medium): Tên video/sản phẩm chứa ký tự nháy kép (\") làm vỡ thuộc tính data-name trên HTML Admin",
            "  -> Khắc phục: Xây dựng hàm chuyên biệt escapeAttr() mã hóa ký tự nháy kép thành &quot; và nháy đơn thành &#39;. (PASS)",
            "BUG-04 (Medium): USER chưa có shop gọi /api/shops/me/orders trả về 404 thay vì 403 Forbidden",
            "  -> Khắc phục: Cập nhật _get_owned_shop_or_404() kiểm tra _is_approved_seller(); chặn 403 đúng chuẩn RBAC. (PASS)",
            "BUG-05 (High): Video bị Admin ẩn vẫn nhận thêm lượt Thích (Like), Bình luận và xem bình luận công khai",
            "  -> Khắc phục: Bổ sung check_video_available() trong app/routers/social.py, chặn 400 Bad Request đồng bộ với /share. (PASS)",
        ],
    },
    {
        "title": "5. KẾT QUẢ KIỂM THỬ THỰC TẾ TOÀN HỆ THỐNG",
        "subtitle": "Bao phủ 100% chức năng phân hệ Admin, phân quyền, kiểm duyệt và luồng xuyên suốt E2E",
        "bullets": [
            "Tài liệu kiểm thử Excel T3D1D6C (T3D1D6C_TestCase_TestLog_BuiDuyHoang_B25DTCN093.xlsx):",
            "  • 52 Test Cases: Bao phủ Duyệt đơn bán hàng, Quản lý tài khoản, Kiểm duyệt video, Kiểm duyệt sản phẩm, Dashboard",
            "  • 55 Test Logs thực tế: 100% Pass (52/52 tình huống đạt yêu cầu)",
            "  • 5 Bugs theo dõi trong Bug Log: 100% đã được khắc phục và kiểm tra lại thành công (Closed)",
            "Kiểm thử tự động hồi quy với Pytest (Backend):",
            "  • 176 Tests tự động trong test suite toàn dự án PASSED 100% (0 lỗi, 0 thất bại)",
            "  • 65 tests chuyên sâu cho Admin, Moderation, Social, Seller Shop & E2E luồng xuyên suốt",
            "Kiểm thử tích hợp trực tiếp trên server thật (Live HTTP E2E Flow):",
            "  • 105/105 kịch bản tích hợp chạy qua API & MySQL thật đạt kết quả PASSED (100%)",
        ],
    },
    {
        "title": "6. KỊCH BẢN LIVE DEMO LUỒNG XUYÊN SUỐT & KẾT LUẬN",
        "subtitle": "Kịch bản trình diễn 4 bước thực tế (đã nạp sẵn dữ liệu mẫu qua python app/seed_demo_flow.py)",
        "bullets": [
            "Trình tự demo thực tế (Thời lượng ~3-5 phút):",
            "  • Bước 1: Đăng nhập admin01 -> Mở 'Đơn đăng ký bán hàng' -> Thử Từ chối không lý do (báo lỗi) -> Bấm Duyệt đơn của seller_candidate",
            "  • Bước 2: Mở tab 'Tài khoản' -> Tìm kiếm user_normal -> Bấm 'Khoá' -> Thử đăng nhập tab ẩn danh (báo lỗi khoá) -> Mở khoá thành công",
            "  • Bước 3: Mở tab 'Video' & 'Sản phẩm' -> Ẩn video/sản phẩm kèm lý do vi phạm -> Kiểm tra bên mua bị ẩn -> Thử dùng seller bật lại (bị chặn 403)",
            "  • Bước 4: Mở tab 'Dashboard' -> Kiểm tra 6 thẻ số liệu -> Chuyển bộ lọc 7 ngày / 30 ngày -> Biểu đồ Chart.js cập nhật trực quan tức thì",
            "Kết luận dự án:",
            "  • Toàn bộ các module phụ trách hoạt động trơn tru, đồng bộ, xử lý ngoại lệ chặt chẽ và đáp ứng vượt mức yêu cầu đề ra.",
        ],
    },
]


def create_presentation(output_path: Path):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    for idx, slide_info in enumerate(SLIDES_DATA):
        slide = prs.slides.add_slide(blank_layout)

        # Header banner
        header_shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.45)
        )
        header_shape.fill.solid()
        header_shape.fill.fore_color.rgb = (
            RGBColor(15, 23, 42) if idx == 0 else RGBColor(30, 58, 138)
        )
        header_shape.line.fill.background()

        tf_h = header_shape.text_frame
        tf_h.word_wrap = True
        p_title = tf_h.paragraphs[0]
        p_title.text = slide_info["title"]
        p_title.font.size = Pt(25 if idx == 0 else 21)
        p_title.font.bold = True
        p_title.font.color.rgb = RGBColor(255, 255, 255)

        p_sub = tf_h.add_paragraph()
        p_sub.text = slide_info["subtitle"]
        p_sub.font.size = Pt(12)
        p_sub.font.color.rgb = RGBColor(191, 219, 254)

        # Content box
        body_shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(0.6),
            Inches(1.65),
            Inches(12.133),
            Inches(5.25),
        )
        body_shape.fill.solid()
        body_shape.fill.fore_color.rgb = RGBColor(248, 250, 252)
        body_shape.line.color.rgb = RGBColor(203, 213, 225)

        tf_b = body_shape.text_frame
        tf_b.word_wrap = True
        tf_b.margin_left = Inches(0.35)
        tf_b.margin_right = Inches(0.35)
        tf_b.margin_top = Inches(0.25)

        for b_idx, line in enumerate(slide_info["bullets"]):
            p = tf_b.paragraphs[0] if b_idx == 0 else tf_b.add_paragraph()
            p.text = f"✔  {line}" if not line.startswith("  •") else f"    {line}"
            p.font.size = Pt(15.5)
            p.font.color.rgb = RGBColor(30, 41, 59)
            p.space_after = Pt(10)

        # Footer
        footer_box = slide.shapes.add_textbox(
            Inches(0.6), Inches(7.0), Inches(12.133), Inches(0.4)
        )
        tf_f = footer_box.text_frame
        pf = tf_f.paragraphs[0]
        pf.text = f"ClipShop AI · Bùi Duy Hoàng (B25DTCN093) · Task T3D1DB4 · Slide {idx + 1}/{len(SLIDES_DATA)}"
        pf.font.size = Pt(11)
        pf.font.color.rgb = RGBColor(100, 116, 139)
        pf.alignment = PP_ALIGN.RIGHT

    prs.save(output_path)


if __name__ == "__main__":
    pptx_in_docs = DOCS_DIR / "T3D1DB4_Slide_BaoVe_BuiDuyHoang_B25DTCN093.pptx"
    pptx_in_backend = ROOT_DIR / "backend" / "docs" / "T3D1DB4_Slide_BaoVe_BuiDuyHoang_B25DTCN093.pptx"
    create_presentation(pptx_in_docs)
    create_presentation(pptx_in_backend)
    print(f"Generated PowerPoint files:\n - {pptx_in_docs}\n - {pptx_in_backend}")
