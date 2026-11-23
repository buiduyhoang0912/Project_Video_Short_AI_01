"""API cửa hàng: /api/shops

- GET   /api/shops                              Xem danh sách cửa hàng công khai
- GET   /api/shops/me                           Xem cửa hàng của người bán đang đăng nhập
- GET   /api/shops/me/products                  Xem danh sách sản phẩm thuộc shop của mình
- GET   /api/shops/me/orders                    Người bán xem danh sách đơn hàng của shop mình
- GET   /api/shops/me/orders/{order_id}         Người bán xem chi tiết 1 đơn hàng của shop mình
- PATCH /api/shops/me/orders/{order_id}/status  Cập nhật trạng thái đơn: pending -> confirmed -> shipping -> completed / cancelled
- PUT   /api/shops/me/orders/{order_id}/status  Cập nhật trạng thái đơn
- GET   /api/shops/me/analytics                 Thống kê doanh thu theo ngày và sản phẩm bán chạy của shop
- GET   /api/shops/me/revenue-daily             Doanh thu theo ngày của shop
- GET   /api/shops/me/best-sellers              Danh sách sản phẩm bán chạy của shop
- GET   /api/shops/{shop_id}                    Xem chi tiết thông tin cửa hàng công khai
- GET   /api/shops/{shop_id}/products           Xem danh sách sản phẩm của cửa hàng
- GET   /api/shops/{shop_id}/videos             Xem danh sách video của cửa hàng
- POST  /api/shops                              Tạo cửa hàng (sau khi đã được Admin duyệt đơn)
- PUT   /api/shops/{shop_id}                    Sửa thông tin cửa hàng của mình
"""

from io import BytesIO
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials
from PIL import Image
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.crud import product as product_crud
from app.crud import seller_application as sa_crud
from app.crud import shop as shop_crud
from app.db.session import get_db
from app.dependencies.auth import bearer_scheme, get_current_user
from app.models.revoked_token import RevokedToken
from app.models.shop import Shop
from app.models.user import User
from app.schemas.order import OrderResponse
from app.schemas.product import ProductOut
from app.schemas.shop import (
    BestSellingProductItem,
    DailyRevenueItem,
    ShopAnalyticsOut,
    ShopCreate,
    ShopOrderStatusUpdate,
    ShopOut,
    ShopUpdate,
)

router = APIRouter(prefix="/shops", tags=["Shops"])

UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads"
SHOP_UPLOADS_DIR = UPLOADS_DIR / "shops"
MAX_LOGO_BYTES = 10 * 1024 * 1024
ALLOWED_LOGO_EXTENSIONS = {
    ".jpg": ("jpg", "JPEG"),
    ".jpeg": ("jpg", "JPEG"),
    ".png": ("png", "PNG"),
    ".webp": ("webp", "WEBP"),
}


def _is_approved_seller(db: Session, user: User) -> bool:
    if user.role == "SELLER":
        return True
    return sa_crud.get_approved_application_by_user(db, user.id) is not None


def _get_owned_shop_or_404(db: Session, user: User) -> Shop:
    shop = shop_crud.get_shop_by_owner(db, user.id)
    if shop is None:
        # T3D1DB4: tài khoản chưa được Admin duyệt bán hàng (USER/ADMIN) là sai quyền -> 403,
        # chỉ người bán đã duyệt nhưng chưa tạo shop mới nhận 404.
        if not _is_approved_seller(db, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chức năng dành cho người bán đã được Admin duyệt",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bạn chưa có cửa hàng nào",
        )
    return shop


@router.get("", response_model=list[ShopOut])
def list_public_shops(q: str | None = None, db: Session = Depends(get_db)):
    return shop_crud.get_public_shops(db, keyword=q)


@router.get("/me", response_model=ShopOut)
def get_my_shop(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_shop_or_404(db, user)


@router.get("/me/products", response_model=list[ProductOut])
def list_my_shop_products_via_shops(
    status_filter: Literal["ACTIVE", "HIDDEN", "INACTIVE"] | None = None,
    category_id: int | None = None,
    q: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = _get_owned_shop_or_404(db, user)
    return product_crud.get_shop_products(
        db,
        shop_id=shop.id,
        include_hidden=True,
        status_filter=status_filter,
        keyword=q,
        category_id=category_id,
    )


# ---------- Quản lý Đơn hàng của Shop & Doanh thu / Bán chạy ----------

@router.get("/me/orders", response_model=list[OrderResponse])
def list_my_shop_orders(
    status_filter: str | None = Query(
        default=None,
        description="Lọc trạng thái: pending, confirmed, shipping, completed, cancelled",
    ),
    q: str | None = Query(
        default=None,
        description="Tìm theo mã đơn, tên người nhận, SĐT hoặc tên sản phẩm",
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = _get_owned_shop_or_404(db, user)
    return shop_crud.get_shop_orders(
        db, shop=shop, status_filter=status_filter, keyword=q
    )


@router.get("/me/orders/{order_id}", response_model=OrderResponse)
def get_my_shop_order_detail(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = _get_owned_shop_or_404(db, user)
    order = shop_crud.get_shop_order_or_error(db, shop, order_id)
    return shop_crud._serialize_order(order, shop.name)


@router.patch("/me/orders/{order_id}/status", response_model=OrderResponse)
@router.put("/me/orders/{order_id}/status", response_model=OrderResponse)
def change_my_shop_order_status(
    order_id: int,
    data: ShopOrderStatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = _get_owned_shop_or_404(db, user)
    return shop_crud.update_shop_order_status(db, shop, order_id, data.status)


@router.post("/me/orders/{order_id}/confirm", response_model=OrderResponse)
@router.post("/me/orders/{order_id}/confirm-payment", response_model=OrderResponse, summary="Người bán xác nhận đã nhận tiền chuyển khoản QR VietQR")
def confirm_my_shop_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = _get_owned_shop_or_404(db, user)
    return shop_crud.update_shop_order_status(db, shop, order_id, "confirmed")



@router.post("/me/orders/{order_id}/ship", response_model=OrderResponse)
def ship_my_shop_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = _get_owned_shop_or_404(db, user)
    return shop_crud.update_shop_order_status(db, shop, order_id, "shipping")


@router.post("/me/orders/{order_id}/complete", response_model=OrderResponse)
def complete_my_shop_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = _get_owned_shop_or_404(db, user)
    return shop_crud.update_shop_order_status(db, shop, order_id, "completed")


@router.post("/me/orders/{order_id}/cancel", response_model=OrderResponse)
def cancel_my_shop_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = _get_owned_shop_or_404(db, user)
    return shop_crud.update_shop_order_status(db, shop, order_id, "cancelled")


@router.get("/me/analytics", response_model=ShopAnalyticsOut)
def get_my_shop_analytics(
    limit: int = Query(default=5, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = _get_owned_shop_or_404(db, user)
    return shop_crud.get_shop_analytics(
        db, shop=shop, limit_best_sellers=limit
    )


@router.get("/me/revenue-daily", response_model=list[DailyRevenueItem])
def get_my_shop_daily_revenue(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = _get_owned_shop_or_404(db, user)
    analytics = shop_crud.get_shop_analytics(db, shop=shop)
    return analytics.daily_revenue


@router.get("/me/best-sellers", response_model=list[BestSellingProductItem])
def get_my_shop_best_sellers(
    limit: int = Query(default=5, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = _get_owned_shop_or_404(db, user)
    analytics = shop_crud.get_shop_analytics(
        db, shop=shop, limit_best_sellers=limit
    )
    return analytics.best_selling_products


# ---------- Các API Cửa hàng công khai & Cập nhật Shop ----------

@router.get("/{shop_id}/products", response_model=list[ProductOut])
def list_shop_products(
    shop_id: int,
    include_hidden: bool = False,
    status_filter: Literal["ACTIVE", "HIDDEN", "INACTIVE"] | None = None,
    category_id: int | None = None,
    q: str | None = None,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    shop = shop_crud.get_shop(db, shop_id)
    if shop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy cửa hàng id={shop_id}",
        )

    is_owner = False
    if credentials is not None:
        try:
            payload = decode_access_token(credentials.credentials)
            if db.get(RevokedToken, payload.get("jti")) is None:
                user_id = int(payload["sub"])
                is_owner = shop.owner_id == user_id
        except Exception:
            is_owner = False

    if not is_owner and shop.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy cửa hàng id={shop_id}",
        )

    allow_hidden = is_owner and include_hidden
    effective_status = status_filter if is_owner else "ACTIVE"

    return product_crud.get_shop_products(
        db,
        shop_id=shop.id,
        include_hidden=allow_hidden,
        status_filter=effective_status,
        keyword=q,
        category_id=category_id,
    )


@router.get("/{shop_id}", response_model=ShopOut)
def get_public_shop_detail(shop_id: int, db: Session = Depends(get_db)):
    shop = shop_crud.get_public_shop(db, shop_id)
    if shop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy cửa hàng id={shop_id}",
        )
    return shop


@router.get("/{shop_id}/videos")
def list_shop_videos(shop_id: int, db: Session = Depends(get_db)):
    shop = shop_crud.get_public_shop(db, shop_id)
    if shop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy cửa hàng id={shop_id}",
        )
    return shop_crud.get_shop_videos(db, shop)


@router.post("/me/logo", response_model=ShopOut)
def upload_my_shop_logo(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = _get_owned_shop_or_404(db, user)
    return _save_shop_logo_file(db, shop, file)


@router.post("/{shop_id}/logo", response_model=ShopOut)
def upload_shop_logo(
    shop_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = shop_crud.get_shop(db, shop_id)
    if shop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy cửa hàng id={shop_id}",
        )
    if shop.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền cập nhật logo cho cửa hàng này",
        )
    return _save_shop_logo_file(db, shop, file)


def _save_shop_logo_file(db: Session, shop, upload: UploadFile):
    ext = Path(upload.filename or "").suffix.lower()
    if ext not in ALLOWED_LOGO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Logo cửa hàng phải là ảnh JPG, JPEG, PNG hoặc WebP",
        )

    norm_ext, pil_format = ALLOWED_LOGO_EXTENSIONS[ext]
    raw_bytes = upload.file.read(MAX_LOGO_BYTES + 1)
    if len(raw_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tệp ảnh tải lên không được rỗng",
        )
    if len(raw_bytes) > MAX_LOGO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Dung lượng ảnh logo không được vượt quá 10MB",
        )

    try:
        with Image.open(BytesIO(raw_bytes), formats=[pil_format]) as img:
            img.load()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tệp tải lên bị hỏng hoặc không đúng định dạng ảnh",
        ) from error

    SHOP_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.{norm_ext}"
    dest_path = SHOP_UPLOADS_DIR / filename
    dest_path.write_bytes(raw_bytes)

    shop.avatar_key = f"/uploads/shops/{filename}"
    db.commit()
    db.refresh(shop)
    return shop


@router.post("", response_model=ShopOut, status_code=status.HTTP_201_CREATED)
def create_shop(
    data: ShopCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_approved_seller(db, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn cần được Admin duyệt đơn đăng ký bán hàng trước khi tạo cửa hàng",
        )

    if data.owner_id is not None and data.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không thể tạo cửa hàng cho tài khoản khác",
        )

    if shop_crud.get_shop_by_owner(db, user.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mỗi người bán chỉ được tạo một cửa hàng",
        )

    if not data.name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tên cửa hàng không được chỉ gồm khoảng trắng",
        )

    return shop_crud.create_shop(db, user.id, data)


@router.put("/{shop_id}", response_model=ShopOut)
def update_shop(
    shop_id: int,
    data: ShopUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = shop_crud.get_shop(db, shop_id)
    if shop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy cửa hàng id={shop_id}",
        )

    if shop.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền chỉnh sửa cửa hàng này",
        )

    if not _is_approved_seller(db, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản chưa được duyệt quyền bán hàng",
        )

    if data.name is not None and not data.name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tên cửa hàng không được chỉ gồm khoảng trắng",
        )

    return shop_crud.update_shop(db, shop, data)
