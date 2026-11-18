"""Xử lý ảnh đại diện (avatar): kiểm tra ở server, lưu tên ngẫu nhiên, tạo URL công khai.

avatar_key lưu trong DB có dạng ``avatars/<32 ký tự hex>.<jpg|png>`` (đường dẫn
tương đối trong thư mục uploads). URL truy cập được tạo từ key bằng
``avatar_url_from_key``.
"""

import io
import logging
import re
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

import filetype
from PIL import Image, ImageOps

from app.core.config import settings

UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads"
AVATAR_DIR_NAME = "avatars"

# Giới hạn dung lượng avatar: 2 MB (đề chưa quy định mức cụ thể).
MAX_AVATAR_BYTES = 2 * 1024 * 1024
# Giới hạn kích thước ảnh để tránh ảnh "bom giải nén".
MAX_AVATAR_SIDE = 4096

ALLOWED_AVATAR_TYPES = {"image/jpeg": "jpg", "image/png": "png"}
_PIL_FORMAT = {"jpg": "JPEG", "png": "PNG"}
_AVATAR_KEY_PATTERN = re.compile(r"avatars/[0-9a-f]{32}\.(jpg|png)")


class AvatarTooLargeError(ValueError):
    """Ảnh vượt quá MAX_AVATAR_BYTES."""


class AvatarInvalidError(ValueError):
    """Tệp không phải ảnh JPG/PNG hợp lệ."""


def avatar_url_from_key(key: str | None) -> str | None:
    """Đổi avatar_key thành URL đầy đủ để frontend gán vào <img src>."""
    if not key:
        return None
    if key.startswith(("http://", "https://")):
        return key  # dữ liệu cũ/seed lưu sẵn URL tuyệt đối
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    return f"{base}/uploads/{key.lstrip('/')}"


def read_limited(source: BinaryIO, max_bytes: int = MAX_AVATAR_BYTES) -> bytes:
    """Đọc tối đa max_bytes; vượt quá thì từ chối (không đọc hết tệp khổng lồ)."""
    source.seek(0)
    data = source.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise AvatarTooLargeError(
            f"Ảnh vượt quá dung lượng cho phép ({max_bytes // (1024 * 1024)} MB)."
        )
    if not data:
        raise AvatarInvalidError("Tệp tải lên đang trống.")
    return data


def validate_and_reencode(data: bytes) -> tuple[bytes, str]:
    """Kiểm tra nội dung thật (magic bytes + Pillow), trả về (bytes sạch, đuôi tệp).

    Không tin tên tệp hay Content-Type do client gửi. Ảnh được mã hóa lại để
    loại bỏ metadata (EXIF/GPS) và mọi dữ liệu thừa gắn kèm.
    """
    detected = filetype.guess(data)
    if detected is None or detected.mime not in ALLOWED_AVATAR_TYPES:
        raise AvatarInvalidError("Chỉ chấp nhận ảnh JPG hoặc PNG.")
    extension = ALLOWED_AVATAR_TYPES[detected.mime]

    try:
        with Image.open(io.BytesIO(data), formats=[_PIL_FORMAT[extension]]) as image:
            if max(image.size) > MAX_AVATAR_SIDE:
                raise AvatarInvalidError(
                    f"Kích thước ảnh tối đa {MAX_AVATAR_SIDE}x{MAX_AVATAR_SIDE} pixel."
                )
            image.load()
            image = ImageOps.exif_transpose(image)
            output = io.BytesIO()
            if extension == "jpg":
                image.convert("RGB").save(output, format="JPEG", quality=90)
            else:
                image.save(output, format="PNG")
    except AvatarInvalidError:
        raise
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError) as error:
        raise AvatarInvalidError("Ảnh bị hỏng hoặc sai định dạng.") from error

    return output.getvalue(), extension


def save_avatar(data: bytes, extension: str, uploads_dir: Path | None = None) -> str:
    """Ghi ảnh với tên ngẫu nhiên, trả về avatar_key để lưu vào DB."""
    folder = (uploads_dir or UPLOADS_DIR) / AVATAR_DIR_NAME
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.{extension}"
    with (folder / filename).open("xb") as output:
        output.write(data)
    return f"{AVATAR_DIR_NAME}/{filename}"


def remove_avatar_file(key: str | None, uploads_dir: Path | None = None) -> None:
    """Xóa file avatar cũ. Chỉ xóa key đúng định dạng do hệ thống tạo ra."""
    if not key or not _AVATAR_KEY_PATTERN.fullmatch(key):
        return
    path = (uploads_dir or UPLOADS_DIR) / key
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logging.getLogger(__name__).exception("Không thể xóa avatar cũ %s", key)
