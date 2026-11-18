"""CRUD xử lý nghiệp vụ Đặt hàng & Đơn hàng trong Transaction.

Yêu cầu nghiệp vụ:
- Tách đơn theo shop
- Kiểm tra tồn kho, trừ kho
- 2 người cùng mua sản phẩm cuối không làm tồn âm (SELECT FOR UPDATE)
- Lưu giá lúc đặt (snapshot unit_price)
- Xóa các dòng đã đặt khỏi giỏ
- Lỗi giữa chừng tự động rollback
- Thanh toán mô phỏng đánh dấu đã thanh toán (status = confirmed)
"""
from collections import defaultdict
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.cart import Cart, CartItem
from app.models.order import Address, Order, OrderItem
from app.models.product import Product
from app.models.shop import Shop
from app.schemas.order import (
    OrderCheckout,
    OrderCheckoutResponse,
    OrderItemResponse,
    OrderResponse,
)


def create_orders_from_cart(
    db: Session,
    user_id: int,
    checkout_data: OrderCheckout,
) -> OrderCheckoutResponse:
    """Tạo đơn hàng từ giỏ hàng trong một Database Transaction duy nhất."""
    # 1. Xác định địa chỉ giao hàng
    rec_name = checkout_data.recipient_name
    rec_phone = checkout_data.recipient_phone
    rec_address = checkout_data.recipient_address

    if checkout_data.address_id:
        saved_addr = db.get(Address, checkout_data.address_id)
        if saved_addr is None or saved_addr.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Địa chỉ #{checkout_data.address_id} không hợp lệ hoặc không thuộc về bạn",
            )
        rec_name = saved_addr.recipient_name
        rec_phone = saved_addr.phone
        rec_address = saved_addr.address_line
    elif not (rec_name and rec_phone and rec_address):
        # Tìm địa chỉ mặc định
        default_addr = db.scalar(
            select(Address).where(Address.user_id == user_id, Address.is_default == True)
        )
        if default_addr:
            rec_name = default_addr.recipient_name
            rec_phone = default_addr.phone
            rec_address = default_addr.address_line
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vui lòng cung cấp đầy đủ thông tin người nhận (tên, số điện thoại, địa chỉ)",
            )

    # 2. Lấy giỏ hàng của user
    cart = db.scalar(select(Cart).where(Cart.user_id == user_id))
    if cart is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giỏ hàng của bạn đang trống",
        )

    # Nạp danh sách item trong giỏ
    items_stmt = (
        select(CartItem)
        .options(joinedload(CartItem.product))
        .where(CartItem.cart_id == cart.id)
    )
    all_cart_items = list(db.scalars(items_stmt).unique())
    if not all_cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giỏ hàng của bạn đang trống, không thể đặt hàng",
        )

    # Lọc danh sách items cần đặt nếu có cart_item_ids
    if checkout_data.cart_item_ids:
        target_ids = set(checkout_data.cart_item_ids)
        items_to_order = [it for it in all_cart_items if it.id in target_ids]
        if not items_to_order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không tìm thấy các sản phẩm đã chọn trong giỏ hàng",
            )
    else:
        items_to_order = all_cart_items

    # 3. BẮT ĐẦU TRANSACTION ĐẶT HÀNG
    try:
        # Nhóm các sản phẩm theo từng Shop
        items_by_shop: dict[int, list[CartItem]] = defaultdict(list)
        product_ids = sorted({it.product_id for it in items_to_order})

        # Khóa dòng các sản phẩm bằng SELECT FOR UPDATE để tránh Race Condition (2 người mua cuối)
        stmt_lock = (
            select(Product)
            .where(Product.id.in_(product_ids))
            .with_for_update()
        )
        locked_products = {p.id: p for p in db.scalars(stmt_lock).all()}

        for it in items_to_order:
            items_by_shop[it.product.shop_id].append(it)

        created_orders: list[Order] = []
        total_all_amount = Decimal("0")

        # Tách đơn theo từng Shop
        for shop_id, shop_cart_items in items_by_shop.items():
            shop = db.get(Shop, shop_id)
            if shop is None or getattr(shop, "status", "ACTIVE").upper() != "ACTIVE":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cửa hàng #{shop_id} hiện đang tạm ngừng hoạt động",
                )

            shop_total = Decimal("0")
            order_items: list[OrderItem] = []

            for it in shop_cart_items:
                product = locked_products.get(it.product_id)
                if product is None or product.status.upper() != "ACTIVE":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Sản phẩm #{it.product_id} đã bị ẩn hoặc ngừng bán",
                    )

                # Kiểm tra tồn kho: 2 người cùng mua sản phẩm cuối không làm tồn âm
                if product.stock < it.quantity:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Sản phẩm '{product.name}' không đủ số lượng tồn kho (chỉ còn {product.stock}, bạn yêu cầu {it.quantity})",
                    )

                # Trừ tồn kho & cộng lượt bán
                product.stock -= it.quantity
                product.sold_count = (product.sold_count or 0) + it.quantity

                # Lưu giá tại thời điểm đặt (snapshot price)
                unit_price = Decimal(str(product.price))
                shop_total += unit_price * it.quantity

                order_item = OrderItem(
                    product_id=product.id,
                    quantity=it.quantity,
                    unit_price=unit_price,
                )
                order_items.append(order_item)

            # Thanh toán mô phỏng đánh dấu đã thanh toán (status = confirmed)
            pay_method_raw = (checkout_data.payment_method or "COD").strip().upper()
            is_simulated = pay_method_raw in ["SIMULATED", "MÔ PHỎNG", "MOPHONNG", "SIMULATION"]
            payment_method_str = "SIMULATED" if is_simulated else "COD"
            order_status = "confirmed" if is_simulated else "pending"

            order = Order(
                buyer_id=user_id,
                shop_id=shop_id,
                total_amount=shop_total,
                payment_method=payment_method_str,
                status=order_status,
                recipient_name=rec_name,
                recipient_phone=rec_phone,
                recipient_address=rec_address,
                items=order_items,
            )
            db.add(order)
            created_orders.append(order)
            total_all_amount += shop_total

        # Xóa các dòng đã đặt khỏi giỏ hàng trong cùng transaction
        for it in items_to_order:
            db.delete(it)

        # Commit toàn bộ transaction nếu không có lỗi
        db.commit()

        for o in created_orders:
            db.refresh(o)

    except Exception as exc:
        # Nếu có lỗi giữa chừng -> ROLLBACK ngay lập tức
        db.rollback()
        raise exc

    # 4. Chuẩn bị dữ liệu trả về
    order_responses: list[OrderResponse] = []
    for o in created_orders:
        shop_obj = db.get(Shop, o.shop_id)
        shop_name = shop_obj.name if shop_obj else f"Shop #{o.shop_id}"

        item_resps: list[OrderItemResponse] = []
        for it in o.items:
            p_obj = db.get(Product, it.product_id)
            p_name = p_obj.name if p_obj else f"Sản phẩm #{it.product_id}"
            item_resps.append(
                OrderItemResponse(
                    id=it.id,
                    product_id=it.product_id,
                    product_name=p_name,
                    quantity=it.quantity,
                    unit_price=float(it.unit_price),
                    line_total=round(float(it.unit_price) * it.quantity, 2),
                )
            )

        order_responses.append(
            OrderResponse(
                id=o.id,
                buyer_id=o.buyer_id,
                shop_id=o.shop_id,
                shop_name=shop_name,
                total_amount=float(o.total_amount),
                payment_method=o.payment_method,
                status=o.status,
                recipient_name=o.recipient_name,
                recipient_phone=o.recipient_phone,
                recipient_address=o.recipient_address,
                created_at=o.created_at,
                items=item_resps,
            )
        )

    return OrderCheckoutResponse(
        message=f"Đặt hàng thành công! Đã tách thành {len(created_orders)} đơn hàng theo từng shop.",
        total_orders_created=len(created_orders),
        total_amount=round(float(total_all_amount), 2),
        orders=order_responses,
    )


def get_user_orders(db: Session, user_id: int) -> list[OrderResponse]:
    """Lấy danh sách các đơn hàng của user."""
    stmt = (
        select(Order)
        .options(
            joinedload(Order.shop),
            joinedload(Order.items).joinedload(OrderItem.product),
        )
        .where(Order.buyer_id == user_id)
        .order_by(Order.created_at.desc())
    )
    orders = list(db.scalars(stmt).unique())

    res: list[OrderResponse] = []
    for o in orders:
        shop_name = o.shop.name if o.shop else f"Shop #{o.shop_id}"
        item_resps = [
            OrderItemResponse(
                id=it.id,
                product_id=it.product_id,
                product_name=it.product.name if it.product else f"Sản phẩm #{it.product_id}",
                quantity=it.quantity,
                unit_price=float(it.unit_price),
                line_total=round(float(it.unit_price) * it.quantity, 2),
            )
            for it in o.items
        ]
        res.append(
            OrderResponse(
                id=o.id,
                buyer_id=o.buyer_id,
                shop_id=o.shop_id,
                shop_name=shop_name,
                total_amount=float(o.total_amount),
                payment_method=o.payment_method,
                status=o.status,
                recipient_name=o.recipient_name,
                recipient_phone=o.recipient_phone,
                recipient_address=o.recipient_address,
                created_at=o.created_at,
                items=item_resps,
            )
        )
    return res


def get_order_detail(db: Session, user_id: int, order_id: int) -> OrderResponse:
    """Xem chi tiết một đơn hàng của user."""
    stmt = (
        select(Order)
        .options(
            joinedload(Order.shop),
            joinedload(Order.items).joinedload(OrderItem.product),
        )
        .where(Order.id == order_id, Order.buyer_id == user_id)
    )
    o = db.scalar(stmt)
    if o is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy đơn hàng #{order_id}",
        )

    shop_name = o.shop.name if o.shop else f"Shop #{o.shop_id}"
    item_resps = [
        OrderItemResponse(
            id=it.id,
            product_id=it.product_id,
            product_name=it.product.name if it.product else f"Sản phẩm #{it.product_id}",
            quantity=it.quantity,
            unit_price=float(it.unit_price),
            line_total=round(float(it.unit_price) * it.quantity, 2),
        )
        for it in o.items
    ]
    return OrderResponse(
        id=o.id,
        buyer_id=o.buyer_id,
        shop_id=o.shop_id,
        shop_name=shop_name,
        total_amount=float(o.total_amount),
        payment_method=o.payment_method,
        status=o.status,
        recipient_name=o.recipient_name,
        recipient_phone=o.recipient_phone,
        recipient_address=o.recipient_address,
        created_at=o.created_at,
        items=item_resps,
    )
