# SLIDE BÁO CÁO BẢO VỆ DỰ ÁN: CLIPSHOP AI (TASK T3D1DB6)

- **Sinh viên thực hiện**: Phạm Công Khải Hoàn (`B25DTCN092`)
- **Mã Task**: `T3D1DB6` — `[Hoàn thiện] Ghép nối toàn hệ thống, sửa bug, slide và demo`
- **Sprint**: `Sprint 3 (18/11 - 24/11/2026)`

## Slide 1: BÁO CÁO BẢO VỆ DỰ ÁN: CLIPSHOP AI (TOKFLOW)
*Phân hệ Video Ngắn, Trình phát Feed cuộn dọc, Quản lý Video, Gắn sản phẩm E-commerce & Cloudflare R2 - Sinh viên thực hiện: PHẠM CÔNG KHẢI HOÀN (B25DTCN092) · Task hoàn thiện: T3D1DB6*

- Đề tài: Nền tảng Video ngắn kết hợp Thương mại điện tử & Trợ lý AI (ClipShop AI / TokFlow)
- Vai trò phụ trách chính trong nhóm:
-   • T3D2235: Trang đăng video, tải file MP4/WebM <=100MB, trích xuất thời lượng ffprobe, custom thumbnail, thanh tiến trình upload
-   • T3D2202: Feed video cuộn dọc toàn màn hình TikTok-style, tự động phát/dừng theo viewport, đồng bộ âm thanh loa, phím tắt điều hướng
-   • T3D226A: Lưới video 3 cột trên hồ sơ cá nhân, trang Quản lý video của tôi (my-videos.html), sửa mô tả, ẩn/hiện, xóa video kèm dọn dẹp
-   • T3D2296: Người bán gắn tối đa 3 sản phẩm của shop mình vào video, nút giỏ hàng & pill sản phẩm trên Feed, Bottom Sheet mở chi tiết SP
-   • T3D2BC7 (Bonus 10 điểm): Lưu trữ video và ảnh trên Cloudflare R2 qua S3 API boto3, hỗ trợ đa tầng LocalStorage & R2Storage
-   • T3D1D6E: Thiết kế bộ kiểm thử toàn diện (40 Test Cases, 40 Test Logs PASS 100%, khắc phục 5 lỗi phát hiện)
- Công nghệ áp dụng: FastAPI, SQLAlchemy 2.0, Boto3 (Cloudflare R2), HTML5 Video, IntersectionObserver, Axios, Vanilla JS

---

## Slide 2: 1. TRANG ĐĂNG VIDEO & XỬ LÝ ĐA PHƯƠNG TIỆN (TASK T3D2235)
*Kiểm soát tính toàn vẹn file video, tự động trích xuất metadata và tối ưu hóa trải nghiệm người dùng*

- Xác thực và tiền xử lý file video an toàn (prepare_video_upload):
-   • Kiểm soát dung lượng: Giới hạn tối đa 100MB, chặn trả lời 413 Payload Too Large nếu vượt quá
-   • Kiểm tra tính hợp lệ: Xác thực đuôi file (.mp4, .webm) và kiểm tra cấu trúc video bằng ffprobe/magic bytes; chặn 422 nếu sai cấu trúc
-   • Tự động trích xuất metadata: Sử dụng ffprobe đọc thời lượng chính xác theo giây (duration_seconds)
- Ảnh bìa thumbnail linh hoạt:
-   • Tùy chọn ảnh bìa: Cho phép người dùng upload ảnh bìa tùy chỉnh (JPG, PNG, WebP) hoặc tự động sinh từ video
- Trải nghiệm người dùng mượt mà trên frontend (upload.html):
-   • Thanh tiến trình upload thời gian thực (Progress Bar) thông qua Axios onUploadProgress từ 0% -> 100%
-   • Trình xem trước (Preview) video và thumbnail ngay khi chọn tệp trước khi bấm Đăng tải

---

## Slide 3: 2. FEED VIDEO CUỘN DỌC TIKTOK-STYLE (TASK T3D2202)
*Trải nghiệm lướt video ngắn chuẩn hiện đại, tối ưu tài nguyên và quản lý vòng đời phát video*

- API Feed Dành cho bạn (/api/videos/feed) & Phân trang cuộn dọc:
-   • Phân trang cursor-based thông minh: Ưu tiên video mới nhất và nhiều lượt xem nhất, lọc bỏ toàn bộ video bị ẩn (HIDDEN)
- Tối ưu hóa trình phát video và tiết kiệm băng thông (IntersectionObserver):
-   • Tự động phát video trung tâm: Chỉ phát (play()) video đang chiếm >= 70% viewport, lập tức tạm dừng (pause()) toàn bộ video khác
-   • Triệt tiêu hoàn toàn lỗi âm thanh chồng lấn: Đảm bảo tại một thời điểm chỉ có duy nhất 1 video phát ra tiếng
- Đồng bộ trải nghiệm người dùng xuyên suốt:
-   • Quản lý trạng thái âm thanh toàn cục: Bật/Tắt âm thanh (Mute/Unmute) được ghi nhớ và áp dụng tự động cho các video tiếp theo
-   • Hỗ trợ phím tắt tiện lợi: Phím Mũi tên Lên/Xuống để chuyển video, Phím Space để Tạm dừng/Tiếp tục

---

## Slide 4: 3. LƯỚI VIDEO HỒ SƠ & QUẢN LÝ VIDEO CỦA TÔI (TASK T3D226A)
*Quản trị danh mục video cá nhân, phân quyền thao tác chặt chẽ và bảo vệ tính riêng tư*

- Hiển thị lưới video 3 cột trên hồ sơ người dùng (profile.html):
-   • Hiển thị trực quan: Ảnh bìa, biểu tượng lượt xem (view_count) định dạng chuẩn tiếng Việt và thời lượng video
-   • Bảo vệ quyền riêng tư: Người xem khác chỉ thấy video VISIBLE; Chủ kênh hoặc Admin xem được toàn bộ video (bao gồm HIDDEN)
- Trung tâm quản lý video chuyên biệt (my-videos.html):
-   • Danh sách video trực quan kèm trạng thái (Đang hiển thị / Đã ẩn), số lượt xem, ngày đăng
-   • Chỉnh sửa mô tả nhanh: Cập nhật mô tả qua modal không cần tải lại trang (/api/videos/{id})
-   • Ẩn / Hiển thị video linh hoạt: Chủ video hoặc Admin chủ động ẩn video khỏi Feed công khai khi cần thiết
-   • Xóa video an toàn: Bắt buộc xác nhận qua modal; tự động xóa dọn sạch liên kết phụ thuộc (Like, Comment, VideoProduct) và file vật lý

---

## Slide 5: 4. GẮN SẢN PHẨM VÀO VIDEO & GIỎ HÀNG (TASK T3D2296)
*Cầu nối trực tiếp giữa Video ngắn và Thương mại điện tử, gia tăng tỷ lệ chuyển đổi đơn hàng*

- Nghiệp vụ gắn sản phẩm dành cho Người bán (Seller):
-   • Chọn sản phẩm linh hoạt: Người bán chọn tối đa 3 sản phẩm của shop mình khi đăng video mới hoặc sửa video đã đăng
-   • Kiểm tra ràng buộc chặt chẽ: Chỉ cho phép gắn sản phẩm thuộc Shop của chính mình và đang ở trạng thái ACTIVE (HTTP 400 nếu sai)
- Hiển thị và tương tác mua sắm trên Feed video:
-   • Pill sản phẩm nổi bật góc dưới màn hình video và Nút Giỏ hàng nổi bật ở thanh công cụ bên phải
-   • Bottom Sheet danh sách sản phẩm: Bấm vào giỏ hàng mở danh sách thẻ sản phẩm kèm ảnh đại diện, giá tiền và tên shop
-   • Điều hướng 1 chạm: Bấm vào sản phẩm mở ngay trang chi tiết sản phẩm (product.html?id=...) để người mua thêm giỏ hàng
- Hiển thị khối sản phẩm đồng bộ trên trang xem riêng một video (video.html?id=...)

---

## Slide 6: 5. LƯU TRỮ CLOUDFLARE R2 QUA S3 API (BONUS TASK T3D2BC7)
*Kiến trúc lưu trữ đám mây phân tán, không tốn phí băng thông và khả năng mở rộng không giới hạn*

- Thiết kế kiến trúc Storage Abstraction đa tầng (app/core/storage.py):
-   • LocalStorage: Lưu trữ tệp tin vào thư mục uploads/videos/ và uploads/covers/ (phù hợp môi trường dev offline)
-   • R2Storage: Kết nối Cloudflare R2 qua S3 API với thư viện boto3, tải lên với Content-Type chuẩn và cấp URL công khai .r2.dev
-   • Factory Method get_storage(): Tự động nhận diện cấu hình STORAGE_DRIVER=r2 hoặc local; tự động fallback an toàn nếu thiếu key
- Tổ chức đặt tên file chuẩn quy định: videos/<uuid>.mp4 và covers/<uuid>.jpg
- Dọn dẹp file tự động: Khi video bị xóa, hệ thống gọi storage.delete() xóa sạch file trên Cloudflare R2 bucket
- Đã kiểm thử và chạy thực tế thành công trên Bucket: clipshop-media, Public URL: pub-0891989b79c24e44a57caa5935b6a4fc.r2.dev

---

## Slide 7: 6. KIỂM THỬ HỆ THỐNG & NHẬT KÝ SỬA BUG (TASK T3D1D6E)
*Tài liệu kiểm thử toàn diện 40 Test Cases, kiểm thử tự động Pytest và 5 Bug được xử lý triệt để*

- Tài liệu kiểm thử Excel T3D1D6E (T3D1D6E_TestCase_TestLog_PhamCongKhaiHoan_B25DTCN092.xlsx):
-   • 40 Test Cases chi tiết bao phủ 4 nhóm: Đúng dữ liệu (18 TC), Sai dữ liệu (12 TC), Chưa đăng nhập (5 TC), Sai quyền (5 TC)
-   • 40/40 Test Logs thực tế đạt kết quả PASSED (100% Pass)
-   • Kiểm thử tự động Pytest: 22/22 test suites passed 100% (test_video_products.py, test_storage_r2.py, test_social.py)
- 5 Bug thực tế phát hiện trong quá trình tích hợp và đã khắc phục hoàn toàn:
-   • BUG-01: Giải phóng file tạm trong khối try...finally khi upload gặp lỗi, tránh tràn ổ cứng
-   • BUG-02: Bổ sung điều kiện lọc che giấu video HIDDEN trên trang cá nhân đối với người xem khác
-   • BUG-03: Xóa liên kết trong bảng video_products trước khi xóa video để tránh lỗi khóa ngoại IntegrityError
-   • BUG-04: Thiết lập threshold 0.7 và dừng video cũ ngay khi phát video mới, triệt tiêu tiếng lặp
-   • BUG-05: Thêm cơ chế fallback tự động lấy ảnh đầu tiên trong mảng images nếu sản phẩm thiếu ảnh is_primary

---

## Slide 8: 7. KỊCH BẢN LIVE DEMO LUỒNG XUYÊN SUỐT & KẾT LUẬN
*Quy trình trình diễn thực tế từ Upload Video -> Gắn sản phẩm -> Lướt Feed -> Mua hàng trong 3-5 phút*

- Kịch bản trình diễn thực tế tại buổi bảo vệ (Thời lượng ~3-5 phút):
-   • Bước 1 (Đăng video & Gắn SP): Đăng nhập tài khoản người bán -> Vào trang upload.html -> Chọn video và thumbnail -> Chọn gắn 3 sản phẩm của shop -> Bấm Đăng tải -> Quan sát thanh tiến trình 100%
-   • Bước 2 (Quản lý video): Mở my-videos.html -> Xem video vừa đăng kèm badge 3 sản phẩm -> Thử sửa mô tả -> Thử ẩn video
-   • Bước 3 (Lướt Feed & Trải nghiệm): Mở feed.html -> Video tự động phát mượt mà -> Thử cuộn dọc chuyển video và bấm Mute/Unmute -> Quan sát phím tắt
-   • Bước 4 (Mua sắm E-commerce): Bấm vào nút Giỏ hàng trên video -> Mở Bottom Sheet danh sách sản phẩm -> Bấm vào thẻ sản phẩm chuyển sang trang chi tiết product.html -> Thêm vào giỏ hàng thành công
- Kết luận:
-   • Hệ thống vận hành ổn định, giao diện mượt mà chuẩn responsive và sẵn sàng 100% cho buổi nghiệm thu bảo vệ đồ án.

---

