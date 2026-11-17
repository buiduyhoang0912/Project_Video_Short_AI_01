# Hướng dẫn dùng dependency xác thực & phân quyền

Nguồn duy nhất: `backend/app/dependencies/auth.py`. **Không** tự viết lại hàm kiểm tra token trong router.

```python
from app.dependencies.auth import (
    get_current_user, get_optional_user, require_seller, require_admin,
)
```

## 4 hàm

| Hàm | Khi nào dùng | Kết quả |
|---|---|---|
| `get_current_user` | Bắt buộc đăng nhập: hồ sơ, giỏ hàng, bình luận, like, follow | `User` |
| `get_optional_user` | Khách vẫn xem được: feed, xem video | `User` hoặc `None` |
| `require_seller` | Quản lý sản phẩm, cửa hàng | `User` có `role == SELLER` |
| `require_admin` | Quản lý người dùng, duyệt người bán | `User` có `role == ADMIN` |

Role/status luôn đọc từ database ở mỗi request, nên tài khoản vừa bị khóa hoặc đổi quyền có hiệu lực ngay dù token chưa hết hạn.

## Gửi token

```
Authorization: Bearer <access_token>
```
Lấy `access_token` từ `POST /auth/login`. Trên Swagger (`/docs`) bấm **Authorize** rồi dán token.

## Lỗi

| Mã | detail | Khi nào |
|---|---|---|
| 401 | `Chưa đăng nhập` | API bắt buộc đăng nhập nhưng không có token |
| 401 | `Token không hợp lệ` | Token sai, hết hạn, đã logout, hoặc user không tồn tại (kể cả khi gửi vào API dùng `get_optional_user`) |
| 403 | `Tài khoản đã bị khóa` | `status == LOCKED` (kể cả với `get_optional_user`) |
| 403 | `Không đủ quyền truy cập` | Sai role khi gọi API seller/admin |

Header `Authorization` sai định dạng (`Bearer` không có token, `Basic ...`) cũng bị 401, kể cả với `get_optional_user`.

Lỗi 401 luôn kèm header `WWW-Authenticate: Bearer`.

`get_optional_user`: **chỉ** khi không gửi token mới được coi là khách (`None`). Đã gửi token thì token phải hợp lệ.

## Ví dụ

```python
@router.get("/feed")                       # khách
def feed(user: User | None = Depends(get_optional_user)):
    liked = user is not None and ...       # phải xử lý user is None

@router.post("/comments")                  # người dùng
def comment(user: User = Depends(get_current_user)): ...

@router.post("/products")                  # seller
def create_product(seller: User = Depends(require_seller)): ...

@router.put("/seller-applications/{id}/approve")   # admin
def approve(id: int, admin: User = Depends(require_admin)): ...
```

## Quy định ADMIN và API seller

`require_seller` **chỉ cho SELLER**; ADMIN nhận 403. Admin quản trị nền tảng, không sở hữu cửa hàng. Nếu một API cần cả hai, tự dùng `get_current_user` rồi kiểm tra `user.role in ("SELLER", "ADMIN")`.

## Kiểm thử

```
cd backend
pytest tests/test_auth_dependencies.py
```

## Lưu ý

API video (upload/sửa/xóa) hiện còn dùng Basic Auth riêng (`core/video_auth.py`); nhóm cần chuyển sang `get_current_user` khi tích hợp.
