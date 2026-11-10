from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import ForeignKey, String, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.database import Base
from app.models import Address, Cart, CartItem, Order, OrderItem, OrderStatus, PaymentMethod
from app.schemas.cart import CartRead
from app.schemas.order import OrderCreate, OrderRead


# --- stub các bảng của module khác (chỉ để test) ---
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(100))


class Shop(Base):
    __tablename__ = "shops"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"))
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[Decimal] = mapped_column()
    stock: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(20), default="active")


@pytest.fixture
def db():
    from sqlalchemy import event
    engine = create_engine("sqlite://")
    event.listen(engine, "connect", lambda c, _: c.cursor().execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        s.add_all([User(id=1, email="a@x"), Shop(id=1, name="S")])
        s.commit()
        s.add(Product(id=1, shop_id=1, name="Áo", price=Decimal("100000"), stock=5))
        s.commit()
        yield s


def test_cart_unique_and_total(db):
    cart = Cart(user_id=1, items=[CartItem(product_id=1, quantity=3)])
    db.add(cart); db.commit()
    data = CartRead.model_validate(cart)
    assert data.total_amount == Decimal("300000")
    db.add(CartItem(cart_id=cart.id, product_id=1, quantity=1))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.add(Cart(user_id=1))
    with pytest.raises(IntegrityError):
        db.commit()


def test_cart_quantity_check(db):
    db.add(Cart(user_id=1, items=[CartItem(product_id=1, quantity=0)]))
    with pytest.raises(IntegrityError):
        db.commit()


def test_order_snapshot_price_and_transitions(db):
    o = Order(
        order_code="CS-1", buyer_id=1, shop_id=1, recipient_name="An", recipient_phone="0901234567",
        shipping_address="1 Lê Lợi", payment_method=PaymentMethod.SIMULATED, total_amount=Decimal("200000"),
        items=[OrderItem(product_id=1, product_name="Áo", unit_price=Decimal("100000"), quantity=2)],
    )
    db.add(o); db.commit()
    db.get(Product, 1).price = Decimal("999")
    db.commit(); db.refresh(o)
    assert o.items[0].unit_price == Decimal("100000")
    out = OrderRead.model_validate(o)
    assert out.items[0].line_total == Decimal("200000") and out.status == OrderStatus.PENDING
    assert o.can_transition_to(OrderStatus.CONFIRMED)
    assert not o.can_transition_to(OrderStatus.SHIPPING)
    assert not o.can_transition_to(OrderStatus.COMPLETED)


def test_address_default(db):
    db.add(Address(user_id=1, recipient_name="An", phone="0901234567", address="1 Lê Lợi"))
    db.commit()
    assert db.scalars(select(Address)).one().is_default is False


def test_order_create_validation():
    ok = OrderCreate(shop_id=1, payment_method="cod", address_id=3)
    assert ok.payment_method == PaymentMethod.COD
    inline = OrderCreate(shop_id=1, payment_method="simulated", recipient_name="An",
                         recipient_phone="090 123 4567", shipping_address="1 Lê Lợi, Q1")
    assert inline.recipient_phone == "0901234567"
    with pytest.raises(ValidationError):
        OrderCreate(shop_id=1, payment_method="cod")
    with pytest.raises(ValidationError):
        OrderCreate(shop_id=1, payment_method="cod", address_id=1, recipient_name="An")
    with pytest.raises(ValidationError):
        OrderCreate(shop_id=1, payment_method="momo", address_id=1)
    with pytest.raises(ValidationError):
        OrderCreate(shop_id=1, payment_method="cod", recipient_name="An", recipient_phone="123", shipping_address="abcdef")
