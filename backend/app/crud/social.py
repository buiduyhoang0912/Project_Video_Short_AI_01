from sqlalchemy import Integer, column, func, select, table
from sqlalchemy.orm import Session

from app.models.social import AiChatLog, Comment, Follow, Like, VideoShare

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

    like_count = db.scalar(
        select(func.count(Like.id)).where(Like.video_id == video_id)
    ) or 0
    comment_count = db.scalar(
        select(func.count(Comment.id)).where(Comment.video_id == video_id)
    ) or 0
    share_count = db.scalar(
        select(func.count(VideoShare.id)).where(VideoShare.video_id == video_id)
    ) or 0

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
