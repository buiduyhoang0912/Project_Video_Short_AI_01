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

from app.crud import voucher as voucher_crud
from app.crud.notification import create_notification
from app.models.cart import Cart, CartItem
from app.models.order import Address, Order, OrderItem
from app.models.product import Product
from app.models.shop import Shop
from app.schemas.order import (
    OrderCancelResponse,
    OrderCheckout,
    OrderCheckoutResponse,
    OrderItemResponse,
    OrderResponse,
    OrderStatusTimeline,
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

        # Mã giảm giá của shop (T3D2BFB): khoá dòng mã để không vượt số lượt khi nhiều người dùng cùng lúc
        vouchers_by_shop = voucher_crud.resolve_vouchers_for_checkout(
            db, checkout_data.voucher_codes, set(items_by_shop.keys()), lock=True
        )
        voucher_info: dict[int, dict] = {}  # id(order) -> thông tin giảm giá để trả về

        created_orders: list[Order] = []
        total_all_amount = Decimal("0")
        total_before_discount = Decimal("0")
        total_discount = Decimal("0")

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

            # Kiểm tra mã giảm giá của shop và TÍNH LẠI TIỀN tại server
            voucher = vouchers_by_shop.get(shop_id)
            discount = Decimal("0")
            if voucher is not None:
                discount = voucher_crud.validate_voucher_for_order(
                    db, voucher, user_id, shop_total
                )
            shop_pay_amount = shop_total - discount

            order = Order(
                buyer_id=user_id,
                shop_id=shop_id,
                total_amount=shop_pay_amount,
                payment_method=payment_method_str,
                status=order_status,
                recipient_name=rec_name,
                recipient_phone=rec_phone,
                recipient_address=rec_address,
                items=order_items,
            )
            db.add(order)
            if voucher is not None:
                voucher_crud.record_voucher_usage(
                    db, voucher, order, user_id, shop_total, discount
                )
            voucher_info[id(order)] = {
                "subtotal_amount": float(shop_total),
                "discount_amount": float(discount),
                "voucher_code": voucher.code if voucher is not None else None,
            }
            created_orders.append(order)
            total_all_amount += shop_pay_amount
            total_before_discount += shop_total
            total_discount += discount

        # Xóa các dòng đã đặt khỏi giỏ hàng trong cùng transaction
        for it in items_to_order:
            db.delete(it)

        # Tạo thông báo đơn hàng mới cho từng chủ shop
        for o in created_orders:
            shop_for_notif = db.get(Shop, o.shop_id)
            if shop_for_notif and shop_for_notif.owner_id:
                amount_str = f"{int(o.total_amount):,}".replace(",", ".")
                create_notification(
                    db,
                    recipient_id=shop_for_notif.owner_id,
                    actor_id=user_id,
                    type="ORDER_NEW",
                    content=f"Bạn có đơn hàng mới #{o.id} ({amount_str} ₫)",
                    order_id=o.id,
                )

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

        qr_info = _extract_vietqr_info(o, shop_obj)
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
                **qr_info,
                **voucher_info.get(id(o), {}),
            )
        )

    return OrderCheckoutResponse(
        message=f"Đặt hàng thành công! Đã tách thành {len(created_orders)} đơn hàng theo từng shop.",
        total_orders_created=len(created_orders),
        total_amount=round(float(total_all_amount), 2),
        orders=order_responses,
        total_before_discount=round(float(total_before_discount), 2),
        total_discount=round(float(total_discount), 2),
    )


def build_order_timeline(order: Order) -> list[OrderStatusTimeline]:
    """Tạo danh sách các mốc trên dòng thời gian trạng thái đơn hàng (Timeline)."""
    current_status = (order.status or "PENDING").upper()
    created_at = order.created_at

    if current_status == "CANCELLED":
        return [
            OrderStatusTimeline(
                status_code="CREATED",
                title="Đặt hàng thành công",
                description="Đơn hàng đã được tạo trên hệ thống",
                timestamp=created_at,
                is_current=False,
                is_completed=True,
            ),
            OrderStatusTimeline(
                status_code="PENDING",
                title="Chờ xác nhận",
                description="Đơn hàng ở trạng thái chờ người bán xử lý",
                timestamp=created_at,
                is_current=False,
                is_completed=True,
            ),
            OrderStatusTimeline(
                status_code="CANCELLED",
                title="Đã huỷ đơn",
                description="Đơn hàng đã được huỷ và số lượng sản phẩm đã hoàn lại vào kho",
                timestamp=None,
                is_current=True,
                is_completed=True,
            ),
        ]

    stages = [
        ("CREATED", "Đặt hàng thành công", "Đơn hàng đã được ghi nhận vào hệ thống"),
        ("PENDING", "Chờ xác nhận", "Đơn hàng đang chờ người bán kiểm tra & đóng gói"),
        ("CONFIRMED", "Đã xác nhận", "Người bán đã chuẩn bị xong kiện hàng"),
        ("SHIPPED", "Đang vận chuyển", "Kiện hàng đang trên đường giao tới bạn"),
        ("DELIVERED", "Giao hàng thành công", "Đơn hàng đã giao thành công tới người nhận"),
    ]

    status_weights = {
        "CREATED": 0,
        "PENDING": 1,
        "CONFIRMED": 2,
        "SHIPPED": 3,
        "DELIVERED": 4,
    }
    cur_weight = status_weights.get(current_status, 1)

    timeline = []
    for code, title, desc in stages:
        weight = status_weights[code]
        completed = weight <= cur_weight
        is_cur = weight == cur_weight
        ts = created_at if weight == 0 else None
        timeline.append(
            OrderStatusTimeline(
                status_code=code,
                title=title,
                description=desc,
                timestamp=ts,
                is_current=is_cur,
                is_completed=completed,
            )
        )
    return timeline


def _extract_vietqr_info(o: Order, shop_obj=None) -> dict:
    """Tạo thông tin thanh toán chuyển khoản VietQR cho đơn hàng."""
    is_bank = (o.payment_method or "").upper() in ("BANK_TRANSFER", "QR_TRANSFER")
    shop = shop_obj or o.shop
    vietqr_url = None
    b_name = None
    b_num = None
    b_holder = None
    if is_bank and shop:
        b_name = getattr(shop, "bank_name", "MB") or "MB"
        b_num = getattr(shop, "bank_account_number", "0987654321") or "0987654321"
        b_holder = getattr(shop, "bank_account_holder", shop.name) or (shop.name.upper() if shop.name else "SHOP")
        if hasattr(shop, "generate_vietqr_url"):
            vietqr_url = shop.generate_vietqr_url(float(o.total_amount), o.id)
        else:
            import urllib.parse
            encoded_memo = urllib.parse.quote(f"DH{o.id}")
            encoded_holder = urllib.parse.quote(b_holder)
            vietqr_url = f"https://img.vietqr.io/image/{b_name}-{b_num}-compact2.png?amount={int(o.total_amount)}&addInfo={encoded_memo}&accountName={encoded_holder}"

    pay_status = "PAID" if (o.status or "").upper() in ("CONFIRMED", "SHIPPED", "DELIVERED", "COMPLETED") else "UNPAID"
    return {
        "payment_status": pay_status,
        "vietqr_url": vietqr_url,
        "bank_name": b_name,
        "bank_account_number": b_num,
        "bank_account_holder": b_holder,
    }


def get_user_orders(
    db: Session, user_id: int, status_filter: str | None = None
) -> list[OrderResponse]:
    """Lấy danh sách các đơn hàng của user, hỗ trợ lọc theo trạng thái."""
    stmt = (
        select(Order)
        .options(
            joinedload(Order.shop),
            joinedload(Order.items).joinedload(OrderItem.product),
        )
        .where(Order.buyer_id == user_id)
        .order_by(Order.created_at.desc())
    )
    if status_filter and status_filter.strip():
        st = status_filter.strip().upper()
        stmt = stmt.where(Order.status.ilike(st))

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
        qr_info = _extract_vietqr_info(o)
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
                timeline=build_order_timeline(o),
                **qr_info,
            )
        )
    return voucher_crud.attach_voucher_info(db, res)


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
    qr_info = _extract_vietqr_info(o)
    resp = OrderResponse(
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
        timeline=build_order_timeline(o),
        **qr_info,
    )
    return voucher_crud.attach_voucher_info(db, [resp])[0]


def cancel_order(db: Session, user_id: int, order_id: int) -> OrderCancelResponse:
    """Huỷ đơn hàng khi còn ở trạng thái Chờ xác nhận (PENDING) và hoàn tồn kho đúng một lần."""
    stmt = (
        select(Order)
        .where(Order.id == order_id, Order.buyer_id == user_id)
        .with_for_update()
    )
    order = db.scalar(stmt)

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy đơn hàng #{order_id} hoặc bạn không có quyền huỷ đơn này.",
        )

    order_status_upper = (order.status or "").upper()

    if order_status_upper == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Đơn hàng #{order_id} đã bị huỷ trước đó. Không thể huỷ lại.",
        )

    if order_status_upper != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chỉ có thể huỷ đơn khi đơn đang ở trạng thái 'Chờ xác nhận' (PENDING). Trạng thái hiện tại: '{order.status}'.",
        )

    # Lấy danh sách item của đơn hàng và hoàn lại tồn kho đúng 1 lần
    item_stmt = select(OrderItem).where(OrderItem.order_id == order_id)
    items = db.scalars(item_stmt).all()

    for it in items:
        prod_stmt = select(Product).where(Product.id == it.product_id).with_for_update()
        product = db.scalar(prod_stmt)
        if product:
            product.stock += it.quantity
            if hasattr(product, "sold_count") and product.sold_count is not None:
                if product.sold_count >= it.quantity:
                    product.sold_count -= it.quantity
                else:
                    product.sold_count = 0

    order.status = "CANCELLED"
    shop_for_notif = db.get(Shop, order.shop_id)
    if shop_for_notif and shop_for_notif.owner_id:
        create_notification(
            db,
            recipient_id=shop_for_notif.owner_id,
            actor_id=user_id,
            type="ORDER_CANCELLED",
            content=f"Khách hàng đã hủy đơn hàng #{order.id}",
            order_id=order.id,
        )
    db.commit()
    db.refresh(order)

    return OrderCancelResponse(
        message=f"Đơn hàng #{order_id} đã được huỷ thành công và số lượng sản phẩm đã được hoàn lại vào kho.",
        order_id=order.id,
        status=order.status,
        restocked_items_count=len(items),
    )

