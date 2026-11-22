"""Test tính năng Lưu trữ Video và Ảnh trên Cloudflare R2 & Local (Task T3D2BC7 - Phạm Công Khải Hoàn).
Chạy: pytest backend/tests/test_storage_r2.py -v
"""

import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.core.config import settings
from app.core.storage import BaseStorage, LocalStorage, R2Storage, get_storage


def test_local_storage_save_and_delete():
    """Kiểm tra LocalStorage lưu tệp và xóa tệp trong thư mục uploads."""
    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td)
        storage = LocalStorage(base_dir=tmp_path)

        # 1. Lưu file từ Path
        dummy_file = tmp_path / "dummy_video.mp4"
        dummy_file.write_bytes(b"dummy video content")

        url = storage.save(dummy_file, "videos/uuid123.mp4")
        assert url == "/uploads/videos/uuid123.mp4"
        assert (tmp_path / "videos" / "uuid123.mp4").exists()
        assert (tmp_path / "videos" / "uuid123.mp4").read_bytes() == b"dummy video content"

        # 2. Lưu file từ BytesIO (file-like object)
        thumb_data = BytesIO(b"dummy thumbnail content")
        thumb_url = storage.save(thumb_data, "covers/uuid123.jpg", content_type="image/jpeg")
        assert thumb_url == "/uploads/covers/uuid123.jpg"
        assert (tmp_path / "covers" / "uuid123.jpg").exists()

        # 3. Xóa file theo URL
        assert storage.delete(url) is True
        assert not (tmp_path / "videos" / "uuid123.mp4").exists()

        assert storage.delete(thumb_url) is True
        assert not (tmp_path / "covers" / "uuid123.jpg").exists()

        # Xóa file không tồn tại trả về False
        assert storage.delete("/uploads/videos/non_existent.mp4") is False


def test_r2_storage_save_and_delete():
    """Kiểm tra R2Storage gọi S3 API upload_fileobj và delete_object đúng quy chuẩn."""
    mock_boto_client = MagicMock()

    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td)
        with patch("boto3.client", return_value=mock_boto_client):
            storage = R2Storage(
                account_id="acc123",
                access_key_id="key123",
                secret_access_key="secret123",
                bucket="clipshop-media",
                public_url="https://pub-xyz.r2.dev",
            )

            dummy_file = tmp_path / "test_upload.mp4"
            dummy_file.write_bytes(b"sample video bytes")

            # 1. Test save()
            url = storage.save(dummy_file, "videos/uuid456.mp4", content_type="video/mp4")
            assert url == "https://pub-xyz.r2.dev/videos/uuid456.mp4"

            # Kiểm tra gọi upload_fileobj
            mock_boto_client.upload_fileobj.assert_called_once()
            args, kwargs = mock_boto_client.upload_fileobj.call_args
            assert args[1] == "clipshop-media"
            assert args[2] == "videos/uuid456.mp4"
            assert kwargs["ExtraArgs"] == {"ContentType": "video/mp4"}

            # 2. Test delete() với URL công khai
            res_del = storage.delete("https://pub-xyz.r2.dev/videos/uuid456.mp4")
            assert res_del is True
            mock_boto_client.delete_object.assert_called_once_with(
                Bucket="clipshop-media", Key="videos/uuid456.mp4"
            )


def test_get_storage_driver_selection():
    """Kiểm tra hàm get_storage() chuyển đổi linh hoạt giữa LocalStorage và R2Storage theo biến môi trường."""
    # 1. Khi STORAGE_DRIVER=local (hoặc mặc định)
    with patch.object(settings, "STORAGE_DRIVER", "local"):
        storage = get_storage()
        assert isinstance(storage, LocalStorage)

    # 2. Khi STORAGE_DRIVER=r2 nhưng chưa điền key -> tự động fallback sang LocalStorage an toàn
    with patch.object(settings, "STORAGE_DRIVER", "r2"), \
         patch.object(settings, "R2_ACCOUNT_ID", ""), \
         patch.object(settings, "R2_ACCESS_KEY_ID", ""), \
         patch.object(settings, "R2_BUCKET", ""):
        storage = get_storage()
        assert isinstance(storage, LocalStorage)

    # 3. Khi STORAGE_DRIVER=r2 và đã cấu hình đủ key
    with patch.object(settings, "STORAGE_DRIVER", "r2"), \
         patch.object(settings, "R2_ACCOUNT_ID", "acc123"), \
         patch.object(settings, "R2_ACCESS_KEY_ID", "key123"), \
         patch.object(settings, "R2_SECRET_ACCESS_KEY", "sec123"), \
         patch.object(settings, "R2_BUCKET", "clipshop-bucket"), \
         patch.object(settings, "R2_PUBLIC_URL", "https://media.clipshop.vn"), \
         patch("boto3.client", return_value=MagicMock()):
        storage = get_storage()
        assert isinstance(storage, R2Storage)
        assert storage.bucket == "clipshop-bucket"
        assert storage.public_url == "https://media.clipshop.vn"


def test_save_uploaded_video_and_remove():
    """Kiểm tra hàm save_uploaded_video và remove_uploaded_files tích hợp với get_storage()."""
    from app.routers.videos import remove_uploaded_files, save_uploaded_video

    mock_db = MagicMock()
    mock_storage = MagicMock()
    mock_storage.save.side_effect = lambda path, key: f"https://r2.test/{key}"

    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td)
        vid_file = tmp_path / "vid.mp4"
        vid_file.write_bytes(b"video bytes")
        thumb_file = tmp_path / "cover.jpg"
        thumb_file.write_bytes(b"cover bytes")

        with patch("app.routers.videos.get_storage", return_value=mock_storage), patch(
            "app.routers.videos.create_uploaded_video"
        ) as mock_create:
            mock_create.return_value = MagicMock(
                id=1,
                video_url="https://r2.test/videos/vid.mp4",
                thumbnail_url="https://r2.test/covers/cover.jpg",
            )

            record = save_uploaded_video(
                db=mock_db,
                user_id=10,
                title="Video test R2",
                description="Mo ta",
                video_path=vid_file,
                thumbnail_path=thumb_file,
                duration_seconds=45,
            )

            assert record.id == 1
            assert mock_storage.save.call_count == 2
            mock_db.commit.assert_called_once()

        # Test remove_uploaded_files
        with patch("app.routers.videos.get_storage", return_value=mock_storage):
            remove_uploaded_files(
                "https://r2.test/videos/vid.mp4",
                "https://r2.test/covers/cover.jpg",
            )
            assert mock_storage.delete.call_count == 2

