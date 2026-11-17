"""Test 4 dependency trong app/dependencies/auth.py. Chay: pytest tests/test_auth_dependencies.py"""
import time
import uuid

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.core.config import settings
from app.core.security import create_access_token, decode_access_token
from app.db.session import Base, get_db
from app.dependencies.auth import (
    get_current_user,
    get_optional_user,
    require_admin,
    require_seller,
)
from app.models.revoked_token import RevokedToken
from app.models.user import User


@pytest.fixture()
def Session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine)
    engine.dispose()


@pytest.fixture()
def client(Session):
    app = FastAPI()

    @app.get("/feed")
    def feed(user: User | None = Depends(get_optional_user)):
        return {"user": user.username if user else None}

    @app.get("/me")
    def me(user: User = Depends(get_current_user)):
        return {"id": user.id, "role": user.role}

    @app.get("/seller")
    def seller(user: User = Depends(require_seller)):
        return {"id": user.id}

    @app.get("/admin")
    def admin(user: User = Depends(require_admin)):
        return {"id": user.id}

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    return TestClient(app)


def make_user(Session, role="USER", status="ACTIVE"):
    n = uuid.uuid4().hex[:8]
    with Session() as db:
        u = User(email=f"{n}@x.com", username=n, display_name=n,
                 password_hash="x", role=role, status=status)
        db.add(u)
        db.commit()
        return u.id


def headers(uid):
    token, _ = create_access_token(uid)
    return {"Authorization": f"Bearer {token}"}


def test_guest_can_view_feed(client):
    r = client.get("/feed")
    assert r.status_code == 200 and r.json() == {"user": None}


def test_guest_blocked_on_protected(client):
    r = client.get("/me")
    assert r.status_code == 401
    assert r.json()["detail"] == "Chưa đăng nhập"
    assert r.headers["www-authenticate"] == "Bearer"


def test_valid_token_returns_user(client, Session):
    uid = make_user(Session)
    assert client.get("/me", headers=headers(uid)).json()["id"] == uid
    assert client.get("/feed", headers=headers(uid)).status_code == 200


@pytest.mark.parametrize("path", ["/me", "/feed", "/seller", "/admin"])
def test_bad_token_401(client, path):
    r = client.get(path, headers={"Authorization": "Bearer abc"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Token không hợp lệ"
    assert r.headers["www-authenticate"] == "Bearer"


def test_expired_token_401(client, Session):
    uid = make_user(Session)
    token = jwt.encode(
        {"sub": str(uid), "jti": uuid.uuid4().hex, "exp": int(time.time()) - 10},
        settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM,
    )
    for p in ("/me", "/feed"):
        assert client.get(p, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_logged_out_token_401(client, Session):
    uid = make_user(Session)
    h = headers(uid)
    payload = decode_access_token(h["Authorization"].split()[1])
    with Session() as db:
        db.add(RevokedToken(jti=payload["jti"], expires_at=__import__("datetime").datetime.utcnow()))
        db.commit()
    assert client.get("/me", headers=h).status_code == 401
    assert client.get("/feed", headers=h).status_code == 401


def test_nonexistent_user_401(client):
    assert client.get("/me", headers=headers(99999)).status_code == 401


def test_locked_user_403_even_on_feed(client, Session):
    uid = make_user(Session, status="LOCKED")
    for p in ("/me", "/feed", "/seller", "/admin"):
        r = client.get(p, headers=headers(uid))
        assert r.status_code == 403 and r.json()["detail"] == "Tài khoản đã bị khóa"


def test_locking_after_token_issued_blocks(client, Session):
    uid = make_user(Session)
    h = headers(uid)
    assert client.get("/me", headers=h).status_code == 200
    with Session() as db:
        db.get(User, uid).status = "LOCKED"
        db.commit()
    assert client.get("/me", headers=h).status_code == 403


def test_role_change_applies_immediately(client, Session):
    uid = make_user(Session)
    h = headers(uid)
    assert client.get("/seller", headers=h).status_code == 403
    with Session() as db:
        db.get(User, uid).role = "SELLER"
        db.commit()
    assert client.get("/seller", headers=h).status_code == 200


def test_user_blocked_on_seller_admin(client, Session):
    h = headers(make_user(Session))
    for p in ("/seller", "/admin"):
        r = client.get(p, headers=h)
        assert r.status_code == 403 and r.json()["detail"] == "Không đủ quyền truy cập"


def test_seller_and_admin_access(client, Session):
    seller = headers(make_user(Session, role="SELLER"))
    admin = headers(make_user(Session, role="ADMIN"))
    assert client.get("/seller", headers=seller).status_code == 200
    assert client.get("/admin", headers=seller).status_code == 403
    assert client.get("/admin", headers=admin).status_code == 200
    assert client.get("/seller", headers=admin).status_code == 403  # admin khong dung API seller


def test_no_token_on_role_apis_401(client):
    assert client.get("/seller").status_code == 401
    assert client.get("/admin").status_code == 401



@pytest.mark.parametrize("value", ["Bearer", "Bearer ", "Basic abc", "abc", ""])
def test_malformed_authorization_header_401(client, value):
    for path in ("/feed", "/me"):
        r = client.get(path, headers={"Authorization": value})
        assert r.status_code == 401
        assert r.headers["www-authenticate"] == "Bearer"
