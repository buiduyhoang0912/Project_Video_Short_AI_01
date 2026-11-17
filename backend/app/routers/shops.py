"""API cửa hàng: /api/shops

- GET  /api/shops                      Xem danh sách cửa hàng công khai
- GET  /api/shops/me                   Xem cửa hàng của người bán đang đăng nhập
- GET  /api/shops/me/products          Xem danh sách sản phẩm thuộc shop của mình
- GET  /api/shops/{shop_id}            Xem chi tiết thông tin cửa hàng công khai
- GET  /api/shops/{shop_id}/products   Xem danh sách sản phẩm của cửa hàng
- POST /api/shops                      Tạo cửa hàng (sau khi đã được Admin duyệt đơn)
- PUT  /api/shops/{shop_id}            Sửa thông tin cửa hàng của mình
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.crud import product as product_crud
from app.crud import seller_application as sa_crud
from app.crud import shop as shop_crud
from app.db.session import get_db
from app.dependencies.auth import bearer_scheme, get_current_user
from app.models.revoked_token import RevokedToken
from app.models.user import User
from app.schemas.product import ProductOut
from app.schemas.shop import ShopCreate, ShopOut, ShopUpdate

router = APIRouter(prefix="/shops", tags=["Shops"])


def _is_approved_seller(db: Session, user: User) -> bool:
    if user.role == "SELLER":
        return True
    return sa_crud.get_approved_application_by_user(db, user.id) is not None


@router.get("", response_model=list[ShopOut])
def list_public_shops(q: str | None = None, db: Session = Depends(get_db)):
    return shop_crud.get_public_shops(db, keyword=q)


@router.get("/me", response_model=ShopOut)
def get_my_shop(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = shop_crud.get_shop_by_owner(db, user.id)
    if shop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bạn chưa có cửa hàng nào",
        )
    return shop


@router.get("/me/products", response_model=list[ProductOut])
def list_my_shop_products_via_shops(
    status_filter: Literal["ACTIVE", "HIDDEN", "INACTIVE"] | None = None,
    category_id: int | None = None,
    q: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = shop_crud.get_shop_by_owner(db, user.id)
    if shop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bạn chưa có cửa hàng nào",
        )
    return product_crud.get_shop_products(
        db,
        shop_id=shop.id,
        include_hidden=True,
        status_filter=status_filter,
        keyword=q,
        category_id=category_id,
    )


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
