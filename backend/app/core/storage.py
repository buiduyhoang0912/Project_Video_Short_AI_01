"""Module quản lý lưu trữ tệp tin (Task T3D2BC7 - Cloudflare R2 & Local Storage)."""

import logging
import mimetypes
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings

logger = logging.getLogger(__name__)

# Thư mục uploads cục bộ
UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads"


class BaseStorage(ABC):
    """Lớp trừu tượng cho driver lưu trữ."""

    @abstractmethod
    def save(
        self, file: Path | BinaryIO, key: str, content_type: str | None = None
    ) -> str:
        """Lưu tệp tin và trả về URL truy cập."""
        pass

    @abstractmethod
    def delete(self, key_or_url: str) -> bool:
        """Xóa tệp tin theo key hoặc URL."""
        pass


class LocalStorage(BaseStorage):
    """Driver lưu trữ tệp tin trên thư mục uploads cục bộ."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or UPLOADS_DIR

    def save(
        self, file: Path | BinaryIO, key: str, content_type: str | None = None
    ) -> str:
        dest_path = self.base_dir / key
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(file, (str, Path)):
            src_path = Path(file)
            shutil.copy2(src_path, dest_path)
        elif hasattr(file, "read"):
            with open(dest_path, "wb") as f_out:
                shutil.copyfileobj(file, f_out)
        else:
            raise ValueError(f"Không hỗ trợ kiểu tệp tin: {type(file)}")

        norm_key = key.replace("\\", "/").lstrip("/")
        return f"/uploads/{norm_key}"

    def delete(self, key_or_url: str) -> bool:
        norm = key_or_url.replace("\\", "/").strip()
        prefix = "/uploads/"
        if norm.startswith(prefix):
            key = norm[len(prefix) :]
        else:
            key = norm.lstrip("/")

        target_path = self.base_dir / key
        if target_path.exists() and target_path.is_file():
            try:
                target_path.unlink()
                return True
            except OSError as err:
                logger.warning(
                    "Không xóa được file local %s: %s", target_path, err
                )
                return False
        return False


class R2Storage(BaseStorage):
    """Driver lưu trữ tệp tin trên Cloudflare R2 qua S3 API."""

    def __init__(
        self,
        account_id: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        bucket: str | None = None,
        public_url: str | None = None,
    ):
        self.account_id = account_id or settings.R2_ACCOUNT_ID
        self.access_key_id = access_key_id or settings.R2_ACCESS_KEY_ID
        self.secret_access_key = (
            secret_access_key or settings.R2_SECRET_ACCESS_KEY
        )
        self.bucket = bucket or settings.R2_BUCKET
        self.public_url = (public_url or settings.R2_PUBLIC_URL).rstrip("/")

        endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"

        import boto3

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name="auto",
        )

    def save(
        self, file: Path | BinaryIO, key: str, content_type: str | None = None
    ) -> str:
        norm_key = key.replace("\\", "/").lstrip("/")

        if not content_type:
            guessed_type, _ = mimetypes.guess_type(norm_key)
            content_type = guessed_type or "application/octet-stream"

        extra_args = {"ContentType": content_type}

        if isinstance(file, (str, Path)):
            with open(file, "rb") as f_in:
                self.client.upload_fileobj(
                    f_in, self.bucket, norm_key, ExtraArgs=extra_args
                )
        elif hasattr(file, "file"):
            self.client.upload_fileobj(
                file.file, self.bucket, norm_key, ExtraArgs=extra_args
            )
        elif hasattr(file, "read"):
            self.client.upload_fileobj(
                file, self.bucket, norm_key, ExtraArgs=extra_args
            )
        else:
            raise ValueError(f"Không hỗ trợ kiểu tệp tin: {type(file)}")

        return f"{self.public_url}/{norm_key}"

    def delete(self, key_or_url: str) -> bool:
        norm = key_or_url.replace("\\", "/").strip()
        if self.public_url and norm.startswith(self.public_url):
            key = norm[len(self.public_url) :].lstrip("/")
        elif norm.startswith("http://") or norm.startswith("https://"):
            from urllib.parse import urlparse

            key = urlparse(norm).path.lstrip("/")
        elif norm.startswith("/uploads/"):
            key = norm[len("/uploads/") :]
        else:
            key = norm.lstrip("/")

        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception as err:
            logger.warning(
                "Không xóa được tệp trên Cloudflare R2 (key=%s): %s", key, err
            )
            return False


def get_storage() -> BaseStorage:
    """Đọc STORAGE_DRIVER để trả về driver lưu trữ tương ứng."""
    driver = (settings.STORAGE_DRIVER or "local").strip().lower()
    if driver == "r2":
        if not (
            settings.R2_ACCOUNT_ID
            and settings.R2_ACCESS_KEY_ID
            and settings.R2_BUCKET
        ):
            logger.warning(
                "STORAGE_DRIVER=r2 nhưng chưa cấu hình đủ R2 key/bucket, fallback sang LocalStorage"
            )
            return LocalStorage()
        try:
            return R2Storage()
        except Exception as err:
            logger.error(
                "Không thể khởi tạo R2Storage: %s. Fallback sang LocalStorage",
                err,
            )
            return LocalStorage()

    return LocalStorage()


_r2_storage_cache: R2Storage | None = None
_r2_cache_key: tuple[str, str, str, str, str] | None = None


def resolve_media_url(url: str | None, expires_in: int = 3600) -> str | None:
    """Chuyển đổi R2 public URL sang presigned URL để phát/hiển thị ổn định kể cả khi r2.dev chưa bật public."""
    if not url or not isinstance(url, str):
        return url

    driver = (settings.STORAGE_DRIVER or "local").strip().lower()
    public_base = (settings.R2_PUBLIC_URL or "").rstrip("/")
    if driver != "r2" or not public_base or not url.startswith(public_base + "/"):
        return url

    if not (
        settings.R2_ACCOUNT_ID
        and settings.R2_ACCESS_KEY_ID
        and settings.R2_SECRET_ACCESS_KEY
        and settings.R2_BUCKET
    ):
        return url

    global _r2_storage_cache, _r2_cache_key
    current_key = (
        settings.R2_ACCOUNT_ID,
        settings.R2_ACCESS_KEY_ID,
        settings.R2_SECRET_ACCESS_KEY,
        settings.R2_BUCKET,
        public_base,
    )
    if _r2_storage_cache is None or _r2_cache_key != current_key:
        _r2_storage_cache = R2Storage()
        _r2_cache_key = current_key

    object_key = url[len(public_base) :].lstrip("/")
    try:
        return _r2_storage_cache.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": _r2_storage_cache.bucket, "Key": object_key},
            ExpiresIn=expires_in,
        )
    except Exception as err:
        logger.warning("Không tạo được presigned URL cho %s: %s", object_key, err)
        return url
