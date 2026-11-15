"""Các hàm thao tác DB cho bảng products và product_images (Task T3D24C4)."""

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.cart import CartItem
from app.models.category import Category
from app.models.order import OrderItem
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.video import VideoProduct
from app.schemas.product import ProductCreate, ProductUpdate


def get_category(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def get_product(db: Session, product_id: int) -> Product | None:
    return db.get(Product, product_id)


def get_shop_products(
    db: Session,
    shop_id: int,
    include_hidden: bool = False,
    status_filter: str | None = None,
    keyword: str | None = None,
    category_id: int | None = None,
) -> list[Product]:
    query = select(Product).where(Product.shop_id == shop_id)

    if status_filter:
        query = query.where(Product.status == status_filter)
    elif not include_hidden:
        query = query.where(Product.status == "ACTIVE")

    if category_id is not None:
        query = query.where(Product.category_id == category_id)

    if keyword:
        query = query.where(Product.name.contains(keyword))

    query = query.order_by(Product.id.desc())
    return list(db.scalars(query))


def create_product(db: Session, shop_id: int, data: ProductCreate) -> Product:
    product = Product(
        shop_id=shop_id,
        category_id=data.category_id,
        name=data.name.strip(),
        description=data.description,
        price=data.price,
        stock=data.stock,
        status="ACTIVE",
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(
    db: Session, product: Product, data: ProductUpdate
) -> Product:
    update_data = data.model_dump(exclude_unset=True)
    if "name" in update_data and isinstance(update_data["name"], str):
        update_data["name"] = update_data["name"].strip()

    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


def update_product_stock(
    db: Session, product: Product, stock: int
) -> Product:
    product.stock = stock
    db.commit()
    db.refresh(product)
    return product


def hide_product(db: Session, product: Product) -> Product:
    product.status = "HIDDEN"
    db.commit()
    db.refresh(product)
    return product


def product_has_orders(db: Session, product_id: int) -> bool:
    query = (
        select(OrderItem.id)
        .where(OrderItem.product_id == product_id)
        .limit(1)
    )
    return db.scalar(query) is not None


def delete_or_hide_product(
    db: Session, product: Product
) -> tuple[str, Product | None, list[str]]:
    """Nếu sản phẩm đã có đơn hàng thì chỉ ẩn (status='HIDDEN'), không xoá cứng.
    Nếu chưa có đơn hàng thì xoá cứng và trả về danh sách đường dẫn ảnh để dọn file.
    """
    if product_has_orders(db, product.id):
        product.status = "HIDDEN"
        db.commit()
        db.refresh(product)
        return "hidden", product, []

    image_keys = [img.object_key for img in product.images]

    # Xoá các liên kết phụ thuộc nếu có (giỏ hàng, video gắn sản phẩm; ảnh tự xoá qua cascade)
    db.execute(delete(CartItem).where(CartItem.product_id == product.id))
    db.execute(delete(VideoProduct).where(VideoProduct.product_id == product.id))
    db.delete(product)
    db.commit()
    return "deleted", None, image_keys


def get_product_images(db: Session, product_id: int) -> list[ProductImage]:
    query = (
        select(ProductImage)
        .where(ProductImage.product_id == product_id)
        .order_by(
            ProductImage.is_primary.desc(),
            ProductImage.sort_order.asc(),
            ProductImage.id.asc(),
        )
    )
    return list(db.scalars(query))


def add_product_images(
    db: Session, product_id: int, object_keys: list[str]
) -> list[ProductImage]:
    existing_images = get_product_images(db, product_id)
    has_primary = any(img.is_primary for img in existing_images)

    max_sort = db.scalar(
        select(func.max(ProductImage.sort_order)).where(
            ProductImage.product_id == product_id
        )
    )
    next_sort = 0 if max_sort is None else int(max_sort) + 1

    created_images: list[ProductImage] = []
    for index, key in enumerate(object_keys):
        is_primary = (not has_primary) and (index == 0)
        image = ProductImage(
            product_id=product_id,
            object_key=key,
            is_primary=is_primary,
            sort_order=next_sort + index,
        )
        db.add(image)
        created_images.append(image)

    db.commit()
    for image in created_images:
        db.refresh(image)

    return created_images


def get_product_image(
    db: Session, product_id: int, image_id: int
) -> ProductImage | None:
    query = select(ProductImage).where(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id,
    )
    return db.scalar(query)


def delete_product_image(db: Session, image: ProductImage) -> str:
    product_id = image.product_id
    was_primary = image.is_primary
    object_key = image.object_key

    db.delete(image)
    db.flush()

    if was_primary:
        remaining = get_product_images(db, product_id)
        if remaining:
            remaining[0].is_primary = True

    db.commit()
    return object_key
