import json
import subprocess
from pathlib import Path
from math import ceil
import filetype
from typing import BinaryIO
from uuid import uuid4
from PIL import Image

from app.core.config import settings


def probe_video(path: Path) -> dict:
    command = [
        settings.FFPROBE_PATH,
        "-v", "error",
        "-protocol_whitelist", "file",
        "-show_entries",
        "format=format_name,duration:format_tags=major_brand:"
        "stream=codec_type,codec_name:stream_disposition=attached_pic",
        "-of", "json",
        str(path.resolve()),
    ]
    result = subprocess.run(
        command, capture_output=True, text=True, check=True, timeout=15
    )
    return json.loads(result.stdout)

def validate_video(path: Path) -> int:
    detected = filetype.guess(str(path))
    extension = path.suffix.lower().lstrip(".")

    if detected is None or detected.extension not in ("mp4", "webm"):
        raise ValueError("Chỉ chấp nhận video MP4 hoặc WebM.")

    if detected.extension != extension:
        raise ValueError("Đuôi tệp không khớp với định dạng video.")
    metadata = probe_video(path)
    has_video = False

    for stream in metadata.get("streams", []):
        is_cover = stream.get("disposition", {}).get("attached_pic", 0)
        if stream.get("codec_type") == "video" and not is_cover:
            has_video = True
            break

    if not has_video:
        raise ValueError("Tệp không có luồng hình video.")
    raw_duration = metadata.get("format", {}).get("duration")

    try:
        duration = float(raw_duration)
    except (TypeError, ValueError) as error:
        raise ValueError("Không đọc được thời lượng video.") from error

    if not 0 < duration <= 60:
        raise ValueError("Video phải dài hơn 0 giây và tối đa 60 giây.")

    return ceil(duration)

MAX_VIDEO_BYTES = 50_000_000


class UploadTooLargeError(ValueError):
    pass


def copy_upload(source: BinaryIO, destination: Path, max_bytes: int) -> None:
    total_bytes = 0
    source.seek(0)

    with destination.open("xb") as output:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break

            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                raise UploadTooLargeError("Tệp vượt quá dung lượng cho phép.")

            output.write(chunk)

    if total_bytes == 0:
        raise ValueError("Tệp tải lên đang trống.")

def prepare_video_upload(
    source: BinaryIO, original_filename: str | None, temp_dir: Path
) -> tuple[Path, int]:
    extension = Path(original_filename or "").suffix.lower()
    if extension not in (".mp4", ".webm"):
        raise ValueError("Tên tệp phải có đuôi .mp4 hoặc .webm.")

    temp_path = temp_dir / f"{uuid4().hex}{extension}"
    copy_upload(source, temp_path, MAX_VIDEO_BYTES)
    duration_seconds = validate_video(temp_path)

    return temp_path, duration_seconds

def prepare_thumbnail_upload(
    source: BinaryIO, original_filename: str | None, temp_dir: Path
) -> Path:
    allowed_extensions = {
        ".jpg": "jpg",
        ".jpeg": "jpg",
        ".png": "png",
        ".webp": "webp",
    }
    extension = Path(original_filename or "").suffix.lower()
    expected_type = allowed_extensions.get(extension)

    if expected_type is None:
        raise ValueError("Ảnh bìa phải là JPG, PNG hoặc WebP.")

    temp_path = temp_dir / f"{uuid4().hex}.{expected_type}"
    copy_upload(source, temp_path, MAX_VIDEO_BYTES)

    image_format = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP"}[expected_type]

    try:
        with Image.open(temp_path, formats=[image_format]) as image:
            image.load()
    except (OSError, SyntaxError, Image.DecompressionBombError) as error:
        raise ValueError("Ảnh bìa bị hỏng hoặc sai định dạng.") from error

    return temp_path