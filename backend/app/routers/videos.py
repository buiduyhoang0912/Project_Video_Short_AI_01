import json
import logging
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.storage import resolve_media_url
from app.core.video_auth import get_video_user
from app.dependencies.auth import get_current_user, get_optional_user
from app.core.video_media import (
    UploadTooLargeError,
    prepare_thumbnail_upload,
    prepare_video_upload,
)
from app.db.session import get_db
from app.models.user import User

from app.schemas.product import ProductListItemOut
from app.schemas.video import (
    UserVideoListResponse,
    VideoDescription,
    VideoDescriptionUpdate,
    VideoFeedResponse,
    VideoProductsUpdate,
    VideoViewResponse,
)

from app.crud.video import (
    create_uploaded_video,
    delete_owned_video,
    get_feed_videos,
    get_user_videos,
    get_video_products,
    increment_video_view,
    serialize_product_item,
    set_video_products,
    update_video_description,
)
from app.core.storage import get_storage

router = APIRouter(prefix="/videos", tags=["Videos"])

UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads"


def save_uploaded_video(
    db, user_id, title, description, video_path, thumbnail_path, duration_seconds
):
    storage = get_storage()
    video_key = f"videos/{video_path.name}"
    cover_key = f"covers/{thumbnail_path.name}"
    uploaded_urls = []

    try:
        video_url = storage.save(video_path, video_key)
        uploaded_urls.append(video_url)

        thumbnail_url = storage.save(thumbnail_path, cover_key)
        uploaded_urls.append(thumbnail_url)

        record = create_uploaded_video(
            db=db,
            user_id=user_id,
            title=title,
            description=description,
            video_url=video_url,
            thumbnail_url=thumbnail_url,
            duration_seconds=duration_seconds,
        )

        db.commit()
    except Exception:
        db.rollback()
        for url in uploaded_urls:
            try:
                storage.delete(url)
            except Exception:
                pass
        raise

    return record


def remove_uploaded_files(video_url, thumbnail_url):
    storage = get_storage()
    if video_url:
        try:
            storage.delete(video_url)
        except Exception:
            logging.getLogger(__name__).warning("Không thể dọn video: %s", video_url)
    if thumbnail_url:
        try:
            storage.delete(thumbnail_url)
        except Exception:
            logging.getLogger(__name__).warning("Không thể dọn thumbnail: %s", thumbnail_url)

@router.post("", status_code=201)
def create_video(
    title: str = Form(min_length=1, max_length=255),
    video: UploadFile = File(...),
    thumbnail: UploadFile = File(...),
    description: VideoDescription | None = Form(None),
    product_ids: str | None = Form(None),
    user: User = Depends(get_video_user),
    db: Session = Depends(get_db),
):
        with TemporaryDirectory(dir=UPLOADS_DIR.parent) as directory:
            temp_dir = Path(directory)

            try:
                video_path, duration_seconds = prepare_video_upload(
                    video.file, video.filename, temp_dir
                )
                thumbnail_path = prepare_thumbnail_upload(
                    thumbnail.file, thumbnail.filename, temp_dir
                )
            except UploadTooLargeError as error:
                raise HTTPException(status_code=413, detail=str(error)) from error
            except ValueError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
                raise HTTPException(
                    status_code=422, detail="Không đọc được nội dung video."
                ) from error
            except FileNotFoundError as error:
                raise HTTPException(
                    status_code=503, detail="Máy chủ chưa gọi được ffprobe."
                ) from error

            record = save_uploaded_video(
                db=db,
                user_id=user.id,
                title=title,
                description=description,
                video_path=video_path,
                thumbnail_path=thumbnail_path,
                duration_seconds=duration_seconds,
            )

            # Gắn sản phẩm nếu người bán chọn khi tải lên video (Task T3D2296)
            if product_ids:
                try:
                    pids = json.loads(product_ids) if isinstance(product_ids, str) else product_ids
                    if isinstance(pids, list) and len(pids) > 0:
                        set_video_products(db, record.id, user.id, [int(x) for x in pids])
                except Exception as err:
                    logging.getLogger(__name__).warning("Không gắn được sản phẩm khi tạo video: %s", err)

            return {
                "id": record.id,
                "video_url": resolve_media_url(record.video_url),
                "thumbnail_url": resolve_media_url(record.thumbnail_url),
                "duration_seconds": record.duration_seconds,
            }

@router.patch("/{video_id}")
def patch_video_description(
    video_id: int,
    data: VideoDescriptionUpdate,
    user: User = Depends(get_video_user),
    db: Session = Depends(get_db),
):
    video = update_video_description(db, video_id, user.id, data.description)

    if video is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy video của bạn.")

    result = {"id": video.id, "description": video.description}
    db.commit()
    return result

@router.delete("/{video_id}", status_code=204)
def delete_video(
    video_id: int,
    user: User = Depends(get_video_user),
    db: Session = Depends(get_db),
):
    file_urls = delete_owned_video(db, video_id, user.id)

    if file_urls is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy video của bạn.")

    db.commit()
    video_url, thumbnail_url = file_urls
    remove_uploaded_files(video_url, thumbnail_url)

    return Response(status_code=204)

# --- APIs phục vụ Feed, Video người dùng và Tăng Lượt Xem ---

@router.get("/feed", response_model=VideoFeedResponse)
def get_for_you_feed(
    limit: int = Query(10, ge=1, le=50, description="Số lượng video mỗi lần tải (1 - 50)"),
    cursor: int | None = Query(None, description="ID video cuối cùng ở lần tải trước"),
    db: Session = Depends(get_db),
):
    """
    API Feed Dành cho bạn (For You):
    - Phân trang dạng cuộn qua tham số `cursor`.
    - Lọc bỏ video HIDDEN.
    - Ưu tiên video mới nhất và nhiều tương tác nhất.
    """
    items, next_cursor, has_more = get_feed_videos(db=db, limit=limit, cursor=cursor)

    # Gắn kèm sản phẩm vào từng video trên Feed để hiện nút giỏ hàng (T3D2296)
    for item in items:
        prods = get_video_products(db, item.id)
        item.products = [serialize_product_item(p) for p in prods]

    return VideoFeedResponse(
        items=items,
        next_cursor=str(next_cursor) if next_cursor is not None else None,
        has_more=has_more,
    )


@router.get("/users/{user_id}", response_model=UserVideoListResponse)
def get_user_video_list(
    user_id: int,
    limit: int = Query(10, ge=1, le=50, description="Số lượng video mỗi lần tải (1 - 50)"),
    cursor: int | None = Query(None, description="ID video cuối cùng ở lần tải trước"),
    include_hidden: bool = Query(False, description="Lấy cả video đang ẩn (nếu là chủ sở hữu hoặc admin)"),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """
    API Danh sách video của một người dùng:
    - Lọc theo `user_id`.
    - Nếu include_hidden=True và là chủ sở hữu thì trả về cả video HIDDEN.
    """
    is_owner = user is not None and user.id == user_id
    is_admin = user is not None and getattr(user, "role", "USER") == "ADMIN"
    allow_hidden = (is_owner or is_admin) and include_hidden

    items, next_cursor, has_more = get_user_videos(
        db=db, user_id=user_id, limit=limit, cursor=cursor, include_hidden=allow_hidden
    )

    for item in items:
        prods = get_video_products(db, item.id)
        item.products = [serialize_product_item(p) for p in prods]

    return UserVideoListResponse(
        items=items,
        next_cursor=str(next_cursor) if next_cursor is not None else None,
        has_more=has_more,
    )


@router.post("/{video_id}/views", response_model=VideoViewResponse)
def record_video_view(
    video_id: int,
    db: Session = Depends(get_db),
):
    """
    API ghi nhận lượt xem khi người dùng xem video quá 3 giây.
    Tăng `view_count` lên 1 trong cơ sở dữ liệu.
    """
    new_view_count = increment_video_view(db=db, video_id=video_id)

    if new_view_count is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy video.")

    db.commit()

    return VideoViewResponse(
        id=video_id,
        view_count=new_view_count,
        message="Ghi nhận lượt xem thành công",
    )


# --- APIs Quản lý Sản phẩm gắn trong Video (Task T3D2296) ---

@router.get("/{video_id}/products", response_model=list[ProductListItemOut])
def get_products_attached_to_video(
    video_id: int,
    db: Session = Depends(get_db),
):
    """Lấy danh sách các sản phẩm đang hoạt động được gắn trong video."""
    products = get_video_products(db, video_id)
    return [serialize_product_item(p) for p in products]


@router.post("/{video_id}/products", response_model=list[ProductListItemOut])
def update_products_attached_to_video(
    video_id: int,
    data: VideoProductsUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Người bán cập nhật danh sách sản phẩm gắn trong video của mình (tối đa 3)."""
    products = set_video_products(db, video_id, user.id, data.product_ids)
    return [serialize_product_item(p) for p in products]