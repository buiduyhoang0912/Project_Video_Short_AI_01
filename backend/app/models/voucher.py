"""Bảng mã giảm giá của shop (shop_vouchers) và lịch sử dùng mã (voucher_usages).

Task T3D2BFB - [Bonus] Mã giảm giá của shop.
- Người bán tạo mã: giảm theo phần trăm (PERCENT) hoặc số tiền (FIXED),
  đơn tối thiểu, hạn dùng, tổng số lượt và số lượt mỗi người.
- Người mua nhập mã khi thanh toán, server kiểm tra và tính lại tiền.

Lưu ý: dùng bảng MỚI (không thêm cột vào bảng orders) để database MySQL cũ
của các thành viên chỉ cần create_all là chạy được, không phải ALTER TABLE.
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import relationship

from app.db.session import Base


class ShopVoucher(Base):
    __tablename__ = "shop_vouchers"
    __table_args__ = (
        UniqueConstraint("shop_id", "code", name="uq_shop_vouchers_shop_code"),
    )

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    shop_id = Column(
        BIGINT(unsigned=True), ForeignKey("shops.id"), nullable=False, index=True
    )
    code = Column(String(30), nullable=False, index=True)
    description = Column(String(255), nullable=True)

    # PERCENT: giảm theo % ; FIXED: giảm số tiền cố định
    discount_type = Column(String(10), nullable=False, default="PERCENT")
    discount_value = Column(Numeric(12, 2), nullable=False)
    # Giảm tối đa (chỉ dùng cho PERCENT, None = không giới hạn)
    max_discount_amount = Column(Numeric(12, 2), nullable=True)
    # Giá trị đơn (của shop) tối thiểu để được dùng mã
    min_order_amount = Column(Numeric(12, 2), nullable=False, default=0)

    usage_limit = Column(Integer, nullable=False, default=1)  # tổng số lượt
    used_count = Column(Integer, nullable=False, default=0)  # đã dùng
    per_user_limit = Column(Integer, nullable=False, default=1)  # lượt / người mua

    starts_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")  # ACTIVE | INACTIVE
    created_at = Column(DateTime, default=datetime.now)

    shop = relationship("Shop")
    usages = relationship(
        "VoucherUsage", back_populates="voucher", cascade="all, delete-orphan"
    )


class VoucherUsage(Base):
    __tablename__ = "voucher_usages"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    voucher_id = Column(
        BIGINT(unsigned=True), ForeignKey("shop_vouchers.id"), nullable=False, index=True
    )
    order_id = Column(
        BIGINT(unsigned=True), ForeignKey("orders.id"), nullable=False, unique=True
    )
    user_id = Column(
        BIGINT(unsigned=True), ForeignKey("users.id"), nullable=False, index=True
    )
    subtotal_amount = Column(Numeric(12, 2), nullable=False)  # tiền hàng trước giảm
    discount_amount = Column(Numeric(12, 2), nullable=False)  # số tiền được giảm
    created_at = Column(DateTime, default=datetime.now)

    voucher = relationship("ShopVoucher", back_populates="usages")
    order = relationship("Order")
