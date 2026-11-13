from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import relationship

from app.db.session import Base


class Cart(Base):
    __tablename__ = "carts"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    user_id = Column(BIGINT(unsigned=True), ForeignKey("users.id"), unique=True, nullable=False)

    user = relationship("User", back_populates="cart")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    cart_id = Column(BIGINT(unsigned=True), ForeignKey("carts.id"), nullable=False)
    product_id = Column(BIGINT(unsigned=True), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)

    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")