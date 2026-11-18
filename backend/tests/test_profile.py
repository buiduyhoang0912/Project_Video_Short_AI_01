"""Test API hồ sơ cá nhân (T3D1FE9). Chạy: pytest tests/test_profile.py (SQLite in-memory)."""
import io
import re

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.core import avatar as avatar_module
from app.db.session import Base, get_db
from app.main import app
from app.models.user import User


@compiles(BIGINT, "sqlite")
def _bigint_sqlite(t, c, **k):
    return "INTEGER"


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine)
    engine.dispose()


@pytest.fixture()
def uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(avatar_module, "UPLOADS_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def client(db_session, uploads):
    def override():
        db = db_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def register(client, username, password="password123", display_name=None):
    r = client.post(
        "/auth/register",
        json={
            "email": f"{username}@x.com",
            "username": username,
            "password": password,
            "display_name": display_name or username.title(),
        },
    )
    assert r.status_code == 201, r.text


def login(client, username, password="password123"):
    r = client.post("/auth/login", json={"identifier": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def alice(client):
    register(client, "alice")
    return login(client, "alice")


def image_bytes(fmt="PNG", size=(40, 30), color=(200, 50, 50)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt)
    return buf.getvalue()


def upload(client, headers, data, filename="a.png", content_type="image/png"):
    return client.post(
        "/api/me/avatar", headers=headers, files={"file": (filename, data, content_type)}
    )


# ---------------- Xem hồ sơ của mình ----------------
def test_my_profile_requires_login(client):
    assert client.get("/api/me/profile").status_code == 401


def test_my_profile_returns_expected_fields(client, alice):
    r = client.get("/api/me/profile", headers=alice)
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "alice"
    assert data["display_name"] == "Alice"
    assert data["bio"] is None and data["avatar_url"] is None
    assert set(data) == {"id", "username", "display_name", "bio", "avatar_url"}


# ---------------- Sửa hồ sơ ----------------
def test_update_profile_persists(client, alice):
    r = client.patch(
        "/api/me/profile",
        headers=alice,
        json={"display_name": "  Alice Nguyễn  ", "bio": "Xin chào\nmọi người"},
    )
    assert r.status_code == 200
    assert r.json()["display_name"] == "Alice Nguyễn"
    again = client.get("/api/me/profile", headers=alice).json()
    assert again["display_name"] == "Alice Nguyễn"
    assert again["bio"] == "Xin chào\nmọi người"
    # /auth/me (dùng cho header) cũng thấy tên mới
    assert client.get("/auth/me", headers=alice).json()["display_name"] == "Alice Nguyễn"


def test_update_profile_partial_and_clear_bio(client, alice):
    client.patch("/api/me/profile", headers=alice, json={"bio": "hello"})
    r = client.patch("/api/me/profile", headers=alice, json={"display_name": "Moi"})
    assert r.json()["display_name"] == "Moi" and r.json()["bio"] == "hello"
    r = client.patch("/api/me/profile", headers=alice, json={"bio": "   "})
    assert r.status_code == 200 and r.json()["bio"] is None


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"display_name": ""},
        {"display_name": "   "},
        {"display_name": None},
        {"display_name": "x" * 101},
        {"display_name": "bad\x00name"},
        {"bio": "y" * 501},
        {"bio": 123},
        {"display_name": "Ok", "role": "ADMIN"},
        {"display_name": "Ok", "avatar_key": "avatars/hack.png"},
        {"display_name": "Ok", "username": "evil"},
    ],
)
def test_update_profile_validation_422(client, alice, body):
    assert client.patch("/api/me/profile", headers=alice, json=body).status_code == 422
    assert client.get("/api/me/profile", headers=alice).json()["display_name"] == "Alice"


def test_update_profile_requires_login(client):
    r = client.patch("/api/me/profile", json={"display_name": "X"})
    assert r.status_code == 401


def test_cannot_edit_other_account(client, alice):
    register(client, "bob")
    bob = login(client, "bob")
    # Không có tham số nào để chỉ định tài khoản khác: id/username bị từ chối
    other_id = client.get("/api/me/profile", headers=bob).json()["id"]
    r = client.patch("/api/me/profile", headers=alice, json={"id": other_id, "display_name": "Hacked"})
    assert r.status_code == 422
    # Sửa bằng token của alice chỉ đổi alice
    client.patch("/api/me/profile", headers=alice, json={"display_name": "Alice 2"})
    assert client.get("/api/me/profile", headers=bob).json()["display_name"] == "Bob"
    assert client.get("/api/profiles/alice").json()["display_name"] == "Alice 2"


# ---------------- Upload avatar ----------------
def test_avatar_requires_login(client):
    r = client.post("/api/me/avatar", files={"file": ("a.png", image_bytes(), "image/png")})
    assert r.status_code == 401


@pytest.mark.parametrize("fmt,ext,mime", [("PNG", "png", "image/png"), ("JPEG", "jpg", "image/jpeg")])
def test_avatar_valid_upload(client, alice, uploads, fmt, ext, mime):
    r = upload(client, alice, image_bytes(fmt), f"me.{ext}", mime)
    assert r.status_code == 200, r.text
    url = r.json()["avatar_url"]
    assert re.fullmatch(rf"http://127\.0\.0\.1:8000/uploads/avatars/[0-9a-f]{{32}}\.{ext}", url)
    files = list((uploads / "avatars").iterdir())
    assert len(files) == 1 and files[0].name == url.rsplit("/", 1)[1]
    # đọc lại -> vẫn còn (đã lưu DB)
    assert client.get("/api/me/profile", headers=alice).json()["avatar_url"] == url
    assert client.get("/api/profiles/alice").json()["avatar_url"] == url


def test_avatar_random_name_ignores_client_filename(client, alice, uploads):
    r = upload(client, alice, image_bytes(), "../../evil name.png")
    assert r.status_code == 200
    names = [p.name for p in (uploads / "avatars").iterdir()]
    assert len(names) == 1 and re.fullmatch(r"[0-9a-f]{32}\.png", names[0])


def test_avatar_replace_removes_old_file(client, alice, uploads):
    upload(client, alice, image_bytes("PNG"))
    upload(client, alice, image_bytes("JPEG"), "b.jpg", "image/jpeg")
    names = [p.name for p in (uploads / "avatars").iterdir()]
    assert len(names) == 1 and names[0].endswith(".jpg")


@pytest.mark.parametrize(
    "data,name,mime",
    [
        (image_bytes("GIF"), "a.gif", "image/gif"),
        (image_bytes("WEBP"), "a.webp", "image/webp"),
        (b"just some text pretending to be an image", "a.png", "image/png"),
        (b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", "a.png", "image/png"),
        (image_bytes("PNG")[:60], "broken.png", "image/png"),
        (b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "fake.png", "image/png"),
    ],
)
def test_avatar_rejects_wrong_format(client, alice, uploads, data, name, mime):
    r = upload(client, alice, data, name, mime)
    assert r.status_code == 422
    assert client.get("/api/me/profile", headers=alice).json()["avatar_url"] is None
    assert not list((uploads / "avatars").glob("*")) if (uploads / "avatars").exists() else True


def test_avatar_rejects_empty_file(client, alice):
    assert upload(client, alice, b"").status_code == 422


def test_avatar_rejects_too_large(client, alice, uploads):
    r = upload(client, alice, b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024))
    assert r.status_code == 413
    assert client.get("/api/me/profile", headers=alice).json()["avatar_url"] is None


def test_avatar_exactly_at_limit_is_not_rejected_for_size(client, alice, monkeypatch):
    # Ảnh hợp lệ nhỏ hơn giới hạn thì qua; giới hạn là 2 MB
    assert avatar_module.MAX_AVATAR_BYTES == 2 * 1024 * 1024
    assert upload(client, alice, image_bytes(size=(300, 300))).status_code == 200


def test_avatar_strips_exif_metadata(client, alice, uploads):
    img = Image.new("RGB", (20, 20), (1, 2, 3))
    exif = Image.Exif()
    exif[0x010F] = "SecretCameraMaker"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    assert b"SecretCameraMaker" in buf.getvalue()
    r = upload(client, alice, buf.getvalue(), "x.jpg", "image/jpeg")
    assert r.status_code == 200
    saved = next((uploads / "avatars").iterdir()).read_bytes()
    assert b"SecretCameraMaker" not in saved


def test_avatar_only_affects_own_account(client, alice):
    register(client, "bob")
    upload(client, alice, image_bytes())
    assert client.get("/api/profiles/bob").json()["avatar_url"] is None


def test_old_non_generated_avatar_key_is_never_deleted(client, alice, db_session, uploads):
    s = db_session()
    victim = uploads / "secret.txt"
    victim.write_text("keep me")
    u = s.query(User).filter_by(username="alice").one()
    u.avatar_key = "../secret.txt"
    s.commit()
    upload(client, alice, image_bytes())
    assert victim.exists()


# ---------------- Đổi mật khẩu ----------------
PW = {"current_password": "password123", "new_password": "newpass456", "confirm_password": "newpass456"}


def test_change_password_requires_login(client):
    assert client.put("/api/me/password", json=PW).status_code == 401


def test_change_password_wrong_current_rejected(client, alice):
    r = client.put("/api/me/password", headers=alice, json={**PW, "current_password": "wrongpass1"})
    assert r.status_code == 400
    assert "hiện tại" in r.json()["detail"]
    login(client, "alice", "password123")  # mật khẩu cũ vẫn dùng được
    assert client.get("/api/me/profile", headers=alice).status_code == 200  # không bị đăng xuất


@pytest.mark.parametrize(
    "patch",
    [
        {"confirm_password": "different789"},
        {"new_password": "short", "confirm_password": "short"},
        {"new_password": "        ", "confirm_password": "        "},
        {"new_password": "password123", "confirm_password": "password123"},
        {"new_password": "é" * 40, "confirm_password": "é" * 40},  # 80 byte > 72
        {"current_password": ""},
    ],
)
def test_change_password_validation_422(client, alice, patch):
    r = client.put("/api/me/password", headers=alice, json={**PW, **patch})
    assert r.status_code == 422
    login(client, "alice", "password123")


def test_change_password_success(client, alice, db_session):
    r = client.put("/api/me/password", headers=alice, json=PW)
    assert r.status_code == 200
    assert "newpass456" not in r.text
    stored = db_session().query(User).filter_by(username="alice").one().password_hash
    assert stored.startswith("$2b$") and stored != "newpass456"
    # mật khẩu cũ không đăng nhập được, mật khẩu mới đăng nhập được
    bad = client.post("/auth/login", json={"identifier": "alice", "password": "password123"})
    assert bad.status_code == 401
    login(client, "alice", "newpass456")


def test_change_password_only_affects_self(client, alice):
    register(client, "bob")
    client.put("/api/me/password", headers=alice, json=PW)
    login(client, "bob", "password123")


# ---------------- Hồ sơ công khai ----------------
def test_public_profile_no_login_and_no_private_data(client, alice):
    client.patch("/api/me/profile", headers=alice, json={"bio": "bio của alice"})
    r = client.get("/api/profiles/alice")  # không gửi token
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "alice" and data["display_name"] == "Alice"
    assert data["bio"] == "bio của alice" and data["id"] > 0
    for forbidden in ("email", "password", "password_hash", "role", "status", "avatar_key"):
        assert forbidden not in data
    assert "alice@x.com" not in r.text and "password" not in r.text


def test_public_profile_case_insensitive(client, alice):
    assert client.get("/api/profiles/ALICE").status_code == 200


def test_public_profile_unknown_username_404(client):
    r = client.get("/api/profiles/nobody_here")
    assert r.status_code == 404 and r.json()["detail"]


def test_public_profile_locked_user_hidden(client, db_session):
    register(client, "carol")
    s = db_session()
    s.query(User).filter_by(username="carol").one().status = "LOCKED"
    s.commit()
    assert client.get("/api/profiles/carol").status_code == 404


def test_public_profile_with_sql_injection_like_username(client):
    assert client.get("/api/profiles/' OR '1'='1").status_code == 404


# ---------------- Tích hợp với module social/video ----------------
def test_social_profile_gets_absolute_avatar_url(client, alice):
    upload(client, alice, image_bytes())
    uid = client.get("/api/me/profile", headers=alice).json()["id"]
    r = client.get(f"/api/users/{uid}/profile")
    assert r.status_code == 200
    assert r.json()["avatar_url"].startswith("http://127.0.0.1:8000/uploads/avatars/")
