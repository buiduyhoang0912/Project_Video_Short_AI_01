from sqlalchemy import Integer, column, func, select, table
from sqlalchemy.orm import Session

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


# ---- THEO DOI VA FEED NGUOI THEO DOI (TASK T3D2331) ----


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
            "avatar_url": user.avatar_key,
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
            "avatar_url": user.avatar_key,
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

    results = []
    for video, user in rows:
        results.append({
            "id": video.id,
            "user_id": video.user_id,
            "author_name": user.display_name,
            "author_username": user.username,
            "author_avatar_key": user.avatar_key,
            "author_avatar_url": user.avatar_key,
            "title": video.title,
            "description": video.description,
            "video_url": video.video_url,
            "thumbnail_url": video.thumbnail_url,
            "duration_seconds": video.duration_seconds,
            "created_at": video.created_at,
            "like_count": likes_grouped.get(video.id, 0),
            "comment_count": comments_grouped.get(video.id, 0),
            "is_liked": video.id in liked_video_ids,
        })

    return results
