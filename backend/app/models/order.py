from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import relationship

from app.db.session import Base


class Address(Base):
    __tablename__ = "addresses"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    user_id = Column(BIGINT(unsigned=True), ForeignKey("users.id"), nullable=False)
    recipient_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    address_line = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)

    user = relationship("User", back_populates="addresses")


class Order(Base):
    __tablename__ = "orders"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    buyer_id = Column(BIGINT(unsigned=True), ForeignKey("users.id"), nullable=False)
    shop_id = Column(BIGINT(unsigned=True), ForeignKey("shops.id"), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(50), default="COD")  # COD hoặc MÔ PHỎNG
    status = Column(String(50), default="pending")     # pending, confirmed, shipping, completed, cancelled
    
    # Lưu thông tin nhận hàng tại thời điểm đặt đơn
    recipient_name = Column(String(100), nullable=False)
    recipient_phone = Column(String(20), nullable=False)
    recipient_address = Column(Text, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    buyer = relationship("User", back_populates="orders")
    shop = relationship("Shop", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    order_id = Column(BIGINT(unsigned=True), ForeignKey("orders.id"), nullable=False)
    product_id = Column(BIGINT(unsigned=True), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)  # Giá chốt tại thời điểm mua

    order = relationship("Order", back_populates="items")
    product = relationship("Product")