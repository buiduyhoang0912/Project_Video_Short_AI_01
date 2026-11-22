# HƯỚNG DẪN KỊCH BẢN DEMO BẢO VỆ DỰ ÁN (TASK T3D1DB4)

Tài liệu này hướng dẫn chi tiết từng bước để bạn thực hiện phần demo trước thầy cô / hội đồng chấm bảo vệ.

---

## 1. Chuẩn bị trước khi Demo

### Bước 1: Khởi động Backend & Frontend
1. **Backend**:
   ```bash
   cd backend
   # Kích hoạt venv (nếu có)
   python app/seed_demo_flow.py      # Tạo ngay dữ liệu mẫu chuẩn chỉ trong 2 giây!
   uvicorn app.main:app --reload      # Chạy server tại http://127.0.0.1:8000
   ```
2. **Frontend**:
   - Mở VS Code, chuột phải vào file `frontend/pages/admin.html` (hoặc `frontend/index.html`) chọn **Open with Live Server** (hoặc truy cập `http://localhost:5500/pages/admin.html`).

### Bước 2: Danh sách tài khoản mẫu dùng cho demo
Mật khẩu chung cho tất cả các tài khoản demo là: `Password123!`

| Tài khoản | Vai trò | Mục đích demo |
|---|:---:|---|
| `admin01` | **ADMIN** | Đăng nhập trang Admin để thực hiện mọi thao tác quản trị |
| `seller_candidate` | **USER** | Có sẵn 1 đơn đăng ký bán hàng ở trạng thái `PENDING` để demo Duyệt đơn |
| `seller_active` | **SELLER** | Đang sở hữu Shop và có sẵn sản phẩm & video để demo Kiểm duyệt |
| `user_normal` | **USER** | Đang ở trạng thái `ACTIVE` để demo tìm kiếm và thao tác Khoá tài khoản |
| `user_locked` | **USER** | Đang ở trạng thái `LOCKED` để demo Mở khoá và kiểm tra chặn đăng nhập |
| `buyer_sample` | **USER** | Người mua đã phát sinh các đơn hàng hoàn tất để phục vụ Dashboard |

---

## 2. Các bước tiến hành Demo (Live Demo Walkthrough)

### PHẦN 1: DUYỆT ĐƠN ĐĂNG KÝ BÁN HÀNG (TASK T3D2003)
1. Đăng nhập bằng tài khoản: `admin01` / `Password123!`.
2. Mở menu góc trên bấm vào **🛡️ Admin** (hoặc vào `pages/admin.html`).
3. Chọn tab **📝 Đơn đăng ký bán hàng**:
   - Thấy ngay đơn đăng ký của người dùng `@seller_candidate` (Shop: *GenZ Fashion Official*).
   - **Thử trường hợp lỗi**: Bấm nút "Từ chối" màu đỏ → Modal hiện lên → Bấm "Xác nhận từ chối" khi chưa nhập lý do → Giao diện báo lỗi đỏ: *"Vui lòng nhập lý do từ chối"*. Bấm nút "Huỷ".
   - **Thực hiện duyệt**: Bấm nút **"Duyệt"** màu xanh → Xác nhận popup → Hiện toast xanh: *"Đã duyệt đơn, tài khoản được cấp quyền SELLER"*.
   - Giải thích: Đơn đã chuyển sang `APPROVED` và role của tài khoản được cập nhật cùng lúc trong 1 Database Transaction duy nhất để bảo đảm toàn vẹn dữ liệu.

---

### PHẦN 2: QUẢN LÝ TÀI KHOẢN & CHẶN TRUY CẬP (TASK T3D2003)
1. Bấm sang tab **👥 Tài khoản**:
   - Thấy danh sách đầy đủ người dùng kèm vai trò (`ADMIN`, `SELLER`, `USER`) và trạng thái (`Hoạt động`, `Bị khoá`).
   - Riêng dòng tài khoản `admin01` của chính mình: Nút khoá bị ẩn và ghi *"Tài khoản của bạn"*, giải thích cơ chế ngăn Admin tự khoá chính mình.
2. **Tìm kiếm**:
   - Nhập `user_normal` vào ô tìm kiếm → Bấm "Tìm kiếm" → Bảng lọc đúng tài khoản cần tìm.
3. **Thao tác Khoá**:
   - Bấm nút **"Khoá"** tại dòng `user_normal` → Xác nhận popup → Trạng thái chuyển sang badge đỏ *"Bị khoá"*, nút đổi thành *"Mở khoá"*.
   - **Chứng minh hiệu quả**: Mở một cửa sổ ẩn danh (Incognito), vào trang đăng nhập `pages/login.html`, nhập `user_normal` / `Password123!` → Bấm Đăng nhập → Hệ thống báo lỗi đỏ: *"Tài khoản đã bị khóa"*.
4. **Thao tác Mở khoá**:
   - Quay lại cửa sổ Admin, bấm nút **"Mở khoá"** tại dòng tài khoản đó → Trạng thái chuyển lại thành *"Hoạt động"*.
   - Đăng nhập lại ở cửa sổ ẩn danh → Đăng nhập thành công ngay lập tức!

---

### PHẦN 3: KIỂM DUYỆT VIDEO & SẢN PHẨM VI PHẠM (TASK T3D201D)
1. Bấm sang tab **🎬 Video**:
   - Danh sách hiển thị video *"Review Áo Hoodie Mới Về Đẹp Hết Nấc"* của người dùng `@seller_active`.
   - Bấm nút **"Ẩn vi phạm"** → Modal bật lên → Nhập lý do: *"Nội dung vi phạm tiêu chuẩn bản quyền âm nhạc"* → Bấm "Xác nhận ẩn".
   - Bảng cập nhật trạng thái *"Đã ẩn vi phạm"* kèm dòng lý do màu đỏ ghi rõ người ẩn và thời gian.
   - Video lập tức bị loại khỏi Feed công khai và tìm kiếm.
2. Bấm sang tab **🛍️ Sản phẩm**:
   - Bảng hiển thị sản phẩm kèm ảnh thumbnail, shop, giá tiền.
   - Bấm **"Ẩn vi phạm"** sản phẩm *"Mũ Lưỡi Trai Classic"* → Nhập lý do: *"Hàng giả mạo thương hiệu"* → Xác nhận.
   - Sản phẩm chuyển sang trạng thái bị ẩn.
   - Giải thích cho hội đồng: Sản phẩm bị ẩn sẽ bị chặn ở cả API xem chi tiết (404), giỏ hàng (400) và quy trình thanh toán đặt hàng. Đồng thời, seller không thể tự ý gọi API để kích hoạt lại sản phẩm bị Admin ẩn.
3. **Mở lại nội dung**:
   - Bấm nút **"Hiện lại"** → Nội dung được gỡ bỏ cờ vi phạm và hiển thị công khai bình thường.

---

### PHẦN 4: DASHBOARD THỐNG KÊ DOANH THU CHART.JS (TASK T3D201D)
1. Bấm về tab **📊 Dashboard**:
   - Xem **6 thẻ chỉ số nền tảng**: Người dùng, Người bán, Tổng Video, Tổng Sản phẩm, Tổng Đơn hàng, Doanh thu toàn sàn.
   - **Nhấn mạnh logic tính doanh thu**:
     - Doanh thu chỉ tính các đơn hàng đã thanh toán hoặc hoàn tất (`confirmed`, `shipping`, `completed`).
     - Đơn hủy (`cancelled`) và đơn chờ (`pending`) hoàn toàn bị loại bỏ.
     - Đơn có nhiều mặt hàng được tính chuẩn xác 1 lần tổng tiền, không bị nhân bản/cộng trùng.
2. **Thao tác biểu đồ Chart.js**:
   - Cuộn xuống xem 3 biểu đồ trực quan:
     1. *Biểu đồ Doanh thu theo ngày (₫)* (Line chart màu đỏ có đổ màu diện tích).
     2. *Số đơn hàng theo ngày* (Bar chart màu xanh).
     3. *Tăng trưởng người dùng & video mới* (Multi-line chart màu xanh lá & cam).
   - Bấm các nút chọn nhanh thời gian: **7 ngày**, **14 ngày**, **30 ngày**, **90 ngày** → Quan sát biểu đồ tự động co giãn và cập nhật mượt mà.
   - Thử chọn bộ lọc ngày: Nhập Từ ngày & Đến ngày → Bấm **Áp dụng** → Dữ liệu cập nhật chuẩn xác theo khoảng ngày đã chọn.

---

## 3. Câu hỏi phản biện thường gặp và cách trả lời

**Q1: Nếu có 2 Admin cùng duyệt 1 đơn đăng ký bán hàng thì sao?**  
> *Trả lời:* Backend sử dụng cơ chế `SELECT FOR UPDATE` khóa bản ghi đơn đăng ký trong Database Transaction và kiểm tra `status == 'PENDING'`. Khi Admin thứ nhất duyệt xong, đơn chuyển sang `APPROVED`. Admin thứ hai gửi request sẽ bị chặn ngay với mã lỗi `409 Conflict` ("Chỉ có thể duyệt đơn đang ở trạng thái chờ").

**Q2: Tài khoản bị khoá thì token cũ còn dùng được không?**  
> *Trả lời:* Trong `backend/app/dependencies/auth.py`, hàm `get_current_user` tải lại trạng thái tài khoản từ database trong mỗi request. Khi `user.status != 'ACTIVE'`, hệ thống lập tức ném ra ngoại lệ `403 Forbidden` ("Tài khoản đã bị khóa"). Vì vậy, token cũ bị vô hiệu hóa ngay tại thời điểm Admin bấm khoá mà không cần chờ hết hạn token.

**Q3: Làm thế nào tránh việc người bán tự ý bật lại sản phẩm/video bị Admin phạt ẩn?**  
> *Trả lời:* Khi Admin ẩn nội dung, backend lưu vết cờ `moderated_at`. Tại các API cập nhật trạng thái của Seller (`PATCH /api/products/{id}` và `PATCH /api/videos/{id}/status`), backend kiểm tra nếu `moderated_at IS NOT NULL` và người gọi không có role `ADMIN` thì chặn ngay bằng mã lỗi `403 Forbidden`. Chỉ duy nhất Admin mới có quyền gỡ cờ vi phạm này.
