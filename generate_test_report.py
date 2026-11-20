import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = openpyxl.Workbook()
# remove default sheet
wb.remove(wb.active)

# Color palettes
NAVY_HEADER = "1F4E79"
ICE_HEADER = "2F5597"
ACCENT_GREEN = "2E75B6"
BORDER_GRAY = "D9D9D9"

header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
title_font = Font(name="Calibri", size=14, bold=True, color="1F4E79")
subtitle_font = Font(name="Calibri", size=10, italic=True, color="595959")
regular_font = Font(name="Calibri", size=10)
bold_font = Font(name="Calibri", size=10, bold=True)
pass_font = Font(name="Calibri", size=10, bold=True, color="006100")
fail_font = Font(name="Calibri", size=10, bold=True, color="9C0006")

pass_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
fail_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
zebra_fill = PatternFill(start_color="F9FAFC", end_color="F9FAFC", fill_type="solid")

thin_side = Side(border_style="thin", color=BORDER_GRAY)
cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

# ==============================================================================
# 1. SHEET: Test Cases
# ==============================================================================
ws_tc = wb.create_sheet(title="Test Cases")
ws_tc.views.sheetView[0].showGridLines = True

ws_tc["A1"] = "BẢNG TÌNH HUỐNG KIỂM THỬ HỆ THỐNG QUẢN TRỊ ADMIN (TASK T3D2003 & T3D201D)"
ws_tc["A1"].font = title_font
ws_tc["A2"] = "Dự án: ClipShop AI / TokFlow - Người thực hiện: Bùi Duy Hoàng (B25DTCN093) - Mã task: T3D1D6C"
ws_tc["A2"].font = subtitle_font

tc_headers = [
    "Mã TC",
    "Chức năng",
    "Tình huống kiểm thử",
    "Điều kiện trước",
    "Các bước thực hiện",
    "Dữ liệu nhập",
    "Kết quả mong đợi"
]

header_fill_1 = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")
for col_idx, h in enumerate(tc_headers, 1):
    cell = ws_tc.cell(row=4, column=col_idx, value=h)
    cell.font = header_font
    cell.fill = header_fill_1
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = cell_border

tc_data = [
    # T3D2003: Duyệt đơn người bán
    (
        "TC_SA_01",
        "Duyệt đơn người bán",
        "Admin xem danh sách đơn đăng ký bán hàng (mặc định chờ duyệt)",
        "Đăng nhập tài khoản ADMIN",
        "1. Mở trang Quản trị (pages/admin.html)\n2. Bấm tab 'Đơn đăng ký bán hàng'",
        "status = PENDING (mặc định)",
        "Hiển thị danh sách các đơn có trạng thái PENDING gồm tên shop, SĐT, mô tả, người gửi và 2 nút Duyệt, Từ chối."
    ),
    (
        "TC_SA_02",
        "Duyệt đơn người bán",
        "Admin lọc danh sách đơn theo trạng thái (APPROVED, REJECTED, Tất cả)",
        "Đăng nhập tài khoản ADMIN",
        "1. Tại tab Đơn đăng ký, chọn dropdown Trạng thái\n2. Lần lượt chọn 'Đã duyệt', 'Từ chối', 'Tất cả'",
        "status_filter = APPROVED / REJECTED / ''",
        "Bảng dữ liệu cập nhật chính xác các đơn theo đúng trạng thái đã chọn. Đơn đã duyệt/từ chối hiển thị 'Đã xử lý'."
    ),
    (
        "TC_SA_03",
        "Duyệt đơn người bán",
        "Duyệt đơn đang chờ duyệt (Happy path)",
        "Có tài khoản USER đã gửi đơn PENDING",
        "1. Tìm đơn PENDING cần duyệt\n2. Bấm nút 'Duyệt'\n3. Xác nhận popup xác nhận duyệt",
        "PATCH /api/admin/seller-applications/{id}/approve",
        "Đơn chuyển sang APPROVED, tài khoản đổi role thành SELLER. Cập nhật cùng trong 1 transaction, thông báo thành công."
    ),
    (
        "TC_SA_04",
        "Duyệt đơn người bán",
        "Duyệt lại đơn đã ở trạng thái APPROVED hoặc REJECTED",
        "Đơn đã được duyệt hoặc từ chối trước đó",
        "1. Gọi API duyệt đơn đối với đơn đã duyệt/từ chối",
        "PATCH /api/admin/seller-applications/{id}/approve",
        "Hệ thống từ chối xử lý, trả về mã lỗi 409 Conflict với thông báo 'Chỉ có thể duyệt đơn đang ở trạng thái chờ (PENDING)'."
    ),
    (
        "TC_SA_05",
        "Duyệt đơn người bán",
        "Duyệt đơn không tồn tại trong hệ thống",
        "Đăng nhập tài khoản ADMIN",
        "1. Gửi request duyệt đơn với application_id không có thật",
        "application_id = 99999",
        "Hệ thống trả về mã lỗi 404 Not Found ('Không tìm thấy đơn đăng ký bán hàng')."
    ),
    (
        "TC_SA_06",
        "Duyệt đơn người bán",
        "Từ chối đơn có nhập lý do hợp lệ",
        "Có đơn đăng ký ở trạng thái PENDING",
        "1. Bấm nút 'Từ chối' tại dòng đơn PENDING\n2. Nhập lý do hợp lệ vào modal\n3. Bấm 'Xác nhận từ chối'",
        "rejection_reason = 'Thông tin số điện thoại không chính xác'",
        "Đơn chuyển sang REJECTED, lưu lý do và ID admin vào DB. Danh sách cập nhật kèm lý do từ chối. Role user giữ nguyên USER."
    ),
    (
        "TC_SA_07",
        "Duyệt đơn người bán",
        "Từ chối đơn nhưng bỏ trống lý do hoặc chỉ nhập khoảng trắng",
        "Có đơn đăng ký ở trạng thái PENDING",
        "1. Bấm 'Từ chối'\n2. Không nhập gì hoặc gõ toàn dấu cách\n3. Bấm 'Xác nhận từ chối'",
        "rejection_reason = '' hoặc '    '",
        "Giao diện hiển thị lỗi 'Vui lòng nhập lý do từ chối'; Backend trả về lỗi 422 Unprocessable Content. Không lưu thay đổi."
    ),
    (
        "TC_SA_08",
        "Duyệt đơn người bán",
        "Từ chối đơn đã được xử lý trước đó",
        "Đơn đã APPROVED hoặc REJECTED",
        "1. Gửi request từ chối đơn với ID đơn đã duyệt",
        "PATCH /api/admin/seller-applications/{id}/reject",
        "Hệ thống trả về mã lỗi 409 Conflict ('Chỉ có thể từ chối đơn đang ở trạng thái chờ')."
    ),
    (
        "TC_SA_09",
        "Duyệt đơn người bán",
        "Người dùng thường (USER / SELLER) gọi API quản trị đơn",
        "Đăng nhập tài khoản role USER hoặc SELLER",
        "1. Gửi request đến /api/admin/seller-applications hoặc /approve hoặc /reject",
        "Authorization: Bearer <token_user>",
        "Backend chặn với mã lỗi 403 Forbidden ('Không đủ quyền truy cập'). Giao diện ẩn menu Admin."
    ),
    (
        "TC_SA_10",
        "Duyệt đơn người bán",
        "Khách vãng lai chưa đăng nhập gọi API duyệt đơn",
        "Chưa đăng nhập hệ thống",
        "1. Gửi request đến API admin không kèm header Authorization",
        "Headers không có token",
        "Hệ thống trả về mã lỗi 401 Unauthorized ('Chưa đăng nhập')."
    ),
    (
        "TC_SA_11",
        "Duyệt đơn người bán",
        "Kiểm tra đã gỡ bỏ API tự duyệt demo (quick-setup)",
        "Đăng nhập tài khoản USER thường",
        "1. Gọi POST /api/seller-applications/quick-setup",
        "Token user thường",
        "Hệ thống trả về 404/405 Not Found. Người dùng thường không thể tự thăng quyền SELLER nếu không có Admin duyệt."
    ),

    # T3D2003: Quản lý tài khoản
    (
        "TC_USR_01",
        "Quản lý tài khoản",
        "Xem danh sách tài khoản người dùng",
        "Đăng nhập tài khoản ADMIN",
        "1. Mở trang Admin\n2. Bấm tab 'Tài khoản'",
        "GET /api/admin/users",
        "Hiển thị danh sách tài khoản: username, họ tên, email, vai trò (USER/SELLER/ADMIN), trạng thái (ACTIVE/LOCKED). Không lộ hash mật khẩu."
    ),
    (
        "TC_USR_02",
        "Quản lý tài khoản",
        "Tìm kiếm tài khoản theo username hoặc email tồn tại",
        "Đang ở tab Tài khoản",
        "1. Nhập từ khóa tìm kiếm vào ô tìm kiếm\n2. Bấm 'Tìm kiếm'",
        "search = 'seller_van' hoặc 'test@gmail.com'",
        "Bảng lọc đúng các tài khoản có username, email hoặc tên hiển thị khớp từ khóa."
    ),
    (
        "TC_USR_03",
        "Quản lý tài khoản",
        "Tìm kiếm tài khoản với từ khóa không tồn tại",
        "Đang ở tab Tài khoản",
        "1. Nhập từ khóa không có trong hệ thống\n2. Bấm 'Tìm kiếm'",
        "search = 'nguoidungkhongtontai999'",
        "Bảng hiển thị thông báo 'Không tìm thấy tài khoản nào'."
    ),
    (
        "TC_USR_04",
        "Quản lý tài khoản",
        "Tìm kiếm với ký tự đặc biệt SQL wildcard (% và _)",
        "Đang ở tab Tài khoản",
        "1. Nhập ký tự % hoặc _ vào ô tìm kiếm\n2. Bấm 'Tìm kiếm'",
        "search = '%'",
        "Hệ thống escape an toàn ký tự đặc biệt, không trả về toàn bộ DB hoặc gây lỗi SQL Injection."
    ),
    (
        "TC_USR_05",
        "Quản lý tài khoản",
        "Khoá tài khoản người dùng đang hoạt động",
        "Tài khoản mục tiêu đang có status = ACTIVE",
        "1. Bấm nút 'Khoá' tại dòng tài khoản mục tiêu\n2. Xác nhận popup xác nhận khoá",
        "PATCH /api/admin/users/{id}/lock",
        "Tài khoản chuyển status thành LOCKED. Badge đổi màu đỏ 'Bị khoá', nút chuyển thành 'Mở khoá', thông báo thành công."
    ),
    (
        "TC_USR_06",
        "Quản lý tài khoản",
        "Kiểm tra tài khoản bị khoá bị chặn đăng nhập và chặn token cũ",
        "Tài khoản vừa bị Admin khoá (LOCKED)",
        "1. Đăng nhập bằng tài khoản bị khoá\n2. Dùng token cũ trước khi khoá để gọi API cần đăng nhập",
        "Username/Password của tài khoản bị khoá; Token cũ",
        "1. Đăng nhập báo lỗi 403 'Tài khoản đã bị khóa'.\n2. Gọi API bằng token cũ báo lỗi 403 'Tài khoản đã bị khóa' ngay lập tức."
    ),
    (
        "TC_USR_07",
        "Quản lý tài khoản",
        "Admin tự khoá chính mình",
        "Đang đăng nhập bằng tài khoản ADMIN hiện tại",
        "1. Gửi request khoá tài khoản với user_id chính là Admin",
        "PATCH /api/admin/users/{admin_id}/lock",
        "Trên giao diện nút khoá bị ẩn (hiển thị 'Tài khoản của bạn'). Gọi API trực tiếp trả về lỗi 400 Bad Request."
    ),
    (
        "TC_USR_08",
        "Quản lý tài khoản",
        "Khoá tài khoản đã bị khoá từ trước",
        "Tài khoản mục tiêu đã có status = LOCKED",
        "1. Gửi request khoá tài khoản đã LOCKED",
        "PATCH /api/admin/users/{id}/lock",
        "Hệ thống trả về mã lỗi 409 Conflict ('Tài khoản đã bị khoá')."
    ),
    (
        "TC_USR_09",
        "Quản lý tài khoản",
        "Mở khoá tài khoản đang bị khoá",
        "Tài khoản mục tiêu đang có status = LOCKED",
        "1. Bấm nút 'Mở khoá' tại dòng tài khoản mục tiêu",
        "PATCH /api/admin/users/{id}/unlock",
        "Tài khoản chuyển status thành ACTIVE. Badge chuyển xanh 'Hoạt động', nút đổi thành 'Khoá'. Người dùng đăng nhập lại thành công."
    ),
    (
        "TC_USR_10",
        "Quản lý tài khoản",
        "Mở khoá tài khoản đang hoạt động (ACTIVE)",
        "Tài khoản đang ACTIVE",
        "1. Gửi request mở khoá tài khoản đang ACTIVE",
        "PATCH /api/admin/users/{id}/unlock",
        "Hệ thống trả về mã lỗi 409 Conflict ('Tài khoản đang hoạt động')."
    ),
    (
        "TC_USR_11",
        "Quản lý tài khoản",
        "Người dùng thường gọi API danh sách / khoá / mở khoá tài khoản",
        "Đăng nhập role USER hoặc SELLER",
        "1. Gọi GET /api/admin/users hoặc PATCH /api/admin/users/{id}/lock",
        "Token user thường",
        "Hệ thống chặn truy cập với mã lỗi 403 Forbidden."
    ),
    (
        "TC_USR_12",
        "Quản lý tài khoản",
        "Khách chưa đăng nhập gọi API quản lý tài khoản",
        "Chưa đăng nhập",
        "1. Gửi request đến /api/admin/users không kèm token",
        "Headers không có token",
        "Hệ thống trả về mã lỗi 401 Unauthorized."
    ),

    # T3D201D: Kiểm duyệt video
    (
        "TC_VID_01",
        "Kiểm duyệt video",
        "Admin xem danh sách video cần kiểm duyệt",
        "Đăng nhập tài khoản ADMIN",
        "1. Mở trang Admin\n2. Bấm tab 'Video'",
        "GET /api/admin/videos",
        "Hiển thị bảng video gồm tiêu đề, người đăng, lượt xem, trạng thái (VISIBLE/HIDDEN), lý do vi phạm (nếu có) và nút Ẩn/Hiện."
    ),
    (
        "TC_VID_02",
        "Kiểm duyệt video",
        "Lọc video theo trạng thái và tìm kiếm tiêu đề/người đăng",
        "Đang ở tab Video",
        "1. Chọn lọc trạng thái 'Đã ẩn (vi phạm)'\n2. Nhập từ khóa tìm kiếm và bấm Tìm",
        "status = HIDDEN, search = 'son'",
        "Bảng lọc đúng các video vi phạm có tiêu đề hoặc username chứa từ khóa tìm kiếm."
    ),
    (
        "TC_VID_03",
        "Kiểm duyệt video",
        "Admin ẩn video vi phạm có nhập lý do hợp lệ",
        "Video đang ở trạng thái VISIBLE",
        "1. Bấm nút 'Ẩn vi phạm'\n2. Nhập lý do vào modal\n3. Bấm 'Xác nhận ẩn'",
        "PATCH /api/admin/videos/{id}/visibility với status=HIDDEN, reason='Nội dung bạo lực, vi phạm tiêu chuẩn cộng đồng'",
        "Video chuyển status sang HIDDEN, lưu reason, moderated_by và thời gian moderated_at vào DB. Bảng hiển thị badge vi phạm kèm lý do."
    ),
    (
        "TC_VID_04",
        "Kiểm duyệt video",
        "Admin ẩn video nhưng bỏ trống lý do vi phạm",
        "Video đang ở trạng thái VISIBLE",
        "1. Bấm 'Ẩn vi phạm'\n2. Bỏ trống lý do\n3. Bấm 'Xác nhận ẩn'",
        "reason = '' hoặc không truyền",
        "Báo lỗi 'Vui lòng nhập lý do ẩn nội dung vi phạm'; API trả về lỗi 422 Unprocessable Content. Không thay đổi trạng thái video."
    ),
    (
        "TC_VID_05",
        "Kiểm duyệt video",
        "Ẩn video đã bị ẩn từ trước",
        "Video đã có status = HIDDEN",
        "1. Gửi request ẩn video đã bị ẩn",
        "PATCH /api/admin/videos/{id}/hide",
        "Hệ thống trả về mã lỗi 409 Conflict ('Video đã bị ẩn')."
    ),
    (
        "TC_VID_06",
        "Kiểm duyệt video",
        "Kiểm tra video bị ẩn không xuất hiện trên các trang công khai",
        "Video vừa bị Admin ẩn (HIDDEN)",
        "1. Mở trang Bảng tin (feed.html)\n2. Tìm kiếm video trên search.html\n3. Truy cập link xem chi tiết video (video.html?id=...)",
        "ID của video bị ẩn",
        "Video hoàn toàn biến mất khỏi feed và kết quả tìm kiếm. Trang xem chi tiết báo video không tồn tại hoặc đã bị ẩn."
    ),
    (
        "TC_VID_07",
        "Kiểm duyệt video",
        "Chủ video cố tình tự bật lại video bị Admin ẩn vi phạm",
        "Video bị Admin ẩn (moderated_at IS NOT NULL)",
        "1. Chủ video gọi API PATCH /api/videos/{id}/status để đổi sang VISIBLE",
        "PATCH /api/videos/{id}/status với body {'status': 'VISIBLE'}",
        "Backend chặn với mã lỗi 403 Forbidden ('Video đang bị Admin ẩn do vi phạm, không thể tự hiển thị lại'). Video vẫn giữ nguyên HIDDEN."
    ),
    (
        "TC_VID_08",
        "Kiểm duyệt video",
        "Admin mở lại video đã ẩn (gỡ vi phạm)",
        "Video đang bị ẩn (HIDDEN)",
        "1. Admin bấm nút 'Hiện lại' tại dòng video bị ẩn\n2. Xác nhận popup",
        "PATCH /api/admin/videos/{id}/visibility với status=VISIBLE",
        "Video chuyển sang VISIBLE, xóa cờ moderated_at và reason trong DB. Video xuất hiện công khai trở lại trên feed/search."
    ),
    (
        "TC_VID_09",
        "Kiểm duyệt video",
        "Gọi API /visibility với body rỗng hoặc trạng thái mâu thuẫn",
        "Đăng nhập tài khoản ADMIN",
        "1. Gửi PATCH /api/admin/videos/{id}/visibility với body {}\n2. Gửi body mâu thuẫn {status: VISIBLE, is_visible: false}",
        "Body = {} hoặc {status: 'VISIBLE', is_visible: false}",
        "Backend bắt lỗi validation, trả về mã 422 Unprocessable Content, không tự động chạy nhánh 'hiện lại'."
    ),
    (
        "TC_VID_10",
        "Kiểm duyệt video",
        "Người dùng thường hoặc khách gọi API kiểm duyệt video",
        "Đăng nhập USER thường hoặc chưa đăng nhập",
        "1. Gửi request đến /api/admin/videos hoặc /visibility",
        "Token user thường hoặc không có token",
        "Bị chặn với mã 403 Forbidden (nếu có token user) hoặc 401 Unauthorized (nếu không có token)."
    ),

    # T3D201D: Kiểm duyệt sản phẩm
    (
        "TC_PRD_01",
        "Kiểm duyệt sản phẩm",
        "Admin xem danh sách sản phẩm cần kiểm duyệt",
        "Đăng nhập tài khoản ADMIN",
        "1. Mở trang Admin\n2. Bấm tab 'Sản phẩm'",
        "GET /api/admin/products",
        "Hiển thị bảng sản phẩm gồm ảnh thumbnail, tên sản phẩm, tên cửa hàng, giá bán, trạng thái (ACTIVE/HIDDEN/INACTIVE) và lý do vi phạm."
    ),
    (
        "TC_PRD_02",
        "Kiểm duyệt sản phẩm",
        "Lọc sản phẩm theo trạng thái và tìm kiếm tên sản phẩm/shop",
        "Đang ở tab Sản phẩm",
        "1. Chọn lọc trạng thái 'Đã ẩn (vi phạm)'\n2. Nhập từ khóa tìm kiếm tên sản phẩm hoặc shop",
        "status = HIDDEN, search = 'áo khoác'",
        "Bảng lọc đúng các sản phẩm thỏa mãn điều kiện trạng thái và từ khóa tìm kiếm."
    ),
    (
        "TC_PRD_03",
        "Kiểm duyệt sản phẩm",
        "Admin ẩn sản phẩm vi phạm có nhập lý do",
        "Sản phẩm đang ở trạng thái ACTIVE",
        "1. Bấm 'Ẩn vi phạm'\n2. Nhập lý do vi phạm vào modal\n3. Bấm 'Xác nhận ẩn'",
        "PATCH /api/admin/products/{id}/visibility với status=HIDDEN, reason='Hàng giả mạo nhãn hiệu'",
        "Sản phẩm chuyển status sang HIDDEN, lưu lý do vi phạm và người kiểm duyệt vào DB. Hiển thị badge vi phạm kèm lý do."
    ),
    (
        "TC_PRD_04",
        "Kiểm duyệt sản phẩm",
        "Admin ẩn sản phẩm nhưng bỏ trống lý do",
        "Sản phẩm đang ACTIVE",
        "1. Bấm 'Ẩn vi phạm'\n2. Bỏ trống lý do\n3. Bấm 'Xác nhận ẩn'",
        "reason = ''",
        "Giao diện hiện lỗi bắt buộc nhập lý do; API trả về mã lỗi 422 Unprocessable Content. Trạng thái sản phẩm giữ nguyên."
    ),
    (
        "TC_PRD_05",
        "Kiểm duyệt sản phẩm",
        "Kiểm tra sản phẩm bị ẩn không mua được và không hiển thị công khai",
        "Sản phẩm vừa bị Admin ẩn (HIDDEN)",
        "1. Truy cập API xem chi tiết GET /api/products/{id}\n2. Thử thêm sản phẩm vào giỏ hàng POST /api/cart/items\n3. Thử tạo đơn hàng",
        "ID của sản phẩm bị ẩn",
        "Xem chi tiết trả về 404 Not Found; Thêm vào giỏ hàng bị từ chối 400 Bad Request; Đặt đơn hàng bị chặn không cho thanh toán."
    ),
    (
        "TC_PRD_06",
        "Kiểm duyệt sản phẩm",
        "Người bán (SELLER) tự ý sửa trạng thái sản phẩm bị Admin ẩn",
        "Sản phẩm bị Admin ẩn (moderated_at IS NOT NULL)",
        "1. Seller gọi PATCH /api/products/{id} để chuyển status về ACTIVE",
        "PATCH /api/products/{id} với body {'status': 'ACTIVE'}",
        "Backend chặn với mã lỗi 403 Forbidden ('Sản phẩm đang bị Admin ẩn do vi phạm, không thể tự hiển thị lại')."
    ),
    (
        "TC_PRD_07",
        "Kiểm duyệt sản phẩm",
        "Admin mở lại sản phẩm đã ẩn",
        "Sản phẩm đang HIDDEN",
        "1. Admin bấm nút 'Hiện lại' tại dòng sản phẩm\n2. Xác nhận popup",
        "PATCH /api/admin/products/{id}/visibility với status=ACTIVE",
        "Sản phẩm chuyển status sang ACTIVE, xóa cờ kiểm duyệt. Sản phẩm xuất hiện công khai và mua hàng lại bình thường."
    ),
    (
        "TC_PRD_08",
        "Kiểm duyệt sản phẩm",
        "Gọi API /visibility sản phẩm với body rỗng hoặc mâu thuẫn",
        "Đăng nhập tài khoản ADMIN",
        "1. Gửi request PATCH /api/admin/products/{id}/visibility với body {}",
        "Body = {}",
        "Backend bắt lỗi validation, trả về mã lỗi 422 Unprocessable Content."
    ),
    (
        "TC_PRD_09",
        "Kiểm duyệt sản phẩm",
        "Người dùng thường / SELLER gọi API kiểm duyệt sản phẩm của Admin",
        "Đăng nhập tài khoản không phải ADMIN",
        "1. Gửi request đến /api/admin/products hoặc /visibility",
        "Token user/seller",
        "Hệ thống trả về mã lỗi 403 Forbidden."
    ),

    # T3D201D: Dashboard thống kê
    (
        "TC_DSH_01",
        "Dashboard thống kê",
        "Xem dashboard tổng quan khi hệ thống có dữ liệu",
        "Đăng nhập tài khoản ADMIN, DB có dữ liệu người dùng, video, sản phẩm, đơn hàng",
        "1. Mở trang Admin\n2. Mặc định mở tab 'Dashboard'",
        "GET /api/admin/dashboard",
        "Hiển thị đủ 6 thẻ chỉ số: Người dùng, Người bán, Tổng Video, Tổng Sản phẩm, Tổng Đơn hàng, Doanh thu toàn sàn đúng với DB."
    ),
    (
        "TC_DSH_02",
        "Dashboard thống kê",
        "Kiểm tra cách tính doanh thu toàn sàn (loại trừ đơn huỷ và đơn chờ)",
        "DB có các đơn hàng completed, confirmed, shipping, pending và cancelled",
        "1. Kiểm tra số tiền doanh thu hiển thị trên thẻ Doanh thu và biểu đồ",
        "Đơn completed: 100k, confirmed: 50k, cancelled: 999k, pending: 777k",
        "Doanh thu chỉ cộng các đơn confirmed, shipping, completed (= 150k). Hoàn toàn loại bỏ đơn cancelled và pending."
    ),
    (
        "TC_DSH_03",
        "Dashboard thống kê",
        "Kiểm tra không bị cộng trùng doanh thu khi đơn hàng có nhiều mặt hàng",
        "Có 1 đơn hàng giá trị 100k nhưng chứa 3 OrderItem",
        "1. Gọi API tính tổng doanh thu và xem thống kê doanh thu",
        "Đơn hàng total_amount = 100,000 chứa 3 item",
        "Doanh thu được tính đúng 100,000 (truy vấn trực tiếp trên bảng Order, không join nhân bản theo OrderItem)."
    ),
    (
        "TC_DSH_04",
        "Dashboard thống kê",
        "Hiển thị 3 biểu đồ Chart.js theo ngày",
        "Đang ở tab Dashboard",
        "1. Quan sát 3 biểu đồ phía dưới các thẻ thống kê",
        "GET /api/admin/dashboard (dữ liệu daily)",
        "Hiển thị đủ 3 biểu đồ Chart.js hoạt động mượt mà: 1) Doanh thu theo ngày (line chart); 2) Đơn hàng theo ngày (bar chart); 3) Người dùng & video mới (multi-line)."
    ),
    (
        "TC_DSH_05",
        "Dashboard thống kê",
        "Lọc dữ liệu thống kê theo khoảng ngày (Từ ngày – Đến ngày)",
        "Đang ở tab Dashboard",
        "1. Nhập 'Từ ngày' (from_date) và 'Đến ngày' (to_date)\n2. Bấm nút 'Áp dụng'",
        "from_date = '2026-11-01', to_date = '2026-11-20'",
        "Biểu đồ và số liệu theo ngày cập nhật chính xác từng ngày trong khoảng 01/11 đến 20/11. Trục hoành hiển thị đúng ngày."
    ),
    (
        "TC_DSH_06",
        "Dashboard thống kê",
        "Chọn nhanh mốc thời gian 7 ngày, 14 ngày, 30 ngày, 90 ngày",
        "Đang ở tab Dashboard",
        "1. Lần lượt bấm các nút chọn nhanh '7 ngày', '14 ngày', '30 ngày', '90 ngày'",
        "Click nút chọn nhanh",
        "Số ngày trên biểu đồ thay đổi tương ứng theo đúng số điểm ngày được chọn. Nút được chọn nổi bật màu primary."
    ),
    (
        "TC_DSH_07",
        "Dashboard thống kê",
        "Chọn Từ ngày lớn hơn Đến ngày",
        "Đang ở tab Dashboard",
        "1. Chọn Từ ngày = 2026-11-20, Đến ngày = 2026-11-01\n2. Bấm 'Áp dụng'",
        "from_date > to_date",
        "Giao diện hiện toast thông báo lỗi; API trả về mã 400 Bad Request ('from_date không được lớn hơn to_date')."
    ),
    (
        "TC_DSH_08",
        "Dashboard thống kê",
        "Chọn khoảng thời gian vượt quá 365 ngày",
        "Đang ở tab Dashboard",
        "1. Gửi request với khoảng ngày kéo dài hơn 1 năm",
        "Khoảng cách > 365 ngày",
        "Backend trả về mã lỗi 400 Bad Request ('Khoảng thời gian không được vượt quá 365 ngày')."
    ),
    (
        "TC_DSH_09",
        "Dashboard thống kê",
        "Người dùng thường / khách chưa đăng nhập truy cập API Dashboard",
        "Role USER hoặc không gửi token",
        "1. Gửi request đến /api/admin/dashboard",
        "Token user hoặc không có token",
        "Hệ thống trả về mã lỗi 403 Forbidden hoặc 401 Unauthorized."
    ),

    # An toàn bảo mật XSS
    (
        "TC_SEC_01",
        "Bảo mật & UI",
        "Kiểm tra chống tấn công XSS khi tên video, sản phẩm, username chứa ký tự nháy kép (\") và mã HTML",
        "Có video / sản phẩm chứa ký tự đặc biệt trong tên: Test \"<script>alert(1)</script>\" & demo",
        "1. Mở trang Admin\n2. Xem hiển thị bảng và bấm nút 'Ẩn vi phạm'",
        "Tên có chứa \", ', <, >, &",
        "Các ký tự đặc biệt được hàm escapeAttr và escapeHtml xử lý an toàn. Không làm vỡ thuộc tính HTML data-name và không thực thi mã độc JS."
    ),
]

for row_idx, r in enumerate(tc_data, 5):
    for col_idx, val in enumerate(r, 1):
        cell = ws_tc.cell(row=row_idx, column=col_idx, value=val)
        cell.font = bold_font if col_idx == 1 else regular_font
        cell.border = cell_border
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        if row_idx % 2 == 0:
            cell.fill = zebra_fill


# ==============================================================================
# 2. SHEET: Test Log
# ==============================================================================
ws_log = wb.create_sheet(title="Test Log")
ws_log.views.sheetView[0].showGridLines = True

ws_log["A1"] = "NHẬT KÝ THỰC THI KIỂM THỬ (TEST EXECUTION LOG)"
ws_log["A1"].font = title_font
ws_log["A2"] = "Dự án: ClipShop AI - Người kiểm thử: Bùi Duy Hoàng (B25DTCN093) - Ngày chạy: 20/11/2026"
ws_log["A2"].font = subtitle_font

log_headers = [
    "Mã TC",
    "Ngày chạy",
    "Người kiểm thử",
    "Kết quả thực tế",
    "Pass/Fail",
    "Mã bug",
    "Minh chứng / Ghi chú"
]

header_fill_2 = PatternFill(start_color=ICE_HEADER, end_color=ICE_HEADER, fill_type="solid")
for col_idx, h in enumerate(log_headers, 1):
    cell = ws_log.cell(row=4, column=col_idx, value=h)
    cell.font = header_font
    cell.fill = header_fill_2
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = cell_border

# Execution log rows matching the 52 TCs + retest rows
log_data = [
    ("TC_SA_01", "20/11/2026", "Bùi Duy Hoàng", "Hiển thị đúng danh sách đơn PENDING kèm thông tin chi tiết và 2 nút Duyệt/Từ chối", "Pass", "", "UI admin.html, API GET /seller-applications"),
    ("TC_SA_02", "20/11/2026", "Bùi Duy Hoàng", "Dropdown lọc trạng thái tải lại bảng chính xác theo từng bộ lọc", "Pass", "", "UI admin.html"),
    ("TC_SA_03", "20/11/2026", "Bùi Duy Hoàng", "Đơn chuyển sang APPROVED và user được đổi role thành SELLER cùng lúc", "Pass", "", "test_admin.py::test_approve_sets_seller"),
    ("TC_SA_04", "20/11/2026", "Bùi Duy Hoàng", "Trả về HTTP 409 Conflict khi cố duyệt lại đơn đã xử lý", "Pass", "", "test_admin.py::test_approve_twice_conflict"),
    ("TC_SA_05", "20/11/2026", "Bùi Duy Hoàng", "Trả về HTTP 404 Not Found đối với application_id không tồn tại", "Pass", "", "test_admin.py::test_approve_twice_conflict"),
    ("TC_SA_06", "20/11/2026", "Bùi Duy Hoàng", "Đơn chuyển sang REJECTED, lưu đúng lý do từ chối vào database", "Pass", "", "test_admin.py::test_reject_requires_reason"),
    ("TC_SA_07", "20/11/2026", "Bùi Duy Hoàng", "Modal báo lỗi khi bỏ trống lý do, API trả về mã lỗi 422", "Pass", "", "test_admin.py::test_reject_requires_reason"),
    ("TC_SA_08", "20/11/2026", "Bùi Duy Hoàng", "Trả về HTTP 409 Conflict khi từ chối đơn đã xử lý", "Pass", "", "test_admin.py::test_reject_requires_reason"),
    ("TC_SA_09", "20/11/2026", "Bùi Duy Hoàng", "Tài khoản USER và SELLER đều nhận mã 403 Forbidden khi gọi API admin", "Pass", "", "test_admin.py::test_non_admin_forbidden"),
    ("TC_SA_10", "20/11/2026", "Bùi Duy Hoàng", "Trả về HTTP 401 Unauthorized khi không gửi Authorization token", "Pass", "", "test_admin.py::test_no_token_unauthorized"),
    ("TC_SA_11", "20/11/2026", "Bùi Duy Hoàng", "Endpoint /quick-setup đã bị gỡ bỏ (trả về 404/405), không tự duyệt được", "Pass", "", "test_admin.py::test_quick_setup_self_approve_endpoint_removed"),

    ("TC_USR_01", "20/11/2026", "Bùi Duy Hoàng", "Hiển thị danh sách tài khoản đầy đủ, trường password_hash không xuất hiện", "Pass", "", "test_admin.py::test_search_users"),
    ("TC_USR_02", "20/11/2026", "Bùi Duy Hoàng", "Tìm kiếm theo username và email trả về chính xác tài khoản cần tìm", "Pass", "", "test_admin.py::test_search_users"),
    ("TC_USR_03", "20/11/2026", "Bùi Duy Hoàng", "Tìm kiếm từ khóa không có trả về danh sách rỗng và giao diện hiện thông báo", "Pass", "", "test_admin.py::test_search_users"),
    ("TC_USR_04", "20/11/2026", "Bùi Duy Hoàng", "Tìm kiếm ký tự % được escape an toàn, không gây lỗi hệ thống", "Pass", "", "test_admin.py::test_search_users"),
    ("TC_USR_05", "20/11/2026", "Bùi Duy Hoàng", "Tài khoản chuyển trạng thái LOCKED thành công, UI cập nhật badge đỏ", "Pass", "", "test_admin.py::test_lock_blocks_old_token"),
    ("TC_USR_06", "20/11/2026", "Bùi Duy Hoàng", "Đăng nhập bị từ chối 403; token đang dùng bị chặn 403 ngay lập tức", "Pass", "", "test_admin.py::test_lock_blocks_old_token"),
    ("TC_USR_07", "20/11/2026", "Bùi Duy Hoàng", "Giao diện ẩn nút khoá tài khoản bản thân; gọi API trả về 400 Bad Request", "Pass", "", "test_admin.py::test_admin_cannot_lock_self"),
    ("TC_USR_08", "20/11/2026", "Bùi Duy Hoàng", "Trả về HTTP 409 Conflict khi cố khoá tài khoản đã LOCKED", "Pass", "", "test_admin.py::test_lock_blocks_old_token"),
    ("TC_USR_09", "20/11/2026", "Bùi Duy Hoàng", "Tài khoản chuyển sang ACTIVE, đăng nhập lại thành công và dùng API bình thường", "Pass", "", "test_admin.py::test_lock_blocks_old_token"),
    ("TC_USR_10", "20/11/2026", "Bùi Duy Hoàng", "Trả về HTTP 409 Conflict khi mở khoá tài khoản đang ACTIVE", "Pass", "", "test_admin.py::test_lock_blocks_old_token"),
    ("TC_USR_11", "20/11/2026", "Bùi Duy Hoàng", "Người dùng role USER/SELLER gọi API tài khoản admin bị trả về 403", "Pass", "", "test_admin.py::test_non_admin_forbidden"),
    ("TC_USR_12", "20/11/2026", "Bùi Duy Hoàng", "Khách chưa đăng nhập nhận 401 Unauthorized khi gọi API tài khoản", "Pass", "", "test_admin.py::test_no_token_unauthorized"),

    ("TC_VID_01", "20/11/2026", "Bùi Duy Hoàng", "Bảng video hiển thị đầy đủ thông tin, trạng thái badge và lý do vi phạm", "Pass", "", "UI admin.html tab Video"),
    ("TC_VID_02", "20/11/2026", "Bùi Duy Hoàng", "Lọc theo trạng thái HIDDEN/VISIBLE và tìm kiếm tiêu đề hoạt động chính xác", "Pass", "", "test_admin_moderation.py::test_search_videos"),
    ("TC_VID_03", "20/11/2026", "Bùi Duy Hoàng", "Video chuyển sang HIDDEN, lưu đúng reason, admin_id và thời gian vào DB", "Pass", "", "test_admin_moderation.py::test_hide_video_requires_reason"),
    ("TC_VID_04", "20/11/2026", "Bùi Duy Hoàng", "Không nhập lý do bị báo lỗi ở UI; API trả về 422 Unprocessable Content", "Pass", "", "test_admin_moderation.py::test_hide_video_requires_reason"),
    ("TC_VID_05", "20/11/2026", "Bùi Duy Hoàng", "Trả về HTTP 409 Conflict khi cố ẩn video đã bị ẩn", "Pass", "", "test_admin_moderation.py::test_hide_video_requires_reason"),
    ("TC_VID_06", "20/11/2026", "Bùi Duy Hoàng", "Video bị ẩn biến mất khỏi feed công khai, tìm kiếm và chi tiết video (404)", "Pass", "", "test_admin_moderation.py::test_hide_video_requires_reason"),
    ("TC_VID_07 (Lần 1)", "20/11/2026", "Bùi Duy Hoàng", "Chủ video gọi PATCH /api/videos/{id}/status vẫn bật lại được video vi phạm", "Fail", "BUG-01", "Phát hiện lỗ hổng: social.py chưa kiểm tra moderated_at"),
    ("TC_VID_07 (Retest)", "20/11/2026", "Bùi Duy Hoàng", "Chủ video bị chặn 403 Forbidden ('Video đang bị Admin ẩn do vi phạm')", "Pass", "BUG-01 (Closed)", "test_admin_moderation.py::test_video_owner_cannot_unhide"),
    ("TC_VID_08", "20/11/2026", "Bùi Duy Hoàng", "Admin gỡ ẩn thành công, video chuyển VISIBLE và xóa sạch cờ vi phạm", "Pass", "", "test_admin_moderation.py::test_hide_video_requires_reason"),
    ("TC_VID_09 (Lần 1)", "20/11/2026", "Bùi Duy Hoàng", "Gửi body rỗng {} vào /visibility vẫn tự động chạy nhánh hiện lại video", "Fail", "BUG-02", "Schema cho phép để trống cả status và is_visible"),
    ("TC_VID_09 (Retest)", "20/11/2026", "Bùi Duy Hoàng", "Gửi body rỗng {} hoặc mâu thuẫn bị chặn với mã 422 Unprocessable Content", "Pass", "BUG-02 (Closed)", "test_admin_moderation.py::test_video_visibility_endpoint"),
    ("TC_VID_10", "20/11/2026", "Bùi Duy Hoàng", "Người dùng thường bị chặn 403, khách vãng lai bị chặn 401 khi gọi API", "Pass", "", "test_admin_moderation.py::test_only_admin"),

    ("TC_PRD_01", "20/11/2026", "Bùi Duy Hoàng", "Bảng sản phẩm hiển thị ảnh thumbnail, tên, shop, giá, trạng thái, lý do", "Pass", "", "UI admin.html tab Sản phẩm"),
    ("TC_PRD_02", "20/11/2026", "Bùi Duy Hoàng", "Bộ lọc trạng thái và tìm kiếm sản phẩm trả về kết quả chính xác", "Pass", "", "test_admin_moderation.py::test_list_products_filter"),
    ("TC_PRD_03", "20/11/2026", "Bùi Duy Hoàng", "Sản phẩm chuyển sang HIDDEN, lưu đúng lý do vi phạm và người ẩn vào DB", "Pass", "", "test_admin_moderation.py::test_hide_product_requires_reason"),
    ("TC_PRD_04", "20/11/2026", "Bùi Duy Hoàng", "Bỏ trống lý do ẩn sản phẩm bị chặn với mã 422 Unprocessable Content", "Pass", "", "test_admin_moderation.py::test_hide_product_requires_reason"),
    ("TC_PRD_05", "20/11/2026", "Bùi Duy Hoàng", "Chi tiết sản phẩm trả về 404; thêm vào giỏ hàng và đặt đơn đều bị chặn 400", "Pass", "", "test_admin_moderation.py::test_hide_product_requires_reason"),
    ("TC_PRD_06", "20/11/2026", "Bùi Duy Hoàng", "Seller gọi PATCH /api/products/{id} bị chặn 403 khi sản phẩm bị Admin ẩn", "Pass", "", "test_admin_moderation.py::test_hide_product_requires_reason"),
    ("TC_PRD_07", "20/11/2026", "Bùi Duy Hoàng", "Admin gỡ ẩn thành công, sản phẩm trở lại ACTIVE và cho phép mua hàng", "Pass", "", "test_admin_moderation.py::test_hide_product_requires_reason"),
    ("TC_PRD_08", "20/11/2026", "Bùi Duy Hoàng", "Body rỗng {} hoặc mâu thuẫn trên API sản phẩm bị chặn 422", "Pass", "", "test_admin_moderation.py::test_product_visibility_endpoint"),
    ("TC_PRD_09", "20/11/2026", "Bùi Duy Hoàng", "Non-admin gọi API kiểm duyệt sản phẩm nhận mã 403 Forbidden", "Pass", "", "test_admin_moderation.py::test_only_admin"),

    ("TC_DSH_01", "20/11/2026", "Bùi Duy Hoàng", "Hiển thị chính xác 6 thẻ chỉ số người dùng, người bán, video, sp, đơn, doanh thu", "Pass", "", "test_admin_moderation.py::test_dashboard_summary"),
    ("TC_DSH_02", "20/11/2026", "Bùi Duy Hoàng", "Chỉ cộng đơn confirmed, shipping, completed; loại bỏ đơn cancelled, pending", "Pass", "", "test_admin_moderation.py::test_dashboard_summary"),
    ("TC_DSH_03", "20/11/2026", "Bùi Duy Hoàng", "Đơn hàng có 3 sản phẩm không bị cộng trùng doanh thu, tính đúng 1 lần tiền đơn", "Pass", "", "test_admin_moderation.py::test_dashboard_summary"),
    ("TC_DSH_04", "20/11/2026", "Bùi Duy Hoàng", "3 biểu đồ Chart.js (doanh thu, đơn hàng, tăng trưởng) hiển thị mượt mà", "Pass", "", "UI admin.html tab Dashboard"),
    ("TC_DSH_05", "20/11/2026", "Bùi Duy Hoàng", "Chọn Từ ngày - Đến ngày tải lại biểu đồ chính xác theo từng ngày trong khoảng", "Pass", "", "test_admin_moderation.py::test_dashboard_summary"),
    ("TC_DSH_06", "20/11/2026", "Bùi Duy Hoàng", "Các nút chọn nhanh 7, 14, 30, 90 ngày cập nhật biểu đồ nhanh chóng", "Pass", "", "UI admin.html tab Dashboard"),
    ("TC_DSH_07", "20/11/2026", "Bùi Duy Hoàng", "Chọn Từ ngày > Đến ngày bị chặn với mã 400 Bad Request và toast thông báo", "Pass", "", "test_admin_moderation.py::test_dashboard_summary"),
    ("TC_DSH_08", "20/11/2026", "Bùi Duy Hoàng", "Khoảng ngày vượt quá 365 ngày bị backend trả về lỗi 400 Bad Request", "Pass", "", "test_admin_moderation.py::test_dashboard_summary"),
    ("TC_DSH_09", "20/11/2026", "Bùi Duy Hoàng", "Người dùng thường bị trả về 403 Forbidden khi truy cập API Dashboard", "Pass", "", "test_admin_moderation.py::test_only_admin"),

    ("TC_SEC_01 (Lần 1)", "20/11/2026", "Bùi Duy Hoàng", "Tên video có dấu nháy kép \" làm vỡ thuộc tính data-name=\"...\" trong HTML", "Fail", "BUG-03", "escapeHtml chỉ dùng div.innerHTML nên không escape dấu nháy"),
    ("TC_SEC_01 (Retest)", "20/11/2026", "Bùi Duy Hoàng", "Đã bổ sung escapeAttr escape dấu nháy kép thành &quot;, thuộc tính hiển thị chuẩn xác", "Pass", "BUG-03 (Closed)", "UI admin.html & utils.js"),
]

for row_idx, r in enumerate(log_data, 5):
    for col_idx, val in enumerate(r, 1):
        cell = ws_log.cell(row=row_idx, column=col_idx, value=val)
        cell.font = regular_font
        cell.border = cell_border
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        if col_idx == 1:
            cell.font = bold_font
        elif col_idx == 5:
            if "Pass" in val:
                cell.font = pass_font
                cell.fill = pass_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.font = fail_font
                cell.fill = fail_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")


# ==============================================================================
# 3. SHEET: Bug Log
# ==============================================================================
ws_bug = wb.create_sheet(title="Bug Log")
ws_bug.views.sheetView[0].showGridLines = True

ws_bug["A1"] = "DANH SÁCH LỖI PHÁT HIỆN VÀ THEO DÕI XỬ LÝ (BUG LOG)"
ws_bug["A1"].font = title_font
ws_bug["A2"] = "Dự án: ClipShop AI - Người quản lý lỗi: Bùi Duy Hoàng (B25DTCN093)"
ws_bug["A2"].font = subtitle_font

bug_headers = [
    "Mã bug",
    "Mô tả lỗi",
    "Cách tái hiện",
    "Mức độ",
    "Trạng thái sửa",
    "Kết quả kiểm tra lại (Retest)"
]

header_fill_3 = PatternFill(start_color=ACCENT_GREEN, end_color=ACCENT_GREEN, fill_type="solid")
for col_idx, h in enumerate(bug_headers, 1):
    cell = ws_bug.cell(row=4, column=col_idx, value=h)
    cell.font = header_font
    cell.fill = header_fill_3
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = cell_border

bug_data = [
    (
        "BUG-01",
        "Chủ video vẫn có thể tự bật lại video đang bị Admin ẩn do vi phạm thông qua API cũ /api/videos/{id}/status",
        "1. Admin gọi PATCH /api/admin/videos/{id}/visibility ẩn video vi phạm.\n2. Chủ video dùng token của mình gọi PATCH /api/videos/{id}/status với body {'status': 'VISIBLE'}.\n3. Video bị chuyển lại thành VISIBLE, bỏ qua quyết định kiểm duyệt của Admin.",
        "High (Nghiêm trọng)",
        "Đã sửa (Closed)",
        "Pass: Đã bổ sung kiểm tra cờ video.moderated_at IS NOT NULL trong app/routers/social.py. Người dùng thường bị chặn 403 Forbidden. Chỉ Admin mới được gỡ ẩn video."
    ),
    (
        "BUG-02",
        "API PATCH /api/admin/videos/{id}/visibility và /products/{id}/visibility nhận body rỗng {} vẫn tự động chạy nhánh 'Hiện lại'",
        "1. Gửi request PATCH /api/admin/videos/{id}/visibility với body rỗng {}.\n2. Do schema cho phép status và is_visible đều là None nên code mặc định coi là show.\n3. Gây rủi ro vô tình gỡ ẩn nội dung vi phạm khi gửi request không đầy đủ.",
        "Medium (Trung bình)",
        "Đã sửa (Closed)",
        "Pass: Đã cập nhật schema VideoVisibilityRequest & ProductVisibilityRequest với model_validator(mode='after') và extra='forbid'. Request body rỗng {} hoặc mâu thuẫn đều bị bắt lỗi 422 Unprocessable Content."
    ),
    (
        "BUG-03",
        "Tên video và sản phẩm chứa ký tự dấu nháy kép (\") gây vỡ thuộc tính HTML data-name khi render trên bảng Admin",
        "1. Tạo video hoặc sản phẩm có tiêu đề chứa dấu nháy kép (vd: Áo khoác \"Bomber\" thời trang).\n2. Mở trang Admin tab Video hoặc Sản phẩm.\n3. Thuộc tính data-name=\"...\" bị đóng ngoặc sớm gây hỏng cấu trúc HTML do hàm escapeHtml chỉ dùng div.innerHTML (không escape dấu nháy kép).",
        "Medium (Trung bình)",
        "Đã sửa (Closed)",
        "Pass: Đã bổ sung hàm chuyên biệt escapeAttr() trong frontend/js/utils.js để mã hóa dấu nháy kép thành &quot; và dấu nháy đơn thành &#39;, đồng thời nâng cấp escapeHtml(). Dữ liệu render an toàn tuyệt đối."
    ),
]

for row_idx, r in enumerate(bug_data, 5):
    for col_idx, val in enumerate(r, 1):
        cell = ws_bug.cell(row=row_idx, column=col_idx, value=val)
        cell.border = cell_border
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        if col_idx == 1:
            cell.font = bold_font
        elif col_idx == 4:
            cell.font = bold_font
            if "High" in val:
                cell.fill = fail_fill
        elif col_idx == 5:
            cell.font = pass_font
            cell.fill = pass_fill
            cell.alignment = Alignment(horizontal="center", vertical="top")
        else:
            cell.font = regular_font

# ==============================================================================
# Auto adjust column widths & padding
# ==============================================================================
for sheet in [ws_tc, ws_log, ws_bug]:
    for col in sheet.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            # ignore title rows
            if cell.row < 4:
                continue
            val_str = str(cell.value or "")
            lines = val_str.split("\n")
            line_max = max(len(l) for l in lines) if lines else 0
            if line_max > max_len:
                max_len = line_max
        sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 48)

# Set specific column widths for optimal reading
ws_tc.column_dimensions["A"].width = 14
ws_tc.column_dimensions["B"].width = 22
ws_tc.column_dimensions["C"].width = 36
ws_tc.column_dimensions["D"].width = 28
ws_tc.column_dimensions["E"].width = 38
ws_tc.column_dimensions["F"].width = 30
ws_tc.column_dimensions["G"].width = 42

ws_log.column_dimensions["A"].width = 18
ws_log.column_dimensions["B"].width = 14
ws_log.column_dimensions["C"].width = 18
ws_log.column_dimensions["D"].width = 46
ws_log.column_dimensions["E"].width = 14
ws_log.column_dimensions["F"].width = 18
ws_log.column_dimensions["G"].width = 40

ws_bug.column_dimensions["A"].width = 14
ws_bug.column_dimensions["B"].width = 38
ws_bug.column_dimensions["C"].width = 42
ws_bug.column_dimensions["D"].width = 18
ws_bug.column_dimensions["E"].width = 18
ws_bug.column_dimensions["F"].width = 48

# Save to destination paths
out_filename = "T3D1D6C_TestCase_TestLog_BuiDuyHoang_B25DTCN093.xlsx"

destinations = [
    os.path.join("docs", "t3d1d6c-test-cases", out_filename),
    out_filename,
    os.path.join("..", out_filename)
]

for p in destinations:
    try:
        wb.save(p)
        print(f"Đã lưu thành công: {os.path.abspath(p)}")
    except Exception as e:
        print(f"Lỗi lưu tại {p}: {e}")
