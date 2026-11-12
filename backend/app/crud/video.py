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

def create_uploaded_video(
    db, user_id, title, description, video_url, thumbnail_url, duration_seconds
):
    video = Video(
        user_id=user_id,
        title=title,
        description=description,
        video_url=video_url,
        thumbnail_url=thumbnail_url,
        duration_seconds=duration_seconds,
    )
    db.add(video)
    db.flush()
    return video

def get_owned_video_for_update(db, video_id, user_id):
    query = (
        select(Video)
        .where(Video.id == video_id, Video.user_id == user_id)
        .with_for_update()
    )
    return db.scalar(query)

def update_video_description(db, video_id, user_id, description):
    video = get_owned_video_for_update(db, video_id, user_id)

    if video is None:
        return None

    video.description = description
    db.flush()
    return video

def delete_owned_video(db, video_id, user_id):
    video = get_owned_video_for_update(db, video_id, user_id)

    if video is None:
        return None

    file_urls = (video.video_url, video.thumbnail_url)
    db.delete(video)
    db.flush()
    return file_urls