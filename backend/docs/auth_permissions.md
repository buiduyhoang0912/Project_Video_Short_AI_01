# Hướng dẫn xác thực & phân quyền dùng chung (T3D1E2C)

Module: `backend/app/core/dependencies.py` (JWT Bearer: `Authorization: Bearer <token>`).

```python
from fastapi import APIRouter, Depends
from app.core.dependencies import (
    get_current_user, get_optional_user, require_seller, require_admin,
)
from app.models.user import User
```

| Dependency | Dùng cho | Kết quả |
|---|---|---|
| `get_current_user` | API bắt buộc đăng nhập (like, comment, follow, tạo/sửa/xóa video, shop, đơn seller...) | `User` |
| `get_optional_user` | API khách được xem (feed) | `User` hoặc `None` (không token) |
| `require_seller` | API chỉ SELLER | `User` role SELLER |
| `require_admin` | API chỉ ADMIN | `User` role ADMIN |

## Ví dụ

```python
@router.get("/videos/feed")           # khách xem được
def feed(user: User | None = Depends(get_optional_user)): ...

@router.post("/videos/{id}/likes")    # phải đăng nhập
def like(user: User = Depends(get_current_user)): ...

@router.post("/products")             # chỉ SELLER
def create_product(seller: User = Depends(require_seller)): ...

@router.put("/seller-applications/{id}/approve")   # chỉ ADMIN
def approve(admin: User = Depends(require_admin)): ...
```

Hoặc gắn cả router: `APIRouter(dependencies=[Depends(require_admin)])`.

## Quy tắc lỗi

| Mã | Khi nào |
|---|---|
| **401** | Thiếu token (với API bắt buộc), token sai, hết hạn, đã logout, user không tồn tại. Kèm `WWW-Authenticate: Bearer`. |
| **403** | Đã xác thực nhưng sai quyền (USER gọi API SELLER/ADMIN) hoặc tài khoản `LOCKED` (kể cả token còn hạn). |

`get_optional_user`: không có header → `None`; **có token sai/hết hạn → 401** (không tự thành khách); tài khoản khóa → 403.

Lưu ý: `require_seller` chỉ chấp nhận `role == "SELLER"` (ADMIN không tự động qua). Nếu API cần cả hai, tự kiểm tra bằng `get_current_user`.

Helper lỗi: `unauthorized(detail)`, `forbidden(detail)` trong cùng module — dùng thay vì tự tạo `HTTPException`.

## Đã chuyển sang dùng chung
- `routers/auth.py`, `seller_applications.py` (`require_admin`), `shops.py`: import từ `core.dependencies`.
- `routers/videos.py`: bỏ HTTP Basic, dùng JWT; thêm `GET /api/videos/feed` (khách xem được).
- `core/social_auth.py`: hết trả 501, re-export `get_current_user` thật. (Router social chưa được include trong `main.py` — người phụ trách social include khi merge.)
- `core/video_auth.py`: chỉ còn alias tương thích.

## Test
`cd backend && pytest tests/test_permissions.py`
