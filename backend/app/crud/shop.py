"""Các hàm thao tác DB cho bảng shops (cửa hàng)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.shop import Shop
from app.schemas.shop import ShopCreate, ShopUpdate


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

