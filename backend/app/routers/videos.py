import logging
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user as get_video_user, get_optional_user
from app.core.video_media import (
    UploadTooLargeError,
    prepare_thumbnail_upload,
    prepare_video_upload,
)
from app.db.session import get_db
from app.models.user import User

from app.schemas.video import VideoDescription, VideoDescriptionUpdate

from app.crud.video import (
    create_uploaded_video,
    delete_owned_video,
    update_video_description,
)

router = APIRouter(prefix="/videos", tags=["Videos"])

UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads"


def save_uploaded_video(
    db, user_id, title, description, video_path, thumbnail_path, duration_seconds
):
    video_destination = UPLOADS_DIR / "videos" / video_path.name
    thumbnail_destination = UPLOADS_DIR / "thumbnails" / thumbnail_path.name
    moved_files = []

    try:
        record = create_uploaded_video(
            db=db,
            user_id=user_id,
            title=title,
            description=description,
            video_url=f"/uploads/videos/{video_path.name}",
            thumbnail_url=f"/uploads/thumbnails/{thumbnail_path.name}",
            duration_seconds=duration_seconds,
        )

        video_path.replace(video_destination)
        moved_files.append(video_destination)

        thumbnail_path.replace(thumbnail_destination)
        moved_files.append(thumbnail_destination)

        db.commit()
    except Exception:
        db.rollback()
        for path in moved_files:
            path.unlink(missing_ok=True)
        raise

    return record

def remove_uploaded_files(video_url, thumbnail_url):
    files = (
        (video_url, "videos", r"[0-9a-f]{32}\.(mp4|webm)"),
        (thumbnail_url, "thumbnails", r"[0-9a-f]{32}\.(jpg|png|webp)"),
    )

    for url, folder, pattern in files:
        prefix = f"/uploads/{folder}/"
        if url is None or not url.startswith(prefix):
            continue

        filename = url.removeprefix(prefix)
        if not re.fullmatch(pattern, filename):
            continue

        path = UPLOADS_DIR / folder / filename
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logging.getLogger(__name__).exception(
                "Không thể dọn tệp %s", filename
            )

@router.get("/feed")
def video_feed(
    limit: int = 20,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Feed cong khai: khach (khong token) van xem duoc; token sai/het han -> 401."""
    from sqlalchemy import select

    from app.models.video import Video

    limit = max(1, min(limit, 50))
    rows = db.scalars(
        select(Video)
        .where(Video.status == "VISIBLE")
        .order_by(Video.created_at.desc(), Video.id.desc())
        .limit(limit)
    ).all()
    return {
        "viewer_id": user.id if user else None,
        "items": [
            {
                "id": v.id,
                "title": v.title,
                "video_url": v.video_url,
                "thumbnail_url": v.thumbnail_url,
            }
            for v in rows
        ],
    }


@router.post("", status_code=201)
def create_video(
    title: str = Form(min_length=1, max_length=255),
    video: UploadFile = File(...),
    thumbnail: UploadFile = File(...),
    description: VideoDescription | None = Form(None),
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

            return {
                "id": record.id,
                "video_url": record.video_url,
                "thumbnail_url": record.thumbnail_url,
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