from sqlalchemy import select

from app.models.video import Video, VideoProduct


def add_video_product(db, video_id, product_id):
    query = select(Video.id).where(Video.id == video_id).with_for_update()
    found_id = db.execute(query).scalar_one_or_none()

    if found_id is None:
        raise ValueError("Video không tồn tại")

    query = (
        select(VideoProduct.product_id)
        .where(VideoProduct.video_id == video_id)
        .with_for_update()
    )
    product_ids = db.execute(query).scalars().all()

    if product_id in product_ids:
        raise ValueError("Sản phẩm này đã được gắn vào video")

    if len(product_ids) >= 3:
        raise ValueError("Một video chỉ được gắn tối đa 3 sản phẩm")

    link = VideoProduct(video_id=video_id, product_id=product_id)
    db.add(link)
    db.flush()
    return link