import json
import re
from collections import Counter

from sqlalchemy import Integer, String, cast, column, func, or_, select, table
from sqlalchemy.orm import Session

from app.core.avatar import avatar_url_from_key
from app.models.social import AiChatLog, Comment, Follow, Like, VideoShare
from app.models.user import User
from app.models.video import Video

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
            "video_url": video.video_url,
            "thumbnail_url": video.thumbnail_url,
            "duration_seconds": video.duration_seconds,
            "created_at": video.created_at,
            "like_count": likes_grouped.get(video.id, 0),
            "comment_count": comments_grouped.get(video.id, 0),
            "share_count": shares_grouped.get(video.id, 0),
            "is_liked": video.id in liked_video_ids,
            "is_following": True,
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
            "video_url": video.video_url,
            "thumbnail_url": video.thumbnail_url,
            "duration_seconds": video.duration_seconds,
            "created_at": video.created_at,
            "like_count": likes_grouped.get(video.id, 0),
            "comment_count": comments_grouped.get(video.id, 0),
            "share_count": shares_grouped.get(video.id, 0),
            "is_liked": video.id in liked_video_ids,
            "is_following": user.id in following_author_ids,
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

    return {
        "id": video.id,
        "user_id": video.user_id,
        "title": video.title,
        "description": video.description,
        "hashtags": tags,
        "video_url": video.video_url,
        "thumbnail_url": video.thumbnail_url,
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
                "thumbnail_url": v.thumbnail_url,
                "video_url": v.video_url,
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
            "video_url": video.video_url,
            "thumbnail_url": video.thumbnail_url,
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

