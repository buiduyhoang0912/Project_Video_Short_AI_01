from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.social_auth import get_current_user
from app.crud import social as crud
from app.db.session import get_db
from app.models.social import AiChatLog, Comment, Follow, Like
from app.schemas.social import (
    ChatLogCreate,
    ChatLogOut,
    CommentCreate,
    CommentOut,
)

router = APIRouter(tags=["Tương tác video"])


def check_video(db: Session, video_id: int):
    if not crud.video_exists(db, video_id):
        raise HTTPException(404, "Không tìm thấy video")


def current_user_id(user) -> int:
    if not hasattr(user, "id"):
        raise HTTPException(
            500, "Auth phải trả về user có id"
        )
    return user.id


# 1. LIKE VIDEO
@router.post("/videos/{video_id}/likes")
def like_video(
    video_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    check_video(db, video_id)
    uid = current_user_id(user)

    if crud.find_like(db, uid, video_id) is not None:
        return {
            "message": "Bạn đã thích video này",
            "liked": True,
        }

    db.add(Like(user_id=uid, video_id=video_id))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if crud.find_like(db, uid, video_id) is None:
            raise HTTPException(
                409, "Không thể thích video"
            )

    return {"message": "Đã thích video", "liked": True}


# 2. BO LIKE VIDEO
@router.delete("/videos/{video_id}/likes")
def unlike_video(
    video_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    check_video(db, video_id)

    found = crud.find_like(
        db, current_user_id(user), video_id
    )

    if found is not None:
        db.delete(found)
        db.commit()

    return {"message": "Đã bỏ thích", "liked": False}


# 3. THEM BINH LUAN / TRA LOI
@router.post(
    "/videos/{video_id}/comments",
    response_model=CommentOut,
    status_code=201,
)
def create_comment(
    video_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    check_video(db, video_id)

    if not data.content.strip():
        raise HTTPException(
            422, "Nội dung bình luận không được để trống"
        )

    if data.parent_id is not None:
        parent = db.get(Comment, data.parent_id)

        if parent is None or parent.video_id != video_id:
            raise HTTPException(
                status_code=400,
                detail="Bình luận trả lời phải cùng video",
            )

        if parent.parent_id is not None:
            raise HTTPException(
                status_code=400,
                detail="Chỉ được trả lời bình luận 1 cấp",
            )

    comment = Comment(
        video_id=video_id,
        user_id=current_user_id(user),
        parent_id=data.parent_id,
        content=data.content.strip(),
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

    return comment


# 4. XEM BINH LUAN
@router.get(
    "/videos/{video_id}/comments",
    response_model=list[CommentOut],
)
def list_comments(
    video_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    check_video(db, video_id)

    if skip < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, "Phân trang không hợp lệ")

    return db.scalars(
        select(Comment)
        .where(Comment.video_id == video_id)
        .order_by(Comment.created_at, Comment.id)
        .offset(skip)
        .limit(limit)
    ).all()


# 5. XOA BINH LUAN
@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    comment = db.get(Comment, comment_id)

    if comment is None:
        raise HTTPException(
            404, "Không tìm thấy bình luận"
        )

    uid = current_user_id(user)

    is_comment_owner = comment.user_id == uid
    is_video_owner = (
        crud.video_owner_id(db, comment.video_id) == uid
    )
    is_admin = getattr(user, "role", "USER") == "ADMIN"

    if not (is_comment_owner or is_video_owner or is_admin):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền xóa bình luận này",
        )

    all_ids = crud.all_comment_ids_in_thread(
        db, comment_id
    )

    db.execute(
        delete(Comment).where(Comment.id.in_(all_ids))
    )
    db.commit()

    return {
        "message": "Đã xóa bình luận",
        "deleted_comments": len(all_ids),
    }


# 6. FOLLOW USER
@router.post("/users/{following_id}/follow")
def follow_user(
    following_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    uid = current_user_id(user)

    if uid == following_id:
        raise HTTPException(
            400, "Không thể tự theo dõi chính mình"
        )

    if not crud.user_exists(db, following_id):
        raise HTTPException(
            404, "Không tìm thấy người dùng"
        )

    if crud.find_follow(db, uid, following_id) is not None:
        return {
            "message": "Đã theo dõi từ trước",
            "following": True,
        }

    db.add(
        Follow(
            follower_id=uid,
            following_id=following_id,
        )
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if crud.find_follow(db, uid, following_id) is None:
            raise HTTPException(
                409, "Không thể theo dõi tài khoản"
            )

    return {"message": "Đã theo dõi", "following": True}


# 7. UNFOLLOW USER
@router.delete("/users/{following_id}/follow")
def unfollow_user(
    following_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    record = crud.find_follow(
        db, current_user_id(user), following_id
    )

    if record is not None:
        db.delete(record)
        db.commit()

    return {
        "message": "Đã bỏ theo dõi",
        "following": False,
    }


# 8. CHIA SE VIDEO
@router.post("/videos/{video_id}/share")
def share_video(
    video_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    uid = current_user_id(user)
    check_video(db, video_id)

    crud.record_video_share(db, video_id, uid)

    return {"message": "Đã ghi nhận lượt chia sẻ"}


# 9. XEM SO LUOT TUONG TAC
@router.get("/videos/{video_id}/stats")
def get_stats(
    video_id: int,
    db: Session = Depends(get_db),
):
    stats = crud.video_stats(db, video_id)

    if stats is None:
        raise HTTPException(
            404, "Không tìm thấy video"
        )

    return stats


# 10. LUU LICH SU CHAT AI
@router.post(
    "/ai/chat-logs",
    response_model=ChatLogOut,
    status_code=201,
)
def create_chat_log(
    data: ChatLogCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not data.message.strip():
        raise HTTPException(
            422, "Tin nhắn không được rỗng"
        )

    return crud.save_ai_log(
        db, current_user_id(user), "user", data.message
    )


# 11. XEM LICH SU CHAT AI
@router.get(
    "/ai/chat-logs",
    response_model=list[ChatLogOut],
)
def my_chat_logs(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if skip < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, "Phân trang không hợp lệ")

    return db.scalars(
        select(AiChatLog)
        .where(
            AiChatLog.user_id == current_user_id(user)
        )
        .order_by(AiChatLog.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()
