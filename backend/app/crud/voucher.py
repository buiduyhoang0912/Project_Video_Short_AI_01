"""Nghiệp vụ Mã giảm giá của shop (Task T3D2BFB).

- Người bán: tạo / xem / sửa / tắt / xoá mã của shop mình.
- Người mua: xem trước số tiền được giảm (apply) trên giỏ hàng.
- Đặt hàng: khoá dòng mã (SELECT FOR UPDATE), kiểm tra lại toàn bộ điều kiện,
  tính lại tiền ở server, tăng lượt dùng và lưu lịch sử trong cùng transaction.
- Người bán huỷ đơn: trả lại lượt dùng mã.
"""

from collections import defaultdict
from datetime import datetime
from decimal import ROUND_DOWN, Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.cart import Cart, CartItem
from app.models.order import Order
from app.models.shop import Shop
from app.models.voucher import ShopVoucher, VoucherUsage
from app.schemas.voucher import (
    VoucherApplyRequest,
    VoucherApplyResponse,
    VoucherCreate,
    VoucherOut,
    VoucherPublicOut,
    VoucherUpdate,
    normalize_code,
)

ZERO = Decimal("0")


def _money(value) -> Decimal:
    return Decimal(str(value or 0))


def _fmt_vnd(value) -> str:
    return f"{int(_money(value)):,}".replace(",", ".") + "đ"


# ---------- Trạng thái & hiển thị ----------

def voucher_state(voucher: ShopVoucher, now: datetime | None = None) -> str:
    now = now or datetime.now()
    if (voucher.status or "ACTIVE").upper() != "ACTIVE":
        return "INACTIVE"
    if voucher.expires_at and voucher.expires_at < now:
        return "EXPIRED"
    if voucher.starts_at and voucher.starts_at > now:
        return "UPCOMING"
    if int(voucher.used_count or 0) >= int(voucher.usage_limit or 0):
        return "USED_UP"
    return "ACTIVE"


def _remaining(voucher: ShopVoucher) -> int:
    return max(0, int(voucher.usage_limit or 0) - int(voucher.used_count or 0))


def serialize_voucher(voucher: ShopVoucher) -> VoucherOut:
    return VoucherOut(
        id=voucher.id,
        shop_id=voucher.shop_id,
        code=voucher.code,
        description=voucher.description,
        discount_type=voucher.discount_type,
        discount_value=float(voucher.discount_value),
        max_discount_amount=(
            float(voucher.max_discount_amount)
            if voucher.max_discount_amount is not None
            else None
        ),
        min_order_amount=float(voucher.min_order_amount or 0),
        usage_limit=int(voucher.usage_limit),
        used_count=int(voucher.used_count or 0),
        remaining_uses=_remaining(voucher),
        per_user_limit=int(voucher.per_user_limit or 1),
        starts_at=voucher.starts_at,
        expires_at=voucher.expires_at,
        status=voucher.status,
        state=voucher_state(voucher),
        created_at=voucher.created_at,
    )


# ---------- Người bán quản lý mã ----------

def list_shop_vouchers(db: Session, shop: Shop) -> list[VoucherOut]:
    stmt = (
        select(ShopVoucher)
        .where(ShopVoucher.shop_id == shop.id)
        .order_by(ShopVoucher.created_at.desc(), ShopVoucher.id.desc())
    )
    return [serialize_voucher(v) for v in db.scalars(stmt).all()]


def create_voucher(db: Session, shop: Shop, data: VoucherCreate) -> VoucherOut:
    duplicate = db.scalar(
        select(ShopVoucher).where(
            ShopVoucher.shop_id == shop.id, ShopVoucher.code == data.code
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Shop đã có mã '{data.code}', vui lòng chọn mã khác",
        )

    voucher = ShopVoucher(
        shop_id=shop.id,
        code=data.code,
        description=(data.description or "").strip() or None,
        discount_type=data.discount_type,
        discount_value=data.discount_value,
        max_discount_amount=data.max_discount_amount,
        min_order_amount=data.min_order_amount,
        usage_limit=data.usage_limit,
        used_count=0,
        per_user_limit=data.per_user_limit,
        starts_at=data.starts_at,
        expires_at=data.expires_at,
        status="ACTIVE",
    )
    db.add(voucher)
    db.commit()
    db.refresh(voucher)
    return serialize_voucher(voucher)


def get_owned_voucher(db: Session, shop: Shop, voucher_id: int) -> ShopVoucher:
    voucher = db.get(ShopVoucher, voucher_id)
    if voucher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy mã giảm giá #{voucher_id}",
        )
    if voucher.shop_id != shop.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền thao tác trên mã giảm giá của cửa hàng khác",
        )
    return voucher


def update_voucher(
    db: Session, shop: Shop, voucher_id: int, data: VoucherUpdate
) -> VoucherOut:
    voucher = get_owned_voucher(db, shop, voucher_id)
    changes = data.model_dump(exclude_unset=True)

    # Tính giá trị sau khi sửa rồi kiểm tra lại các ràng buộc
    new_type = changes.get("discount_type", voucher.discount_type)
    new_value = _money(changes.get("discount_value", voucher.discount_value))
    new_start = changes.get("starts_at", voucher.starts_at)
    new_expire = changes.get("expires_at", voucher.expires_at)
    new_limit = changes.get("usage_limit", voucher.usage_limit)
    new_per_user = changes.get("per_user_limit", voucher.per_user_limit)

    if new_expire is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Hạn dùng không được để trống",
        )
    if new_type == "PERCENT" and new_value > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Giảm theo phần trăm chỉ được từ 1% đến 100%",
        )
    if new_start and new_expire <= new_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Hạn dùng phải sau thời điểm bắt đầu",
        )
    if int(new_limit) < int(voucher.used_count or 0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tổng số lượt không được nhỏ hơn số lượt đã dùng ({voucher.used_count})",
        )
    if int(new_per_user) > int(new_limit):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Số lượt mỗi người không được lớn hơn tổng số lượt",
        )

    for field, value in changes.items():
        if field == "description":
            value = (value or "").strip() or None
        setattr(voucher, field, value)
    if voucher.discount_type == "FIXED":
        voucher.max_discount_amount = None

    db.commit()
    db.refresh(voucher)
    return serialize_voucher(voucher)


def delete_voucher(db: Session, shop: Shop, voucher_id: int) -> dict:
    voucher = get_owned_voucher(db, shop, voucher_id)
    if int(voucher.used_count or 0) > 0 or voucher.usages:
        # Đã có đơn dùng mã -> chỉ tắt để giữ lịch sử đơn hàng
        voucher.status = "INACTIVE"
        db.commit()
        db.refresh(voucher)
        return {
            "action": "deactivated",
            "message": "Mã đã được dùng trong đơn hàng nên chỉ được tắt (không xoá hẳn)",
            "voucher": serialize_voucher(voucher),
        }
    db.delete(voucher)
    db.commit()
    return {"action": "deleted", "message": "Đã xoá mã giảm giá", "voucher": None}


def list_public_vouchers(db: Session, shop_id: int) -> list[VoucherPublicOut]:
    stmt = (
        select(ShopVoucher)
        .where(ShopVoucher.shop_id == shop_id, ShopVoucher.status == "ACTIVE")
        .order_by(ShopVoucher.expires_at.asc())
    )
    now = datetime.now()
    return [
        VoucherPublicOut(
            code=v.code,
            description=v.description,
            discount_type=v.discount_type,
            discount_value=float(v.discount_value),
            max_discount_amount=(
                float(v.max_discount_amount) if v.max_discount_amount is not None else None
            ),
            min_order_amount=float(v.min_order_amount or 0),
            expires_at=v.expires_at,
            remaining_uses=_remaining(v),
        )
        for v in db.scalars(stmt).all()
        if voucher_state(v, now) == "ACTIVE"
    ]


# ---------- Tính tiền & kiểm tra điều kiện (dùng chung cho apply và đặt hàng) ----------

def calculate_discount(voucher: ShopVoucher, subtotal: Decimal) -> Decimal:
    subtotal = _money(subtotal)
    if subtotal <= ZERO:
        return ZERO
    if voucher.discount_type == "PERCENT":
        discount = subtotal * _money(voucher.discount_value) / Decimal("100")
        if voucher.max_discount_amount is not None:
            discount = min(discount, _money(voucher.max_discount_amount))
    else:
        discount = _money(voucher.discount_value)
    # Tiền Việt: làm tròn xuống tới đồng, không giảm quá tiền hàng
    discount = discount.quantize(Decimal("1"), rounding=ROUND_DOWN)
    return max(ZERO, min(discount, subtotal))


def count_user_usages(db: Session, voucher_id: int, user_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(VoucherUsage.id)).where(
                VoucherUsage.voucher_id == voucher_id, VoucherUsage.user_id == user_id
            )
        )
        or 0
    )


def validate_voucher_for_order(
    db: Session,
    voucher: ShopVoucher,
    user_id: int,
    subtotal: Decimal,
    now: datetime | None = None,
) -> Decimal:
    """Kiểm tra mọi điều kiện của mã; hợp lệ thì trả về số tiền được giảm."""
    now = now or datetime.now()
    state = voucher_state(voucher, now)
    code = voucher.code

    def bad(msg: str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    if state == "INACTIVE":
        bad(f"Mã '{code}' hiện đã bị người bán tạm ngừng")
    if state == "EXPIRED":
        bad(f"Mã '{code}' đã hết hạn sử dụng")
    if state == "UPCOMING":
        bad(f"Mã '{code}' chưa đến thời gian áp dụng")
    if state == "USED_UP":
        bad(f"Mã '{code}' đã hết lượt sử dụng")

    if count_user_usages(db, voucher.id, user_id) >= int(voucher.per_user_limit or 1):
        bad(f"Bạn đã dùng hết số lượt cho phép của mã '{code}'")

    subtotal = _money(subtotal)
    min_order = _money(voucher.min_order_amount)
    if subtotal < min_order:
        bad(
            f"Mã '{code}' chỉ áp dụng cho đơn từ {_fmt_vnd(min_order)} "
            f"(đơn của shop hiện là {_fmt_vnd(subtotal)}, cần mua thêm {_fmt_vnd(min_order - subtotal)})"
        )

    return calculate_discount(voucher, subtotal)


def resolve_vouchers_for_checkout(
    db: Session, codes: list[str] | None, shop_ids: set[int], lock: bool = False
) -> dict[int, ShopVoucher]:
    """Tìm mã cho từng shop trong đơn. Trả về {shop_id: voucher}.

    - Mã không tồn tại ở bất kỳ shop nào -> 404
    - Mã có tồn tại nhưng thuộc shop không có trong đơn -> 400
    - Mỗi shop chỉ được áp 1 mã -> 400
    """
    clean_codes: list[str] = []
    for raw in codes or []:
        code = normalize_code(raw)
        if code and code not in clean_codes:
            clean_codes.append(code)
    if not clean_codes:
        return {}

    stmt = select(ShopVoucher).where(ShopVoucher.code.in_(clean_codes))
    if shop_ids:
        stmt = stmt.where(ShopVoucher.shop_id.in_(shop_ids))
    else:
        stmt = stmt.where(ShopVoucher.id == -1)
    if lock:
        stmt = stmt.with_for_update()
    matched = list(db.scalars(stmt).all())

    by_shop: dict[int, ShopVoucher] = {}
    matched_codes = set()
    for v in matched:
        if v.shop_id in by_shop:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mỗi cửa hàng chỉ được áp dụng 1 mã giảm giá cho mỗi đơn",
            )
        by_shop[v.shop_id] = v
        matched_codes.add(v.code)

    for code in clean_codes:
        if code in matched_codes:
            continue
        exists_elsewhere = db.scalar(
            select(func.count(ShopVoucher.id)).where(ShopVoucher.code == code)
        )
        if exists_elsewhere:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã '{code}' không áp dụng cho sản phẩm nào trong đơn hàng của bạn",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mã giảm giá '{code}' không tồn tại",
        )
    return by_shop


def _cart_subtotals_by_shop(
    db: Session, user_id: int, cart_item_ids: list[int] | None
) -> dict[int, Decimal]:
    cart = db.scalar(select(Cart).where(Cart.user_id == user_id))
    if cart is None:
        return {}
    items = list(
        db.scalars(
            select(CartItem)
            .options(joinedload(CartItem.product))
            .where(CartItem.cart_id == cart.id)
        ).unique()
    )
    if cart_item_ids:
        wanted = set(cart_item_ids)
        items = [it for it in items if it.id in wanted]

    totals: dict[int, Decimal] = defaultdict(lambda: ZERO)
    for it in items:
        p = it.product
        if p is None or (p.status or "").upper() != "ACTIVE":
            continue
        totals[p.shop_id] += _money(p.price) * int(it.quantity)
    return dict(totals)


def preview_apply_voucher(
    db: Session, user_id: int, data: VoucherApplyRequest
) -> VoucherApplyResponse:
    """Người mua bấm 'Áp dụng': server tự tính tiền hàng từ giỏ và số tiền được giảm."""
    totals = _cart_subtotals_by_shop(db, user_id, data.cart_item_ids)
    if not totals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giỏ hàng đang trống hoặc không có sản phẩm hợp lệ để áp mã",
        )

    by_shop = resolve_vouchers_for_checkout(db, [data.code], set(totals.keys()))
    shop_id, voucher = next(iter(by_shop.items()))
    subtotal = totals[shop_id]
    discount = validate_voucher_for_order(db, voucher, user_id, subtotal)
    shop = db.get(Shop, shop_id)

    return VoucherApplyResponse(
        voucher_id=voucher.id,
        code=voucher.code,
        shop_id=shop_id,
        shop_name=shop.name if shop else f"Shop #{shop_id}",
        discount_type=voucher.discount_type,
        discount_value=float(voucher.discount_value),
        subtotal=float(subtotal),
        discount_amount=float(discount),
        total_after_discount=float(subtotal - discount),
        message=f"Áp dụng mã '{voucher.code}' thành công: giảm {_fmt_vnd(discount)}",
    )


# ---------- Ghi nhận / hoàn lượt dùng mã gắn với đơn hàng ----------

def record_voucher_usage(
    db: Session,
    voucher: ShopVoucher,
    order: Order,
    user_id: int,
    subtotal: Decimal,
    discount: Decimal,
) -> None:
    voucher.used_count = int(voucher.used_count or 0) + 1
    db.add(
        VoucherUsage(
            voucher=voucher,
            order=order,
            user_id=user_id,
            subtotal_amount=subtotal,
            discount_amount=discount,
        )
    )


def release_voucher_for_order(db: Session, order_id: int) -> None:
    """Đơn bị huỷ -> trả lại lượt dùng mã cho người mua (không commit, để hàm gọi commit)."""
    usage = db.scalar(select(VoucherUsage).where(VoucherUsage.order_id == order_id))
    if usage is None:
        return
    voucher = db.get(ShopVoucher, usage.voucher_id)
    if voucher is not None:
        voucher.used_count = max(0, int(voucher.used_count or 0) - 1)
    db.delete(usage)


def get_order_voucher_map(db: Session, order_ids: list[int]) -> dict[int, dict]:
    """{order_id: {voucher_code, discount_amount, subtotal_amount}} để hiển thị trong đơn."""
    if not order_ids:
        return {}
    rows = db.execute(
        select(VoucherUsage, ShopVoucher.code)
        .join(ShopVoucher, ShopVoucher.id == VoucherUsage.voucher_id)
        .where(VoucherUsage.order_id.in_(order_ids))
    ).all()
    return {
        usage.order_id: {
            "voucher_code": code,
            "discount_amount": float(usage.discount_amount),
            "subtotal_amount": float(usage.subtotal_amount),
        }
        for usage, code in rows
    }


def attach_voucher_info(db: Session, responses: list) -> list:
    """Gắn thông tin mã giảm giá vào danh sách OrderResponse."""
    info = get_order_voucher_map(db, [r.id for r in responses])
    for r in responses:
        meta = info.get(r.id)
        if meta:
            r.voucher_code = meta["voucher_code"]
            r.discount_amount = meta["discount_amount"]
            r.subtotal_amount = meta["subtotal_amount"]
        else:
            r.subtotal_amount = r.total_amount
    return responses
