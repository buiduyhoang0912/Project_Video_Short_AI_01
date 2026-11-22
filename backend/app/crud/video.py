from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

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

# --- CRUD phục vụ Feed, Video theo User và Tăng View ---

def get_feed_videos(
    db: Session, limit: int = 10, cursor: int | None = None
) -> tuple[list[Video], int | None, bool]:
    """
    Lấy danh sách video cho Feed Dành cho bạn:
    - Bỏ qua video HIDDEN (chỉ lấy VISIBLE).
    - Ưu tiên video mới nhất và nhiều lượt xem nhất.
    - Phân trang dạng cuộn (cursor là ID của video cuối cùng ở lần tải trước).
    """
    query = select(Video).where(Video.status == "VISIBLE")

    # Nếu có cursor từ trang trước, xác định mốc để lấy tiếp
    if cursor is not None:
        ref_video = db.scalar(select(Video).where(Video.id == cursor))
        if ref_video is not None:
            query = query.where(
                or_(
                    Video.created_at < ref_video.created_at,
                    and_(
                        Video.created_at == ref_video.created_at,
                        Video.view_count < ref_video.view_count,
                    ),
                    and_(
                        Video.created_at == ref_video.created_at,
                        Video.view_count == ref_video.view_count,
                        Video.id < ref_video.id,
                    ),
                )
            )

    # Ưu tiên mới nhất -> nhiều view nhất -> id giảm dần
    query = query.order_by(
        Video.created_at.desc(),
        Video.view_count.desc(),
        Video.id.desc(),
    ).limit(limit + 1)

    items = list(db.scalars(query).all())

    has_more = len(items) > limit
    if has_more:
        items = items[:limit]

    next_cursor = items[-1].id if (items and has_more) else None
    return items, next_cursor, has_more


def get_user_videos(
    db: Session,
    user_id: int,
    limit: int = 10,
    cursor: int | None = None,
    include_hidden: bool = False,
) -> tuple[list[Video], int | None, bool]:
    """
    Lấy danh sách video của một người dùng:
    - Lọc theo user_id.
    - Mặc định chỉ lấy status == 'VISIBLE', nếu include_hidden=True thì lấy cả VISIBLE và HIDDEN.
    - Sắp xếp mới nhất trước.
    """
    query = select(Video).where(Video.user_id == user_id)
    if not include_hidden:
        query = query.where(Video.status == "VISIBLE")

    if cursor is not None:
        query = query.where(Video.id < cursor)

    query = query.order_by(Video.created_at.desc(), Video.id.desc()).limit(limit + 1)

    items = list(db.scalars(query).all())

    has_more = len(items) > limit
    if has_more:
        items = items[:limit]

    next_cursor = items[-1].id if (items and has_more) else None
    return items, next_cursor, has_more


def increment_video_view(db: Session, video_id: int) -> int | None:
    """Tăng view_count lên 1 khi người xem quá 3 giây."""
    video = db.scalar(
        select(Video).where(Video.id == video_id, Video.status == "VISIBLE").with_for_update()
    )
    if video is None:
        return None

    video.view_count = (video.view_count or 0) + 1
    db.flush()
    return video.view_count