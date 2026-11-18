"""CRUD xử lý nghiệp vụ giỏ hàng (Cart)."""
from collections import defaultdict
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.shop import Shop
from app.schemas.cart import (
    CartItemOut,
    CartProductBrief,
    CartViewResponse,
    ShopCartGroup,
)


def get_or_create_cart(db: Session, user_id: int) -> Cart:
    """Lấy giỏ hàng của user, nếu chưa có thì tạo mới."""
    cart = db.scalar(select(Cart).where(Cart.user_id == user_id))
    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def get_cart_view(db: Session, user_id: int) -> CartViewResponse:
    """Lấy danh sách giỏ hàng:

    - Nhóm theo shop
    - Chặn / cảnh báo sản phẩm đã ẩn (không ACTIVE) hoặc vượt tồn kho
    - Tạm tính tính chuẩn xác ở server
    """
    cart = get_or_create_cart(db, user_id)

    # Nạp cart_items kèm product và shop
    stmt = (
        select(CartItem)
        .options(
            joinedload(CartItem.product).joinedload(Product.shop),
            joinedload(CartItem.product).joinedload(Product.images),
        )
        .where(CartItem.cart_id == cart.id)
        .order_by(CartItem.id.asc())
    )
    cart_items = list(db.scalars(stmt).unique())

    # Nhóm theo shop
    shops_dict: dict[int, dict] = {}
    total_subtotal = 0.0
    total_valid_items = 0

    for item in cart_items:
        product = item.product
        if product is None:
            continue

        shop = product.shop
        shop_id = product.shop_id
        shop_name = shop.name if shop else f"Shop #{shop_id}"

        # Kiểm tra tính hợp lệ của sản phẩm trong giỏ
        is_active = (product.status.upper() == "ACTIVE") and (shop is not None and getattr(shop, "status", "ACTIVE").upper() == "ACTIVE")
        has_stock = product.stock >= item.quantity
        is_valid = is_active and has_stock

        error_message = None
        if not is_active:
            error_message = "Sản phẩm đã bị ẩn hoặc ngừng kinh doanh"
        elif not has_stock:
            error_message = f"Vượt quá tồn kho (chỉ còn {product.stock})"

        # Thumbnail
        thumb = getattr(product, "thumbnail_url", None)
        if not thumb and product.images:
            thumb = product.images[0].image_url

        price_float = float(product.price)
        line_total = price_float * item.quantity if is_valid else 0.0

        if is_valid:
            total_subtotal += line_total
            total_valid_items += item.quantity

        product_brief = CartProductBrief(
            id=product.id,
            name=product.name,
            price=price_float,
            stock=product.stock,
            status=product.status,
            thumbnail_url=thumb,
        )

        item_out = CartItemOut(
            id=item.id,
            product_id=item.product_id,
            quantity=item.quantity,
            product=product_brief,
            line_total=round(line_total, 2),
            is_valid=is_valid,
            error_message=error_message,
        )

        if shop_id not in shops_dict:
            shops_dict[shop_id] = {
                "shop_id": shop_id,
                "shop_name": shop_name,
                "items": [],
                "shop_subtotal": 0.0,
            }

        shops_dict[shop_id]["items"].append(item_out)
        if is_valid:
            shops_dict[shop_id]["shop_subtotal"] = round(shops_dict[shop_id]["shop_subtotal"] + line_total, 2)

    shop_groups = [
        ShopCartGroup(
            shop_id=data["shop_id"],
            shop_name=data["shop_name"],
            items=data["items"],
            shop_subtotal=data["shop_subtotal"],
        )
        for data in shops_dict.values()
    ]

    return CartViewResponse(
        id=cart.id,
        user_id=user_id,
        shops=shop_groups,
        total_valid_items=total_valid_items,
        subtotal=round(total_subtotal, 2),
    )


def add_to_cart(db: Session, user_id: int, product_id: int, quantity: int) -> CartItem:
    """Thêm sản phẩm vào giỏ (cộng dồn nếu đã có), chặn sản phẩm đã ẩn, không vượt tồn kho."""
    # 1. Kiểm tra sản phẩm tồn tại
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sản phẩm #{product_id} không tồn tại",
        )

    # 2. Chặn sản phẩm đã ẩn / không hoạt động
    if product.status.upper() != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sản phẩm đã bị ẩn hoặc ngừng kinh doanh, không thể thêm vào giỏ hàng",
        )

    # 3. Lấy hoặc tạo giỏ hàng
    cart = get_or_create_cart(db, user_id)

    # 4. Tìm xem sản phẩm đã có trong giỏ chưa
    existing_item = db.scalar(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product_id,
        )
    )

    current_qty = existing_item.quantity if existing_item else 0
    new_qty = current_qty + quantity  # Cộng dồn

    # 5. Kiểm tra không vượt tồn kho
    if new_qty > product.stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Số lượng yêu cầu ({new_qty}) vượt quá số lượng tồn kho còn lại ({product.stock})",
        )

    if existing_item:
        existing_item.quantity = new_qty
        db.commit()
        db.refresh(existing_item)
        return existing_item
    else:
        new_item = CartItem(
            cart_id=cart.id,
            product_id=product_id,
            quantity=new_qty,
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return new_item


def update_cart_item_quantity(
    db: Session, user_id: int, item_id: int, new_quantity: int
) -> CartItem:
    """Sửa số lượng sản phẩm trong giỏ (không vượt tồn kho)."""
    cart = get_or_create_cart(db, user_id)

    item = db.scalar(
        select(CartItem).where(
            CartItem.id == item_id,
            CartItem.cart_id == cart.id,
        )
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sản phẩm trong giỏ hàng (item_id={item_id})",
        )

    product = db.get(Product, item.product_id)
    if product is None or product.status.upper() != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sản phẩm này đã bị ẩn hoặc ngừng kinh doanh",
        )

    if new_quantity > product.stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Số lượng cập nhật ({new_quantity}) vượt quá tồn kho ({product.stock})",
        )

    item.quantity = new_quantity
    db.commit()
    db.refresh(item)
    return item


def delete_cart_item(db: Session, user_id: int, item_id: int) -> bool:
    """Xóa một sản phẩm khỏi giỏ hàng."""
    cart = get_or_create_cart(db, user_id)
    item = db.scalar(
        select(CartItem).where(
            CartItem.id == item_id,
            CartItem.cart_id == cart.id,
        )
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sản phẩm trong giỏ hàng (item_id={item_id})",
        )

    db.delete(item)
    db.commit()
    return True


def clear_user_cart(db: Session, user_id: int) -> None:
    """Xóa toàn bộ giỏ hàng của user."""
    cart = get_or_create_cart(db, user_id)
    cart_items = list(db.scalars(select(CartItem).where(CartItem.cart_id == cart.id)))
    for item in cart_items:
        db.delete(item)
    db.commit()
