"""Test dependency phan quyen dung chung (app.core.dependencies)."""
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.dependencies import (
    get_current_user,
    get_optional_user,
    require_admin,
    require_seller,
)
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import app as main_app
from app.models.user import User

from .test_auth import client, db_session  # noqa: F401  (fixtures)


@pytest.fixture()
def api(db_session):
    app = FastAPI()

    def override():
        db = db_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override

    @app.get("/public")
    def public(u=Depends(get_optional_user)):
        return {"user": u.username if u else None}

    @app.get("/private")
    def private(u=Depends(get_current_user)):
        return {"user": u.username}

    @app.get("/seller")
    def seller(u=Depends(require_seller)):
        return {"user": u.username}

    @app.get("/admin")
    def admin(u=Depends(require_admin)):
        return {"user": u.username}

    return TestClient(app)


def make(db_session, username, role="USER", status="ACTIVE"):
    db = db_session()
    u = User(
        email=f"{username}@x.com",
        username=username,
        password_hash=hash_password("password123"),
        display_name=username,
        role=role,
        status=status,
    )
    db.add(u)
    db.commit()
    token, _ = create_access_token(u.id)
    uid = u.id
    db.close()
    return uid, {"Authorization": f"Bearer {token}"}


def test_guest_feed_and_optional(client, api):
    assert client.get("/api/videos/feed").status_code == 200
    r = api.get("/public")
    assert r.status_code == 200 and r.json() == {"user": None}


def test_optional_bad_token_is_401_not_guest(client, api):
    assert api.get("/public", headers={"Authorization": "Bearer abc"}).status_code == 401
    assert client.get("/api/videos/feed", headers={"Authorization": "Bearer abc"}).status_code == 401


def test_optional_valid_token(db_session, api):
    _, h = make(db_session, "u1")
    assert api.get("/public", headers=h).json() == {"user": "u1"}


def test_private_missing_bad_expired_401(db_session, api):
    uid, _ = make(db_session, "u1")
    assert api.get("/private").status_code == 401
    assert api.get("/private", headers={"Authorization": "Bearer x.y.z"}).status_code == 401
    now = datetime.now(timezone.utc)
    expired = jwt.encode(
        {"sub": str(uid), "jti": uuid.uuid4().hex, "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    assert api.get("/private", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    assert api.get("/public", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_role_matrix(db_session, api):
    _, user = make(db_session, "u1", "USER")
    _, seller = make(db_session, "s1", "SELLER")
    _, admin = make(db_session, "a1", "ADMIN")
    assert api.get("/seller", headers=user).status_code == 403
    assert api.get("/admin", headers=user).status_code == 403
    assert api.get("/seller", headers=seller).status_code == 200
    assert api.get("/admin", headers=seller).status_code == 403
    assert api.get("/admin", headers=admin).status_code == 200
    assert api.get("/seller", headers=admin).status_code == 403
    assert api.get("/seller").status_code == 401
    assert api.get("/admin").status_code == 401


def test_locked_user_blocked_with_valid_token(db_session, api):
    _, h = make(db_session, "l1", "ADMIN", "LOCKED")
    assert api.get("/private", headers=h).status_code == 403
    assert api.get("/public", headers=h).status_code == 403
    assert api.get("/admin", headers=h).status_code == 403


def test_video_write_requires_jwt(client):
    assert client.post("/api/videos").status_code == 401
