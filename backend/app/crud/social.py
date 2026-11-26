import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
from sqlalchemy import Integer, String, cast, column, func, or_, select, table
from sqlalchemy.orm import Session

from app.core.avatar import avatar_url_from_key
from app.core.config import settings
from app.core.storage import resolve_media_url
from app.models.category import Category
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.shop import Shop
from app.models.social import AiChatLog, Comment, Follow, Like, VideoShare
from app.models.user import User
from app.models.video import Video, VideoProduct


def _get_products_by_video_ids(db: Session, video_ids: list[int]) -> dict[int, list[dict]]:
    """Lấy danh sách sản phẩm ACTIVE được gắn vào từng video theo batch (tránh N+1 query)."""
    grouped: dict[int, list[dict]] = {}
    if not video_ids:
        return grouped
    try:
        from app.crud.video import serialize_product_item
        rows = db.execute(
            select(VideoProduct.video_id, Product)
            .join(Product, VideoProduct.product_id == Product.id)
            .where(VideoProduct.video_id.in_(video_ids), Product.status == "ACTIVE")
        ).all()
        for vid, prod in rows:
            grouped.setdefault(vid, []).append(serialize_product_item(prod))
    except Exception:
        pass
    return grouped

VIDEOS = table(
    "videos",
    column("id", Integer),
    column("user_id", Integer),
)

USERS = table("users", column("id", Integer))


def video_exists(db: Session, video_id: int) -> bool:
    result = db.execute(
        select(VIDEOS.c.id).where(VIDEOS.c.id == video_id)
    ).scalar_one_or_none()

    return result is not None


def user_exists(db: Session, user_id: int) -> bool:
    result = db.execute(
        select(USERS.c.id).where(USERS.c.id == user_id)
    ).scalar_one_or_none()

    return result is not None


def video_stats(db: Session, video_id: int):
    if not video_exists(db, video_id):
        return None

    like_count = (
        db.scalar(
            select(func.count(Like.id)).where(Like.video_id == video_id)
        )
        or 0
    )
    comment_count = (
        db.scalar(
            select(func.count(Comment.id)).where(Comment.video_id == video_id)
        )
        or 0
    )
    share_count = (
        db.scalar(
            select(func.count(VideoShare.id)).where(
                VideoShare.video_id == video_id
            )
        )
        or 0
    )

    return {
        "video_id": video_id,
        "like_count": like_count,
        "comment_count": comment_count,
        "share_count": share_count,
    }


def find_like(db: Session, user_id: int, video_id: int):
    return db.scalar(
        select(Like).where(
            Like.user_id == user_id,
            Like.video_id == video_id,
        )
    )


def find_follow(db: Session, follower_id: int, following_id: int):
    return db.scalar(
        select(Follow).where(
            Follow.follower_id == follower_id,
            Follow.following_id == following_id,
        )
    )


def all_comment_ids_in_thread(db: Session, root_id: int) -> list[int]:
    found = set()
    frontier = [root_id]

    while frontier:
        batch = [x for x in frontier if x not in found]
        if not batch:
            break

        found.update(batch)
        frontier = list(
            db.scalars(
                select(Comment.id).where(Comment.parent_id.in_(batch))
            ).all()
        )

    return list(found)


def record_video_share(
    db: Session, video_id: int, user_id: int | None = None
) -> VideoShare:
    share = VideoShare(video_id=video_id, user_id=user_id)
    db.add(share)
    db.commit()
    db.refresh(share)
    return share


def save_ai_log(db: Session, user_id: int, role: str, message: str):
    if role not in ("user", "assistant"):
        raise ValueError("Role không hợp lệ")

    if not message.strip():
        raise ValueError("Nội dung không được rỗng")

    log = AiChatLog(
        user_id=user_id,
        role=role,
        message=message.strip(),
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return log


def video_owner_id(db: Session, video_id: int):
    return db.scalar(
        select(VIDEOS.c.user_id).where(VIDEOS.c.id == video_id)
    )


# ---- THEO DOI VA FEED NGUOI THEO DOI (TASK T3D2331 & T3D2428) ----


def get_follow_stats(
    db: Session, target_user_id: int, current_user_id: int | None = None
) -> dict:
    followers_count = (
        db.scalar(
            select(func.count(Follow.id)).where(
                Follow.following_id == target_user_id
            )
        )
        or 0
    )
    following_count = (
        db.scalar(
            select(func.count(Follow.id)).where(
                Follow.follower_id == target_user_id
            )
        )
        or 0
    )

    is_following = False
    if current_user_id is not None and current_user_id != target_user_id:
        is_following = (
            find_follow(db, current_user_id, target_user_id) is not None
        )

    return {
        "user_id": target_user_id,
        "followers_count": followers_count,
        "following_count": following_count,
        "is_following": is_following,
    }


def get_followers_list(
    db: Session, user_id: int, skip: int = 0, limit: int = 20
) -> list[dict]:
    query = (
        select(User, Follow.created_at)
        .join(User, Follow.follower_id == User.id)
        .where(Follow.following_id == user_id)
        .order_by(Follow.created_at.desc(), Follow.id.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = db.execute(query).all()
    return [
        {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "avatar_key": user.avatar_key,
            "avatar_url": avatar_url_from_key(user.avatar_key),
            "followed_at": created_at,
        }
        for user, created_at in rows
    ]


def get_following_list(
    db: Session, user_id: int, skip: int = 0, limit: int = 20
) -> list[dict]:
    query = (
        select(User, Follow.created_at)
        .join(User, Follow.following_id == User.id)
        .where(Follow.follower_id == user_id)
        .order_by(Follow.created_at.desc(), Follow.id.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = db.execute(query).all()
    return [
        {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "avatar_key": user.avatar_key,
            "avatar_url": avatar_url_from_key(user.avatar_key),
            "followed_at": created_at,
        }
        for user, created_at in rows
    ]


def get_following_feed(
    db: Session, current_user_id: int, skip: int = 0, limit: int = 20
) -> list[dict]:
    following_ids = list(
        db.scalars(
            select(Follow.following_id).where(
                Follow.follower_id == current_user_id
            )
        ).all()
    )

    if not following_ids:
        return []

    query = (
        select(Video, User)
        .join(User, Video.user_id == User.id)
        .where(
            Video.user_id.in_(following_ids),
            Video.status == "VISIBLE",
        )
        .order_by(Video.created_at.desc(), Video.id.desc())
        .offset(skip)
        .limit(limit)
    )

    rows = db.execute(query).all()
    if not rows:
        return []

    video_ids = [v.id for v, _ in rows]

    liked_video_ids = set(
        db.scalars(
            select(Like.video_id).where(
                Like.user_id == current_user_id,
                Like.video_id.in_(video_ids),
            )
        ).all()
    )

    likes_grouped = dict(
        db.execute(
            select(Like.video_id, func.count(Like.id))
            .where(Like.video_id.in_(video_ids))
            .group_by(Like.video_id)
        ).all()
    )

    comments_grouped = dict(
        db.execute(
            select(Comment.video_id, func.count(Comment.id))
            .where(Comment.video_id.in_(video_ids))
            .group_by(Comment.video_id)
        ).all()
    )

    shares_grouped = dict(
        db.execute(
            select(VideoShare.video_id, func.count(VideoShare.id))
            .where(VideoShare.video_id.in_(video_ids))
            .group_by(VideoShare.video_id)
        ).all()
    )

    products_grouped = _get_products_by_video_ids(db, video_ids)

    results = []
    for video, user in rows:
        results.append({
            "id": video.id,
            "user_id": video.user_id,
            "author_name": user.display_name,
            "author_username": user.username,
            "author_avatar_key": user.avatar_key,
            "author_avatar_url": avatar_url_from_key(user.avatar_key),
            "title": video.title,
            "description": video.description,
            "video_url": resolve_media_url(video.video_url),
            "thumbnail_url": resolve_media_url(video.thumbnail_url),
            "duration_seconds": video.duration_seconds,
            "created_at": video.created_at,
            "like_count": likes_grouped.get(video.id, 0),
            "comment_count": comments_grouped.get(video.id, 0),
            "share_count": shares_grouped.get(video.id, 0),
            "is_liked": video.id in liked_video_ids,
            "is_following": True,
            "products": products_grouped.get(video.id, []),
        })

    return results


def get_public_feed(
    db: Session, current_user_id: int | None = None, skip: int = 0, limit: int = 20
) -> list[dict]:
    query = (
        select(Video, User)
        .join(User, Video.user_id == User.id)
        .where(Video.status == "VISIBLE")
        .order_by(Video.created_at.desc(), Video.id.desc())
        .offset(skip)
        .limit(limit)
    )

    rows = db.execute(query).all()
    if not rows:
        return []

    video_ids = [v.id for v, _ in rows]

    liked_video_ids = set()
    following_author_ids = set()
    if current_user_id:
        liked_video_ids = set(
            db.scalars(
                select(Like.video_id).where(
                    Like.user_id == current_user_id,
                    Like.video_id.in_(video_ids),
                )
            ).all()
        )
        author_ids = [u.id for _, u in rows]
        following_author_ids = set(
            db.scalars(
                select(Follow.following_id).where(
                    Follow.follower_id == current_user_id,
                    Follow.following_id.in_(author_ids),
                )
            ).all()
        )

    likes_grouped = dict(
        db.execute(
            select(Like.video_id, func.count(Like.id))
            .where(Like.video_id.in_(video_ids))
            .group_by(Like.video_id)
        ).all()
    )

    comments_grouped = dict(
        db.execute(
            select(Comment.video_id, func.count(Comment.id))
            .where(Comment.video_id.in_(video_ids))
            .group_by(Comment.video_id)
        ).all()
    )

    shares_grouped = dict(
        db.execute(
            select(VideoShare.video_id, func.count(VideoShare.id))
            .where(VideoShare.video_id.in_(video_ids))
            .group_by(VideoShare.video_id)
        ).all()
    )

    products_grouped = _get_products_by_video_ids(db, video_ids)

    results = []
    for video, user in rows:
        results.append({
            "id": video.id,
            "user_id": video.user_id,
            "author_name": user.display_name,
            "author_username": user.username,
            "author_avatar_key": user.avatar_key,
            "author_avatar_url": avatar_url_from_key(user.avatar_key),
            "title": video.title,
            "description": video.description,
            "video_url": resolve_media_url(video.video_url),
            "thumbnail_url": resolve_media_url(video.thumbnail_url),
            "duration_seconds": video.duration_seconds,
            "created_at": video.created_at,
            "like_count": likes_grouped.get(video.id, 0),
            "comment_count": comments_grouped.get(video.id, 0),
            "share_count": shares_grouped.get(video.id, 0),
            "is_liked": video.id in liked_video_ids,
            "is_following": user.id in following_author_ids,
            "products": products_grouped.get(video.id, []),
        })

    return results


def get_video_detail(
    db: Session,
    video_id: int,
    current_user_id: int | None = None,
    increment_view: bool = True,
) -> dict | None:
    row = db.execute(
        select(Video, User)
        .join(User, Video.user_id == User.id)
        .where(Video.id == video_id)
    ).first()

    if row is None:
        return None

    video, user = row

    like_count = (
        db.scalar(
            select(func.count(Like.id)).where(Like.video_id == video_id)
        )
        or 0
    )
    comment_count = (
        db.scalar(
            select(func.count(Comment.id)).where(Comment.video_id == video_id)
        )
        or 0
    )
    share_count = (
        db.scalar(
            select(func.count(VideoShare.id)).where(
                VideoShare.video_id == video_id
            )
        )
        or 0
    )

    is_liked = False
    is_following = False
    if current_user_id is not None:
        is_liked = find_like(db, current_user_id, video_id) is not None
        if current_user_id != user.id:
            is_following = (
                find_follow(db, current_user_id, user.id) is not None
            )

    if video.status == "HIDDEN":
        return {
            "id": video.id,
            "user_id": video.user_id,
            "title": video.title,
            "description": None,
            "hashtags": [],
            "video_url": None,
            "thumbnail_url": None,
            "duration_seconds": video.duration_seconds,
            "view_count": getattr(video, "view_count", 0) or 0,
            "status": "HIDDEN",
            "is_available": False,
            "unavailable_message": "Video này đã bị ẩn và không còn khả dụng.",
            "created_at": video.created_at,
            "author_name": user.display_name,
            "author_username": user.username,
            "author_avatar_key": user.avatar_key,
            "author_avatar_url": avatar_url_from_key(user.avatar_key),
            "like_count": like_count,
            "comment_count": comment_count,
            "share_count": share_count,
            "is_liked": is_liked,
            "is_following": is_following,
            "products": [],
        }

    if increment_view:
        video.view_count = (getattr(video, "view_count", 0) or 0) + 1
        db.commit()
        db.refresh(video)

    tags = video.hashtags
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = []
    if not isinstance(tags, list):
        tags = []

    products_out = []
    try:
        from app.crud.video import get_video_products, serialize_product_item
        prods = get_video_products(db, video.id)
        products_out = [serialize_product_item(p) for p in prods]
    except Exception:
        products_out = []

    return {
        "id": video.id,
        "user_id": video.user_id,
        "title": video.title,
        "description": video.description,
        "hashtags": tags,
        "video_url": resolve_media_url(video.video_url),
        "thumbnail_url": resolve_media_url(video.thumbnail_url),
        "duration_seconds": video.duration_seconds,
        "view_count": getattr(video, "view_count", 0) or 0,
        "status": "VISIBLE",
        "is_available": True,
        "unavailable_message": None,
        "created_at": video.created_at,
        "author_name": user.display_name,
        "author_username": user.username,
        "author_avatar_key": user.avatar_key,
        "author_avatar_url": avatar_url_from_key(user.avatar_key),
        "like_count": like_count,
        "comment_count": comment_count,
        "share_count": share_count,
        "is_liked": is_liked,
        "is_following": is_following,
        "products": products_out,
    }


def get_user_profile(
    db: Session, target_user_id: int, current_user_id: int | None = None
) -> dict:
    user = db.get(User, target_user_id)
    if user is None:
        return None

    stats = get_follow_stats(db, target_user_id, current_user_id)
    video_count = (
        db.scalar(
            select(func.count(Video.id)).where(
                Video.user_id == target_user_id,
                Video.status == "VISIBLE",
            )
        )
        or 0
    )

    user_videos = db.scalars(
        select(Video)
        .where(
            Video.user_id == target_user_id,
            Video.status == "VISIBLE",
        )
        .order_by(Video.created_at.desc())
        .limit(30)
    ).all()

    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "avatar_key": user.avatar_key,
        "avatar_url": avatar_url_from_key(user.avatar_key),
        "bio": getattr(user, "bio", None),
        "role": getattr(user, "role", "USER"),
        "created_at": user.created_at,
        "followers_count": stats["followers_count"],
        "following_count": stats["following_count"],
        "is_following": stats["is_following"],
        "video_count": video_count,
        "videos": [
            {
                "id": v.id,
                "title": v.title,
                "thumbnail_url": resolve_media_url(v.thumbnail_url),
                "video_url": resolve_media_url(v.video_url),
                "view_count": getattr(v, "view_count", 0),
                "created_at": v.created_at,
            }
            for v in user_videos
        ],
    }


def search_videos(
    db: Session,
    query_str: str | None = None,
    tag: str | None = None,
    current_user_id: int | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[dict]:
    query = (
        select(Video, User)
        .join(User, Video.user_id == User.id)
        .where(Video.status == "VISIBLE")
    )

    if tag:
        clean_tag = tag.strip().lstrip("#").lower()
        tag_like = f"%{clean_tag}%"
        hash_tag_like = f"%#{clean_tag}%"
        query = query.where(
            or_(
                cast(Video.hashtags, String).ilike(tag_like),
                Video.title.ilike(hash_tag_like),
                Video.description.ilike(hash_tag_like),
                Video.title.ilike(tag_like),
            )
        )

    if query_str:
        q = query_str.strip()
        clean_q = q.lstrip("#")
        q_like = f"%{q}%"
        clean_like = f"%{clean_q}%"
        query = query.where(
            or_(
                Video.title.ilike(q_like),
                Video.description.ilike(q_like),
                Video.title.ilike(clean_like),
                Video.description.ilike(clean_like),
                cast(Video.hashtags, String).ilike(clean_like),
            )
        )

    query = (
        query.order_by(Video.created_at.desc(), Video.id.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = db.execute(query).all()
    if not rows:
        return []

    video_ids = [video.id for video, _ in rows]

    liked_video_ids = set()
    if current_user_id:
        liked_video_ids = set(
            db.scalars(
                select(Like.video_id).where(
                    Like.user_id == current_user_id,
                    Like.video_id.in_(video_ids),
                )
            ).all()
        )

    likes_grouped = dict(
        db.execute(
            select(Like.video_id, func.count(Like.id))
            .where(Like.video_id.in_(video_ids))
            .group_by(Like.video_id)
        ).all()
    )

    comments_grouped = dict(
        db.execute(
            select(Comment.video_id, func.count(Comment.id))
            .where(Comment.video_id.in_(video_ids))
            .group_by(Comment.video_id)
        ).all()
    )

    shares_grouped = dict(
        db.execute(
            select(VideoShare.video_id, func.count(VideoShare.id))
            .where(VideoShare.video_id.in_(video_ids))
            .group_by(VideoShare.video_id)
        ).all()
    )

    results = []
    for video, user in rows:
        tags = video.hashtags
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except Exception:
                tags = []
        if not isinstance(tags, list):
            tags = []

        results.append({
            "id": video.id,
            "user_id": video.user_id,
            "title": video.title,
            "description": video.description,
            "hashtags": tags,
            "video_url": resolve_media_url(video.video_url),
            "thumbnail_url": resolve_media_url(video.thumbnail_url),
            "duration_seconds": video.duration_seconds,
            "view_count": getattr(video, "view_count", 0),
            "created_at": video.created_at,
            "author_name": user.display_name,
            "author_username": user.username,
            "author_avatar_url": avatar_url_from_key(user.avatar_key),
            "like_count": likes_grouped.get(video.id, 0),
            "comment_count": comments_grouped.get(video.id, 0),
            "share_count": shares_grouped.get(video.id, 0),
            "is_liked": video.id in liked_video_ids,
        })

    return results


def search_users(
    db: Session,
    query_str: str | None = None,
    current_user_id: int | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[dict]:
    query = select(User).where(User.status == "ACTIVE")

    if query_str:
        q = query_str.strip().lstrip("@")
        if q:
            q_like = f"%{q}%"
            query = query.where(
                or_(
                    User.username.ilike(q_like),
                    User.display_name.ilike(q_like),
                )
            )

    query = query.order_by(User.id.desc()).offset(skip).limit(limit)
    users = list(db.scalars(query).all())
    if not users:
        return []

    user_ids = [u.id for u in users]

    follower_counts = dict(
        db.execute(
            select(Follow.following_id, func.count(Follow.id))
            .where(Follow.following_id.in_(user_ids))
            .group_by(Follow.following_id)
        ).all()
    )

    following_counts = dict(
        db.execute(
            select(Follow.follower_id, func.count(Follow.id))
            .where(Follow.follower_id.in_(user_ids))
            .group_by(Follow.follower_id)
        ).all()
    )

    video_counts = dict(
        db.execute(
            select(Video.user_id, func.count(Video.id))
            .where(Video.user_id.in_(user_ids), Video.status == "VISIBLE")
            .group_by(Video.user_id)
        ).all()
    )

    following_set = set()
    if current_user_id:
        following_set = set(
            db.scalars(
                select(Follow.following_id).where(
                    Follow.follower_id == current_user_id,
                    Follow.following_id.in_(user_ids),
                )
            ).all()
        )

    return [
        {
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name,
            "avatar_url": avatar_url_from_key(u.avatar_key),
            "bio": getattr(u, "bio", None),
            "role": getattr(u, "role", "USER"),
            "followers_count": follower_counts.get(u.id, 0),
            "following_count": following_counts.get(u.id, 0),
            "video_count": video_counts.get(u.id, 0),
            "is_following": u.id in following_set,
        }
        for u in users
    ]


def search_hashtags(
    db: Session,
    query_str: str | None = None,
    limit: int = 20,
) -> list[dict]:
    videos = db.execute(
        select(Video.hashtags, Video.title, Video.description).where(
            Video.status == "VISIBLE"
        )
    ).all()

    tag_counts = Counter()
    for hashtags_json, title, desc in videos:
        seen_tags_for_video = set()
        if hashtags_json:
            if isinstance(hashtags_json, list):
                for tag in hashtags_json:
                    if isinstance(tag, str) and tag.strip():
                        seen_tags_for_video.add(
                            tag.strip().lstrip("#").lower()
                        )
            elif isinstance(hashtags_json, str):
                try:
                    parsed = json.loads(hashtags_json)
                    if isinstance(parsed, list):
                        for tag in parsed:
                            if isinstance(tag, str) and tag.strip():
                                seen_tags_for_video.add(
                                    tag.strip().lstrip("#").lower()
                                )
                except Exception:
                    pass

        text_content = f"{title or ''} {desc or ''}"
        found_in_text = re.findall(r"#([\w\u0080-\uffff]+)", text_content)
        for tag in found_in_text:
            if tag.strip():
                seen_tags_for_video.add(tag.strip().lower())

        for tag in seen_tags_for_video:
            tag_counts[tag] += 1

    clean_q = query_str.strip().lstrip("#").lower() if query_str else ""
    results = []
    for tag, count in tag_counts.items():
        if not clean_q or clean_q in tag:
            results.append({"tag": tag, "video_count": count})

    results.sort(key=lambda x: (-x["video_count"], x["tag"]))
    return results[:limit]


def _extract_tags_for_video_record(
    hashtags_json, title: str | None, desc: str | None
) -> set[str]:
    seen: set[str] = set()
    if hashtags_json:
        if isinstance(hashtags_json, list):
            for tag in hashtags_json:
                if isinstance(tag, str) and tag.strip():
                    seen.add(tag.strip().lstrip("#").lower())
        elif isinstance(hashtags_json, str):
            try:
                parsed = json.loads(hashtags_json)
                if isinstance(parsed, list):
                    for tag in parsed:
                        if isinstance(tag, str) and tag.strip():
                            seen.add(tag.strip().lstrip("#").lower())
            except Exception:
                pass

    text_content = f"{title or ''} {desc or ''}"
    for tag in re.findall(r"#([\w\u0080-\uffff]+)", text_content):
        if tag.strip():
            seen.add(tag.strip().lower())
    return seen


def get_trending_hashtags(
    db: Session,
    days: int = 7,
    limit: int = 10,
) -> list[dict]:
    """Bảng xếp hạng hashtag nhiều video / tương tác nhất trong N ngày gần đây (mặc định 7 ngày)."""
    db_now = db.scalar(select(func.now()))
    if isinstance(db_now, str):
        try:
            db_now = datetime.fromisoformat(db_now)
        except Exception:
            db_now = datetime.now()
    elif db_now is None:
        db_now = datetime.now()

    cutoff = db_now - timedelta(days=max(1, days))

    videos = db.scalars(
        select(Video).where(Video.status == "VISIBLE")
    ).all()
    if not videos:
        return []

    video_ids = [v.id for v in videos]

    likes_7d = dict(
        db.execute(
            select(Like.video_id, func.count(Like.id))
            .where(
                Like.video_id.in_(video_ids),
                Like.created_at >= cutoff,
            )
            .group_by(Like.video_id)
        ).all()
    )
    comments_7d = dict(
        db.execute(
            select(Comment.video_id, func.count(Comment.id))
            .where(
                Comment.video_id.in_(video_ids),
                Comment.created_at >= cutoff,
            )
            .group_by(Comment.video_id)
        ).all()
    )
    shares_7d = dict(
        db.execute(
            select(VideoShare.video_id, func.count(VideoShare.id))
            .where(
                VideoShare.video_id.in_(video_ids),
                VideoShare.created_at >= cutoff,
            )
            .group_by(VideoShare.video_id)
        ).all()
    )

    stats_by_tag: dict[str, dict] = {}
    for v in videos:
        tags = _extract_tags_for_video_record(
            v.hashtags, v.title, v.description
        )
        if not tags:
            continue

        l_cnt = likes_7d.get(v.id, 0)
        c_cnt = comments_7d.get(v.id, 0)
        s_cnt = shares_7d.get(v.id, 0)
        inter_cnt = l_cnt + c_cnt + s_cnt
        is_recent_video = (
            v.created_at is not None and v.created_at >= cutoff
        )

        # Chỉ tính video đăng trong 7 ngày qua hoặc có tương tác mới trong 7 ngày qua
        if not is_recent_video and inter_cnt == 0:
            continue

        for tag in tags:
            entry = stats_by_tag.setdefault(
                tag,
                {
                    "tag": tag,
                    "video_count": 0,
                    "like_count": 0,
                    "comment_count": 0,
                    "share_count": 0,
                    "view_count": 0,
                    "interaction_count": 0,
                    "score": 0,
                },
            )
            entry["video_count"] += 1
            entry["like_count"] += l_cnt
            entry["comment_count"] += c_cnt
            entry["share_count"] += s_cnt
            entry["view_count"] += int(getattr(v, "view_count", 0) or 0)
            entry["interaction_count"] += inter_cnt
            entry["score"] = (
                entry["video_count"] + entry["interaction_count"]
            )

    ranked = sorted(
        stats_by_tag.values(),
        key=lambda x: (
            -x["score"],
            -x["interaction_count"],
            -x["video_count"],
            -x["view_count"],
            x["tag"],
        ),
    )[: max(1, min(limit, 50))]

    for idx, item in enumerate(ranked, start=1):
        item["rank"] = idx

    return ranked


# ---- AI CHATBOT TU VAN MUA SAM (TASK T3D2476) ----


class AiTimeoutError(Exception):
    """Lỗi khi gọi Gemini/OpenAI quá thời gian chờ (timeout)."""


class AiQuotaExceededError(Exception):
    """Lỗi khi Gemini/OpenAI hết hạn mức (quota) hoặc bị giới hạn tốc độ (429)."""


class AiProviderError(Exception):
    """Lỗi kết nối hoặc cấu hình từ nhà cung cấp AI."""


VIETNAMESE_STOP_WORDS = {
    "toi", "muon", "mua", "tim", "goi", "y", "cho", "san", "pham", "shop",
    "co", "ban", "khong", "tu", "van", "giup", "minh", "can", "loai", "nao",
    "tot", "dep", "re", "duoi", "tren", "khoang", "tu", "den", "trieu", "nghin",
    "ngan", "dong", "vnd", "gia", "mot", "cai", "chiec", "bo", "doi", "va",
    "hoac", "la", "o", "dau", "voi", "nhung", "cac", "nay", "do", "kia", "ai",
    "oi", "shop", "cua", "hang", "xin", "hoi", "em", "anh", "chi", "ad", "admin",
    "nhat", "hien", "tai", "dang", "con", "khong", "vậy", "vay", "nhé", "nhe", "a",
}


def remove_vietnamese_accents(text: str) -> str:
    if not text:
        return ""
    text = text.replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFD", text)
    return "".join(
        ch for ch in normalized if unicodedata.category(ch) != "Mn"
    ).lower()


def _parse_money_token(num_str: str, unit_str: str | None) -> float:
    val = float(num_str.replace(",", "."))
    unit = (unit_str or "").strip().lower()
    if unit in ("tr", "trieu", "triệu", "m", "củ", "cu"):
        return val * 1_000_000
    if unit in ("k", "nghin", "nghìn", "ngan", "ngàn"):
        return val * 1_000
    if val < 1000:
        return val * 1_000
    return val


def parse_price_filters_from_text(
    text: str,
) -> tuple[float | None, float | None]:
    if not text:
        return None, None

    norm = remove_vietnamese_accents(text)

    # Khoảng giá: "tu 100k den 500k" hoặc "100k - 500k"
    range_match = re.search(
        r"(?:tu|khoang)?\s*(\d+(?:[.,]\d+)?)\s*(k|tr|trieu|nghin|ngan|m)?\s*(?:den|-|toi)\s*(\d+(?:[.,]\d+)?)\s*(k|tr|trieu|nghin|ngan|m)?",
        norm,
    )
    if range_match:
        g1, u1, g2, u2 = range_match.groups()
        if u2 and not u1:
            u1 = u2
        p1 = _parse_money_token(g1, u1)
        p2 = _parse_money_token(g2, u2)
        return min(p1, p2), max(p1, p2)

    # Giá tối đa: "duoi 500k", "toi da 1 trieu", "< 300k", "khong qua 200k"
    max_match = re.search(
        r"(?:duoi|toi da|khong qua|nho hon|<|<=)\s*(\d+(?:[.,]\d+)?)\s*(k|tr|trieu|nghin|ngan|m|dong|vnd)?",
        norm,
    )
    if max_match:
        num_s, unit_s = max_match.groups()
        return None, _parse_money_token(num_s, unit_s)

    # Giá tối thiểu: "tren 200k", "tu 500k tro len", "> 500k"
    min_match = re.search(
        r"(?:tren|lon hon|>|>=)\s*(\d+(?:[.,]\d+)?)\s*(k|tr|trieu|nghin|ngan|m|dong|vnd)?",
        norm,
    )
    if min_match:
        num_s, unit_s = min_match.groups()
        return _parse_money_token(num_s, unit_s), None

    return None, None


def extract_product_search_tokens(query: str) -> list[str]:
    if not query:
        return []
    norm = remove_vietnamese_accents(query)
    # Loại bỏ các cụm chỉ giá tiền như 500k, 2tr để không làm nhiễu từ khóa tên sản phẩm
    norm = re.sub(
        r"\b\d+(?:[.,]\d+)?\s*(?:k|tr|trieu|nghin|ngan|m|dong|vnd)\b",
        " ",
        norm,
    )
    raw_tokens = re.findall(r"[a-z0-9]+", norm)
    tokens = [
        t
        for t in raw_tokens
        if t not in VIETNAMESE_STOP_WORDS and (len(t) >= 2 or t.isdigit())
    ]
    return tokens


def search_products_in_mysql(
    db: Session,
    query: str = "",
    min_price: float | None = None,
    max_price: float | None = None,
    limit: int = 5,
) -> list[dict]:
    """Hàm tìm sản phẩm có thật trong MySQL (chỉ lấy sản phẩm ACTIVE của shop ACTIVE còn hàng)."""
    parsed_min, parsed_max = parse_price_filters_from_text(query)
    if min_price is None and parsed_min is not None:
        min_price = parsed_min
    if max_price is None and parsed_max is not None:
        max_price = parsed_max

    stmt = (
        select(
            Product,
            Shop.name.label("shop_name"),
            Category.name.label("category_name"),
        )
        .join(Shop, Product.shop_id == Shop.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(
            func.upper(Product.status) == "ACTIVE",
            func.upper(Shop.status) == "ACTIVE",
            Product.stock > 0,
        )
    )

    if min_price is not None:
        stmt = stmt.where(Product.price >= Decimal(str(min_price)))
    if max_price is not None:
        stmt = stmt.where(Product.price <= Decimal(str(max_price)))

    rows = db.execute(
        stmt.order_by(Product.sold_count.desc(), Product.id.desc())
    ).all()
    if not rows:
        return []

    product_ids = [p.id for p, _, _ in rows]
    images_rows = db.execute(
        select(ProductImage.product_id, ProductImage.object_key)
        .where(ProductImage.product_id.in_(product_ids))
        .order_by(
            ProductImage.is_primary.desc(),
            ProductImage.sort_order.asc(),
            ProductImage.id.asc(),
        )
    ).all()
    primary_img_map: dict[int, str] = {}
    for pid, obj_key in images_rows:
        if pid not in primary_img_map and obj_key:
            primary_img_map[pid] = obj_key

    tokens = extract_product_search_tokens(query)
    norm_full_query = " ".join(tokens)

    scored_items: list[tuple[int, int, dict]] = []
    for product, shop_name, category_name in rows:
        item_dict = {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": float(product.price),
            "stock": product.stock,
            "sold_count": product.sold_count or 0,
            "shop_id": product.shop_id,
            "shop_name": shop_name,
            "category_name": category_name,
            "thumbnail_url": primary_img_map.get(product.id)
            or getattr(product, "thumbnail_url", None),
            "link": f"pages/product.html?id={product.id}",
        }

        if not tokens:
            scored_items.append((1, product.sold_count or 0, item_dict))
            continue

        norm_name = remove_vietnamese_accents(product.name or "")
        norm_cat = remove_vietnamese_accents(category_name or "")
        norm_desc = remove_vietnamese_accents(product.description or "")
        norm_shop = remove_vietnamese_accents(shop_name or "")
        searchable_blob = f"{norm_name} {norm_cat} {norm_desc} {norm_shop}"

        score = 0
        if norm_full_query and norm_full_query in norm_name:
            score += 10
        if norm_full_query and norm_full_query in norm_cat:
            score += 8

        matched_token_count = 0
        for tok in tokens:
            if tok in norm_name:
                score += 4
                matched_token_count += 1
            elif tok in norm_cat:
                score += 3
                matched_token_count += 1
            elif tok in searchable_blob:
                score += 1
                matched_token_count += 1

        if len(tokens) >= 2 and matched_token_count == len(tokens):
            score += 5

        if score > 0:
            scored_items.append((score, product.sold_count or 0, item_dict))

    scored_items.sort(
        key=lambda x: (-x[0], -x[1], x[2]["price"], x[2]["id"])
    )
    return [item for _, _, item in scored_items[: max(1, min(limit, 20))]]


def get_user_daily_chat_quota(
    db: Session,
    user_id: int,
    daily_limit: int | None = None,
) -> dict:
    """Kiểm tra số câu hỏi AI người dùng đã hỏi trong ngày hôm nay."""
    max_questions = (
        daily_limit
        if daily_limit is not None
        else max(1, int(settings.AI_DAILY_QUESTION_LIMIT))
    )

    used_today = (
        db.scalar(
            select(func.count(AiChatLog.id)).where(
                AiChatLog.user_id == user_id,
                AiChatLog.role == "user",
                func.date(AiChatLog.created_at) == func.date(func.now()),
            )
        )
        or 0
    )

    return {
        "daily_limit": max_questions,
        "used_today": used_today,
        "remaining_today": max(0, max_questions - used_today),
    }


def _build_system_prompt(products: list[dict]) -> str:
    if products:
        products_json = json.dumps(products, ensure_ascii=False, indent=2)
    else:
        products_json = "[] (Không tìm thấy sản phẩm nào khớp trong MySQL)"

    return (
        "Bạn là Trợ lý AI tư vấn mua sắm chính thức của nền tảng ClipShop AI.\n"
        "QUY TẮC BẮT BUỘC:\n"
        "1. Bạn CHỈ ĐƯỢC PHÉP gợi ý các sản phẩm CÓ THẬT nằm trong danh sách kết quả truy vấn từ cơ sở dữ liệu MySQL dưới đây (hoặc từ tool `search_products_in_mysql`).\n"
        "2. TUYỆT ĐỐI KHÔNG tự bịa ra tên sản phẩm, mức giá hoặc đường dẫn không có trong MySQL.\n"
        "3. Nếu danh sách sản phẩm rỗng, hãy lịch sự thông báo hiện tại cửa hàng chưa có sản phẩm phù hợp với yêu cầu này và gợi ý khách thử tìm từ khóa hoặc mức giá khác.\n"
        "4. Khi giới thiệu mỗi sản phẩm, BẮT BUỘC ghi rõ: Tên sản phẩm, Giá bán (VNĐ), Tên shop và kèm đường dẫn (link) dạng `pages/product.html?id={id}`.\n"
        "5. Trả lời ngắn gọn, thân thiện bằng tiếng Việt.\n\n"
        f"DANH SÁCH SẢN PHẨM THẬT TỪ MYSQL:\n{products_json}"
    )


def ensure_real_product_links_in_reply(
    reply_text: str, products: list[dict]
) -> str:
    text = (reply_text or "").strip()
    if not products:
        return text

    missing_links = [
        p for p in products if p["link"] not in text
    ]
    if missing_links:
        lines = ["\n\n🔗 **Link sản phẩm gợi ý cho bạn:**"]
        for p in products:
            price_fmt = f"{int(p['price']):,}".replace(",", ".") + " ₫"
            lines.append(
                f"- **{p['name']}** ({price_fmt} · {p.get('shop_name') or 'ClipShop'}): {p['link']}"
            )
        text = text + "\n".join(lines)
    return text


def build_local_mysql_shopping_reply(
    user_message: str, products: list[dict]
) -> str:
    if not products:
        return (
            "Hiện tại hệ thống chưa tìm thấy sản phẩm nào có sẵn trong kho khớp với yêu cầu "
            f'"{user_message.strip()}". Bạn hãy thử tìm với từ khóa khác hoặc điều chỉnh khoảng giá nhé!'
        )

    lines = [
        f"Dựa trên dữ liệu sản phẩm hiện có tại ClipShop AI, mình gợi ý cho bạn {len(products)} sản phẩm phù hợp nhất:"
    ]
    for idx, p in enumerate(products, start=1):
        price_fmt = f"{int(p['price']):,}".replace(",", ".") + " ₫"
        shop_str = p.get("shop_name") or "ClipShop"
        cat_str = f" · Danh mục: {p['category_name']}" if p.get("category_name") else ""
        lines.append(
            f"{idx}. **{p['name']}** — Giá: **{price_fmt}** (Shop: {shop_str}{cat_str}, còn {p['stock']} sản phẩm)\n"
            f"   👉 Xem chi tiết: {p['link']}"
        )
    return "\n".join(lines)


def _call_gemini_api(
    db: Session,
    user_message: str,
    initial_products: list[dict],
    api_key: str,
    model_name: str,
    timeout_sec: float,
) -> tuple[str, list[dict]]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    tools = [
        {
            "function_declarations": [
                {
                    "name": "search_products_in_mysql",
                    "description": "Tìm kiếm sản phẩm có thật trong cơ sở dữ liệu MySQL của ClipShop AI theo từ khóa và khoảng giá.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "query": {
                                "type": "STRING",
                                "description": "Từ khóa tên sản phẩm hoặc danh mục cần tìm",
                            },
                            "min_price": {
                                "type": "NUMBER",
                                "description": "Giá tối thiểu (VNĐ)",
                            },
                            "max_price": {
                                "type": "NUMBER",
                                "description": "Giá tối đa (VNĐ)",
                            },
                        },
                    },
                }
            ]
        }
    ]

    products = list(initial_products)
    payload = {
        "system_instruction": {
            "parts": [{"text": _build_system_prompt(products)}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": user_message}]}
        ],
        "tools": tools,
        "generationConfig": {"temperature": 0.2},
    }

    try:
        with httpx.Client(timeout=timeout_sec) as client:
            resp = client.post(url, json=payload)

            if resp.status_code == 429:
                raise AiQuotaExceededError(
                    "Hệ thống AI (Gemini) hiện đã hết hạn mức (quota) hoặc đang quá tải. Vui lòng thử lại sau ít phút."
                )

            if resp.status_code >= 400:
                body_text = resp.text.lower()
                if "quota" in body_text or "resource_exhausted" in body_text or "rate_limit" in body_text:
                    raise AiQuotaExceededError(
                        "Hệ thống AI (Gemini) hiện đã hết hạn mức (quota) hoặc đang quá tải. Vui lòng thử lại sau ít phút."
                    )
                if resp.status_code in (401, 403):
                    raise AiProviderError(
                        "Khóa kết nối GEMINI_API_KEY trong file .env không hợp lệ hoặc đã hết hạn."
                    )
                raise AiProviderError(
                    f"Dịch vụ AI tạm thời gián đoạn (mã lỗi {resp.status_code}). Vui lòng thử lại sau."
                )

            data = resp.json()
            candidates = data.get("candidates") or []
            if not candidates:
                return build_local_mysql_shopping_reply(user_message, products), products

            parts = (candidates[0].get("content") or {}).get("parts") or []
            fn_call = next(
                (p.get("functionCall") for p in parts if p.get("functionCall")),
                None,
            )

            # Nếu Gemini yêu cầu gọi hàm search_products_in_mysql -> thực thi trên MySQL rồi gửi lại
            if fn_call and fn_call.get("name") == "search_products_in_mysql":
                args = fn_call.get("args") or {}
                q_arg = args.get("query") or user_message
                min_p = args.get("min_price")
                max_p = args.get("max_price")
                products = search_products_in_mysql(
                    db,
                    query=str(q_arg),
                    min_price=float(min_p) if min_p is not None else None,
                    max_price=float(max_p) if max_p is not None else None,
                    limit=5,
                )

                followup_payload = {
                    "system_instruction": {
                        "parts": [{"text": _build_system_prompt(products)}]
                    },
                    "contents": [
                        {"role": "user", "parts": [{"text": user_message}]},
                        {"role": "model", "parts": [{"functionCall": fn_call}]},
                        {
                            "role": "function",
                            "parts": [
                                {
                                    "functionResponse": {
                                        "name": "search_products_in_mysql",
                                        "response": {"products": products},
                                    }
                                }
                            ],
                        },
                    ],
                    "generationConfig": {"temperature": 0.2},
                }
                resp2 = client.post(url, json=followup_payload)
                if resp2.status_code == 429:
                    raise AiQuotaExceededError(
                        "Hệ thống AI (Gemini) hiện đã hết hạn mức (quota) hoặc đang quá tải. Vui lòng thử lại sau ít phút."
                    )
                if resp2.status_code >= 400:
                    return build_local_mysql_shopping_reply(user_message, products), products
                data2 = resp2.json()
                cands2 = data2.get("candidates") or []
                parts2 = (
                    (cands2[0].get("content") or {}).get("parts") or []
                    if cands2
                    else []
                )
                text_out = "\n".join(
                    p.get("text", "") for p in parts2 if p.get("text")
                ).strip()
                if text_out:
                    return ensure_real_product_links_in_reply(text_out, products), products

            text_out = "\n".join(
                p.get("text", "") for p in parts if p.get("text")
            ).strip()
            if text_out:
                return ensure_real_product_links_in_reply(text_out, products), products

            return build_local_mysql_shopping_reply(user_message, products), products

    except (httpx.TimeoutException, TimeoutError) as exc:
        raise AiTimeoutError(
            "Trợ lý AI phản hồi quá thời gian chờ (timeout). Vui lòng thử lại sau giây lát."
        ) from exc
    except httpx.RequestError as exc:
        raise AiProviderError(
            "Không thể kết nối tới máy chủ AI. Vui lòng kiểm tra kết nối mạng và thử lại."
        ) from exc


def _call_openai_api(
    db: Session,
    user_message: str,
    initial_products: list[dict],
    api_key: str,
    model_name: str,
    timeout_sec: float,
) -> tuple[str, list[dict]]:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_products_in_mysql",
                "description": "Tìm sản phẩm có thật trong cơ sở dữ liệu MySQL của ClipShop AI.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Từ khóa tên sản phẩm hoặc danh mục",
                        },
                        "min_price": {"type": "number"},
                        "max_price": {"type": "number"},
                    },
                },
            },
        }
    ]

    products = list(initial_products)
    messages = [
        {"role": "system", "content": _build_system_prompt(products)},
        {"role": "user", "content": user_message},
    ]

    try:
        with httpx.Client(timeout=timeout_sec) as client:
            resp = client.post(
                url,
                headers=headers,
                json={
                    "model": model_name,
                    "messages": messages,
                    "tools": tools,
                    "temperature": 0.2,
                },
            )

            if resp.status_code == 429:
                raise AiQuotaExceededError(
                    "Hệ thống AI (OpenAI) hiện đã hết hạn mức (quota) hoặc đang quá tải. Vui lòng thử lại sau ít phút."
                )

            if resp.status_code >= 400:
                body_text = resp.text.lower()
                if "insufficient_quota" in body_text or "rate_limit" in body_text or "quota" in body_text:
                    raise AiQuotaExceededError(
                        "Hệ thống AI (OpenAI) hiện đã hết hạn mức (quota) hoặc đang quá tải. Vui lòng thử lại sau ít phút."
                    )
                if resp.status_code in (401, 403):
                    raise AiProviderError(
                        "Khóa kết nối OPENAI_API_KEY trong file .env không hợp lệ hoặc đã hết hạn."
                    )
                raise AiProviderError(
                    f"Dịch vụ AI tạm thời gián đoạn (mã lỗi {resp.status_code}). Vui lòng thử lại sau."
                )

            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                return build_local_mysql_shopping_reply(user_message, products), products

            msg = choices[0].get("message") or {}
            tool_calls = msg.get("tool_calls") or []

            if tool_calls:
                tc = tool_calls[0]
                fn = tc.get("function") or {}
                if fn.get("name") == "search_products_in_mysql":
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except Exception:
                        args = {}
                    q_arg = args.get("query") or user_message
                    min_p = args.get("min_price")
                    max_p = args.get("max_price")
                    products = search_products_in_mysql(
                        db,
                        query=str(q_arg),
                        min_price=float(min_p) if min_p is not None else None,
                        max_price=float(max_p) if max_p is not None else None,
                        limit=5,
                    )
                    messages[0] = {
                        "role": "system",
                        "content": _build_system_prompt(products),
                    }
                    messages.append(msg)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.get("id", "call_1"),
                            "content": json.dumps(
                                {"products": products}, ensure_ascii=False
                            ),
                        }
                    )
                    resp2 = client.post(
                        url,
                        headers=headers,
                        json={
                            "model": model_name,
                            "messages": messages,
                            "temperature": 0.2,
                        },
                    )
                    if resp2.status_code == 429:
                        raise AiQuotaExceededError(
                            "Hệ thống AI (OpenAI) hiện đã hết hạn mức (quota) hoặc đang quá tải. Vui lòng thử lại sau ít phút."
                        )
                    if resp2.status_code < 400:
                        c2 = (resp2.json().get("choices") or [{}])[0]
                        content2 = (c2.get("message") or {}).get("content") or ""
                        if content2.strip():
                            return (
                                ensure_real_product_links_in_reply(content2, products),
                                products,
                            )

            content = (msg.get("content") or "").strip()
            if content:
                return ensure_real_product_links_in_reply(content, products), products

            return build_local_mysql_shopping_reply(user_message, products), products

    except (httpx.TimeoutException, TimeoutError) as exc:
        raise AiTimeoutError(
            "Trợ lý AI phản hồi quá thời gian chờ (timeout). Vui lòng thử lại sau giây lát."
        ) from exc
    except httpx.RequestError as exc:
        raise AiProviderError(
            "Không thể kết nối tới máy chủ AI. Vui lòng kiểm tra kết nối mạng và thử lại."
        ) from exc


def generate_ai_shopping_reply(
    db: Session,
    user_message: str,
) -> tuple[str, list[dict], str]:
    """Tìm sản phẩm thật trong MySQL và gọi Gemini/OpenAI (hoặc bộ tư vấn MySQL nội bộ nếu chưa cấu hình key)."""
    matched_products = search_products_in_mysql(db, query=user_message, limit=5)

    provider_pref = (settings.AI_PROVIDER or "auto").strip().lower()
    gemini_key = (settings.GEMINI_API_KEY or "").strip()
    openai_key = (settings.OPENAI_API_KEY or "").strip()
    timeout_sec = max(1.0, float(settings.AI_TIMEOUT_SECONDS or 15.0))

    if provider_pref == "gemini" or (provider_pref == "auto" and gemini_key):
        if not gemini_key:
            raise AiProviderError(
                "Chưa cấu hình GEMINI_API_KEY trong file .env."
            )
        reply, final_products = _call_gemini_api(
            db=db,
            user_message=user_message,
            initial_products=matched_products,
            api_key=gemini_key,
            model_name=settings.GEMINI_MODEL or "gemini-2.0-flash",
            timeout_sec=timeout_sec,
        )
        return reply, final_products, "gemini"

    if provider_pref == "openai" or (provider_pref == "auto" and openai_key):
        if not openai_key:
            raise AiProviderError(
                "Chưa cấu hình OPENAI_API_KEY trong file .env."
            )
        reply, final_products = _call_openai_api(
            db=db,
            user_message=user_message,
            initial_products=matched_products,
            api_key=openai_key,
            model_name=settings.OPENAI_MODEL or "gpt-4o-mini",
            timeout_sec=timeout_sec,
        )
        return reply, final_products, "openai"

    reply = build_local_mysql_shopping_reply(user_message, matched_products)
    return reply, matched_products, "mysql-advisor"

