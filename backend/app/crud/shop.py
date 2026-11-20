"""Các hàm thao tác DB cho bảng shops (cửa hàng)."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.shop import Shop
from app.models.video import Video, VideoProduct
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
                "video_url": video.video_url,
                "thumbnail_url": video.thumbnail_url,
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
