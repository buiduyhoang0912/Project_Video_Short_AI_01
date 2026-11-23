"""Script sinh file Excel (.xlsx), CSV (.csv) và Markdown (.md) cho Task T3D1D74:
[Kiểm thử] Test case và test log module mình - Hoàng Phúc Hiếu (SV1500).
Module: Giỏ hàng, Đặt hàng trong Transaction, Quản lý đơn hàng & Huỷ đơn, Thanh toán VietQR, UI Shop & Chi tiết sản phẩm.
"""

import csv
import shutil
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

DOCS_DIR = Path(__file__).resolve().parent
ROOT_DIR = DOCS_DIR.parent.parent

TEST_CASES = [
    # --- MODULE 1: GIỎ HÀNG (CART API & UI - T3D2853, T3D2B79) ---
    (
        "TC01",
        "Giỏ hàng (Cart API & UI)",
        "Đúng dữ liệu",
        "Thêm sản phẩm hợp lệ vào giỏ hàng (cộng dồn số lượng nếu đã tồn tại)",
        "Người dùng đã đăng nhập (User), sản phẩm trạng thái ACTIVE và còn tồn kho (stock >= quantity)",
        "Gửi POST /api/cart/items với {'product_id': 1, 'quantity': 2}",
        "HTTP 200/201; Sản phẩm được thêm vào giỏ, nếu đã có trong giỏ thì số lượng được cộng dồn chính xác",
        "HTTP 200 OK; quantity=2, line_total tính đúng đơn giá * số lượng",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC02",
        "Giỏ hàng (Cart API & UI)",
        "Đúng dữ liệu",
        "Cập nhật số lượng sản phẩm trong giỏ hàng trong giới hạn tồn kho",
        "Sản phẩm đã có trong giỏ hàng, số lượng mới hợp lệ (1 <= quantity <= stock)",
        "Gửi PUT /api/cart/items/{item_id} với {'quantity': 3}",
        "HTTP 200 OK; Số lượng sản phẩm trong giỏ được cập nhật thành 3, tạm tính dòng sản phẩm cập nhật tương ứng",
        "HTTP 200 OK; quantity=3, line_total = unit_price * 3",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC03",
        "Giỏ hàng (Cart API & UI)",
        "Đúng dữ liệu",
        "Xoá sản phẩm khỏi giỏ hàng",
        "Sản phẩm tồn tại trong giỏ hàng của user",
        "Gửi DELETE /api/cart/items/{item_id}",
        "HTTP 200/204 OK; Sản phẩm bị xoá khỏi giỏ hàng, tổng tiền giỏ hàng giảm tương ứng",
        "HTTP 200 OK; Item bị xoá hoàn toàn khỏi giỏ hàng",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC04",
        "Giỏ hàng (Cart API & UI)",
        "Đúng dữ liệu",
        "Xem giỏ hàng nhóm theo shop và tính tạm tính tại server",
        "User có sản phẩm từ nhiều shop khác nhau trong giỏ",
        "Gửi GET /api/cart",
        "HTTP 200 OK; Danh sách sản phẩm được nhóm theo từng shop_id riêng biệt, subtotal từng shop và tổng giỏ hàng do server tính toán",
        "HTTP 200 OK; shops=[{shop_id: 1, items: [...]}, {shop_id: 2, items: [...]}], subtotal chính xác",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC05",
        "Giỏ hàng (Cart API & UI)",
        "Sai dữ liệu",
        "Thêm hoặc sửa số lượng vượt quá tồn kho của sản phẩm",
        "Sản phẩm chỉ còn tồn kho 5 sản phẩm",
        "Gửi POST /api/cart/items hoặc PUT /api/cart/items/{id} với quantity=10",
        "HTTP 400 Bad Request; Chặn thao tác và báo lỗi không đủ số lượng tồn kho",
        "HTTP 400 Bad Request; {'detail': 'Số lượng yêu cầu vượt quá tồn kho'}",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC06",
        "Giỏ hàng (Cart API & UI)",
        "Sai dữ liệu",
        "Thêm sản phẩm đã bị ẩn hoặc không hoạt động (INACTIVE) vào giỏ",
        "Sản phẩm có status = 'INACTIVE' hoặc 'HIDDEN'",
        "Gửi POST /api/cart/items với ID của sản phẩm bị ẩn",
        "HTTP 400/404; Báo lỗi sản phẩm không khả dụng hoặc bị ẩn",
        "HTTP 400 Bad Request; Sản phẩm không khả dụng",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC07",
        "Giỏ hàng (Cart API & UI)",
        "Chưa đăng nhập",
        "Thao tác xem hoặc thêm giỏ hàng khi chưa gửi JWT Token",
        "Request không có header Authorization Bearer token",
        "Gửi GET /api/cart hoặc POST /api/cart/items không kèm token",
        "HTTP 401 Unauthorized; Từ chối truy cập và yêu cầu đăng nhập",
        "HTTP 401 Unauthorized; {'detail': 'Not authenticated'}",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC08",
        "Giỏ hàng (Cart API & UI)",
        "Đúng dữ liệu",
        "Sử dụng sổ địa chỉ giao hàng đã lưu trên giao diện giỏ hàng",
        "Người dùng đã lưu các địa chỉ nhận hàng trước đó trong trình duyệt",
        "Bấm chọn địa chỉ từ chip sổ địa chỉ tại trang cart.html",
        "Tự động điền Họ tên, Số điện thoại và Địa chỉ chi tiết vào form thanh toán",
        "Form nhận hàng được điền chính xác thông tin từ sổ địa chỉ",
        "PASS",
        "Không",
        "Không có lỗi",
    ),

    # --- MODULE 2: ĐẶT HÀNG TRONG TRANSACTION (ORDER TRANSACTION API & UI - T3D2B17, T3D2B79) ---
    (
        "TC09",
        "Đặt hàng trong Transaction",
        "Đúng dữ liệu",
        "Đặt hàng từ giỏ hàng thành công (Tách đơn theo từng shop riêng biệt)",
        "Giỏ hàng có sản phẩm từ Shop A và Shop B, tất cả sản phẩm đều đủ tồn kho",
        "Gửi POST /api/orders với recipient_name, recipient_phone, recipient_address, payment_method='COD'",
        "HTTP 201 Created; Tách thành 2 đơn hàng riêng cho 2 shop, trừ tồn kho, lưu giá snapshot, xoá sản phẩm đã đặt khỏi giỏ trong 1 Transaction duy nhất",
        "HTTP 201 Created; total_orders_created=2, giỏ hàng được dọn sạch các món đã đặt",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC10",
        "Đặt hàng trong Transaction",
        "Đúng dữ liệu",
        "Đặt hàng với phương thức thanh toán mô phỏng (SIMULATED)",
        "Sản phẩm đủ tồn kho, chọn payment_method = 'SIMULATED'",
        "Gửi POST /api/orders với payment_method='SIMULATED'",
        "HTTP 201 Created; Đơn hàng được tự động đánh dấu đã thanh toán và chuyển trạng thái CONFIRMED",
        "HTTP 201 Created; status='CONFIRMED', payment_status='PAID'",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC11",
        "Đặt hàng trong Transaction",
        "Sai dữ liệu",
        "Lỗi giữa chừng tự động Rollback (Không trừ tồn kho và không tạo đơn dở dang)",
        "Giỏ hàng có 2 sản phẩm: Sản phẩm 1 đủ tồn, sản phẩm 2 bị thiếu tồn hoặc lỗi",
        "Gửi POST /api/orders",
        "HTTP 400 Bad Request; Toàn bộ Transaction bị Rollback, tồn kho của sản phẩm 1 được giữ nguyên, không đơn nào được tạo",
        "HTTP 400 Bad Request; Tồn kho không đổi, Transaction rollback hoàn toàn",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC12",
        "Đặt hàng trong Transaction",
        "Đúng dữ liệu",
        "Chống tồn âm khi 2 người mua cùng sản phẩm cuối cùng (SELECT FOR UPDATE Concurrency)",
        "Sản phẩm chỉ còn tồn kho đúng 1 cái; 2 user cùng bấm đặt hàng đồng thời",
        "Hai luồng đồng thời gọi POST /api/orders mua sản phẩm đó",
        "Khóa bản ghi SELECT FOR UPDATE: 1 đơn thành công trừ tồn về 0, đơn thứ 2 bị chặn báo hết hàng; tồn kho không bao giờ bị âm",
        "1 request 201 Created, 1 request 400 Out of Stock; stock = 0",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC13",
        "Đặt hàng trong Transaction",
        "Sai dữ liệu",
        "Đặt hàng khi giỏ hàng trống hoặc thiếu thông tin nhận hàng bắt buộc",
        "Giỏ hàng không có sản phẩm hoặc không truyền recipient_address",
        "Gửi POST /api/orders với giỏ hàng rỗng hoặc recipient_address = ''",
        "HTTP 400/422; Báo lỗi giỏ hàng trống hoặc thiếu địa chỉ giao hàng",
        "HTTP 400/422 Bad Request; Báo lỗi rõ ràng",
        "PASS",
        "Không",
        "Không có lỗi",
    ),

    # --- MODULE 3: QUẢN LÝ ĐƠN HÀNG & HUỶ ĐƠN HOÀN TỒN (T3D2B93) ---
    (
        "TC14",
        "Quản lý Đơn hàng & Huỷ đơn",
        "Đúng dữ liệu",
        "Lấy danh sách đơn hàng của tôi và lọc theo trạng thái",
        "User đã đăng nhập, có các đơn ở trạng thái PENDING, CONFIRMED, DELIVERED",
        "Gửi GET /api/orders?status=PENDING",
        "HTTP 200 OK; Trả về đúng danh sách đơn hàng có trạng thái PENDING của user",
        "HTTP 200 OK; Tất cả đơn trả về đều có status='PENDING'",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC15",
        "Quản lý Đơn hàng & Huỷ đơn",
        "Đúng dữ liệu",
        "Xem chi tiết đơn hàng kèm Dòng thời gian trạng thái (Status Timeline)",
        "Đơn hàng tồn tại thuộc quyền sở hữu của user",
        "Gửi GET /api/orders/{order_id}",
        "HTTP 200 OK; Trả về chi tiết đơn, danh sách sản phẩm và mảng timeline trực quan qua các mốc CREATED, PENDING, CONFIRMED, SHIPPED, DELIVERED",
        "HTTP 200 OK; timeline=[{status_code: 'CREATED', is_completed: True}, ...]",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC16",
        "Quản lý Đơn hàng & Huỷ đơn",
        "Đúng dữ liệu",
        "Huỷ đơn hàng khi còn ở trạng thái Chờ xác nhận (PENDING) và hoàn tồn kho đúng một lần",
        "Đơn hàng có status='PENDING', sản phẩm trong đơn đã bị trừ kho khi đặt",
        "Gửi POST /api/orders/{order_id}/cancel",
        "HTTP 200 OK; Chuyển trạng thái đơn sang CANCELLED, cộng lại tồn kho cho tất cả sản phẩm trong đơn bằng đúng số lượng đã đặt",
        "HTTP 200 OK; status='CANCELLED', tồn kho sản phẩm tăng trở lại chính xác",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC17",
        "Quản lý Đơn hàng & Huỷ đơn",
        "Sai dữ liệu",
        "Huỷ đơn hàng khi đơn đã được xác nhận hoặc đang vận chuyển (Không phải PENDING)",
        "Đơn hàng có status='CONFIRMED' hoặc 'SHIPPED'",
        "Gửi POST /api/orders/{order_id}/cancel",
        "HTTP 400 Bad Request; Từ chối huỷ vì đơn đã qua bước Chờ xác nhận",
        "HTTP 400 Bad Request; {'detail': 'Chỉ có thể huỷ đơn khi đơn đang ở trạng thái Chờ xác nhận'}",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC18",
        "Quản lý Đơn hàng & Huỷ đơn",
        "Sai dữ liệu",
        "Huỷ đơn hàng lần thứ 2 trên cùng một đơn đã huỷ (Chống hoàn tồn lặp lại)",
        "Đơn hàng đã ở trạng thái CANCELLED",
        "Gửi lại POST /api/orders/{order_id}/cancel lần 2",
        "HTTP 400 Bad Request; Chặn huỷ lặp lại, không cộng thêm tồn kho lần thứ 2",
        "HTTP 400 Bad Request; Tồn kho không bị cộng thừa",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC19",
        "Quản lý Đơn hàng & Huỷ đơn",
        "Sai quyền",
        "User cố gắng huỷ đơn hàng thuộc sở hữu của tài khoản khác",
        "Đơn hàng thuộc về Buyer B; Buyer A cố tình gửi request huỷ đơn này",
        "Buyer A gửi POST /api/orders/{order_id_of_buyer_b}/cancel",
        "HTTP 404 Not Found hoặc 403 Forbidden; Bảo vệ dữ liệu người dùng khác",
        "HTTP 404 Not Found; {'detail': 'Không tìm thấy đơn hàng hoặc không có quyền huỷ'}",
        "PASS",
        "Không",
        "Không có lỗi",
    ),

    # --- MODULE 4: THANH TOÁN CHUYỂN KHOẢN QR VIETQR (T3D2C15) ---
    (
        "TC20",
        "Thanh toán QR VietQR (Bonus)",
        "Đúng dữ liệu",
        "Đặt hàng phương thức chuyển khoản và sinh mã QR VietQR chuẩn xác",
        "Shop có thông tin ngân hàng (bank_name='MB', bank_account_number='0987654321', holder='SHOP A')",
        "Gửi POST /api/orders với payment_method='BANK_TRANSFER'",
        "HTTP 201 Created; Đơn được tạo kèm link vietqr_url chuẩn ảnh VietQR chứa bank, STK, số tiền và nội dung chuyển tiền = DH{order_id}",
        "HTTP 201 Created; vietqr_url chứa 'img.vietqr.io', số tiền và mã đơn đúng định dạng",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC21",
        "Thanh toán QR VietQR (Bonus)",
        "Đúng dữ liệu",
        "Người bán (Seller) kiểm tra tài khoản và xác nhận đã nhận tiền chuyển khoản",
        "Đơn hàng BANK_TRANSFER đang ở trạng thái Chờ xác nhận (pending/unpaid)",
        "Seller gửi POST /api/shops/me/orders/{order_id}/confirm-payment",
        "HTTP 200 OK; Đơn hàng chuyển sang trạng thái 'confirmed', payment_status='PAID'",
        "HTTP 200 OK; status='confirmed', payment_status='PAID'",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC22",
        "Thanh toán QR VietQR (Bonus)",
        "Sai quyền",
        "User không phải chủ Shop thực hiện xác nhận nhận tiền",
        "User bình thường hoặc chủ shop khác gửi request xác nhận đơn",
        "Gửi POST /api/shops/me/orders/{order_id}/confirm-payment từ tài khoản không sở hữu shop",
        "HTTP 403/404; Từ chối thao tác",
        "HTTP 403/404 Forbidden/Not Found",
        "PASS",
        "Không",
        "Không có lỗi",
    ),

    # --- MODULE 5: UI CỬA HÀNG & CHI TIẾT SẢN PHẨM (T3D2839, T3D2B47) ---
    (
        "TC23",
        "UI Shop & Chi tiết sản phẩm",
        "Đúng dữ liệu",
        "Tìm kiếm, lọc danh mục, lọc khoảng giá và sắp xếp sản phẩm trên trang Shop",
        "Có nhiều sản phẩm thuộc các danh mục và mức giá khác nhau",
        "Mở shop.html, nhập từ khoá tìm kiếm, chọn danh mục, nhập giá từ - đến và chọn sắp xếp 'Giá tăng dần'",
        "Lưới sản phẩm hiển thị đúng các sản phẩm ACTIVE thoả mãn điều kiện lọc và sắp xếp theo thứ tự",
        "Hiển thị đúng danh sách sản phẩm theo bộ lọc, phân trang chính xác",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC24",
        "UI Shop & Chi tiết sản phẩm",
        "Đúng dữ liệu",
        "Xem chi tiết sản phẩm: Gallery ảnh, giá, tồn kho, chọn số lượng, nút Thêm giỏ & Mua ngay, thông tin shop",
        "Truy cập product.html?id={valid_product_id}",
        "Trang tải API /api/products/{id}",
        "Hiển thị đầy đủ ảnh chính, thumbnails gallery (bấm đổi ảnh), tồn kho thực tế, bộ điều khiển số lượng (min=1, max=stock), nút thêm giỏ và thẻ thông tin shop",
        "Hiển thị chính xác thông tin sản phẩm và shop, thao tác chuyển ảnh gallery mượt mà",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC25",
        "UI Shop & Chi tiết sản phẩm",
        "Sai dữ liệu",
        "Truy cập trang chi tiết sản phẩm không tồn tại hoặc đã bị ẩn",
        "Truy cập product.html?id=999999",
        "Trang gọi GET /api/products/999999",
        "HTTP 404 Not Found; Giao diện hiển thị thông báo lỗi 'Sản phẩm không tồn tại' rõ ràng, không bị crash trang",
        "Hiển thị cảnh báo thân thiện: 'Không tìm thấy sản phẩm. Vui lòng quay lại trang shop.'",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
]


def create_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Test Cases & Test Log"

    # Styling colors
    NAVY = "1E3A8A"
    LIGHT_BLUE = "EFF6FF"
    GREEN = "16A34A"
    LIGHT_GREEN = "DCFCE7"
    GRAY = "F8FAFC"
    BORDER_COLOR = "CBD5E1"

    thin_border = Border(
        left=Side(style="thin", color=BORDER_COLOR),
        right=Side(style="thin", color=BORDER_COLOR),
        top=Side(style="thin", color=BORDER_COLOR),
        bottom=Side(style="thin", color=BORDER_COLOR),
    )

    # Header title block
    ws.merge_cells("A1:K1")
    ws["A1"] = "BẢNG KẾT QUẢ KIỂM THỬ (TEST CASE & TEST LOG) - SPRINT 3"
    ws["A1"].font = Font(name="Segoe UI", size=16, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill(start_color=NAVY, end_color=NAVY, fill_type="solid")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 40

    # Sub info
    ws.merge_cells("A2:K2")
    ws["A2"] = "Dự án: ClipShop AI · Sinh viên: Hoàng Phúc Hiếu (SV1500) · Module: Giỏ hàng, Đặt hàng Transaction, Huỷ đơn & Hoàn tồn, VietQR, UI Shop"
    ws["A2"].font = Font(name="Segoe UI", size=11, italic=True, color="1E293B")
    ws["A2"].fill = PatternFill(start_color=LIGHT_BLUE, end_color=LIGHT_BLUE, fill_type="solid")
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 25

    # Empty row 3
    ws.row_dimensions[3].height = 10

    # Headers at row 4
    headers = [
        "Mã TC",
        "Phân hệ / Chức năng",
        "Loại kiểm thử",
        "Mô tả kịch bản kiểm thử",
        "Tiền điều kiện",
        "Dữ liệu & Bước thực hiện",
        "Kết quả mong đợi",
        "Kết quả thực tế",
        "Trạng thái",
        "Bug phát hiện",
        "Ghi chú",
    ]

    ws.row_dimensions[4].height = 28
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=h)
        cell.font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    # Data rows
    for row_idx, tc in enumerate(TEST_CASES, 5):
        ws.row_dimensions[row_idx].height = 42
        for col_idx, val in enumerate(tc, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = Font(name="Segoe UI", size=10)
            cell.border = thin_border

            # Căn chỉnh
            if col_idx in (1, 3, 9):  # Mã, Loại, Status
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

            # Highlight Status
            if col_idx == 9:
                if val == "PASS":
                    cell.font = Font(name="Segoe UI", size=10, bold=True, color="15803D")
                    cell.fill = PatternFill(start_color=LIGHT_GREEN, end_color=LIGHT_GREEN, fill_type="solid")

            # Alternate row background
            elif row_idx % 2 == 0:
                cell.fill = PatternFill(start_color=GRAY, end_color=GRAY, fill_type="solid")

    # Column widths
    col_widths = [10, 24, 16, 32, 28, 36, 36, 34, 12, 14, 16]
    for idx, width in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(idx)].width = width

    # Summary block at bottom
    total_row = len(TEST_CASES) + 6
    ws.merge_cells(f"A{total_row}:D{total_row}")
    ws[f"A{total_row}"] = f"TỔNG SỐ TEST CASE: {len(TEST_CASES)} | PASS: {len(TEST_CASES)} (100%) | FAIL: 0 | SỐ BUG CÒN LẠI: 0"
    ws[f"A{total_row}"].font = Font(name="Segoe UI", size=11, bold=True, color="15803D")
    ws[f"A{total_row}"].fill = PatternFill(start_color=LIGHT_GREEN, end_color=LIGHT_GREEN, fill_type="solid")
    ws[f"A{total_row}"].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[total_row].height = 28

    xlsx_path = DOCS_DIR / "T3D1D74_TestCase_TestLog_HoangPhucHieu_SV1500.xlsx"
    wb.save(xlsx_path)
    print(f"✅ Đã lưu file Excel: {xlsx_path}")

    # Copy ra thư mục gốc
    root_xlsx = ROOT_DIR / "T3D1D74_TestCase_TestLog_HoangPhucHieu_SV1500.xlsx"
    shutil.copy2(xlsx_path, root_xlsx)
    print(f"✅ Đã copy ra root: {root_xlsx}")

    # Xuất CSV
    csv_path = DOCS_DIR / "T3D1D74_TestCase_TestLog_HoangPhucHieu_SV1500.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for tc in TEST_CASES:
            writer.writerow(tc)
    print(f"✅ Đã lưu file CSV: {csv_path}")

    # Xuất Markdown
    md_path = DOCS_DIR / "T3D1D74_TestCase_TestLog_HoangPhucHieu_SV1500.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# BẢNG TEST CASE VÀ TEST LOG - HOÀNG PHÚC HIẾU (SV1500)\n\n")
        f.write("**Dự án:** ClipShop AI - Hệ thống Video ngắn & Thương mại điện tử\n")
        f.write("**Sinh viên thực hiện:** Hoàng Phúc Hiếu (SV1500)\n")
        f.write(f"**Tổng số test case:** {len(TEST_CASES)} | **Đạt:** {len(TEST_CASES)}/25 (100%) | **Bug tồn đọng:** 0\n\n")
        f.write("| Mã TC | Phân hệ | Loại test | Mô tả kịch bản | Tiền điều kiện | Bước thực hiện | Kết quả mong đợi | Kết quả thực tế | Trạng thái | Bug | Ghi chú |\n")
        f.write("|---|---|---|---|---|---|---|---|:---:|---|---|\n")
        for tc in TEST_CASES:
            row_str = " | ".join(str(x).replace("\n", " ").replace("|", "/") for x in tc)
            f.write(f"| {row_str} |\n")
    print(f"✅ Đã lưu file Markdown: {md_path}")


if __name__ == "__main__":
    create_excel()
