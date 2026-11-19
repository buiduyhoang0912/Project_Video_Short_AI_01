# SLIDE & KỊCH BẢN DEMO BẢO VỆ DỰ ÁN CLIPSHOP AI (TASK T3D1DB8)

- **Sinh viên thực hiện**: Phùng Quang Huy (`B25DTCN179`)
- **Mã Task**: `T3D1DB8` — `[Hoàn thiện] Ghép nối toàn hệ thống, sửa bug, slide và demo`
- **File Slide PowerPoint (`.pptx`)**: `backend/docs/T3D1DB8_Slide_BaoVe_PhungQuangHuy_B25DTCN179.pptx`

---

## Slide 1: BÁO CÁO BẢO VỆ DỰ ÁN: CLIPSHOP AI
*Module Tương tác Mạng xã hội, Tìm kiếm, Chia sẻ Video & Chatbot AI Tư vấn Mua sắm
Sinh viên thực hiện: Phùng Quang Huy (B25DTCN179) · Mã Task: T3D1DB8*

- Đề tài: Nền tảng Video ngắn kết hợp Thương mại điện tử & AI (ClipShop AI)
- Vai trò cá nhân: Phụ trách toàn bộ phân hệ Tương tác Mạng xã hội (Social), Feed Video, Tìm kiếm, Chia sẻ & Chatbot AI
- Công nghệ sử dụng: FastAPI, SQLAlchemy 2.0, MySQL, JWT Auth, Gemini/OpenAI API, HTML5/CSS3/JS (Axios)
- Trạng thái tích hợp: Đã ghép nối xuyên suốt từ Đăng nhập -> Xem Feed -> Tương tác -> Tìm kiếm -> Chia sẻ -> Tư vấn Mua sắm AI

## Slide 2: 1. TỔNG QUAN CÁC MODULE ĐẢM NHẬN (SPRINT 1 - 3)
*Phùng Quang Huy (B25DTCN179) — 7 Task chức năng & kiểm thử hoàn chỉnh*

- 1. T3D22CA & T3D2300: Thiết kế bảng CSDL (likes, comments, follows, video_shares, ai_chat_logs) & API Thích, Bình luận 1 cấp, Phân quyền xóa
- 2. T3D2331 & T3D2428: API & Giao diện Theo dõi (Follow/Unfollow), Feed Video Dành cho bạn / Đang theo dõi & Trang Hồ sơ người dùng
- 3. T3D2442 & T3D2BE1: Hệ thống Tìm kiếm Video, Người dùng, Hashtag & Bảng xếp hạng Hashtag thịnh hành 7 ngày
- 4. T3D245C: Trang xem riêng một video (/video/{id}), nút Sao chép link, đếm lượt chia sẻ & xử lý video bị ẩn
- 5. T3D2476: Chatbot AI Tư vấn Mua sắm (Gemini/OpenAI) chỉ gợi ý sản phẩm thật trong MySQL kèm link & UI khung chat nổi
- 6. T3D1D70 & T3D1DB8: Bộ 40 Test Cases (100% Pass), sửa 6 bug tích hợp & ghép nối toàn hệ thống

## Slide 3: 2. THIẾT KẾ CƠ SỞ DỮ LIỆU PHÂN HỆ SOCIAL & AI
*5 bảng dữ liệu chuẩn hóa với ràng buộc toàn vẹn (Constraints & Cascade)*

- Bảng `likes`: Khóa duy nhất `uq_likes_user_video(user_id, video_id)` chống bấm thích trùng lặp (Idempotent)
- Bảng `comments`: Hỗ trợ `parent_id` tự tham chiếu cho phép trả lời bình luận đúng 1 cấp, xóa đồng bộ cả thread
- Bảng `follows`: Ràng buộc `uq_follows_pair` và `ck_follow_not_self (follower_id <> following_id)` chống tự follow chính mình
- Bảng `video_shares`: Lưu lượt chia sẻ (`video_id`, `user_id` nullable) cho cả người dùng đăng nhập và khách mở link chia sẻ
- Bảng `ai_chat_logs`: Lưu lịch sử hội thoại (`role IN ('user','assistant')`) và dùng để tính giới hạn số câu hỏi mỗi ngày

## Slide 4: 3. LUỒNG TƯƠNG TÁC VIDEO, FOLLOW & FEED CUỘN DỌC
*Trải nghiệm mượt mà theo phong cách TikTok / Reels (T3D2300, T3D2331, T3D2428)*

- Feed Video cuộn dọc (`pages/feed.html`): Tự động phát/tạm dừng bằng IntersectionObserver khi video vào khung nhìn
- Hai chế độ xem: 'Dành cho bạn' (`/api/videos/feed/for-you`) và 'Đang theo dõi' (`/api/videos/feed/following`)
- Thả tim (Like/Unlike): Cập nhật số lượng ngay lập tức trên giao diện (Optimistic UI) và đồng bộ về MySQL
- Bảng Bình luận trượt lên (Slide-up Bottom Sheet): Hỗ trợ trả lời 1 cấp và phân quyền xóa (Chủ comment, Chủ video, ADMIN)
- Trang Hồ sơ (`pages/profile.html`): Hiển thị thống kê Đang theo dõi, Người theo dõi, lưới Video đã đăng & nút Follow

## Slide 5: 4. TÌM KIẾM ĐA NĂNG & BẢNG XẾP HẠNG HASHTAG 7 NGÀY
*Khám phá nội dung nhanh chóng theo từ khóa và xu hướng (T3D2442, T3D2BE1)*

- API `/api/search`: Tìm kiếm đồng thời hoặc theo từng tab (🎥 Video, 👤 Người dùng, 🏷️ Hashtag) có phân trang
- Lọc theo Hashtag (`/api/search/hashtags/{tag}`): Bấm vào bất kỳ thẻ `#hashtag` nào sẽ mở ngay danh sách video có hashtag đó
- Bảng xếp hạng Hashtag thịnh hành 7 ngày (`/api/search/trending-hashtags?days=7`):
-   • Tổng hợp các video VISIBLE đăng mới hoặc có phát sinh tương tác (Like, Comment, Share) trong 7 ngày gần nhất
-   • Xếp hạng Top #1, #2, #3... hiển thị trực quan đầu trang Tìm kiếm kèm số video và tổng lượt tương tác

## Slide 6: 5. TRANG XEM RIÊNG MỘT VIDEO (/video/{id}) & CHIA SẺ
*Liên kết chia sẻ độc lập, đếm lượt chia sẻ & bảo vệ video ẩn (T3D245C)*

- Trang xem riêng (`pages/video.html?id={id}`): Dành riêng cho liên kết chia sẻ, hiển thị trình phát 9:16, thông tin tác giả và bình luận
- Nút Sao chép Link & Đếm lượt chia sẻ (`POST /api/videos/{id}/share`):
-   • Tự động sao chép đường dẫn vào bộ nhớ tạm (Clipboard) và tăng bộ đếm `share_count` ngay trên giao diện
- Trạng thái Video bị ẩn (`status = HIDDEN`):
-   • Tự động ẩn nguồn phát `video_url` ở tầng API và hiển thị thông báo rõ ràng '🚫 Video không còn khả dụng'
-   • Hỗ trợ nút Ẩn/Hiện nhanh trên giao diện dành riêng cho Chủ sở hữu video hoặc Quản trị viên (ADMIN)

## Slide 7: 6. CHATBOT AI TƯ VẤN MUA SẮM & KHUNG CHAT NỔI
*Kết nối Gemini/OpenAI với dữ liệu sản phẩm thật trong MySQL (T3D2476)*

- API `POST /api/ai/chat`: Đọc khóa `GEMINI_API_KEY` / `OPENAI_API_KEY` từ `.env`, hỗ trợ Function Calling `search_products_in_mysql`
- Chống ảo giác (Anti-Hallucination): AI chỉ gợi ý các sản phẩm ACTIVE còn hàng trong MySQL và luôn đính kèm link `pages/product.html?id={id}`
- Hỗ trợ lọc tiếng Việt có dấu / không dấu và tự động nhận diện khoảng giá tự nhiên (vd: 'tai nghe dưới 500k')
- Kiểm soát hạn mức & Lỗi: Giới hạn số câu hỏi mỗi ngày (`AI_DAILY_QUESTION_LIMIT=20`), báo lỗi dễ hiểu khi Timeout (504) hoặc hết Quota (429)
- UI Khung chat nổi (`🤖 Tư vấn AI`): Hiển thị ở góc phải dưới mọi trang, có chip gợi ý nhanh và thẻ sản phẩm bấm xem trực tiếp

## Slide 8: 7. GHÉP NỐI TOÀN HỆ THỐNG & SỬA BUG TÍCH HỢP (T3D1DB8)
*Kiểm thử 40 kịch bản (100% Pass) & Khắc phục 6 lỗi tích hợp liên module*

- 1. Sửa lỗi tương thích Model `Product`: Bổ sung property `thumbnail_url` và `updated_at` giúp API `/api/products/{id}` chạy xuyên suốt với AI Chatbot
- 2. Sửa lỗi chuẩn hóa tiếng Việt trong AI Search: Khớp từ khóa có dấu của người dùng với tên sản phẩm không dấu trong seed DB
- 3. Sửa lỗi đồng bộ múi giờ giới hạn câu hỏi AI mỗi ngày: Dùng `func.date(created_at) == func.date(func.now())` trong SQL
- 4. Sửa lỗi đếm lượt chia sẻ cho khách: Cho phép khách mở link chia sẻ ghi nhận lượt share (`user_id = NULL`)
- 5. Kiểm thử tự động: 18/18 bộ test `pytest` (40 Test Cases: Đúng, Sai dữ liệu, Chưa đăng nhập 401, Sai quyền 403) đạt 100% PASS

## Slide 9: 8. KỊCH BẢN DEMO BẢO VỆ TRỰC TIẾP (5 PHÚT)
*Luồng trải nghiệm xuyên suốt từ góc nhìn người dùng thực tế*

- Bước 1 (Feed & Tương tác - 1p): Đăng nhập -> Mở Feed Video -> Thả tim, đăng bình luận & trả lời 1 cấp, bấm Follow tác giả -> Chuyển sang tab 'Đang theo dõi'
- Bước 2 (Tìm kiếm & Hashtag thịnh hành - 1p): Mở trang Tìm kiếm -> Xem Bảng xếp hạng Hashtag 7 ngày -> Bấm vào hashtag Top #1 để lọc video
- Bước 3 (Chia sẻ & Xem riêng Video - 1.5p): Bấm vào 1 video -> Mở trang `/video/{id}` -> Bấm '📋 Sao chép link' (tăng lượt chia sẻ) -> Bấm 'Ẩn video' để demo màn hình 'Video không còn khả dụng'
- Bước 4 (Chatbot AI Tư vấn Mua sắm - 1.5p): Mở khung chat nổi '🤖 Tư vấn AI' -> Hỏi 'Tư vấn tai nghe dưới 500k' -> Xem thẻ sản phẩm thật kèm giá & bấm mở chi tiết sản phẩm
