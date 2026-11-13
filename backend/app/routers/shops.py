"""API cửa hàng: /api/shops

- GET  /api/shops            Xem danh sách cửa hàng công khai
- GET  /api/shops/me         Xem cửa hàng của người bán đang đăng nhập
- GET  /api/shops/{shop_id}  Xem chi tiết thông tin cửa hàng công khai
- POST /api/shops            Tạo cửa hàng (sau khi đã được Admin duyệt đơn)
- PUT  /api/shops/{shop_id}  Sửa thông tin cửa hàng của mình
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import seller_application as sa_crud
from app.crud import shop as shop_crud
from app.db.session import get_db
from app.models.user import User
from app.routers.auth import get_current_user
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

