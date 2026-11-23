# KỊCH BẢN DEMO BẢO VỆ ĐỀ TÀI & NỘI DUNG SLIDE TRÌNH CHIẾU
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
