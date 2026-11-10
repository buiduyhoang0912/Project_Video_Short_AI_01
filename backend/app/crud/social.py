
from sqlalchemy import (
    Integer, case, column, select, table, update
)
from sqlalchemy.orm import Session

from app.models.social import AiChatLog, Comment, Follow, Like


VIDEOS = table(
    "videos",
    column("id", Integer),
    column("user_id", Integer),
    column("like_count", Integer),
    column("comment_count", Integer),
    column("share_count", Integer),
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


def change_video_count(
    db: Session, video_id: int, field: str, amount: int
):
    if field not in (
        "like_count", "comment_count", "share_count"
    ):
        raise ValueError("Tên cột không hợp lệ")

    col = VIDEOS.c[field]
    next_value = case(
        (col + amount >= 0, col + amount),
        else_=0
    )

    db.execute(
        update(VIDEOS)
        .where(VIDEOS.c.id == video_id)
        .values({field: next_value})
    )


def video_stats(db: Session, video_id: int):
    result = db.execute(
        select(
            VIDEOS.c.id,
            VIDEOS.c.like_count,
            VIDEOS.c.comment_count,
            VIDEOS.c.share_count,
        ).where(VIDEOS.c.id == video_id)
    ).first()

    if result is None:
        return None

    return {
        "video_id": result.id,
        "like_count": result.like_count,
        "comment_count": result.comment_count,
        "share_count": result.share_count,
    }


def find_like(db: Session, user_id: int, video_id: int):
    return db.scalar(
        select(Like).where(
            Like.user_id == user_id,
            Like.video_id == video_id
        )
    )


def find_follow(
    db: Session, follower_id: int, following_id: int
):
    return db.scalar(
        select(Follow).where(
            Follow.follower_id == follower_id,
            Follow.following_id == following_id
        )
    )


def all_comment_ids_in_thread(
    db: Session, root_id: int
) -> list[int]:
    found = set()
    frontier = [root_id]

    while frontier:
        batch = [x for x in frontier if x not in found]
        if not batch:
            break

        found.update(batch)
        frontier = list(
            db.scalars(
                select(Comment.id).where(
                    Comment.parent_id.in_(batch)
                )
            ).all()
        )

    return list(found)


def save_ai_log(
    db: Session, user_id: int, role: str, message: str
):
    if role not in ("user", "assistant"):
        raise ValueError("Role không hợp lệ")

    if not message.strip():
        raise ValueError("Nội dung không được rỗng")

    log = AiChatLog(
        user_id=user_id,
        role=role,
        message=message.strip()
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return log


def video_owner_id(db: Session, video_id: int):
    return db.scalar(
        select(VIDEOS.c.user_id).where(
            VIDEOS.c.id == video_id
        )
    )
