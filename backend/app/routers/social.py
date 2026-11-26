from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user, get_optional_user
from app.crud import social as crud
from app.crud import notification as notif_crud
from app.db.session import get_db
from app.models.social import AiChatLog, Comment, Follow, Like
from app.models.user import User
from app.models.video import Video
from app.schemas.social import (
    AiChatResponse,
    AiQuotaOut,
    ChatLogCreate,
    ChatLogOut,
    CommentCreate,
    CommentOut,
    FollowStats,
    FollowingFeedItem,
    HashtagItem,
    SearchResultOut,
    SearchUserItem,
    SearchVideoItem,
    TrendingHashtagItem,
    UserFollowItem,
    UserProfileOut,
    VideoDetailOut,
    VideoShareOut,
    VideoStatusUpdate,
)

router = APIRouter(tags=["Tương tác video"])


def check_video(db: Session, video_id: int):
    if not crud.video_exists(db, video_id):
        raise HTTPException(404, "Không tìm thấy video")


def check_video_available(db: Session, video_id: int):
    """Video phải tồn tại VÀ đang hiển thị (T3D1DB4).

    Video bị Admin/chủ ẩn không được nhận thêm tương tác (thích, bình luận)
    và không được lộ danh sách bình luận ra công khai. Cùng quy ước 400 với /share.
    """
    check_video(db, video_id)
    status_value = db.scalar(select(Video.status).where(Video.id == video_id))
    if status_value == "HIDDEN":
        raise HTTPException(400, "Video này đã bị ẩn và không còn khả dụng")


def check_user(db: Session, user_id: int):
    if not crud.user_exists(db, user_id):
        raise HTTPException(404, "Không tìm thấy người dùng")


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
    check_video_available(db, video_id)
    uid = current_user_id(user)

    if crud.find_like(db, uid, video_id) is not None:
        return {
            "message": "Bạn đã thích video này",
            "liked": True,
        }

    try:
        db.add(Like(user_id=uid, video_id=video_id))

        # Tạo thông báo thích video cho chủ video (T3D2BAD)
        video = db.get(Video, video_id)
        if video and video.user_id != uid:
            actor_name = user.display_name or user.username
            notif_crud.create_notification(
                db=db,
                recipient_id=video.user_id,
                actor_id=uid,
                type="LIKE",
                content=f"{actor_name} đã thích video của bạn",
                video_id=video_id,
            )

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
    check_video_available(db, video_id)

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

    try:
        db.add(comment)

        # Tạo thông báo bình luận video cho chủ video (T3D2BAD)
        video = db.get(Video, video_id)
        actor_name = user.display_name or user.username
        if video and video.user_id != user.id:
            notif_crud.create_notification(
                db=db,
                recipient_id=video.user_id,
                actor_id=user.id,
                type="COMMENT",
                content=f"{actor_name} đã bình luận video của bạn",
                video_id=video_id,
            )

        # Nếu là trả lời bình luận -> báo thêm cho tác giả bình luận gốc
        if data.parent_id is not None and parent and parent.user_id != user.id:
            if not video or parent.user_id != video.user_id:
                notif_crud.create_notification(
                    db=db,
                    recipient_id=parent.user_id,
                    actor_id=user.id,
                    type="COMMENT",
                    content=f"{actor_name} đã trả lời bình luận của bạn",
                    video_id=video_id,
                )

        db.commit()
        db.refresh(comment)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "Không thể tạo bình luận"
        )

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
    check_video_available(db, video_id)

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

    check_user(db, following_id)

    if crud.find_follow(db, uid, following_id) is not None:
        return {
            "message": "Đã theo dõi từ trước",
            "following": True,
        }

    try:
        db.add(
            Follow(
                follower_id=uid,
                following_id=following_id,
            )
        )

        # Tạo thông báo theo dõi cho người được theo dõi (T3D2BAD)
        if following_id != uid:
            actor_name = user.display_name or user.username
            notif_crud.create_notification(
                db=db,
                recipient_id=following_id,
                actor_id=uid,
                type="FOLLOW",
                content=f"{actor_name} đã bắt đầu theo dõi bạn",
            )

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


# 8. SO NGUOI THEO DOI / DANG THEO DOI (TASK T3D2331)
@router.get(
    "/users/{user_id}/follow-stats",
    response_model=FollowStats,
)
def get_user_follow_stats(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    check_user(db, user_id)
    cid = current_user.id if current_user else None
    return crud.get_follow_stats(db, user_id, cid)


# 9. DANH SACH NGUOI THEO DOI (FOLLOWERS) (TASK T3D2331)
@router.get(
    "/users/{user_id}/followers",
    response_model=list[UserFollowItem],
)
def list_followers(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    check_user(db, user_id)

    if skip < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, "Phân trang không hợp lệ")

    return crud.get_followers_list(db, user_id, skip=skip, limit=limit)


# 10. DANH SACH DANG THEO DOI (FOLLOWING) (TASK T3D2331)
@router.get(
    "/users/{user_id}/following",
    response_model=list[UserFollowItem],
)
def list_following(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    check_user(db, user_id)

    if skip < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, "Phân trang không hợp lệ")

    return crud.get_following_list(db, user_id, skip=skip, limit=limit)


# 11. FEED VIDEO CUA NHUNG NGUOI DANG THEO DOI (TASK T3D2331)
@router.get(
    "/videos/feed/following",
    response_model=list[FollowingFeedItem],
)
@router.get(
    "/feed/following",
    response_model=list[FollowingFeedItem],
    include_in_schema=False,
)
def get_following_feed(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if skip < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, "Phân trang không hợp lệ")

    uid = current_user_id(user)
    return crud.get_following_feed(db, uid, skip=skip, limit=limit)


# 11B. FEED VIDEO CONG KHAI / DÀNH CHO BẠN (TASK T3D2428)
@router.get(
    "/videos/feed/for-you",
    response_model=list[FollowingFeedItem],
)
@router.get(
    "/feed/for-you",
    response_model=list[FollowingFeedItem],
    include_in_schema=False,
)
def get_for_you_feed(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    if skip < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, "Phân trang không hợp lệ")

    cid = current_user.id if current_user else None
    return crud.get_public_feed(db, current_user_id=cid, skip=skip, limit=limit)


# 11C. THONG TIN HO SO NGUOI DUNG (TASK T3D2428)
@router.get(
    "/users/{user_id}/profile",
    response_model=UserProfileOut,
)
def get_user_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    check_user(db, user_id)
    cid = current_user.id if current_user else None
    profile = crud.get_user_profile(db, target_user_id=user_id, current_user_id=cid)
    if profile is None:
        raise HTTPException(404, "Không tìm thấy người dùng")
    return profile


# 11D. XEM CHI TIET MOT VIDEO / TRANG CHIA SE (TASK T3D245C)
@router.get(
    "/videos/{video_id}",
    response_model=VideoDetailOut,
)
@router.get(
    "/video/{video_id}",
    response_model=VideoDetailOut,
    include_in_schema=False,
)
def get_single_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    cid = current_user.id if current_user else None
    detail = crud.get_video_detail(db, video_id=video_id, current_user_id=cid)
    if detail is None:
        raise HTTPException(404, "Không tìm thấy video")
    return detail


# 11E. AN / HIEN VIDEO (TASK T3D245C)
@router.patch("/videos/{video_id}/status")
def update_video_status(
    video_id: int,
    data: VideoStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(404, "Không tìm thấy video")

    uid = current_user_id(user)
    is_owner = video.user_id == uid
    is_admin = getattr(user, "role", "USER") == "ADMIN"
    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền thay đổi trạng thái video này",
        )

    # Video đang bị Admin ẩn do vi phạm: chỉ Admin được gỡ ẩn, chủ video không được tự bật lại
    if getattr(video, "moderated_at", None) is not None and not is_admin:
        if data.status != "HIDDEN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Video đang bị Admin ẩn do vi phạm, không thể tự hiển thị lại",
            )

    video.status = data.status
    if is_admin and data.status == "VISIBLE":
        video.moderation_reason = None
        video.moderated_by = None
        video.moderated_at = None

    db.commit()
    db.refresh(video)

    return {
        "id": video.id,
        "status": video.status,
        "is_available": video.status == "VISIBLE",
        "message": (
            "Đã ẩn video"
            if video.status == "HIDDEN"
            else "Đã hiển thị lại video"
        ),
    }


# 12. CHIA SE VIDEO
@router.post(
    "/videos/{video_id}/share",
    response_model=VideoShareOut,
)
@router.post(
    "/video/{video_id}/share",
    response_model=VideoShareOut,
    include_in_schema=False,
)
def share_video(
    video_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(404, "Không tìm thấy video")

    if video.status == "HIDDEN":
        raise HTTPException(
            400, "Video này đã bị ẩn và không còn khả dụng"
        )

    uid = user.id if user else None
    crud.record_video_share(db, video_id, uid)
    stats = crud.video_stats(db, video_id)
    share_count = stats["share_count"] if stats else 1

    return {
        "message": "Đã ghi nhận lượt chia sẻ",
        "video_id": video_id,
        "share_count": share_count,
    }


# 13. XEM SO LUOT TUONG TAC
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


# 14. LUU LICH SU CHAT AI
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


# 15. XEM LICH SU CHAT AI
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


# 15B. KIEM TRA SO CAU HOI AI CON LAI TRONG NGAY (TASK T3D2476)
@router.get(
    "/ai/quota",
    response_model=AiQuotaOut,
)
def get_my_ai_quota(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    uid = current_user_id(user)
    return crud.get_user_daily_chat_quota(db, uid)


# 15C. CHATBOT AI TU VAN MUA SAM (TASK T3D2476)
@router.post(
    "/ai/chat",
    response_model=AiChatResponse,
)
@router.post(
    "/ai/chatbot",
    response_model=AiChatResponse,
    include_in_schema=False,
)
def chat_with_shopping_ai(
    data: ChatLogCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    clean_message = data.message.strip()
    if not clean_message:
        raise HTTPException(
            422, "Tin nhắn không được rỗng"
        )

    uid = current_user_id(user)
    quota = crud.get_user_daily_chat_quota(db, uid)
    if quota["remaining_today"] <= 0:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Bạn đã sử dụng hết giới hạn {quota['daily_limit']} câu hỏi mỗi ngày "
                f"({quota['used_today']}/{quota['daily_limit']}). Vui lòng quay lại vào ngày mai!"
            ),
        )

    try:
        reply_text, products, provider_used = (
            crud.generate_ai_shopping_reply(db, clean_message)
        )
    except crud.AiTimeoutError as error:
        raise HTTPException(
            status_code=504, detail=str(error)
        ) from error
    except crud.AiQuotaExceededError as error:
        raise HTTPException(
            status_code=429, detail=str(error)
        ) from error
    except crud.AiProviderError as error:
        raise HTTPException(
            status_code=503, detail=str(error)
        ) from error

    user_log = crud.save_ai_log(db, uid, "user", clean_message)
    assistant_log = crud.save_ai_log(
        db, uid, "assistant", reply_text
    )
    updated_quota = crud.get_user_daily_chat_quota(db, uid)

    return {
        "reply": reply_text,
        "user_message": user_log,
        "assistant_message": assistant_log,
        "recommended_products": products,
        "provider": provider_used,
        "daily_limit": updated_quota["daily_limit"],
        "used_today": updated_quota["used_today"],
        "remaining_today": updated_quota["remaining_today"],
    }


# 16. TIM KIEM VIDEO, NGUOI DUNG, HASHTAG
@router.get(
    "/search",
    response_model=SearchResultOut,
)
def search_all(
    q: str = "",
    type: str = "all",
    tag: str | None = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    user=Depends(get_optional_user),
):
    if skip < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, "Phân trang không hợp lệ")

    uid = user.id if user else None
    search_type = (type or "all").lower()

    videos = []
    users = []
    hashtags = []

    if search_type in ("all", "videos"):
        videos = crud.search_videos(
            db,
            query_str=q if q else None,
            tag=tag,
            current_user_id=uid,
            skip=skip,
            limit=limit,
        )

    if search_type in ("all", "users") and not tag:
        users = crud.search_users(
            db,
            query_str=q if q else None,
            current_user_id=uid,
            skip=skip,
            limit=limit,
        )

    if search_type in ("all", "hashtags") and not tag:
        hashtags = crud.search_hashtags(
            db,
            query_str=q if q else None,
            limit=limit,
        )

    return {
        "query": q or (f"#{tag}" if tag else ""),
        "type": search_type,
        "videos": videos,
        "users": users,
        "hashtags": hashtags,
    }


# 17. DANH SACH VIDEO THEO HASHTAG
@router.get(
    "/search/hashtags/{tag}",
    response_model=list[SearchVideoItem],
)
def get_videos_by_hashtag(
    tag: str,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    user=Depends(get_optional_user),
):
    if skip < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, "Phân trang không hợp lệ")

    uid = user.id if user else None
    return crud.search_videos(
        db,
        tag=tag,
        current_user_id=uid,
        skip=skip,
        limit=limit,
    )


# 18. BANG XEP HANG HASHTAG THINH HANH TRONG 7 NGAY (TASK T3D2BE1)
@router.get(
    "/search/trending-hashtags",
    response_model=list[TrendingHashtagItem],
)
@router.get(
    "/hashtags/trending",
    response_model=list[TrendingHashtagItem],
    include_in_schema=False,
)
def get_trending_hashtags_ranking(
    days: int = 7,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    if not 1 <= days <= 30 or not 1 <= limit <= 50:
        raise HTTPException(
            422, "Tham số days hoặc limit không hợp lệ"
        )
    return crud.get_trending_hashtags(
        db, days=days, limit=limit
    )

