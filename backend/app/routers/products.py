"""API cho Sản phẩm (Products), tồn kho và ảnh sản phẩm. Đường dẫn: /api/products"""

from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from PIL import Image
from sqlalchemy.orm import Session

from app.crud import product as product_crud
from app.crud import shop as shop_crud
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.product import Product
from app.models.shop import Shop
from app.models.user import User
from app.schemas.product import (
    ProductAiSuggestRequest,
    ProductAiSuggestResponse,
    ProductCreate,
    ProductDetailOut,
    ProductListResponse,
    ProductOut,
    ProductSortBy,
    ProductStockUpdate,
    ProductUpdate,
)
from app.schemas.product_image import ProductImageOut

router = APIRouter(prefix="/products", tags=["Products"])

UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads"
PRODUCT_UPLOADS_DIR = UPLOADS_DIR / "products"
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB mỗi ảnh

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg": ("jpg", "JPEG"),
    ".jpeg": ("jpg", "JPEG"),
    ".png": ("png", "PNG"),
    ".webp": ("webp", "WEBP"),
}


def get_seller_shop(user: User, db: Session) -> Shop:
    shop = shop_crud.get_shop_by_owner(db, user.id)
    if shop is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn chưa có cửa hàng, vui lòng tạo cửa hàng trước khi quản lý sản phẩm",
        )
    return shop


def get_owned_product_or_error(
    product_id: int, user: User, db: Session
) -> Product:
    shop = get_seller_shop(user, db)
    product = product_crud.get_product(db, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sản phẩm id={product_id}",
        )
    if product.shop_id != shop.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn chỉ có quyền thao tác trên sản phẩm thuộc cửa hàng của mình",
        )
    return product


def _remove_local_upload(object_key: str) -> None:
    prefix = "/uploads/products/"
    if not object_key or not object_key.startswith(prefix):
        return
    filename = object_key.removeprefix(prefix)
    if "/" in filename or "\\" in filename or ".." in filename:
        return
    file_path = PRODUCT_UPLOADS_DIR / filename
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        pass


@router.get(
    "",
    response_model=ProductListResponse,
    summary="Danh sách sản phẩm (tìm kiếm, lọc, sắp xếp, phân trang)",
)
def list_products(
    q: str | None = Query(None, description="Tìm theo tên sản phẩm"),
    category_id: int | None = Query(None, description="Lọc theo danh mục"),
    min_price: Decimal | None = Query(None, ge=0, description="Giá tối thiểu"),
    max_price: Decimal | None = Query(None, ge=0, description="Giá tối đa"),
    shop_id: int | None = Query(None, description="Lọc theo shop"),
    sort_by: ProductSortBy = Query(
        ProductSortBy.NEWEST,
        description="Sắp xếp: price_asc, price_desc, newest, best_selling",
    ),
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    page_size: int = Query(10, ge=1, le=100, description="Số sản phẩm mỗi trang"),
    db: Session = Depends(get_db),
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price không được lớn hơn max_price",
        )

    return product_crud.get_products(
        db,
        keyword=q,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        shop_id=shop_id,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )


@router.get("/me", response_model=list[ProductOut])
def list_my_shop_products(
    status_filter: Literal["ACTIVE", "HIDDEN", "INACTIVE"] | None = None,
    category_id: int | None = None,
    q: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = get_seller_shop(user, db)
    return product_crud.get_shop_products(
        db,
        shop_id=shop.id,
        include_hidden=True,
        status_filter=status_filter,
        keyword=q,
        category_id=category_id,
    )


@router.post(
    "/ai-suggest",
    response_model=ProductAiSuggestResponse,
    summary="[AI] Trợ lý gợi ý tên, mô tả sản phẩm và kịch bản video 30-60s cho người bán",
)
def suggest_product_content_by_ai(
    data: ProductAiSuggestRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not data.raw_name or not data.raw_name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Vui lòng nhập tên hoặc ý tưởng sản phẩm để AI gợi ý",
        )
    return product_crud.generate_seller_ai_content(db, data)


@router.get(
    "/{product_id}",
    response_model=ProductDetailOut,
    summary="Chi tiết sản phẩm kèm ảnh, tồn, shop, video",
)
def get_product_detail(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = product_crud.get_product_detail(db, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sản phẩm id={product_id} hoặc sản phẩm/shop không còn hoạt động.",
        )
    return product


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    data: ProductCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = get_seller_shop(user, db)

    if data.shop_id is not None and data.shop_id != shop.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không thể thêm sản phẩm vào cửa hàng của người khác",
        )

    if not data.name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tên sản phẩm không được chỉ gồm khoảng trắng",
        )

    category = product_crud.get_category(db, data.category_id)
    if category is None or category.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy danh mục hoạt động id={data.category_id}",
        )

    return product_crud.create_product(db, shop.id, data)


@router.put("/{product_id}", response_model=ProductOut)
@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    data: ProductUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = get_owned_product_or_error(product_id, user, db)

    # Sản phẩm bị Admin ẩn do vi phạm: người bán không được tự bật hiển thị lại
    if (
        product.moderated_at is not None
        and data.status is not None
        and data.status != "HIDDEN"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sản phẩm đang bị Admin ẩn do vi phạm, không thể tự hiển thị lại",
        )

    if data.name is not None and not data.name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tên sản phẩm không được chỉ gồm khoảng trắng",
        )

    if data.category_id is not None:
        category = product_crud.get_category(db, data.category_id)
        if category is None or category.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy danh mục hoạt động id={data.category_id}",
            )

    return product_crud.update_product(db, product, data)


@router.put("/{product_id}/stock", response_model=ProductOut)
@router.patch("/{product_id}/stock", response_model=ProductOut)
def update_stock(
    product_id: int,
    data: ProductStockUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = get_owned_product_or_error(product_id, user, db)
    return product_crud.update_product_stock(db, product, data.stock)


@router.put("/{product_id}/hide", response_model=ProductOut)
@router.patch("/{product_id}/hide", response_model=ProductOut)
def hide_product_endpoint(
    product_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = get_owned_product_or_error(product_id, user, db)
    return product_crud.hide_product(db, product)


@router.delete("/{product_id}")
def delete_or_hide_product_endpoint(
    product_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = get_owned_product_or_error(product_id, user, db)
    action, updated_product, removed_keys = product_crud.delete_or_hide_product(
        db, product
    )

    if action == "hidden" and updated_product is not None:
        return {
            "action": "hidden",
            "message": "Sản phẩm đã có đơn hàng nên chỉ chuyển sang trạng thái ẩn (HIDDEN), không xoá cứng",
            "product": ProductOut.model_validate(updated_product),
        }

    for key in removed_keys:
        _remove_local_upload(key)

    return {
        "action": "deleted",
        "message": "Đã xoá cứng sản phẩm thành công",
        "id": product_id,
    }


@router.get("/{product_id}/images", response_model=list[ProductImageOut])
def list_product_images(product_id: int, db: Session = Depends(get_db)):
    product = product_crud.get_product(db, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sản phẩm id={product_id}",
        )
    return product_crud.get_product_images(db, product_id)


@router.post(
    "/{product_id}/images",
    response_model=list[ProductImageOut],
    status_code=status.HTTP_201_CREATED,
)
def upload_product_images(
    product_id: int,
    files: list[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = get_owned_product_or_error(product_id, user, db)

    if not files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Vui lòng chọn ít nhất 1 tệp ảnh để tải lên",
        )

    PRODUCT_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []
    object_keys: list[str] = []

    try:
        for upload in files:
            ext = Path(upload.filename or "").suffix.lower()
            if ext not in ALLOWED_IMAGE_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Chỉ chấp nhận tệp ảnh JPG, JPEG, PNG hoặc WebP",
                )

            norm_ext, pil_format = ALLOWED_IMAGE_EXTENSIONS[ext]
            raw_bytes = upload.file.read(MAX_IMAGE_BYTES + 1)

            if len(raw_bytes) == 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Tệp ảnh tải lên không được rỗng",
                )
            if len(raw_bytes) > MAX_IMAGE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Dung lượng mỗi ảnh không được vượt quá 10MB",
                )

            try:
                with Image.open(
                    BytesIO(raw_bytes), formats=[pil_format]
                ) as img:
                    img.load()
            except Exception as error:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Tệp tải lên bị hỏng hoặc không đúng định dạng ảnh",
                ) from error

            filename = f"{uuid4().hex}.{norm_ext}"
            dest_path = PRODUCT_UPLOADS_DIR / filename
            dest_path.write_bytes(raw_bytes)
            saved_paths.append(dest_path)
            object_keys.append(f"/uploads/products/{filename}")

        return product_crud.add_product_images(db, product.id, object_keys)
    except Exception:
        for path in saved_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise


@router.delete(
    "/{product_id}/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_product_image(
    product_id: int,
    image_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = get_owned_product_or_error(product_id, user, db)
    image = product_crud.get_product_image(db, product.id, image_id)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy ảnh sản phẩm",
        )

    object_key = product_crud.delete_product_image(db, image)
    _remove_local_upload(object_key)
