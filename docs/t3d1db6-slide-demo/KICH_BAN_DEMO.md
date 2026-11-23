# KỊCH BẢN LIVE DEMO BẢO VỆ ĐỒ ÁN - PHẠM CÔNG KHẢI HOÀN (TASK T3D1DB6)

- **Người trình bày**: Phạm Công Khải Hoàn (`B25DTCN092`)
- **Thời lượng dự kiến**: 3 – 5 phút
- **Chuẩn bị môi trường**: Khởi chạy Backend (`uvicorn app.main:app --reload`) và mở Live Server Frontend (`feed.html`)

## 1. Trình tự Demo các chức năng

### Bước 1: Đăng video mới & Gắn sản phẩm (Task T3D2235, T3D2296)
1. Đăng nhập tài khoản Người bán (`seller1` / `password123`).
2. Bấm vào nút `+ Đăng video` trên thanh điều hướng mở trang `upload.html`.
3. Chọn 1 video MP4 ngắn (15-30s) và chọn ảnh bìa thumbnail tùy chỉnh.
4. Nhập tiêu đề, mô tả và hashtag.
5. Bấm nút `🛍️ Chọn sản phẩm gắn vào video`, chọn tối đa 3 sản phẩm từ cửa hàng của mình.
6. Bấm `Đăng video`, quan sát thanh tiến trình upload chạy mượt mà từ 0% -> 100%.

### Bước 2: Quản lý video của tôi (Task T3D226A)
1. Truy cập vào trang `my-videos.html`.
2. Xem danh sách video đã tải lên, thấy video vừa đăng hiển thị badge `🛍️ 3 sản phẩm`.
3. Thử bấm nút `Sửa mô tả` -> cập nhật mô tả mới trong modal không cần tải lại trang.
4. Thử bấm nút `Ẩn video` -> video chuyển sang trạng thái Ẩn (`HIDDEN`).

### Bước 3: Trải nghiệm Feed video cuộn dọc (Task T3D2202)
1. Mở trang `feed.html`.
2. Video tự động phát khi vào khung nhìn màn hình; khi cuộn xuống video tiếp theo thì video cũ tự dừng (pause).
3. Bấm nút bật/tắt âm thanh (Mute/Unmute) trên video đầu -> cuộn sang video sau thấy trạng thái âm thanh vẫn được duy trì đồng bộ.
4. Thao tác điều hướng bằng phím mũi tên Lên/Xuống và phím Space để tạm dừng/tiếp tục.

### Bước 4: Mua sắm từ video (Task T3D2296 & E-commerce Flow)
1. Trên video Feed có gắn sản phẩm, quan sát thấy nút `Giỏ hàng` ở sidebar và thanh pill sản phẩm nổi bật ở góc dưới.
2. Bấm vào nút Giỏ hàng -> Bottom Sheet trượt lên hiển thị danh sách 3 sản phẩm kèm ảnh, giá tiền và tên shop.
3. Bấm nút `Xem chi tiết` trên thẻ sản phẩm -> hệ thống chuyển hướng sang trang chi tiết `product.html?id=...`.
4. Tại trang chi tiết sản phẩm, bấm `Thêm vào giỏ hàng` hoặc `Mua ngay` -> hoàn tất luồng xuyên suốt E2E từ Video sang Mua hàng.

## 2. Kết luận
Toàn bộ các chức năng phân hệ Video Ngắn, Trình phát Feed dọc, Quản lý Video, Gắn sản phẩm và Lưu trữ Cloudflare R2 đã ghép nối hoàn chỉnh, hoạt động ổn định và đáp ứng 100% yêu cầu đề tài.
