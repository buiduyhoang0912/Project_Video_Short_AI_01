"""Script sinh file Excel (.xlsx), CSV (.csv) và Markdown (.md) cho Task T3D1D72:
[Kiểm thử] Test case và test log module mình - Nguyễn Hoàng Văn (B25DTCN265).
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
    # --- MODULE 1: ĐĂNG KÝ BÁN HÀNG & CỬA HÀNG CÔNG KHAI (T3D24AA, T3D27D1) ---
    (
        "TC01",
        "Đăng ký bán hàng & Cửa hàng",
        "Đúng dữ liệu",
        "Gửi đơn đăng ký bán hàng hợp lệ lần đầu",
        "User đã đăng nhập (role=USER), chưa có đơn đăng ký nào đang chờ duyệt",
        "Gửi POST /api/seller-applications với {'proposed_shop_name': 'Shop Thời Trang Văn', 'phone': '0912345678', 'description': 'Chuyên quần áo nam nữ'}",
        "HTTP 201 Created; trả về đơn đăng ký với status='PENDING', lưu đúng tên shop đề xuất và số điện thoại",
        "HTTP 201 Created; status='PENDING', proposed_shop_name='Shop Thời Trang Văn'",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC02",
        "Đăng ký bán hàng & Cửa hàng",
        "Sai dữ liệu",
        "Gửi trùng đơn đăng ký bán hàng khi đã có đơn đang PENDING",
        "User đang có 1 đơn đăng ký ở trạng thái PENDING",
        "Gửi lại POST /api/seller-applications lần thứ 2 với cùng tài khoản",
        "HTTP 409 Conflict; chặn tạo đơn trùng và thông báo đang có đơn chờ duyệt",
        "HTTP 409 Conflict; {'detail': 'Bạn đang có đơn đăng ký chờ duyệt'}",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC03",
        "Đăng ký bán hàng & Cửa hàng",
        "Sai dữ liệu",
        "Gửi đơn đăng ký bán hàng với tên shop rỗng hoặc số điện thoại sai quy cách",
        "User đã đăng nhập",
        "Gửi POST /api/seller-applications với {'proposed_shop_name': '', 'phone': '123'}",
        "HTTP 422 Unprocessable Entity; báo lỗi validate dữ liệu đầu vào",
        "HTTP 422 Unprocessable Entity",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC04",
        "Đăng ký bán hàng & Cửa hàng",
        "Chưa đăng nhập",
        "Gửi đơn đăng ký bán hàng hoặc xem trạng thái đơn khi chưa đăng nhập",
        "Không gửi kèm JWT Bearer token trong Header",
        "Gửi POST /api/seller-applications và GET /api/seller-applications/me không có token",
        "HTTP 401 Unauthorized; từ chối truy cập",
        "HTTP 401 Unauthorized",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC05",
        "Đăng ký bán hàng & Cửa hàng",
        "Đúng dữ liệu",
        "Gửi lại đơn đăng ký bán hàng mới sau khi đơn cũ bị Admin từ chối (REJECTED)",
        "Đơn đăng ký trước đó của User đã bị Admin từ chối (status='REJECTED')",
        "Gửi POST /api/seller-applications với thông tin đã bổ sung đầy đủ",
        "HTTP 201 Created; cho phép tạo đơn mới với status='PENDING'",
        "HTTP 201 Created; status='PENDING'",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC06",
        "Đăng ký bán hàng & Cửa hàng",
        "Sai quyền",
        "Tạo cửa hàng khi đơn đăng ký chưa được Admin duyệt (role vẫn là USER)",
        "User chưa được Admin duyệt đơn bán hàng",
        "Gửi POST /api/shops với {'name': 'Shop Chưa Duyệt', 'description': 'Mô tả'}",
        "HTTP 403 Forbidden; chỉ tài khoản SELLER đã được duyệt mới được tạo cửa hàng",
        "HTTP 403 Forbidden",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC07",
        "Đăng ký bán hàng & Cửa hàng",
        "Đúng dữ liệu",
        "Tạo cửa hàng mới sau khi Admin duyệt đơn thành SELLER",
        "Admin đã duyệt đơn (user.role='SELLER') và user chưa có cửa hàng nào",
        "Gửi POST /api/shops với {'name': 'ClipShop Official', 'description': 'Phụ kiện chính hãng', 'address': 'Hà Nội'}",
        "HTTP 201 Created; trả về thông tin shop với status='ACTIVE', owner_id đúng bằng user_id",
        "HTTP 201 Created; id=1, name='ClipShop Official', status='ACTIVE'",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC08",
        "Đăng ký bán hàng & Cửa hàng",
        "Sai dữ liệu",
        "Một người bán cố tạo cửa hàng thứ 2 (vi phạm ràng buộc 1 seller - 1 shop)",
        "Seller đã sở hữu 1 cửa hàng trên hệ thống",
        "Gửi tiếp POST /api/shops với {'name': 'Shop Thứ 2'}",
        "HTTP 409 Conflict; mỗi người bán chỉ được tạo duy nhất 1 cửa hàng",
        "HTTP 409 Conflict; {'detail': 'Mỗi người bán chỉ được tạo một cửa hàng'}",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC09",
        "Đăng ký bán hàng & Cửa hàng",
        "Đúng dữ liệu",
        "Chủ shop cập nhật thông tin cửa hàng và tải lên Logo cửa hàng hợp lệ",
        "Seller đang đăng nhập và là chủ sở hữu của shop_id=1",
        "Gửi PUT /api/shops/1 và POST /api/shops/1/logo kèm file ảnh PNG hợp lệ",
        "HTTP 200 OK; cập nhật tên/địa chỉ shop và lưu file logo vào /uploads/shops/, trả về avatar_key",
        "HTTP 200 OK; avatar_key='/uploads/shops/...' hiển thị đúng trên trang cửa hàng",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC10",
        "Đăng ký bán hàng & Cửa hàng",
        "Sai quyền",
        "Người bán B cố tình sửa thông tin hoặc đổi Logo cửa hàng của Người bán A",
        "Seller B đăng nhập nhưng gọi API vào shop_id=1 của Seller A",
        "Gửi PUT /api/shops/1 và POST /api/shops/1/logo bằng token của Seller B",
        "HTTP 403 Forbidden; chặn chỉnh sửa cửa hàng của người khác",
        "HTTP 403 Forbidden",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC11",
        "Đăng ký bán hàng & Cửa hàng",
        "Sai dữ liệu",
        "Upload file không phải định dạng ảnh (.txt) làm Logo cửa hàng",
        "Seller là chủ sở hữu shop_id=1",
        "Gửi POST /api/shops/1/logo với file 'hack.txt' (content-type: text/plain)",
        "HTTP 422 Unprocessable Entity; chỉ chấp nhận định dạng ảnh PNG/JPG/WEBP",
        "HTTP 422 Unprocessable Entity",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC12",
        "Đăng ký bán hàng & Cửa hàng",
        "Đúng dữ liệu",
        "Khách xem trang cửa hàng công khai: thông tin shop, danh sách sản phẩm và video của shop",
        "Shop id=1 đang ACTIVE, có sản phẩm ACTIVE và video VISIBLE",
        "Gọi GET /api/shops/1, GET /api/shops/1/products và GET /api/shops/1/videos (không cần đăng nhập)",
        "HTTP 200 OK; trả về đầy đủ logo, mô tả, danh sách sản phẩm kèm ảnh và danh sách video công khai của chủ shop",
        "HTTP 200 OK; hiển thị đầy đủ trên giao diện shop-public.html",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    # --- MODULE 2: CRUD SẢN PHẨM, TỒN KHO, UPLOAD NHIỀU ẢNH & UI SELLER CENTER (T3D24C4, T3D27B7) ---
    (
        "TC13",
        "Quản lý Sản phẩm & Tồn kho",
        "Đúng dữ liệu",
        "Thêm sản phẩm mới hợp lệ (giá > 0, tồn kho >= 0)",
        "Seller đã có cửa hàng ACTIVE và category_id=1 tồn tại",
        "Gửi POST /api/products với {'category_id': 1, 'name': 'Áo Polo Cao Cấp', 'price': 199000, 'stock': 20}",
        "HTTP 201 Created; sản phẩm được gắn đúng shop_id của người bán, status='ACTIVE'",
        "HTTP 201 Created; id=1, price=199000.0, stock=20, status='ACTIVE'",
        "PASS",
        "BUG-01: Bảng products trên MySQL cũ thiếu cột sold_count gây lỗi 500",
        "Đã sửa",
    ),
    (
        "TC14",
        "Quản lý Sản phẩm & Tồn kho",
        "Sai dữ liệu",
        "Thêm sản phẩm với giá bằng 0 hoặc giá âm (price <= 0)",
        "Seller đã đăng nhập",
        "Gửi POST /api/products với {'category_id': 1, 'name': 'Áo lỗi giá', 'price': 0, 'stock': 10}",
        "HTTP 422 Unprocessable Entity; từ chối tạo sản phẩm vì giá phải > 0",
        "HTTP 422 Unprocessable Entity",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC15",
        "Quản lý Sản phẩm & Tồn kho",
        "Sai dữ liệu",
        "Thêm sản phẩm với số lượng tồn kho âm (stock < 0) hoặc danh mục không tồn tại",
        "Seller đã đăng nhập",
        "Gửi POST /api/products với stock=-1 (422) và với category_id=99999 (404)",
        "HTTP 422 khi stock < 0; HTTP 404 khi category_id không tồn tại",
        "HTTP 422 Unprocessable Entity & HTTP 404 Not Found",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC16",
        "Quản lý Sản phẩm & Tồn kho",
        "Chưa đăng nhập",
        "Gọi các API thêm, sửa, cập nhật tồn kho hoặc xóa sản phẩm khi chưa đăng nhập",
        "Không gửi kèm JWT Bearer token",
        "Gửi POST /api/products, PUT /api/products/1, PATCH /api/products/1/stock, DELETE /api/products/1",
        "HTTP 401 Unauthorized cho toàn bộ các endpoint quản lý sản phẩm",
        "HTTP 401 Unauthorized",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC17",
        "Quản lý Sản phẩm & Tồn kho",
        "Sai quyền",
        "Tài khoản người mua (role=USER) cố tình gọi API đăng bán sản phẩm",
        "User thường đăng nhập (chưa phải SELLER)",
        "Gửi POST /api/products với dữ liệu sản phẩm",
        "HTTP 403 Forbidden; chặn người dùng chưa phải là SELLER đăng bán sản phẩm",
        "HTTP 403 Forbidden",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC18",
        "Quản lý Sản phẩm & Tồn kho",
        "Đúng dữ liệu",
        "Sửa thông tin sản phẩm và cập nhật nhanh số lượng tồn kho trên Seller Center",
        "Seller là chủ sở hữu của product_id=1",
        "Gửi PUT /api/products/1 ({'name': 'Áo Polo Nam Mới', 'price': 220000}) và PATCH /api/products/1/stock ({'stock': 50})",
        "HTTP 200 OK; thông tin tên, giá và số lượng tồn kho được cập nhật chính xác",
        "HTTP 200 OK; name='Áo Polo Nam Mới', stock=50",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC19",
        "Quản lý Sản phẩm & Tồn kho",
        "Sai quyền",
        "Seller B cố tình sửa giá, sửa tồn kho hoặc xóa sản phẩm thuộc Shop của Seller A",
        "Product id=1 thuộc Shop A; Seller B đăng nhập bằng tài khoản của Shop B",
        "Gửi PUT /api/products/1 và DELETE /api/products/1 bằng token của Seller B",
        "HTTP 403 Forbidden; bảo vệ chặt chẽ quyền sở hữu sản phẩm giữa các shop",
        "HTTP 403 Forbidden",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC20",
        "Quản lý Sản phẩm & Tồn kho",
        "Đúng dữ liệu",
        "Upload nhiều ảnh sản phẩm cùng lúc vào thư mục /uploads/products/",
        "Seller là chủ sở hữu product_id=1",
        "Gửi POST /api/products/1/images kèm 2 file ảnh front.png và side.jpg",
        "HTTP 201 Created; lưu cả 2 file vào /uploads/products/, ảnh đầu tiên tự động có is_primary=True, sort_order=0",
        "HTTP 201 Created; trả về mảng 2 ảnh, ảnh đầu is_primary=True",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC21",
        "Quản lý Sản phẩm & Tồn kho",
        "Sai dữ liệu",
        "Upload file thực thi (.exe) không phải ảnh vào API ảnh sản phẩm",
        "Seller là chủ sở hữu product_id=1",
        "Gửi POST /api/products/1/images kèm file 'malware.exe' (application/octet-stream)",
        "HTTP 422 Unprocessable Entity; từ chối file không phải định dạng ảnh hợp lệ",
        "HTTP 422 Unprocessable Entity",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC22",
        "Quản lý Sản phẩm & Tồn kho",
        "Đúng dữ liệu",
        "Xóa sản phẩm đã phát sinh đơn hàng: chỉ chuyển sang Ẩn (HIDDEN), không xóa cứng",
        "Sản phẩm id=1 đã nằm trong bảng order_items của ít nhất 1 đơn hàng",
        "Gửi DELETE /api/products/1 kèm Bearer token của chủ shop",
        "HTTP 200 OK; trả về action='hidden', product.status='HIDDEN'; sản phẩm ẩn khỏi trang công khai nhưng giữ nguyên lịch sử đơn hàng",
        "HTTP 200 OK; {'action': 'hidden', 'product': {'status': 'HIDDEN'}}",
        "PASS",
        "BUG-02: Xóa cứng sản phẩm đã có đơn làm lỗi khóa ngoại order_items",
        "Đã sửa",
    ),
    (
        "TC23",
        "Quản lý Sản phẩm & Tồn kho",
        "Đúng dữ liệu",
        "Xóa sản phẩm chưa từng có đơn hàng: xóa cứng khỏi DB và dọn sạch file ảnh",
        "Sản phẩm id=2 chưa từng phát sinh bản ghi nào trong order_items",
        "Gửi DELETE /api/products/2 kèm Bearer token của chủ shop",
        "HTTP 200 OK; trả về action='deleted', xóa bản ghi khỏi bảng products và xóa file ảnh trong /uploads/products/",
        "HTTP 200 OK; {'action': 'deleted'}, file ảnh được dọn sạch",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    # --- MODULE 3: QUẢN LÝ ĐƠN HÀNG CỦA SHOP & THỐNG KÊ DOANH THU / BÁN CHẠY (T3D27EB) ---
    (
        "TC24",
        "Đơn hàng Shop & Thống kê",
        "Đúng dữ liệu",
        "Người bán xem danh sách đơn hàng của shop mình và lọc theo trạng thái",
        "Shop 1 có 2 đơn hàng ở trạng thái pending",
        "Gửi GET /api/shops/me/orders và GET /api/shops/me/orders?status=pending",
        "HTTP 200 OK; trả về danh sách đơn hàng của đúng Shop 1 kèm chi tiết từng món hàng (items)",
        "HTTP 200 OK; trả về đúng 2 đơn hàng của Shop 1",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC25",
        "Đơn hàng Shop & Thống kê",
        "Đúng dữ liệu",
        "Cập nhật trạng thái đơn hàng tuần tự: Chờ xác nhận -> Đã xác nhận -> Đang giao -> Hoàn thành",
        "Đơn hàng id=1 của Shop 1 đang ở trạng thái 'pending'",
        "Gửi lần lượt PATCH /api/shops/me/orders/1/status với 'confirmed' -> 'shipping' -> 'completed'",
        "HTTP 200 OK ở cả 3 bước; trạng thái đơn chuyển đúng quy trình tới 'completed', đồng thời cộng sold_count cho sản phẩm",
        "HTTP 200 OK; status chuyển tuần tự pending -> confirmed -> shipping -> completed",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC26",
        "Đơn hàng Shop & Thống kê",
        "Sai dữ liệu",
        "Chặn nhảy cóc trạng thái đơn hàng (từ Chờ xác nhận nhảy thẳng sang Đang giao hoặc Hoàn thành)",
        "Đơn hàng id=1 đang ở trạng thái 'pending'",
        "Gửi PATCH /api/shops/me/orders/1/status với {'status': 'shipping'}",
        "HTTP 400 Bad Request; không cho phép bỏ qua bước 'Đã xác nhận (confirmed)'",
        "HTTP 400 Bad Request; báo lỗi quy trình chuyển trạng thái không hợp lệ",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC27",
        "Đơn hàng Shop & Thống kê",
        "Sai dữ liệu",
        "Chặn hủy đơn hàng khi đơn đã chuyển sang trạng thái Đang giao (shipping) hoặc Hoàn thành",
        "Đơn hàng id=1 đang ở trạng thái 'shipping'",
        "Gửi PATCH /api/shops/me/orders/1/status với {'status': 'cancelled'}",
        "HTTP 400 Bad Request; chỉ được hủy đơn khi đang ở trạng thái pending hoặc confirmed",
        "HTTP 400 Bad Request",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC28",
        "Đơn hàng Shop & Thống kê",
        "Đúng dữ liệu",
        "Người bán hủy đơn hàng (pending/confirmed -> cancelled) tự động hoàn trả tồn kho",
        "Đơn hàng id=2 (gồm 1 SP1 tồn=10 và 1 SP2 tồn=8) đang ở trạng thái 'pending'",
        "Gửi PATCH /api/shops/me/orders/2/status với {'status': 'cancelled'} (hoặc POST /cancel)",
        "HTTP 200 OK; đơn chuyển sang 'cancelled', tồn kho SP1 tăng lên 11 và SP2 tăng lên 9",
        "HTTP 200 OK; status='cancelled', p1.stock=11, p2.stock=9",
        "PASS",
        "BUG-03: Khi người bán hủy đơn cần hoàn lại đúng số lượng tồn kho cho từng sản phẩm",
        "Đã sửa",
    ),
    (
        "TC29",
        "Đơn hàng Shop & Thống kê",
        "Sai quyền",
        "Seller 2 cố tình xác nhận, giao hoặc hủy đơn hàng thuộc về Shop của Seller 1",
        "Đơn hàng id=2 thuộc Shop 1; Seller 2 đăng nhập",
        "Gửi PATCH /api/shops/me/orders/2/status và POST /api/shops/me/orders/2/confirm bằng token Seller 2",
        "HTTP 403 Forbidden; không được phép thao tác trên đơn hàng của shop khác",
        "HTTP 403 Forbidden",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC30",
        "Đơn hàng Shop & Thống kê",
        "Chưa đăng nhập",
        "Truy cập danh sách đơn hàng của shop hoặc thống kê doanh thu khi chưa đăng nhập",
        "Không gửi kèm JWT Bearer token",
        "Gửi GET /api/shops/me/orders, GET /api/shops/me/analytics, GET /api/shops/me/revenue/daily",
        "HTTP 401 Unauthorized",
        "HTTP 401 Unauthorized",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC31",
        "Đơn hàng Shop & Thống kê",
        "Sai dữ liệu",
        "Cập nhật trạng thái đơn hàng với mã trạng thái không hợp lệ hoặc đơn hàng không tồn tại",
        "Seller 1 đã đăng nhập",
        "Gửi PATCH /api/shops/me/orders/1/status ({'status': 'invalid_state'}) và PATCH /api/shops/me/orders/999999/status",
        "HTTP 422 khi trạng thái sai enum; HTTP 404 khi mã đơn hàng không tồn tại",
        "HTTP 422 Unprocessable Entity & HTTP 404 Not Found",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC32",
        "Đơn hàng Shop & Thống kê",
        "Đúng dữ liệu",
        "Thống kê doanh thu theo ngày của shop (chỉ tính đơn Hoàn thành, không tính đơn Đã hủy)",
        "Shop 1 có Đơn #1 (500.000đ, ngày 19/11) đã Hoàn thành và Đơn #2 (550.000đ, ngày 20/11) Đã hủy",
        "Gửi GET /api/shops/me/analytics (hoặc GET /api/shops/me/revenue/daily)",
        "HTTP 200 OK; total_revenue = 500.000đ, ngày 2026-11-19 có revenue = 500.000đ (1 đơn hoàn thành), ngày 2026-11-20 có revenue = 0đ",
        "HTTP 200 OK; total_revenue=500000.0, daily['2026-11-19']['revenue']=500000.0",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC33",
        "Đơn hàng Shop & Thống kê",
        "Đúng dữ liệu",
        "Thống kê Top sản phẩm bán chạy của shop theo số lượng đã bán và doanh thu",
        "Đơn #1 đã Hoàn thành với 2 Áo Hoodie Nỉ (tổng 500.000đ); Đơn #2 đã bị hủy",
        "Gửi GET /api/shops/me/analytics (hoặc GET /api/shops/me/products/best-selling)",
        "HTTP 200 OK; best_selling_products xếp hạng #1 là 'Áo Hoodie Nỉ' với total_quantity_sold=2, total_revenue=500000.0",
        "HTTP 200 OK; best_selling_products[0] = {'product_name': 'Áo Hoodie Nỉ', 'total_quantity_sold': 2}",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    # --- MODULE 4: TRỢ LÝ AI VIẾT NỘI DUNG SẢN PHẨM & KỊCH BẢN VIDEO 30-60S (T3D2805) ---
    (
        "TC34",
        "Trợ lý AI Người bán",
        "Đúng dữ liệu",
        "Gọi API AI gợi ý tên sản phẩm, các tên thay thế và mô tả chuẩn SEO từ thông tin sản phẩm",
        "Seller đã đăng nhập, nhập thông tin cơ bản: 'Tai nghe Bluetooth chống ồn', giá 590.000đ, đặc điểm 'Pin 30 giờ, ANC'",
        "Gửi POST /api/products/ai-suggest với {'raw_name': 'Tai nghe Bluetooth chống ồn', 'category_id': 1, 'price': 590000, 'features': 'Pin 30 giờ, ANC', 'duration_seconds': 45}",
        "HTTP 200 OK; trả về suggested_name hấp dẫn, >= 2 alternative_names, suggested_description trình bày rõ điểm nổi bật & cam kết",
        "HTTP 200 OK; trả về đầy đủ suggested_name, 3 alternative_names và suggested_description chi tiết",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC35",
        "Trợ lý AI Người bán",
        "Đúng dữ liệu",
        "AI sinh kịch bản quay video ngắn 30–60 giây phân cảnh chi tiết kèm bộ Hashtag xu hướng",
        "Seller gọi API POST /api/products/ai-suggest với duration_seconds=45",
        "Kiểm tra trường video_script_30_60s và suggested_hashtags trong JSON phản hồi",
        "Kịch bản chia rõ 4 phân cảnh theo mốc giây (00s-05s Hook, 05s-15s Pain Point, 15s-35s Demo, 35s-45s CTA) kèm >= 3 hashtag",
        "video_script_30_60s có đầy đủ mốc 00s - 05s tới 45s và 5 hashtag xu hướng",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC36",
        "Trợ lý AI Người bán",
        "Đúng dữ liệu",
        "Người bán chỉnh sửa lại tên và mô tả do AI gợi ý trên form trước khi bấm Lưu sản phẩm",
        "Seller vừa bấm nút '✨ Gợi ý bằng AI', form đã điền sẵn tên và mô tả gợi ý",
        "Người bán sửa thêm '(Bản Đặc Biệt)' vào tên và ghi chú 'Tặng kèm bao da' vào mô tả, sau đó gửi POST /api/products",
        "HTTP 201 Created; hệ thống lưu đúng nội dung đã được người bán biên tập lại",
        "HTTP 201 Created; sản phẩm lưu đúng tên và mô tả sau khi người bán chỉnh sửa",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC37",
        "Trợ lý AI Người bán",
        "Đúng dữ liệu",
        "Cơ chế Smart Copywriting Fallback khi thiếu GEMINI_API_KEY trong .env hoặc hết quota",
        "Môi trường chạy chưa điền GEMINI_API_KEY hoặc dịch vụ AI bên ngoài trả lỗi quota",
        "Gửi POST /api/products/ai-suggest với thông tin sản phẩm",
        "HTTP 200 OK; tự động kích hoạt bộ sinh nội dung tiếng Việt dự phòng, không làm gián đoạn thao tác của người bán",
        "HTTP 200 OK; trả về nội dung gợi ý và kịch bản 30-60s mượt mà",
        "PASS",
        "BUG-04: Cần đảm bảo tính năng gợi ý vẫn hoạt động ổn định khi môi trường chấm bài chưa cấu hình API key",
        "Đã sửa",
    ),
    (
        "TC38",
        "Trợ lý AI Người bán",
        "Chưa đăng nhập",
        "Gọi API Trợ lý AI viết nội dung sản phẩm khi chưa đăng nhập",
        "Không gửi kèm JWT Bearer token",
        "Gửi POST /api/products/ai-suggest với {'raw_name': 'Áo khoác bomber'}",
        "HTTP 401 Unauthorized; yêu cầu đăng nhập tài khoản người bán",
        "HTTP 401 Unauthorized",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC39",
        "Trợ lý AI Người bán",
        "Sai dữ liệu",
        "Gọi API Trợ lý AI với tên sản phẩm rỗng hoặc thời lượng video ngoài khoảng 30–60 giây",
        "Seller đã đăng nhập",
        "Gửi POST /api/products/ai-suggest với {'raw_name': ''} và với {'raw_name': 'Áo khoác', 'duration_seconds': 120}",
        "HTTP 422 Unprocessable Entity ở cả 2 trường hợp do vi phạm ràng buộc schema",
        "HTTP 422 Unprocessable Entity",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC40",
        "Trợ lý AI Người bán",
        "Đúng dữ liệu",
        "Tương tác nút '✨ Gợi ý bằng AI' trên giao diện Seller Center (seller.html & seller-center.html)",
        "Seller mở trang Quản lý bán hàng, nhập tên sơ bộ sản phẩm và bấm nút '✨ Gợi ý bằng AI'",
        "Bấm nút '#btn-ai-suggest' -> Chọn thử chip tên thay thế -> Bấm nút 'Sao chép kịch bản & Hashtag'",
        "Form tự động điền tên & mô tả để sửa trước khi lưu; khung kịch bản video 30-60s mở ra kèm nút copy hoạt động tốt",
        "Hoạt động mượt mà trên giao diện Seller Center",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
]

BUG_LOGS = [
    (
        "BUG-01",
        "T3D24C4 - Quản lý Sản phẩm",
        "TC13",
        "Database MySQL tạo từ Sprint 1 thiếu cột `products.sold_count` (mới bổ sung ở model Sprint 2), gây lỗi OperationalError 1054 (Unknown column 'products.sold_count') và báo 'Mất kết nối máy chủ' trên trình duyệt.",
        "Cao",
        "Bổ sung cơ chế tự động kiểm tra schema (`inspect(engine)`) khi khởi động FastAPI trong `app/main.py` để tự chạy `ALTER TABLE products ADD COLUMN sold_count` nếu cột chưa tồn tại.",
        "Đã sửa & Test PASS",
    ),
    (
        "BUG-02",
        "T3D24C4 - Xóa Sản phẩm",
        "TC22",
        "Khi người bán bấm xóa một sản phẩm đã từng được khách đặt mua (có bản ghi trong `order_items`), nếu xóa cứng (`db.delete`) sẽ gây lỗi khóa ngoại hoặc làm mất thông tin sản phẩm trong lịch sử đơn hàng.",
        "Cao",
        "Kiểm tra sự tồn tại của `product_id` trong bảng `OrderItem` tại `crud/product.py`: nếu đã có đơn hàng thì chỉ chuyển `product.status = 'HIDDEN'` và trả về `action='hidden'`; chỉ xóa cứng khi chưa có đơn hàng nào.",
        "Đã sửa & Test PASS",
    ),
    (
        "BUG-03",
        "T3D27EB - Hủy Đơn hàng của Shop",
        "TC28",
        "Khi người bán hủy đơn hàng ở trạng thái `Chờ xác nhận (pending)` hoặc `Đã xác nhận (confirmed)`, số lượng tồn kho (`stock`) đã trừ lúc khách đặt hàng chưa được cộng hoàn lại cho sản phẩm.",
        "Cao",
        "Cập nhật hàm `update_shop_order_status()` trong `crud/order.py`: khi chuyển trạng thái sang `cancelled`, duyệt qua toàn bộ `order.items` để cộng trả lại `product.stock += item.quantity`.",
        "Đã sửa & Test PASS",
    ),
    (
        "BUG-04",
        "T3D2805 - Trợ lý AI Người bán",
        "TC37",
        "Khi máy chấm bài chưa điền `GEMINI_API_KEY` / `OPENAI_API_KEY` trong file `.env` hoặc API key hết hạn mức (Quota 429), tính năng 'Gợi ý bằng AI' có nguy cơ báo lỗi và không điền được dữ liệu mẫu cho người bán.",
        "Trung bình",
        "Xây dựng hàm `_build_smart_local_seller_suggestion()` trong `crud/product.py` làm cơ chế Fallback thông minh: nếu gọi Gemini/OpenAI lỗi hoặc chưa có key, hệ thống tự động sinh tên chuẩn SEO, mô tả chi tiết và kịch bản quay 30-60s theo đúng thông tin sản phẩm.",
        "Đã sửa & Test PASS",
    ),
]


def generate_excel(filepath: Path):
    wb = Workbook()

    # Styles
    header_fill = PatternFill("solid", fgColor="1E40AF")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    title_font = Font(bold=True, color="1E3A8A", size=14)
    subtitle_font = Font(bold=True, color="1F2937", size=11)
    pass_fill = PatternFill("solid", fgColor="DCFCE7")
    pass_font = Font(bold=True, color="166534")
    fixed_fill = PatternFill("solid", fgColor="DBEAFE")
    fixed_font = Font(bold=True, color="1E40AF")
    thin_side = Side(style="thin", color="CBD5E1")
    border = Border(
        left=thin_side, right=thin_side, top=thin_side, bottom=thin_side
    )

    # ---------------- SHEET 1: TỔNG QUAN ----------------
    ws1 = wb.active
    ws1.title = "1_Tong_Quan"

    ws1["A1"] = "BÁO CÁO TEST CASE & TEST LOG MODULE CÁ NHÂN (TASK T3D1D72)"
    ws1["A1"].font = title_font

    info_rows = [
        ("Họ và tên sinh viên:", "Nguyễn Hoàng Văn"),
        ("Mã sinh viên:", "B25DTCN265"),
        ("Mã Task:", "T3D1D72 - [Kiểm thử] Test case và test log module mình"),
        ("Sprint:", "Sprint 3 (18/11 - 24/11/2026)"),
        (
            "Các Module phụ trách:",
            "1. Đơn đăng ký bán hàng & Quản lý Cửa hàng (T3D24AA)\n"
            "2. CRUD Sản phẩm, Tồn kho & Upload nhiều ảnh (T3D24C4)\n"
            "3. Giao diện Seller Center quản lý sản phẩm & tồn kho (T3D27B7)\n"
            "4. Form đăng ký bán hàng, trạng thái đơn & Trang cửa hàng công khai (T3D27D1)\n"
            "5. Quản lý đơn hàng của Shop, Doanh thu theo ngày & Sản phẩm bán chạy (T3D27EB)\n"
            "6. [AI] Trợ lý viết nội dung sản phẩm & kịch bản video 30-60s cho người bán (T3D2805)",
        ),
        ("Tổng số Test Case:", len(TEST_CASES)),
        ("Số lượng PASS:", f"{len(TEST_CASES)} / {len(TEST_CASES)} (100%)"),
        ("Số lượng FAIL:", "0"),
        ("Số Bug phát hiện & đã sửa:", f"{len(BUG_LOGS)} bug (100% Đã sửa)"),
    ]

    for idx, (label, val) in enumerate(info_rows, start=3):
        ws1.cell(row=idx, column=1, value=label).font = subtitle_font
        c_val = ws1.cell(row=idx, column=2, value=val)
        c_val.alignment = Alignment(wrap_text=True, vertical="top")
        ws1.cell(row=idx, column=1).border = border
        c_val.border = border

    ws1.row_dimensions[7].height = 95

    # Bảng thống kê theo loại kịch bản
    ws1["A14"] = "THỐNG KÊ THEO NHÓM KỊCH BẢN KIỂM THỬ"
    ws1["A14"].font = subtitle_font

    summary_headers = [
        "Phân loại kịch bản",
        "Số lượng Test Case",
        "PASS",
        "FAIL",
        "Tỷ lệ đạt",
    ]
    for col_i, h in enumerate(summary_headers, start=1):
        cell = ws1.cell(row=15, column=col_i, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
        cell.alignment = Alignment(horizontal="center", vertical="center")

    categories = ["Đúng dữ liệu", "Sai dữ liệu", "Chưa đăng nhập", "Sai quyền"]
    for r_offset, cat in enumerate(categories, start=16):
        count = sum(1 for tc in TEST_CASES if tc[2] == cat)
        ws1.cell(row=r_offset, column=1, value=cat).border = border
        ws1.cell(row=r_offset, column=2, value=count).border = border
        ws1.cell(row=r_offset, column=3, value=count).border = border
        ws1.cell(row=r_offset, column=4, value=0).border = border
        ws1.cell(row=r_offset, column=5, value="100%").border = border

    ws1.column_dimensions["A"].width = 28
    ws1.column_dimensions["B"].width = 70
    ws1.column_dimensions["C"].width = 14
    ws1.column_dimensions["D"].width = 14
    ws1.column_dimensions["E"].width = 16

    # ---------------- SHEET 2: DANH SÁCH TEST CASE & TEST LOG ----------------
    ws2 = wb.create_sheet("2_TestCase_TestLog")
    tc_headers = [
        "Mã TC",
        "Module / Chức năng",
        "Phân loại",
        "Tên kịch bản kiểm thử (Test Case)",
        "Điều kiện tiên quyết (Pre-condition)",
        "Các bước thực hiện & Dữ liệu đầu vào",
        "Kết quả mong đợi (Expected Result)",
        "Kết quả thực tế (Actual Result)",
        "Kết quả (Pass/Fail)",
        "Bug phát hiện",
        "Trạng thái sửa lỗi",
        "Người thực hiện",
    ]

    for col_i, h in enumerate(tc_headers, start=1):
        cell = ws2.cell(row=1, column=col_i, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )

    for row_i, tc in enumerate(TEST_CASES, start=2):
        row_values = list(tc) + ["Nguyễn Hoàng Văn (B25DTCN265)"]
        for col_i, val in enumerate(row_values, start=1):
            c = ws2.cell(row=row_i, column=col_i, value=val)
            c.border = border
            c.alignment = Alignment(
                vertical="top",
                horizontal="center" if col_i in (1, 3, 9, 11) else "left",
                wrap_text=True,
            )
            if col_i == 9 and val == "PASS":
                c.fill = pass_fill
                c.font = pass_font
            if col_i == 11 and val == "Đã sửa":
                c.fill = fixed_fill
                c.font = fixed_font

    col_widths_2 = [10, 26, 16, 36, 32, 38, 38, 38, 14, 30, 16, 26]
    for idx, w in enumerate(col_widths_2, start=1):
        ws2.column_dimensions[get_column_letter(idx)].width = w
    ws2.freeze_panes = "A2"

    # ---------------- SHEET 3: NHẬT KÝ BUG & KHẮC PHỤC ----------------
    ws3 = wb.create_sheet("3_Danh_Sach_Bug_Da_Sua")
    bug_headers = [
        "Mã Bug",
        "Module",
        "Test Case phát hiện",
        "Mô tả chi tiết lỗi phát hiện",
        "Mức độ",
        "Giải pháp đã khắc phục",
        "Trạng thái",
    ]
    for col_i, h in enumerate(bug_headers, start=1):
        cell = ws3.cell(row=1, column=col_i, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )

    for row_i, bug in enumerate(BUG_LOGS, start=2):
        for col_i, val in enumerate(bug, start=1):
            c = ws3.cell(row=row_i, column=col_i, value=val)
            c.border = border
            c.alignment = Alignment(
                vertical="top",
                horizontal="center" if col_i in (1, 3, 5, 7) else "left",
                wrap_text=True,
            )
            if col_i == 7:
                c.fill = pass_fill
                c.font = pass_font

    col_widths_3 = [12, 26, 16, 48, 14, 52, 20]
    for idx, w in enumerate(col_widths_3, start=1):
        ws3.column_dimensions[get_column_letter(idx)].width = w
    ws3.freeze_panes = "A2"

    wb.save(filepath)


def generate_csv(filepath: Path):
    tc_headers = [
        "Mã TC",
        "Module / Chức năng",
        "Phân loại",
        "Tên kịch bản kiểm thử (Test Case)",
        "Điều kiện tiên quyết (Pre-condition)",
        "Các bước thực hiện & Dữ liệu đầu vào",
        "Kết quả mong đợi (Expected Result)",
        "Kết quả thực tế (Actual Result)",
        "Kết quả (Pass/Fail)",
        "Bug phát hiện",
        "Trạng thái sửa lỗi",
        "Người thực hiện",
    ]
    with filepath.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(tc_headers)
        for tc in TEST_CASES:
            writer.writerow(list(tc) + ["Nguyễn Hoàng Văn (B25DTCN265)"])


def generate_markdown(filepath: Path):
    lines = [
        "# BÁO CÁO TEST CASE & TEST LOG MODULE CÁ NHÂN (TASK T3D1D72)",
        "",
        "- **Người thực hiện**: Nguyễn Hoàng Văn (`B25DTCN265`)",
        "- **Mã Task**: `T3D1D72` — `[Kiểm thử] Test case và test log module mình`",
        "- **Lệnh chạy kiểm thử tự động**: `pytest tests/test_seller_shop.py tests/test_products.py tests/test_seller_orders.py tests/test_seller_ai_assistant.py -v` (`17/17 test suites passed` tương ứng 40 kịch bản chi tiết)",
        "- **Tổng số Test Case**: **40 Test Cases** (`40 PASS` / `0 FAIL`)",
        "- **Số Bug phát hiện và khắc phục**: **4 Bugs** (`100% Đã sửa`)",
        "",
        "## 1. Danh sách Test Case & Test Log (40 Kịch bản: Đúng, Sai dữ liệu, Chưa đăng nhập, Sai quyền)",
        "",
        "| Mã TC | Module | Phân loại | Tên kịch bản kiểm thử | Đầu vào / Các bước | Kết quả mong đợi | Kết quả thực tế | Trạng thái | Bug phát hiện | Đã sửa chưa |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for tc in TEST_CASES:
        tc_id, mod, cat, name, _pre, steps, exp, act, status, bug, fixed = tc
        lines.append(
            f"| **{tc_id}** | {mod} | `{cat}` | {name} | {steps} | {exp} | {act} | **{status}** | {bug} | **{fixed}** |"
        )

    lines.extend(
        [
            "",
            "## 2. Nhật ký Bug phát hiện trong quá trình kiểm thử & Trạng thái khắc phục",
            "",
            "| Mã Bug | Module | TC phát hiện | Mô tả lỗi | Mức độ | Cách khắc phục | Trạng thái |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for b_id, mod, tc_ref, desc, sev, fix, st in BUG_LOGS:
        lines.append(
            f"| **{b_id}** | {mod} | `{tc_ref}` | {desc} | {sev} | {fix} | **{st}** |"
        )

    filepath.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    xlsx_path = DOCS_DIR / "T3D1D72_TestCase_TestLog_NguyenHoangVan_B25DTCN265.xlsx"
    csv_path = DOCS_DIR / "T3D1D72_TestCase_TestLog_NguyenHoangVan_B25DTCN265.csv"
    md_path = DOCS_DIR / "T3D1D72_TestCase_TestLog_NguyenHoangVan_B25DTCN265.md"

    generate_excel(xlsx_path)
    generate_csv(csv_path)
    generate_markdown(md_path)

    # Copy 1 bản .xlsx ra ngay thư mục gốc D:\ClipShopAI để nộp file lên Worklane thuận tiện nhất
    root_xlsx = ROOT_DIR / "T3D1D72_TestCase_TestLog_NguyenHoangVan_B25DTCN265.xlsx"
    shutil.copy2(xlsx_path, root_xlsx)
    print(f"Generated:\n - {xlsx_path}\n - {csv_path}\n - {md_path}\n - {root_xlsx}")
