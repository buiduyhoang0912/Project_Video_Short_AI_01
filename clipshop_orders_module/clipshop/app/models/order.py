import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _values(e: type[enum.Enum]) -> list[str]:
    return [m.value for m in e]


class PaymentMethod(str, enum.Enum):
    COD = "cod"
    SIMULATED = "simulated"  # thanh toán MÔ PHỎNG - không thu tiền thật (BR-09)


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPING = "shipping"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# BR-08: pending → confirmed → shipping → completed, có nhánh cancelled; không đi ngược/bỏ bước.
# Hủy chỉ cho phép khi chưa giao (pending/confirmed) - có thể chỉnh khi nhóm chốt chính sách hủy đơn.
ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDING: frozenset({OrderStatus.CONFIRMED, OrderStatus.CANCELLED}),
    OrderStatus.CONFIRMED: frozenset({OrderStatus.SHIPPING, OrderStatus.CANCELLED}),
    OrderStatus.SHIPPING: frozenset({OrderStatus.COMPLETED}),
    OrderStatus.COMPLETED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}


class Order(Base):
    """Đơn hàng. MỖI ĐƠN THUỘC ĐÚNG MỘT SHOP (BR-12): checkout giỏ nhiều shop sẽ được service
    tách thành nhiều đơn. Thông tin người nhận là bản chụp (snapshot), không phụ thuộc bảng addresses."""

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="ck_orders_total_non_negative"),
        Index("ix_orders_buyer_created", "buyer_id", "created_at"),
        Index("ix_orders_shop_status", "shop_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="RESTRICT"), nullable=False)

    recipient_name: Mapped[str] = mapped_column(String(100), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)

    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, values_callable=_values, name="payment_method"), nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, values_callable=_values, name="order_status"),
        nullable=False,
        default=OrderStatus.PENDING,
        server_default=OrderStatus.PENDING.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id"
    )

    def can_transition_to(self, new_status: OrderStatus) -> bool:
        return new_status in ALLOWED_TRANSITIONS[self.status]


class OrderItem(Base):
    """Dòng đơn hàng. unit_price/product_name là giá & tên TẠI THỜI ĐIỂM ĐẶT (BR-06)."""

    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_order_items_price_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship("Product")  # noqa: F821

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity
