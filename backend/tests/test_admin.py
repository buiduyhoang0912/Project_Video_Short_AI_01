"""Test API Admin (Task T3D2003): duyệt đơn bán hàng và quản lý tài khoản.
Chạy: pytest tests/test_admin.py (SQLite in-memory, không cần MySQL).
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.core.security import create_access_token, hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models.seller_application import SellerApplication
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
    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(Session, role="USER", name=None):
    n = name or uuid.uuid4().hex[:8]
    with Session() as db:
        u = User(
            email=f"{n}@test.com", username=n, display_name=f"Ten {n}",
            password_hash=hash_password("Passw0rd!"), role=role,
        )
        db.add(u)
        db.commit()
        return u.id


def auth(uid):
    token, _ = create_access_token(uid)
    return {"Authorization": f"Bearer {token}"}


def make_app(Session, user_id):
    with Session() as db:
        a = SellerApplication(
            user_id=user_id, proposed_shop_name="Shop A", phone="0912345678",
            description="Mo ta", status="PENDING",
        )
        db.add(a)
        db.commit()
        return a.id


def role_of(Session, uid):
    with Session() as db:
        return db.get(User, uid).role


# ---------- Phân quyền ----------
ADMIN_CALLS = [
    ("get", "/api/admin/seller-applications"),
    ("patch", "/api/admin/seller-applications/1/approve"),
    ("patch", "/api/admin/seller-applications/1/reject"),
    ("get", "/api/admin/users"),
    ("patch", "/api/admin/users/1/lock"),
    ("patch", "/api/admin/users/1/unlock"),
]


@pytest.mark.parametrize("method,url", ADMIN_CALLS)
def test_non_admin_forbidden(client, Session, method, url):
    for role in ("USER", "SELLER"):
        uid = make_user(Session, role)
        assert getattr(client, method)(url, headers=auth(uid)).status_code == 403


@pytest.mark.parametrize("method,url", ADMIN_CALLS)
def test_no_token_unauthorized(client, method, url):
    assert getattr(client, method)(url).status_code == 401


# ---------- Duyệt đơn ----------
def test_approve_sets_seller(client, Session):
    admin = make_user(Session, "ADMIN")
    user = make_user(Session, "USER")
    app_id = make_app(Session, user)
    r = client.patch(f"/api/admin/seller-applications/{app_id}/approve", headers=auth(admin))
    assert r.status_code == 200
    assert r.json()["status"] == "APPROVED"
    assert r.json()["reviewed_by"] == admin
    assert role_of(Session, user) == "SELLER"


def test_approve_twice_conflict_and_missing_404(client, Session):
    admin = make_user(Session, "ADMIN")
    app_id = make_app(Session, make_user(Session))
    url = f"/api/admin/seller-applications/{app_id}/approve"
    assert client.patch(url, headers=auth(admin)).status_code == 200
    assert client.patch(url, headers=auth(admin)).status_code == 409
    assert client.patch("/api/admin/seller-applications/9999/approve", headers=auth(admin)).status_code == 404


def test_approve_rolls_back_when_commit_fails(Session, monkeypatch):
    """Nếu commit lỗi thì cả đơn lẫn quyền đều không đổi (cùng thành công/thất bại)."""
    from sqlalchemy.orm import Session as SASession

    from app.crud import admin as admin_crud

    admin = make_user(Session, "ADMIN")
    user = make_user(Session)
    app_id = make_app(Session, user)

    def boom(self):
        raise RuntimeError("db lỗi")

    with Session() as db:
        with monkeypatch.context() as m:
            m.setattr(SASession, "commit", boom)
            with pytest.raises(RuntimeError):
                admin_crud.approve_application(db, app_id, admin)
    with Session() as db:
        assert db.get(SellerApplication, app_id).status == "PENDING"
        assert db.get(User, user).role == "USER"


# ---------- Từ chối ----------
def test_reject_requires_reason(client, Session):
    admin = make_user(Session, "ADMIN")
    user = make_user(Session)
    app_id = make_app(Session, user)
    url = f"/api/admin/seller-applications/{app_id}/reject"
    assert client.patch(url, json={}, headers=auth(admin)).status_code == 422
    assert client.patch(url, json={"rejection_reason": "   "}, headers=auth(admin)).status_code == 422
    r = client.patch(url, json={"rejection_reason": "Thiếu giấy tờ"}, headers=auth(admin))
    assert r.status_code == 200
    assert r.json()["status"] == "REJECTED"
    assert r.json()["rejection_reason"] == "Thiếu giấy tờ"
    with Session() as db:
        assert db.get(SellerApplication, app_id).rejection_reason == "Thiếu giấy tờ"
    assert role_of(Session, user) == "USER"
    # đã xử lý -> không từ chối lại được
    assert client.patch(url, json={"rejection_reason": "x"}, headers=auth(admin)).status_code == 409


def test_list_applications_with_applicant_and_filter(client, Session):
    admin = make_user(Session, "ADMIN")
    u1, u2 = make_user(Session, name="alice"), make_user(Session, name="bob")
    a1 = make_app(Session, u1)
    make_app(Session, u2)
    client.patch(f"/api/admin/seller-applications/{a1}/approve", headers=auth(admin))
    allr = client.get("/api/admin/seller-applications", headers=auth(admin)).json()
    assert len(allr) == 2 and {x["applicant"]["username"] for x in allr} == {"alice", "bob"}
    pend = client.get("/api/admin/seller-applications?status=PENDING", headers=auth(admin)).json()
    assert [x["applicant"]["username"] for x in pend] == ["bob"]
    assert client.get("/api/admin/seller-applications?status=XYZ", headers=auth(admin)).status_code == 422


# ---------- Tài khoản ----------
def test_search_users(client, Session):
    admin = make_user(Session, "ADMIN", name="boss")
    make_user(Session, name="alice")
    make_user(Session, name="bobby")
    h = auth(admin)
    r = client.get("/api/admin/users?search=alice", headers=h).json()
    assert [u["username"] for u in r] == ["alice"]
    assert [u["username"] for u in client.get("/api/admin/users?search=bobby@test", headers=h).json()] == ["bobby"]
    assert client.get("/api/admin/users?search=khongco", headers=h).json() == []
    # ký tự wildcard được xử lý như ký tự thường
    assert client.get("/api/admin/users?search=%25", headers=h).json() == []
    everyone = client.get("/api/admin/users", headers=h).json()
    assert len(everyone) == 3
    assert "password_hash" not in everyone[0]


def test_lock_blocks_old_token_and_login_unlock_restores(client, Session):
    admin = make_user(Session, "ADMIN")
    user = make_user(Session, name="victim")
    old = auth(user)
    login_body = {"identifier": "victim", "password": "Passw0rd!"}
    assert client.get("/api/seller-applications/me", headers=old).status_code == 200

    r = client.patch(f"/api/admin/users/{user}/lock", headers=auth(admin))
    assert r.status_code == 200 and r.json()["status"] == "LOCKED"
    assert client.patch(f"/api/admin/users/{user}/lock", headers=auth(admin)).status_code == 409

    # token cũ và đăng nhập đều bị chặn
    assert client.get("/api/seller-applications/me", headers=old).status_code == 403
    assert client.post("/auth/login", json=login_body).status_code == 403

    r = client.patch(f"/api/admin/users/{user}/unlock", headers=auth(admin))
    assert r.status_code == 200 and r.json()["status"] == "ACTIVE"
    assert client.patch(f"/api/admin/users/{user}/unlock", headers=auth(admin)).status_code == 409
    assert client.get("/api/seller-applications/me", headers=old).status_code == 200
    assert client.post("/auth/login", json=login_body).status_code == 200


def test_admin_cannot_lock_self_and_missing_user(client, Session):
    admin = make_user(Session, "ADMIN")
    assert client.patch(f"/api/admin/users/{admin}/lock", headers=auth(admin)).status_code == 400
    assert client.patch("/api/admin/users/9999/lock", headers=auth(admin)).status_code == 404


def test_quick_setup_self_approve_endpoint_removed(client, Session):
    """Người dùng thường không còn cách tự nhận quyền SELLER bỏ qua Admin."""
    user = make_user(Session, "USER")
    r = client.post("/api/seller-applications/quick-setup", headers=auth(user))
    assert r.status_code in (404, 405)
    assert role_of(Session, user) == "USER"
