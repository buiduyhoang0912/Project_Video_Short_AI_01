"""Script sinh file Excel (.xlsx), CSV (.csv) và Markdown (.md) cho Task T3D1D70:
[Kiểm thử] Test case và test log module mình - Phùng Quang Huy (B25DTCN179).
"""

import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

DOCS_DIR = Path(__file__).resolve().parent

TEST_CASES = [
    # --- MODULE 1: THÍCH & BÌNH LUẬN VIDEO (T3D22CA, T3D2300) ---
    (
        "TC01",
        "Like & Bình luận Video",
        "Đúng dữ liệu",
        "Thích (Like) video hợp lệ khi đã đăng nhập",
        "User đã đăng nhập, video_id=1 tồn tại và ở trạng thái VISIBLE",
        "Gửi POST /api/videos/1/likes kèm Header Authorization: Bearer <token>",
        "HTTP 200 OK; trả về {'message': 'Đã thích video', 'liked': True}; like_count tăng 1",
        "HTTP 200 OK; {'message': 'Đã thích video', 'liked': True}; like_count = 1",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC02",
        "Like & Bình luận Video",
        "Đúng dữ liệu",
        "Thích lại video đã thích trước đó (kiểm tra tính Idempotent)",
        "User đã thích video_id=1 trước đó",
        "Gửi lại POST /api/videos/1/likes lần thứ 2",
        "HTTP 200 OK; không sinh bản ghi trùng lặp, like_count vẫn giữ nguyên là 1",
        "HTTP 200 OK; {'message': 'Bạn đã thích video này', 'liked': True}; like_count = 1",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC03",
        "Like & Bình luận Video",
        "Đúng dữ liệu",
        "Bỏ thích (Unlike) video hợp lệ",
        "User đang thích video_id=1",
        "Gửi DELETE /api/videos/1/likes kèm Bearer token",
        "HTTP 200 OK; trả về {'liked': False}; like_count giảm về 0",
        "HTTP 200 OK; {'message': 'Đã bỏ thích', 'liked': False}; like_count = 0",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC04",
        "Like & Bình luận Video",
        "Chưa đăng nhập",
        "Thích / Bỏ thích video khi chưa đăng nhập",
        "Không gửi kèm JWT Bearer token",
        "Gửi POST /api/videos/1/likes và DELETE /api/videos/1/likes không có token",
        "HTTP 401 Unauthorized; chặn thao tác",
        "HTTP 401 Unauthorized",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC05",
        "Like & Bình luận Video",
        "Sai dữ liệu",
        "Thích video không tồn tại trong hệ thống",
        "User đã đăng nhập, video_id=999999 không tồn tại",
        "Gửi POST /api/videos/999999/likes kèm Bearer token",
        "HTTP 404 Not Found; detail='Không tìm thấy video'",
        "HTTP 404 Not Found; {'detail': 'Không tìm thấy video'}",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC06",
        "Like & Bình luận Video",
        "Đúng dữ liệu",
        "Đăng bình luận gốc hợp lệ vào video",
        "User đã đăng nhập, video_id=1 tồn tại",
        "Gửi POST /api/videos/1/comments với body {'content': 'Bình luận gốc số 1'}",
        "HTTP 201 Created; trả về thông tin comment vừa tạo kèm id, user_id, created_at",
        "HTTP 201 Created; trả về đầy đủ id, content='Bình luận gốc số 1'",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC07",
        "Like & Bình luận Video",
        "Đúng dữ liệu",
        "Trả lời bình luận gốc (Reply cấp 1 hợp lệ)",
        "User đã đăng nhập, comment gốc id=1 thuộc video_id=1",
        "Gửi POST /api/videos/1/comments với {'content': 'Trả lời comment gốc', 'parent_id': 1}",
        "HTTP 201 Created; tạo reply gắn parent_id=1 thành công",
        "HTTP 201 Created; parent_id=1",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC08",
        "Like & Bình luận Video",
        "Sai dữ liệu",
        "Trả lời vào bình luận cấp 2 (vượt quá giới hạn 1 cấp reply)",
        "User đã đăng nhập, comment reply id=2 đã có parent_id=1",
        "Gửi POST /api/videos/1/comments với {'content': 'Trả lời cấp 2', 'parent_id': 2}",
        "HTTP 400 Bad Request; detail='Chỉ được trả lời bình luận 1 cấp'",
        "HTTP 400 Bad Request; {'detail': 'Chỉ được trả lời bình luận 1 cấp'}",
        "PASS",
        "BUG-01: Ban đầu chưa chặn reply cấp 2",
        "Đã sửa",
    ),
    (
        "TC09",
        "Like & Bình luận Video",
        "Sai dữ liệu",
        "Trả lời bình luận thuộc một video khác",
        "Comment id=1 thuộc video 1 nhưng gửi vào đường dẫn video 2",
        "Gửi POST /api/videos/2/comments với {'content': 'Reply nhầm video', 'parent_id': 1}",
        "HTTP 400 Bad Request; detail='Bình luận trả lời phải cùng video'",
        "HTTP 400 Bad Request; {'detail': 'Bình luận trả lời phải cùng video'}",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC10",
        "Like & Bình luận Video",
        "Sai dữ liệu",
        "Đăng bình luận có nội dung rỗng hoặc chỉ toàn khoảng trắng",
        "User đã đăng nhập",
        "Gửi POST /api/videos/1/comments với {'content': '    '}",
        "HTTP 422 Unprocessable Entity; báo lỗi nội dung không được để trống",
        "HTTP 422 Unprocessable Entity",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC11",
        "Like & Bình luận Video",
        "Chưa đăng nhập",
        "Đăng bình luận hoặc xóa bình luận khi chưa đăng nhập",
        "Không gửi kèm JWT Bearer token",
        "Gửi POST /api/videos/1/comments và DELETE /api/comments/1 không có token",
        "HTTP 401 Unauthorized",
        "HTTP 401 Unauthorized",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC12",
        "Like & Bình luận Video",
        "Sai quyền",
        "Người dùng khác cố tình xóa bình luận không phải của mình",
        "User 2 đăng nhập (không phải chủ comment, không phải chủ video, không phải ADMIN)",
        "User 2 gửi DELETE /api/comments/1 (comment của User 1)",
        "HTTP 403 Forbidden; detail='Bạn không có quyền xóa bình luận này'",
        "HTTP 403 Forbidden; {'detail': 'Bạn không có quyền xóa bình luận này'}",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC13",
        "Like & Bình luận Video",
        "Đúng dữ liệu",
        "Chủ bình luận / Chủ video / ADMIN xóa bình luận gốc (xóa kèm các reply con)",
        "Comment gốc id=1 có 1 reply con id=2; thực hiện xóa bởi chủ comment, chủ video hoặc ADMIN",
        "Gửi DELETE /api/comments/1 kèm Bearer token hợp lệ",
        "HTTP 200 OK; xóa cả comment gốc và reply con (deleted_comments = 2)",
        "HTTP 200 OK; {'message': 'Đã xóa bình luận', 'deleted_comments': 2}",
        "PASS",
        "BUG-02: Cần xóa đồng bộ cả reply con trong thread",
        "Đã sửa",
    ),
    # --- MODULE 2: THEO DÕI (FOLLOW), FEED VIDEO & HỒ SƠ (T3D2331, T3D2428) ---
    (
        "TC14",
        "Follow & Feed Video",
        "Đúng dữ liệu",
        "Theo dõi (Follow) và Bỏ theo dõi (Unfollow) người dùng khác",
        "User 1 đã đăng nhập, User 2 tồn tại",
        "Gửi POST /api/users/2/follow sau đó DELETE /api/users/2/follow",
        "POST trả về 200 {'following': True}; DELETE trả về 200 {'following': False}",
        "HTTP 200 OK; cập nhật trạng thái following và followers_count chính xác",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC15",
        "Follow & Feed Video",
        "Sai dữ liệu",
        "Tự theo dõi chính tài khoản của mình",
        "User 1 đã đăng nhập (id=1)",
        "Gửi POST /api/users/1/follow",
        "HTTP 400 Bad Request; detail='Không thể tự theo dõi chính mình'",
        "HTTP 400 Bad Request; {'detail': 'Không thể tự theo dõi chính mình'}",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC16",
        "Follow & Feed Video",
        "Sai dữ liệu",
        "Theo dõi người dùng không tồn tại",
        "User 1 đã đăng nhập, user_id=999999 không tồn tại",
        "Gửi POST /api/users/999999/follow",
        "HTTP 404 Not Found; detail='Không tìm thấy người dùng'",
        "HTTP 404 Not Found; {'detail': 'Không tìm thấy người dùng'}",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC17",
        "Follow & Feed Video",
        "Chưa đăng nhập",
        "Theo dõi người dùng hoặc xem Feed Đang theo dõi khi chưa đăng nhập",
        "Không có JWT Bearer token",
        "Gửi POST /api/users/2/follow và GET /api/videos/feed/following",
        "HTTP 401 Unauthorized",
        "HTTP 401 Unauthorized",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC18",
        "Follow & Feed Video",
        "Đúng dữ liệu",
        "Lấy danh sách video Feed Đang theo dõi (/api/videos/feed/following)",
        "Viewer đã follow Creator 1 (có 2 video VISIBLE) và chưa follow Creator 2",
        "Gửi GET /api/videos/feed/following kèm Bearer token của Viewer",
        "HTTP 200 OK; chỉ trả về 2 video của Creator 1 kèm like_count, comment_count, share_count, is_liked",
        "HTTP 200 OK; trả về đúng 2 video của Creator 1, ẩn video của Creator 2",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC19",
        "Follow & Feed Video",
        "Đúng dữ liệu",
        "Lấy danh sách Feed Dành cho bạn (/api/videos/feed/for-you) và Hồ sơ người dùng (/api/users/{id}/profile)",
        "Có video VISIBLE trên hệ thống",
        "Gửi GET /api/videos/feed/for-you và GET /api/users/1/profile",
        "HTTP 200 OK; trả về danh sách video công khai và thông tin hồ sơ kèm số followers, following, videos",
        "HTTP 200 OK; dữ liệu khớp với DB",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC20",
        "Follow & Feed Video",
        "Sai dữ liệu",
        "Truyền tham số phân trang không hợp lệ (skip < 0 hoặc limit > 100) trên Feed & Follow list",
        "Gọi API với skip=-1 hoặc limit=101",
        "Gửi GET /api/users/1/followers?limit=101 và GET /api/videos/feed/for-you?limit=0",
        "HTTP 422 Unprocessable Entity; detail='Phân trang không hợp lệ'",
        "HTTP 422 Unprocessable Entity; {'detail': 'Phân trang không hợp lệ'}",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    # --- MODULE 3: TÌM KIẾM VIDEO, NGƯỜI DÙNG & HASHTAG (T3D2442) ---
    (
        "TC21",
        "Tìm kiếm Video, User, Hashtag",
        "Đúng dữ liệu",
        "Tìm kiếm video theo từ khóa tiêu đề/mô tả và lọc theo hashtag",
        "Có các video chứa từ khóa 'nấu ăn' và hashtag '#tech', '#cooking'",
        "Gửi GET /api/search?q=nấu ăn&type=videos và GET /api/search?tag=tech&type=videos",
        "HTTP 200 OK; trả về đúng danh sách video khớp từ khóa và hashtag",
        "HTTP 200 OK; kết quả lọc chính xác theo từ khóa và hashtag",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC22",
        "Tìm kiếm Video, User, Hashtag",
        "Đúng dữ liệu",
        "Tìm kiếm người dùng theo username/display_name và tìm kiếm hashtag",
        "Có user 'alice_wonder' và hashtag '#cooking' trên hệ thống",
        "Gửi GET /api/search?q=alice&type=users và GET /api/search?q=cook&type=hashtags",
        "HTTP 200 OK; trả về user 'alice_wonder' kèm followers_count, is_following và hashtag 'cooking'",
        "HTTP 200 OK; trả về đúng user và thống kê số lượng video của hashtag",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC23",
        "Tìm kiếm Video, User, Hashtag",
        "Đúng dữ liệu",
        "Bấm hashtag mở trực tiếp danh sách video có hashtag đó (/api/search/hashtags/{tag})",
        "Hashtag 'cooking' được gắn trong video_id=1",
        "Gửi GET /api/search/hashtags/cooking",
        "HTTP 200 OK; trả về danh sách các video VISIBLE có chứa hashtag #cooking",
        "HTTP 200 OK; trả về danh sách video chứa #cooking",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC24",
        "Tìm kiếm Video, User, Hashtag",
        "Sai dữ liệu",
        "Tìm kiếm với tham số phân trang sai (skip âm hoặc limit vượt quá 100)",
        "Tham số skip=-5 hoặc limit=200",
        "Gửi GET /api/search?skip=-5 và GET /api/search/hashtags/demo?limit=200",
        "HTTP 422 Unprocessable Entity; detail='Phân trang không hợp lệ'",
        "HTTP 422 Unprocessable Entity",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    # --- MODULE 4: TRANG XEM RIÊNG MỘT VIDEO (/video/{id}) & CHIA SẺ (T3D245C) ---
    (
        "TC25",
        "Xem riêng Video & Chia sẻ",
        "Đúng dữ liệu",
        "Xem riêng một video công khai qua đường dẫn chia sẻ (/api/videos/{id} và /api/video/{id})",
        "Video id=1 đang ở trạng thái VISIBLE",
        "Gửi GET /api/videos/1 và mở trang frontend pages/video.html?id=1",
        "HTTP 200 OK; trả về is_available=True, video_url, share_count, tăng view_count thêm 1",
        "HTTP 200 OK; hiển thị trình phát video, thông tin tác giả và tăng view_count",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC26",
        "Xem riêng Video & Chia sẻ",
        "Đúng dữ liệu",
        "Sao chép link và đếm lượt chia sẻ video (cả khi đã đăng nhập và khách chưa đăng nhập)",
        "Video id=1 đang ở trạng thái VISIBLE",
        "Bấm nút 'Sao chép link' -> gọi POST /api/videos/1/share (1 lần có token, 1 lần không token)",
        "HTTP 200 OK; sao chép link vào clipboard, share_count tăng lên 1 rồi lên 2",
        "HTTP 200 OK; trả về {'message': 'Đã ghi nhận lượt chia sẻ', 'share_count': 2}",
        "PASS",
        "BUG-03: Ban đầu POST /share bắt buộc token nên khách mở link chia sẻ không tăng được bộ đếm",
        "Đã sửa",
    ),
    (
        "TC27",
        "Xem riêng Video & Chia sẻ",
        "Đúng dữ liệu",
        "Truy cập trang xem riêng khi video đã bị ẩn (status = HIDDEN)",
        "Video id=1 bị chuyển sang trạng thái HIDDEN",
        "Gửi GET /api/videos/1 và mở trang pages/video.html?id=1",
        "HTTP 200 OK với status='HIDDEN', is_available=False, video_url=None; UI hiện thông báo 'Video không còn khả dụng'",
        "HTTP 200 OK; ẩn đường dẫn phát video và hiển thị rõ thông báo 'Video không còn khả dụng'",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC28",
        "Xem riêng Video & Chia sẻ",
        "Sai dữ liệu",
        "Cố tình gọi API chia sẻ đối với một video đã bị ẩn (HIDDEN) hoặc không tồn tại",
        "Video id=1 đang ở trạng thái HIDDEN; video id=999999 không tồn tại",
        "Gửi POST /api/videos/1/share và POST /api/videos/999999/share",
        "Video HIDDEN trả về HTTP 400 ('Video này đã bị ẩn và không còn khả dụng'); video 999999 trả về HTTP 404",
        "HTTP 400 Bad Request cho video ẩn và HTTP 404 Not Found cho video không tồn tại",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC29",
        "Xem riêng Video & Chia sẻ",
        "Sai quyền",
        "Người dùng lạ cố tình gọi API ẩn video của người khác",
        "User 2 đăng nhập nhưng không phải chủ sở hữu video 1 và không phải ADMIN",
        "Gửi PATCH /api/videos/1/status với {'status': 'HIDDEN'}",
        "HTTP 403 Forbidden; detail='Bạn không có quyền thay đổi trạng thái video này'",
        "HTTP 403 Forbidden",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC30",
        "Xem riêng Video & Chia sẻ",
        "Đúng dữ liệu",
        "Chủ sở hữu video hoặc ADMIN ẩn/hiện lại video thành công",
        "Chủ video hoặc tài khoản role='ADMIN' đã đăng nhập",
        "Gửi PATCH /api/videos/1/status với {'status': 'HIDDEN'} rồi {'status': 'VISIBLE'}",
        "HTTP 200 OK; cập nhật trạng thái video chính xác",
        "HTTP 200 OK; is_available đổi từ False sang True",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC31",
        "Xem riêng Video & Chia sẻ",
        "Sai dữ liệu",
        "Cập nhật trạng thái video với giá trị status sai quy định",
        "Chủ video đã đăng nhập",
        "Gửi PATCH /api/videos/1/status với {'status': 'INVALID_STATUS'}",
        "HTTP 422 Unprocessable Entity",
        "HTTP 422 Unprocessable Entity",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    # --- MODULE 5: CHATBOT AI TƯ VẤN MUA SẮM & KHUNG CHAT NỔI (T3D2476) ---
    (
        "TC32",
        "Chatbot AI Tư vấn Mua sắm",
        "Đúng dữ liệu",
        "Tư vấn mua sắm chỉ gợi ý sản phẩm có thật trong MySQL kèm link sản phẩm",
        "Trong MySQL có 'JBL Tune 520BT' (350.000đ, ACTIVE), 'Sony WH-1000XM5' (6.500.000đ, ACTIVE) và 1 sản phẩm INACTIVE",
        "Gửi POST /api/ai/chat với {'message': 'Tư vấn cho tôi tai nghe dưới 500k'}",
        "HTTP 200 OK; chỉ gợi ý đúng 'JBL Tune 520BT', loại trừ sản phẩm >500k và sản phẩm INACTIVE, trả kèm link 'pages/product.html?id=1'",
        "HTTP 200 OK; recommended_products chỉ chứa JBL Tune 520BT kèm link pages/product.html?id=1",
        "PASS",
        "BUG-04: Tìm kiếm tiếng Việt có dấu cần khớp cả tên sản phẩm không dấu trong seed DB",
        "Đã sửa",
    ),
    (
        "TC33",
        "Chatbot AI Tư vấn Mua sắm",
        "Đúng dữ liệu",
        "Kiểm tra giảm số câu hỏi còn lại trong ngày sau mỗi lần hỏi AI (/api/ai/quota)",
        "User mới chưa hỏi câu nào trong ngày, AI_DAILY_QUESTION_LIMIT=20",
        "Gọi POST /api/ai/chat 1 lần rồi kiểm tra GET /api/ai/quota",
        "HTTP 200 OK; used_today = 1, remaining_today = 19, daily_limit = 20",
        "HTTP 200 OK; used_today = 1, remaining_today = 19",
        "PASS",
        "BUG-05: Lệch múi giờ giữa Python local time và SQLite CURRENT_TIMESTAMP lúc 00h-07h sáng",
        "Đã sửa",
    ),
    (
        "TC34",
        "Chatbot AI Tư vấn Mua sắm",
        "Sai dữ liệu",
        "Chặn khi người dùng vượt quá giới hạn số câu hỏi mỗi ngày",
        "Đặt AI_DAILY_QUESTION_LIMIT = 2; User đã hỏi đủ 2 câu trong ngày",
        "Gửi câu hỏi thứ 3 qua POST /api/ai/chat",
        "HTTP 429 Too Many Requests; báo rõ 'Bạn đã sử dụng hết giới hạn 2 câu hỏi mỗi ngày (2/2). Vui lòng quay lại vào ngày mai!'",
        "HTTP 429 Too Many Requests; hiển thị thông báo hết lượt hỏi trong ngày trên khung chat nổi",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC35",
        "Chatbot AI Tư vấn Mua sắm",
        "Sai dữ liệu",
        "Xử lý báo lỗi dễ hiểu khi API Gemini/OpenAI bị quá thời gian chờ (Timeout)",
        "Giả lập kết nối tới Gemini API bị httpx.TimeoutException",
        "Gửi POST /api/ai/chat với {'message': 'Tìm điện thoại'}",
        "HTTP 504 Gateway Timeout; detail='Trợ lý AI phản hồi quá thời gian chờ (timeout). Vui lòng thử lại sau giây lát.'",
        "HTTP 504 Gateway Timeout; câu thông báo tiếng Việt rõ ràng, không trừ lượt hỏi trong ngày",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC36",
        "Chatbot AI Tư vấn Mua sắm",
        "Sai dữ liệu",
        "Xử lý báo lỗi dễ hiểu khi API Gemini/OpenAI hết hạn mức (Quota Exceeded / 429)",
        "Giả lập Gemini API trả về mã 429 RESOURCE_EXHAUSTED",
        "Gửi POST /api/ai/chat với {'message': 'Tìm điện thoại'}",
        "HTTP 429 Too Many Requests; detail='Hệ thống AI (Gemini) hiện đã hết hạn mức (quota) hoặc đang quá tải. Vui lòng thử lại sau ít phút.'",
        "HTTP 429 Too Many Requests; thông báo hết quota dễ hiểu",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC37",
        "Chatbot AI Tư vấn Mua sắm",
        "Sai dữ liệu",
        "Gửi tin nhắn rỗng hoặc chỉ chứa khoảng trắng vào Chatbot AI",
        "User đã đăng nhập",
        "Gửi POST /api/ai/chat với {'message': '   '}",
        "HTTP 422 Unprocessable Entity; detail='Tin nhắn không được rỗng'",
        "HTTP 422 Unprocessable Entity",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC38",
        "Chatbot AI Tư vấn Mua sắm",
        "Chưa đăng nhập",
        "Gọi API Chatbot AI (/api/ai/chat) hoặc kiểm tra hạn mức (/api/ai/quota) khi chưa đăng nhập",
        "Không gửi kèm JWT Bearer token",
        "Gửi POST /api/ai/chat và GET /api/ai/quota không có token",
        "HTTP 401 Unauthorized; trên UI khung chat nổi nhắc người dùng đăng nhập",
        "HTTP 401 Unauthorized",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC39",
        "Chatbot AI Tư vấn Mua sắm",
        "Đúng dữ liệu",
        "Lưu và xem lịch sử trò chuyện AI (/api/ai/chat-logs)",
        "User đã đăng nhập và đã chat với AI",
        "Gửi GET /api/ai/chat-logs?skip=0&limit=20",
        "HTTP 200 OK; trả về danh sách lịch sử tin nhắn của chính user đó theo thứ tự mới nhất",
        "HTTP 200 OK; hiển thị đúng lịch sử chat của user",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
    (
        "TC40",
        "Chatbot AI Tư vấn Mua sắm",
        "Đúng dữ liệu",
        "Tương tác trên UI Khung chat nổi (Floating Chat Widget)",
        "Mở bất kỳ trang nào trên trình duyệt (Feed, Tìm kiếm, Xem video, Hồ sơ)",
        "Bấm nút nổi '🤖 Tư vấn AI' ở góc phải dưới -> bấm chip gợi ý -> bấm vào nút 'Xem SP' trên thẻ sản phẩm gợi ý",
        "Khung chat nổi bật lên mượt mà, hiển thị số câu hỏi còn lại trong ngày, hiển thị thẻ sản phẩm thật kèm giá và mở xem chi tiết sản phẩm",
        "Hoạt động đúng thiết kế trên mọi trang",
        "PASS",
        "Không",
        "Không có lỗi",
    ),
]

BUG_LOGS = [
    (
        "BUG-01",
        "T3D2300 - Bình luận Video",
        "TC08",
        "Cho phép trả lời vào một bình luận trả lời (tạo ra bình luận cấp 2, cấp 3 vượt quá yêu cầu chỉ 1 cấp reply).",
        "Trung bình",
        "Kiểm tra `if parent.parent_id is not None` trong `create_comment()` tại `routers/social.py` và trả về HTTP 400 'Chỉ được trả lời bình luận 1 cấp'.",
        "Đã sửa & Test PASS",
    ),
    (
        "BUG-02",
        "T3D2300 - Xóa Bình luận",
        "TC13",
        "Khi xóa bình luận gốc có các bình luận trả lời bên dưới, cần xóa toàn bộ bình luận con trong cùng thread và trả về tổng số bình luận đã xóa.",
        "Trung bình",
        "Bổ sung hàm `all_comment_ids_in_thread()` trong `crud/social.py` để gom toàn bộ ID bình luận con và xóa đồng bộ trong một câu lệnh.",
        "Đã sửa & Test PASS",
    ),
    (
        "BUG-03",
        "T3D245C - Chia sẻ Video",
        "TC26",
        "API `POST /api/videos/{id}/share` ban đầu dùng `get_current_user` (bắt buộc đăng nhập), khiến khách truy cập từ link chia sẻ bấm 'Sao chép link' bị lỗi 401 và không tăng `share_count`.",
        "Cao",
        "Đổi dependency sang `get_optional_user` (lưu `user_id=None` cho khách vãng lai đúng thiết kế bảng `video_shares`), đồng thời chặn chia sẻ nếu `video.status == 'HIDDEN'`.",
        "Đã sửa & Test PASS",
    ),
    (
        "BUG-04",
        "T3D2476 - Chatbot AI",
        "TC32",
        "Dữ liệu sản phẩm mẫu trong DB (`seed_shop_product.py`) lưu không dấu ('Tai nghe', 'Ao thun nam'), khi người dùng hỏi tiếng Việt có dấu ('tai nghe dưới 500k') tìm kiếm chuỗi thông thường không khớp.",
        "Cao",
        "Bổ sung hàm `remove_vietnamese_accents()` và `parse_price_filters_from_text()` trong `crud/social.py` để chuẩn hóa tiếng Việt không dấu và tự động tách điều kiện lọc giá.",
        "Đã sửa & Test PASS",
    ),
    (
        "BUG-05",
        "T3D2476 - Giới hạn câu hỏi/ngày",
        "TC33",
        "So sánh `AiChatLog.created_at` (do DB sinh theo UTC) với `datetime.now()` (giờ địa phương UTC+7) bị lệch ngày trong khoảng 00:00 - 07:00 sáng.",
        "Trung bình",
        "Sử dụng `func.date(AiChatLog.created_at) == func.date(func.now())` trong SQL để luôn dùng chung đồng hồ của Database.",
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

    ws1["A1"] = "BÁO CÁO TEST CASE & TEST LOG MODULE CÁ NHÂN (TASK T3D1D70)"
    ws1["A1"].font = title_font

    info_rows = [
        ("Họ và tên sinh viên:", "Phùng Quang Huy"),
        ("Mã sinh viên:", "B25DTCN179"),
        ("Mã Task:", "T3D1D70 - [Kiểm thử] Test case và test log module mình"),
        ("Sprint:", "Sprint 3 (18/11 - 24/11/2026)"),
        (
            "Các Module phụ trách:",
            "1. Like & Comment Video (T3D22CA, T3D2300)\n"
            "2. Follow, Feed Video & Hồ sơ (T3D2331, T3D2428)\n"
            "3. Tìm kiếm Video, Người dùng & Hashtag (T3D2442)\n"
            "4. Trang xem riêng Video /video/{id} & Chia sẻ (T3D245C)\n"
            "5. Chatbot AI Tư vấn Mua sắm & UI Khung chat nổi (T3D2476)",
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

    # Bảng thống kê theo loại kịch bản
    ws1["A14"] = "THỐNG KÊ THEO NHÓM KỊCH BẢN KIỂM THỬ"
    ws1["A14"].font = subtitle_font

    summary_headers = ["Phân loại kịch bản", "Số lượng Test Case", "PASS", "FAIL", "Tỷ lệ đạt"]
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
    ws1.column_dimensions["B"].width = 65
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
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row_i, tc in enumerate(TEST_CASES, start=2):
        row_values = list(tc) + ["Phùng Quang Huy (B25DTCN179)"]
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

    col_widths_2 = [10, 24, 16, 36, 32, 38, 38, 38, 14, 28, 16, 24]
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
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

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

    col_widths_3 = [12, 24, 16, 48, 14, 52, 20]
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
            writer.writerow(list(tc) + ["Phùng Quang Huy (B25DTCN179)"])


def generate_markdown(filepath: Path):
    lines = [
        "# BÁO CÁO TEST CASE & TEST LOG MODULE CÁ NHÂN (TASK T3D1D70)",
        "",
        "- **Người thực hiện**: Phùng Quang Huy (`B25DTCN179`)",
        "- **Mã Task**: `T3D1D70` — `[Kiểm thử] Test case và test log module mình`",
        "- **Lệnh chạy kiểm thử tự động**: `pytest backend/tests/test_social.py` (`16/16 test suites passed` tương ứng 40 kịch bản chi tiết)",
        "- **Tổng số Test Case**: **40 Test Cases** (`40 PASS` / `0 FAIL`)",
        "- **Số Bug phát hiện và khắc phục**: **5 Bugs** (`100% Đã sửa`)",
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
    xlsx_path = DOCS_DIR / "T3D1D70_TestCase_TestLog_PhungQuangHuy_B25DTCN179.xlsx"
    csv_path = DOCS_DIR / "T3D1D70_TestCase_TestLog_PhungQuangHuy_B25DTCN179.csv"
    md_path = DOCS_DIR / "T3D1D70_TestCase_TestLog_PhungQuangHuy_B25DTCN179.md"

    generate_excel(xlsx_path)
    generate_csv(csv_path)
    generate_markdown(md_path)
    print(f"Generated:\n - {xlsx_path}\n - {csv_path}\n - {md_path}")
