"""Test /auth/*. Chay: pytest (dung SQLite in-memory, khong can MySQL)."""
import time
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.models.user import User
from app.models.revoked_token import RevokedToken


@compiles(BIGINT, "sqlite")
def _bigint_sqlite(t, c, **k):
    return "INTEGER"


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    yield Session
    engine.dispose()


@pytest.fixture()
def client(db_session):
    def override():
        db = db_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


BODY = {"email": "A@x.com", "username": "alice", "password": "password123", "display_name": "Alice"}


def login_token(client):
    client.post("/auth/register", json=BODY)
    r = client.post("/auth/login", json={"identifier": "alice", "password": "password123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_ok_and_no_secret_leak(client, db_session):
    r = client.post("/auth/register", json=BODY)
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "a@x.com" and data["role"] == "USER"
    assert "password" not in data and "password_hash" not in data
    assert "password123" not in r.text
    stored = db_session().query(User).one().password_hash
    assert stored.startswith("$2b$") and stored != "password123"


def test_register_duplicates_409(client):
    assert client.post("/auth/register", json=BODY).status_code == 201
    assert client.post("/auth/register", json={**BODY, "username": "bob"}).status_code == 409
    assert client.post("/auth/register", json={**BODY, "email": "b@x.com"}).status_code == 409


def test_register_invalid_422(client):
    assert client.post("/auth/register", json={**BODY, "email": "bad"}).status_code == 422
    assert client.post("/auth/register", json={**BODY, "password": "1"}).status_code == 422
    assert client.post("/auth/register", json={**BODY, "role": "ADMIN"}).status_code == 422


def test_login_ok_and_wrong_password(client):
    client.post("/auth/register", json=BODY)
    r = client.post("/auth/login", json={"identifier": "alice", "password": "password123"})
    assert r.status_code == 200 and r.json()["access_token"]
    r = client.post("/auth/login", json={"identifier": "alice", "password": "wrongpass1"})
    assert r.status_code == 401


def test_me_valid_token(client):
    token = login_token(client)
    r = client.get("/auth/me", headers=auth(token))
    assert r.status_code == 200 and r.json()["username"] == "alice"


def test_me_missing_invalid_expired_and_incomplete_token_401(client):
    login_token(client)
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers=auth("abc.def.ghi")).status_code == 401
    now = int(time.time())
    key, alg = settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM
    expired = jwt.encode({"sub": "1", "jti": uuid.uuid4().hex, "exp": now - 10}, key, algorithm=alg)
    assert client.get("/auth/me", headers=auth(expired)).status_code == 401
    no_jti = jwt.encode({"sub": "1", "exp": now + 600}, key, algorithm=alg)
    assert client.get("/auth/me", headers=auth(no_jti)).status_code == 401
    assert client.post("/auth/logout", headers=auth(no_jti)).status_code == 401


def test_logout_then_reuse_token_401(client):
    token = login_token(client)
    assert client.post("/auth/logout", headers=auth(token)).status_code == 200
    assert client.get("/auth/me", headers=auth(token)).status_code == 401
    assert client.post("/auth/logout", headers=auth(token)).status_code == 401


def test_logout_concurrent_duplicate_jti_no_500(client, db_session):
    """Neu jti da bi chen boi request khac sau buoc kiem tra -> van khong 500."""
    token = login_token(client)
    from app.routers import auth as auth_router
    from app.core.security import decode_access_token

    payload = decode_access_token(token)
    s = db_session()
    s.add(RevokedToken(jti=payload["jti"], expires_at=__import__("datetime").datetime.utcnow()))
    s.commit()
    # goi thang ham logout voi payload da bi thu hoi -> IntegrityError duoc xu ly
    assert auth_router.logout(payload=payload, db=db_session())["message"]