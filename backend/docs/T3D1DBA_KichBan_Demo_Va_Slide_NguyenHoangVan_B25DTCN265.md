# SLIDE & KỊCH BẢN DEMO BẢO VỆ DỰ ÁN CLIPSHOP AI (TASK T3D1DBA)

- **Sinh viên thực hiện**: Nguyễn Hoàng Văn (`B25DTCN265`)
- **Mã Task**: `T3D1DBA` — `[Hoàn thiện] Merge module của mình vào nhánh chính, chạy luồng xuyên suốt, sửa bug, chuẩn bị slide và demo`
- **File Slide PowerPoint (`.pptx`)**: `backend/docs/T3D1DBA_Slide_BaoVe_NguyenHoangVan_B25DTCN265.pptx`
- **Lệnh nạp dữ liệu mẫu trước khi Demo**: `cd backend && python app/seed_demo_flow.py`
- **Tài khoản Demo**:
  - Người bán đã có Shop & Sản phẩm: `seller_active` / `Password123!`
  - Ứng viên đăng ký bán hàng: `seller_candidate` / `Password123!`
  - Người mua hàng: `buyer_sample` / `Password123!`
  - Quản trị viên duyệt đơn: `admin01` / `Password123!`

---

## Slide 1: BÁO CÁO BẢO VỆ DỰ ÁN: CLIPSHOP AI
*Phân hệ Kênh Người Bán (Seller Center), Cửa Hàng Công Khai, Mã Giảm Giá & Trợ Lý AI Copywriter
Sinh viên thực hiện: NGUYỄN HOÀNG VĂN (B25DTCN265) · Mã Task hoàn thiện: T3D1DBA*

- Đề tài: Nền tảng Video ngắn kết hợp Thương mại điện tử & Trợ lý AI (ClipShop AI)
- Vai trò phụ trách chính (Xuyên suốt Sprint 1 - Sprint 3):
-   • T3D24AA & T3D27D1: Đăng ký bán hàng, theo dõi trạng thái xét duyệt & Trang Cửa hàng công khai (Logo, Mô tả, Sản phẩm, Video)
-   • T3D24C4 & T3D27B7: CRUD Sản phẩm, Quản lý tồn kho nhanh, Upload nhiều ảnh, Ẩn sản phẩm đã có đơn & Giao diện Seller Center
-   • T3D27EB: Quản lý Đơn hàng của Shop (Chờ xác nhận -> Đã xác nhận -> Đang giao -> Hoàn thành / Huỷ), Doanh thu ngày & Bán chạy
-   • T3D2805 & T3D2BFB: [AI] Trợ lý viết tên, mô tả, kịch bản video 30–60s & [Bonus] Mã giảm giá của Shop tính lại tiền tại Server
-   • T3D1D72 & T3D1DBA: Thiết kế 40 Test Cases (100% PASS), khắc phục triệt để bug tích hợp & kiểm thử luồng E2E toàn hệ thống

## Slide 2: 1. ĐĂNG KÝ BÁN HÀNG & TRANG CỬA HÀNG CÔNG KHAI (T3D24AA, T3D27D1)
*Quy trình mở gian hàng chặt chẽ và giao diện Flagship Mall trực quan cho khách mua*

- Luồng Đăng ký trở thành Người bán (/api/seller-applications & pages/seller-register.html):
-   • Ràng buộc 1 đơn PENDING duy nhất tại một thời điểm (chặn gửi trùng 409 Conflict); cho phép nộp lại nếu đơn cũ bị từ chối
-   • Sau khi được Admin duyệt (role = SELLER), người bán khởi tạo Cửa hàng (/api/shops) và tải lên Logo (/api/shops/{id}/logo)
-   • Bảo mật & Validate: Chỉ nhận ảnh JPG/PNG/WebP <= 10MB (kiểm tra bằng Pillow), mỗi người bán sở hữu đúng 1 cửa hàng
- Trang Cửa hàng công khai (/api/shops/{id} & pages/shop-public.html):
-   • Hiển thị đầy đủ Banner, Logo, Mô tả, Địa chỉ, Mã giảm giá đang phát hành của shop kèm nút Sao chép mã 1 chạm
-   • Tích hợp 2 Tab: Danh sách sản phẩm đang bán (tìm kiếm, lọc danh mục, sắp xếp giá, thêm vào giỏ) & Danh sách Video của Shop

## Slide 3: 2. QUẢN LÝ SẢN PHẨM, TỒN KHO & UPLOAD NHIỀU ẢNH (T3D24C4, T3D27B7)
*Bảo toàn toàn vẹn dữ liệu lịch sử đơn hàng và cảnh báo tồn kho thông minh trên Seller Center*

- CRUD Sản phẩm & Kiểm soát quyền sở hữu (/api/products & /api/shops/me/products):
-   • Validate chặt chẽ: Giá bán > 0, Số lượng tồn kho >= 0 (trả về 422 nếu vi phạm), chặn 403 Forbidden nếu can thiệp sản phẩm shop khác
-   • Cập nhật nhanh tồn kho (+/- hoặc nhập số trực tiếp qua PATCH /api/products/{id}/stock) kèm Banner cảnh báo hàng sắp hết (<= 5)
- Upload nhiều ảnh cùng lúc (POST /api/products/{id}/images):
-   • Lưu trữ vào /uploads/products/, tự động chọn ảnh đầu tiên làm ảnh đại diện chính (is_primary = True, sort_order = 0)
- Cơ chế Xoá thông minh bảo vệ khoá ngoại (DELETE /api/products/{id}):
-   • Sản phẩm đã phát sinh đơn hàng trong order_items: Không xoá cứng, tự động chuyển sang trạng thái Ẩn (HIDDEN) để giữ lịch sử đơn
-   • Sản phẩm chưa có đơn hàng: Xoá cứng khỏi DB đồng thời dọn sạch các file ảnh vật lý trong thư mục uploads

## Slide 4: 3. QUẢN LÝ ĐƠN HÀNG CỦA SHOP & THỐNG KÊ DOANH THU (T3D27EB)
*Máy trạng thái (State Machine) một chiều nghiêm ngặt và báo cáo tài chính theo thời gian thực*

- Quy trình xử lý đơn hàng chuẩn TMĐT (GET/PATCH /api/shops/me/orders):
-   • Luồng trạng thái hợp lệ: Chờ xác nhận (pending) -> Đã xác nhận (confirmed) -> Đang giao (shipping) -> Hoàn thành (completed)
-   • Chặn nhảy cóc trạng thái (vd: pending -> shipping trả 400 Bad Request) và chặn huỷ đơn khi hàng đã giao (shipping/completed)
-   • Tự động hoàn trả tồn kho (stock) và hoàn lượt dùng Mã giảm giá khi người bán Huỷ đơn ở bước pending hoặc confirmed
- Báo cáo Doanh thu theo ngày & Sản phẩm bán chạy (GET /api/shops/me/analytics):
-   • Bóc tách rõ Doanh thu thực thu (chỉ tính đơn Hoàn thành) và Doanh thu ước tính, loại trừ hoàn toàn đơn Đã huỷ
-   • Bảng xếp hạng Top sản phẩm bán chạy của shop theo tổng số lượng bán ra và doanh số đóng góp kèm thanh tiến độ trực quan

## Slide 5: 4. [AI] TRỢ LÝ VIẾT NỘI DUNG & KỊCH BẢN VIDEO 30–60 GIÂY (T3D2805)
*Ứng dụng Generative AI giúp người bán sáng tạo nội dung chuẩn SEO và kịch bản quay clip ngắn*

- API Trợ lý AI cho người bán (POST /api/products/ai-suggest):
-   • Kết nối Gemini / OpenAI API qua cấu hình .env, nhận thông tin thô (tên/ý tưởng, danh mục, giá bán, đặc điểm nổi bật)
-   • Sinh đồng thời: Tên sản phẩm chuẩn SEO, 3 phương án tên thay thế, Mô tả chi tiết giàu sức thuyết phục & Bộ Hashtag xu hướng
-   • Sinh Kịch bản quay video ngắn 30–60 giây chia rõ 4 phân cảnh: 00s-05s Hook -> 05s-15s Pain Point -> 15s-35s Demo -> 35s-45s CTA
- Trải nghiệm người bán trên Seller Center (Nút '✨ Gợi ý bằng AI'):
-   • Tự động điền tên & mô tả vào form để người bán tự do biên tập, chỉnh sửa lại trước khi bấm Lưu sản phẩm
-   • Cơ chế Smart Copywriting Fallback tiếng Việt: Đảm bảo tính năng hoạt động mượt 100% ngay cả khi hết quota hoặc chưa điền API key

## Slide 6: 5. [BONUS] MÃ GIẢM GIÁ CỦA SHOP & TÍNH LẠI TIỀN TẠI SERVER (T3D2BFB)
*Hệ thống Voucher đa điều kiện, chống Race Condition khi thanh toán trong cùng Transaction*

- Người bán thiết lập Mã giảm giá (GET/POST/PUT/DELETE /api/shops/me/vouchers):
-   • Hỗ trợ 2 hình thức: Giảm theo Phần trăm (PERCENT kèm mức giảm tối đa) và Giảm số tiền cố định (FIXED)
-   • Thiết lập đầy đủ: Giá trị đơn hàng tối thiểu, Hạn dùng, Tổng số lượt sử dụng và Giới hạn số lượt trên mỗi người mua
- Người mua nhập mã khi thanh toán & Server kiểm tra tính lại tiền (POST /api/vouchers/apply & POST /api/orders):
-   • Xem trước số tiền giảm trực tiếp trên Giỏ hàng theo từng Shop; hỗ trợ bấm chọn nhanh chip Voucher đang có của Shop
-   • Khi đặt hàng: Server khoá dòng voucher (SELECT FOR UPDATE), kiểm tra lại hạn dùng/số lượt/đơn tối thiểu, tính lại total_amount
-   • Lưu lịch sử vào bảng voucher_usages trong cùng Database Transaction; nếu bất kỳ điều kiện nào sai sẽ Rollback toàn bộ

## Slide 7: 6. KIỂM THỬ, GHÉP NỐI HỆ THỐNG & SỬA BUG TÍCH HỢP (T3D1D72, T3D1DBA)
*40 Test Cases phân hệ (100% PASS) & 184/184 Automated Tests toàn dự án đạt 100% PASS*

- 1. Sửa lỗi tương thích Schema MySQL (BUG-01): Tự động kiểm tra và bổ sung cột products.sold_count khi khởi động server
- 2. Sửa lỗi toàn vẹn khoá ngoại khi xoá sản phẩm (BUG-02): Tự động chuyển sang HIDDEN nếu sản phẩm đã nằm trong order_items
- 3. Sửa lỗi hoàn kho & hoàn voucher khi huỷ đơn (BUG-03): Cộng trả chính xác stock sản phẩm và lượt dùng mã giảm giá khi huỷ đơn
- 4. Đồng bộ phân quyền RBAC liên module (T3D1DB4/T3D1DBA): Trả về 403 Forbidden chuẩn xác cho tài khoản chưa được duyệt SELLER
- 5. Ghép nối hoàn chỉnh với Giỏ hàng, Đặt hàng, Thông báo đơn hàng (T3D2BAD) và Kiểm duyệt Admin (T3D201D) không còn xung đột

## Slide 8: 7. KỊCH BẢN DEMO BẢO VỆ TRỰC TIẾP (4–5 PHÚT)
*Trình diễn luồng xuyên suốt từ Người bán tạo sản phẩm bằng AI & Voucher đến Người mua đặt hàng*

- Bước 1 (Cửa hàng & Trợ lý AI - 1.5p): Đăng nhập seller_active -> Mở Seller Center -> Nhập tên thô 'Áo khoác Bomber' -> Bấm '✨ Gợi ý bằng AI' -> Xem kịch bản video 30-60s, sửa nhẹ mô tả rồi bấm Lưu & Upload ảnh
- Bước 2 (Tạo Mã giảm giá của Shop - 1p): Chuyển sang tab '🎟️ Mã giảm giá của Shop' -> Tạo mã GIAM10 (Giảm 10% tối đa 30k cho đơn từ 150k) -> Mở Trang Cửa hàng công khai xem sản phẩm, video và bấm Sao chép mã
- Bước 3 (Người mua áp mã & Đặt hàng - 1p): Đăng nhập buyer_sample -> Thêm sản phẩm vào Giỏ hàng -> Bấm áp dụng mã GIAM10 (Server báo giảm 30.000đ và tính lại tổng tiền) -> Bấm Đặt hàng ngay
- Bước 4 (Xử lý đơn & Thống kê Doanh thu - 1p): Quay lại Seller Center tab '🧾 Đơn hàng của Shop' -> Bấm Xác nhận -> Bắt đầu giao -> Hoàn thành -> Mở tab '📊 Doanh thu & Bán chạy' kiểm tra doanh thu ngày và Top sản phẩm
