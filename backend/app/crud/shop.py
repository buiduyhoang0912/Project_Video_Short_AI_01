"""Các hàm thao tác DB cho bảng shops, đơn hàng của shop và thống kê doanh thu."""

from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.storage import resolve_media_url
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.shop import Shop
from app.models.video import Video, VideoProduct
from app.schemas.order import OrderItemResponse, OrderResponse
from app.schemas.shop import (
    BestSellingProductItem,
    DailyRevenueItem,
    ShopAnalyticsOut,
    ShopCreate,
    ShopUpdate,
)

ALLOWED_ORDER_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"shipping", "cancelled"},
    "shipping": {"completed"},
    "completed": set(),
    "cancelled": set(),
}

STATUS_LABELS_VI: dict[str, str] = {
    "pending": "Chờ xác nhận",
    "confirmed": "Đã xác nhận",
    "shipping": "Đang giao",
    "completed": "Hoàn thành",
    "cancelled": "Đã huỷ",
}


def get_shop(db: Session, shop_id: int) -> Shop | None:
    return db.get(Shop, shop_id)


def get_public_shop(db: Session, shop_id: int) -> Shop | None:
    query = select(Shop).where(Shop.id == shop_id, Shop.status == "ACTIVE")
    return db.scalar(query)


def get_public_shops(db: Session, keyword: str | None = None) -> list[Shop]:
    query = select(Shop).where(Shop.status == "ACTIVE").order_by(Shop.id.desc())
    if keyword:
        query = query.where(Shop.name.contains(keyword))
    return list(db.scalars(query))


def get_shop_by_owner(db: Session, owner_id: int) -> Shop | None:
    query = select(Shop).where(Shop.owner_id == owner_id)
    return db.scalar(query)


def create_shop(db: Session, owner_id: int, data: ShopCreate) -> Shop:
    shop = Shop(
        owner_id=owner_id,
        name=data.name.strip(),
        avatar_key=data.avatar_key,
        description=data.description,
        address=data.address,
        status="ACTIVE",
    )
    db.add(shop)
    db.commit()
    db.refresh(shop)
    return shop


def update_shop(db: Session, shop: Shop, data: ShopUpdate) -> Shop:
    update_data = data.model_dump(exclude_unset=True)
    if "name" in update_data and isinstance(update_data["name"], str):
        update_data["name"] = update_data["name"].strip()

    for field, value in update_data.items():
        setattr(shop, field, value)

    db.commit()
    db.refresh(shop)
    return shop


def get_shop_videos(db: Session, shop: Shop) -> list[dict]:
    """Lấy danh sách video công khai (VISIBLE) của chủ shop hoặc có gắn sản phẩm của shop."""
    tagged_video_ids_subq = (
        select(VideoProduct.video_id)
        .join(Product, Product.id == VideoProduct.product_id)
        .where(Product.shop_id == shop.id)
    )

    stmt = (
        select(Video)
        .where(
            Video.status == "VISIBLE",
            or_(
                Video.user_id == shop.owner_id,
                Video.id.in_(tagged_video_ids_subq),
            ),
        )
        .order_by(Video.created_at.desc(), Video.id.desc())
    )
    videos = list(db.scalars(stmt).all())

    results: list[dict] = []
    for video in videos:
        prod_stmt = (
            select(Product)
            .join(VideoProduct, VideoProduct.product_id == Product.id)
            .where(
                VideoProduct.video_id == video.id,
                Product.shop_id == shop.id,
                Product.status == "ACTIVE",
            )
        )
        tagged_prods = list(db.scalars(prod_stmt).all())
        results.append(
            {
                "id": video.id,
                "user_id": video.user_id,
                "title": video.title,
                "description": video.description,
                "video_url": resolve_media_url(video.video_url),
                "thumbnail_url": resolve_media_url(video.thumbnail_url),
                "duration_seconds": video.duration_seconds,
                "view_count": int(video.view_count or 0),
                "status": video.status,
                "created_at": video.created_at,
                "tagged_products": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "price": float(p.price),
                        "thumbnail_url": p.thumbnail_url,
                    }
                    for p in tagged_prods
                ],
            }
        )
    return results


# ---------- Quản lý Đơn hàng của Shop & Thống kê Doanh thu / Bán chạy ----------

def _serialize_order(o: Order, shop_name: str) -> OrderResponse:
    item_resps = [
        OrderItemResponse(
            id=it.id,
            product_id=it.product_id,
            product_name=(
                it.product.name if it.product else f"Sản phẩm #{it.product_id}"
            ),
            quantity=it.quantity,
            unit_price=float(it.unit_price),
            line_total=round(float(it.unit_price) * it.quantity, 2),
        )
        for it in o.items
    ]
    is_bank = (o.payment_method or "").upper() in ("BANK_TRANSFER", "QR_TRANSFER")
    vietqr_url = None
    b_name = None
    b_num = None
    b_holder = None
    if is_bank and o.shop:
        b_name = o.shop.bank_name or "MB"
        b_num = o.shop.bank_account_number or "0987654321"
        b_holder = o.shop.bank_account_holder or shop_name.upper()
        if hasattr(o.shop, "generate_vietqr_url"):
            vietqr_url = o.shop.generate_vietqr_url(float(o.total_amount), o.id)
    pay_status = "PAID" if (o.status or "").lower() in ("confirmed", "shipping", "completed") else "UNPAID"

    return OrderResponse(
        id=o.id,
        buyer_id=o.buyer_id,
        shop_id=o.shop_id,
        shop_name=shop_name,
        total_amount=float(o.total_amount),
        payment_method=o.payment_method,
        status=(o.status or "pending").lower(),
        recipient_name=o.recipient_name,
        recipient_phone=o.recipient_phone,
        recipient_address=o.recipient_address,
        created_at=o.created_at,
        items=item_resps,
        payment_status=pay_status,
        vietqr_url=vietqr_url,
        bank_name=b_name,
        bank_account_number=b_num,
        bank_account_holder=b_holder,
    )


def get_shop_orders(
    db: Session,
    shop: Shop,
    status_filter: str | None = None,
    keyword: str | None = None,
) -> list[OrderResponse]:
    stmt = (
        select(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .where(Order.shop_id == shop.id)
        .order_by(Order.created_at.desc(), Order.id.desc())
    )
    if status_filter:
        stmt = stmt.where(Order.status == status_filter.strip().lower())

    orders = list(db.scalars(stmt).unique())

    if keyword and keyword.strip():
        kw = keyword.strip().lower()
        orders = [
            o
            for o in orders
            if kw in str(o.id)
            or kw in (o.recipient_name or "").lower()
            or kw in (o.recipient_phone or "").lower()
            or any(
                kw in (it.product.name if it.product else "").lower()
                for it in o.items
            )
        ]

    from app.crud import voucher as voucher_crud  # import muộn để tránh vòng lặp import

    return voucher_crud.attach_voucher_info(
        db, [_serialize_order(o, shop.name) for o in orders]
    )


def get_shop_order_or_error(
    db: Session, shop: Shop, order_id: int
) -> Order:
    stmt = (
        select(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .where(Order.id == order_id)
    )
    order = db.scalar(stmt)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy đơn hàng #{order_id}",
        )
    if order.shop_id != shop.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền thao tác trên đơn hàng của cửa hàng khác",
        )
    return order


def update_shop_order_status(
    db: Session, shop: Shop, order_id: int, next_status: str
) -> OrderResponse:
    order = get_shop_order_or_error(db, shop, order_id)
    current_status = (order.status or "pending").strip().lower()
    target_status = next_status.strip().lower()

    allowed_targets = ALLOWED_ORDER_TRANSITIONS.get(current_status, set())
    if target_status not in allowed_targets:
        cur_label = STATUS_LABELS_VI.get(current_status, current_status)
        tgt_label = STATUS_LABELS_VI.get(target_status, target_status)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Không thể chuyển trạng thái đơn hàng từ '{cur_label}' ({current_status}) "
                f"sang '{tgt_label}' ({target_status}). "
                "Luồng hợp lệ: Chờ xác nhận → Đã xác nhận → Đang giao → Hoàn thành (hoặc Huỷ khi chưa giao)."
            ),
        )

    # Nếu người bán huỷ đơn (từ pending hoặc confirmed) -> hoàn lại tồn kho và giảm sold_count
    if target_status == "cancelled":
        for item in order.items:
            product = db.get(Product, item.product_id)
            if product is not None:
                product.stock = int(product.stock or 0) + int(item.quantity)
                product.sold_count = max(
                    0, int(product.sold_count or 0) - int(item.quantity)
                )
        # Trả lại lượt dùng mã giảm giá của shop cho người mua (T3D2BFB)
        from app.crud import voucher as voucher_crud

        voucher_crud.release_voucher_for_order(db, order.id)

    order.status = target_status

    # Tạo thông báo đổi trạng thái đơn hàng cho người mua (T3D2BAD)
    if order.buyer_id:
        from app.crud.notification import create_notification
        if target_status == "shipping":
            msg = f"Đơn #{order.id} đang được giao"
        elif target_status == "confirmed":
            msg = f"Đơn #{order.id} đã được xác nhận"
        elif target_status == "completed":
            msg = f"Đơn #{order.id} đã hoàn thành"
        elif target_status == "cancelled":
            msg = f"Đơn #{order.id} đã bị huỷ"
        else:
            tgt_label = STATUS_LABELS_VI.get(target_status, target_status)
            msg = f"Đơn #{order.id} đã chuyển sang trạng thái: {tgt_label}"

        create_notification(
            db=db,
            recipient_id=order.buyer_id,
            actor_id=shop.owner_id,
            type="ORDER_STATUS",
            content=msg,
            order_id=order.id,
        )

    db.commit()
    db.refresh(order)
    return _serialize_order(order, shop.name)


def get_shop_analytics(
    db: Session, shop: Shop, limit_best_sellers: int = 5
) -> ShopAnalyticsOut:
    stmt = (
        select(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .where(Order.shop_id == shop.id)
        .order_by(Order.created_at.desc(), Order.id.desc())
    )
    orders = list(db.scalars(stmt).unique())

    counts = {
        "pending": 0,
        "confirmed": 0,
        "shipping": 0,
        "completed": 0,
        "cancelled": 0,
    }
    total_revenue = 0.0
    estimated_revenue = 0.0

    # Thống kê theo ngày: date_str -> {"revenue": float, "completed_orders": int, "total_orders": int}
    daily_map: dict[str, dict] = defaultdict(
        lambda: {"revenue": 0.0, "completed_orders": 0, "total_orders": 0}
    )

    # Thống kê sản phẩm bán chạy từ các đơn hàng không bị huỷ
    prod_sales: dict[int, dict] = {}

    for o in orders:
        st = (o.status or "pending").strip().lower()
        if st in counts:
            counts[st] += 1

        amt = float(o.total_amount or 0)
        date_key = (
            o.created_at.strftime("%Y-%m-%d")
            if o.created_at
            else "Chưa rõ ngày"
        )
        daily_map[date_key]["total_orders"] += 1

        if st == "completed":
            total_revenue += amt
            daily_map[date_key]["revenue"] += amt
            daily_map[date_key]["completed_orders"] += 1

        if st in ("confirmed", "shipping", "completed"):
            estimated_revenue += amt

        if st != "cancelled":
            for it in o.items:
                pid = it.product_id
                p_obj = it.product
                if pid not in prod_sales:
                    prod_sales[pid] = {
                        "product_id": pid,
                        "product_name": (
                            p_obj.name if p_obj else f"Sản phẩm #{pid}"
                        ),
                        "price": (
                            float(p_obj.price)
                            if p_obj
                            else float(it.unit_price)
                        ),
                        "stock": int(p_obj.stock) if p_obj else 0,
                        "total_quantity_sold": 0,
                        "total_revenue": 0.0,
                        "thumbnail_url": (
                            p_obj.thumbnail_url if p_obj else None
                        ),
                    }
                qty = int(it.quantity or 0)
                line_rev = float(it.unit_price or 0) * qty
                prod_sales[pid]["total_quantity_sold"] += qty
                prod_sales[pid]["total_revenue"] += line_rev

    daily_list = [
        DailyRevenueItem(
            date=d_key,
            revenue=round(info["revenue"], 2),
            completed_orders=info["completed_orders"],
            total_orders=info["total_orders"],
        )
        for d_key, info in sorted(
            daily_map.items(), key=lambda x: x[0], reverse=True
        )
    ]

    best_sellers_sorted = sorted(
        prod_sales.values(),
        key=lambda x: (x["total_quantity_sold"], x["total_revenue"]),
        reverse=True,
    )[: max(1, limit_best_sellers)]

    best_sellers_list = [
        BestSellingProductItem(
            product_id=item["product_id"],
            product_name=item["product_name"],
            price=round(item["price"], 2),
            stock=item["stock"],
            total_quantity_sold=item["total_quantity_sold"],
            total_revenue=round(item["total_revenue"], 2),
            thumbnail_url=item["thumbnail_url"],
        )
        for item in best_sellers_sorted
    ]

    return ShopAnalyticsOut(
        shop_id=shop.id,
        shop_name=shop.name,
        total_orders=len(orders),
        pending_orders=counts["pending"],
        confirmed_orders=counts["confirmed"],
        shipping_orders=counts["shipping"],
        completed_orders=counts["completed"],
        cancelled_orders=counts["cancelled"],
        total_revenue=round(total_revenue, 2),
        estimated_revenue=round(estimated_revenue, 2),
        daily_revenue=daily_list,
        best_selling_products=best_sellers_list,
    )
