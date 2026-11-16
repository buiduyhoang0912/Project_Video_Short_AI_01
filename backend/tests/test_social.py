"""Test các API tương tác mạng xã hội (Task T3D2300 - Phùng Quang Huy).
Chạy: pytest (dùng SQLite in-memory, không cần MySQL).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import BIGINT, ENUM, INTEGER
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.core.security import create_access_token, hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models.shop import Shop
from app.models.user import User
from app.models.video import Video

# Bổ sung relationship còn thiếu khi chạy test với SQLite
if not hasattr(User, "addresses"):
    User.addresses = relationship("Address", back_populates="user")
if not hasattr(User, "orders"):
    User.orders = relationship("Order", back_populates="buyer")
if not hasattr(User, "cart"):
    User.cart = relationship("Cart", back_populates="user", uselist=False)
if not hasattr(Shop, "orders"):
    Shop.orders = relationship("Order", back_populates="shop")


@compiles(BIGINT, "sqlite")
def _bigint_sqlite(t, c, **k):
    return "INTEGER"


@compiles(INTEGER, "sqlite")
def _int_sqlite(t, c, **k):
    return "INTEGER"


@compiles(ENUM, "sqlite")
def _enum_sqlite(t, c, **k):
    return "VARCHAR(50)"


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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


def make_user(db, username: str, email: str, role: str = "USER") -> tuple[User, str]:
    user = User(
        username=username,
        email=email,
        display_name=username,
        password_hash=hash_password("password123"),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token, _ = create_access_token(user.id)
    return user, token


def make_video(db, user_id: int) -> Video:
    video = Video(
        user_id=user_id,
        title="Test Video Title",
        description="Test video description",
        video_url="https://example.com/video.mp4",
        thumbnail_url="https://example.com/thumb.jpg",
        duration_seconds=30,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


def test_like_and_unlike_flow(client: TestClient, db_session):
    db = db_session()
    user1, token1 = make_user(db, "huy_tester", "huy@test.com")
    video = make_video(db, user1.id)
    headers = {"Authorization": f"Bearer {token1}"}

    # 1. Like video
    res = client.post(f"/api/videos/{video.id}/likes", headers=headers)
    assert res.status_code == 200
    assert res.json()["liked"] is True

    # 2. Like lại (Idempotency - không lỗi)
    res_again = client.post(f"/api/videos/{video.id}/likes", headers=headers)
    assert res_again.status_code == 200
    assert res_again.json()["liked"] is True

    # 3. Kiểm tra stats
    stats = client.get(f"/api/videos/{video.id}/stats")
    assert stats.status_code == 200
    assert stats.json()["like_count"] == 1

    # 4. Unlike video
    res_unlike = client.delete(f"/api/videos/{video.id}/likes", headers=headers)
    assert res_unlike.status_code == 200
    assert res_unlike.json()["liked"] is False

    # 5. Kiểm tra stats sau unlike
    stats_after = client.get(f"/api/videos/{video.id}/stats")
    assert stats_after.json()["like_count"] == 0


def test_comments_flow_and_permissions(client: TestClient, db_session):
    db = db_session()
    user1, token1 = make_user(db, "user_one", "one@test.com")
    user2, token2 = make_user(db, "user_two", "two@test.com")
    video = make_video(db, user1.id)

    h1 = {"Authorization": f"Bearer {token1}"}
    h2 = {"Authorization": f"Bearer {token2}"}

    # 1. Tạo comment gốc
    c1 = client.post(
        f"/api/videos/{video.id}/comments",
        json={"content": "Bình luận gốc số 1"},
        headers=h1,
    )
    assert c1.status_code == 201
    comment1_id = c1.json()["id"]

    # 2. Tạo reply comment (1 cấp)
    c2 = client.post(
        f"/api/videos/{video.id}/comments",
        json={"content": "Trả lời comment gốc", "parent_id": comment1_id},
        headers=h2,
    )
    assert c2.status_code == 201
    reply_id = c2.json()["id"]

    # 3. Thử reply vào comment reply (> 1 cấp) -> Bị từ chối 400
    c3 = client.post(
        f"/api/videos/{video.id}/comments",
        json={"content": "Trả lời comment cấp 2", "parent_id": reply_id},
        headers=h1,
    )
    assert c3.status_code == 400
    assert "1 cấp" in c3.json()["detail"]

    # 4. Xem danh sách comment
    list_res = client.get(f"/api/videos/{video.id}/comments")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 2

    # 5. User 2 không thể xóa comment của User 1 -> 403
    del_forbidden = client.delete(f"/api/comments/{comment1_id}", headers=h2)
    assert del_forbidden.status_code == 403

    # 6. User 1 xóa comment gốc -> Xóa cả reply con trong thread
    del_ok = client.delete(f"/api/comments/{comment1_id}", headers=h1)
    assert del_ok.status_code == 200
    assert del_ok.json()["deleted_comments"] == 2

    # 7. Xem lại danh sách comment -> Trống
    list_after = client.get(f"/api/videos/{video.id}/comments")
    assert len(list_after.json()) == 0


def test_follow_and_unfollow(client: TestClient, db_session):
    db = db_session()
    user1, token1 = make_user(db, "follower", "fl@test.com")
    user2, _ = make_user(db, "target", "target@test.com")

    h1 = {"Authorization": f"Bearer {token1}"}

    # 1. Không thể tự theo dõi chính mình -> 400
    self_follow = client.post(f"/api/users/{user1.id}/follow", headers=h1)
    assert self_follow.status_code == 400

    # 2. Theo dõi user khác
    res_fl = client.post(f"/api/users/{user2.id}/follow", headers=h1)
    assert res_fl.status_code == 200
    assert res_fl.json()["following"] is True

    # 3. Theo dõi lại (Idempotent)
    res_again = client.post(f"/api/users/{user2.id}/follow", headers=h1)
    assert res_again.status_code == 200
    assert res_again.json()["following"] is True

    # 4. Bỏ theo dõi
    un_fl = client.delete(f"/api/users/{user2.id}/follow", headers=h1)
    assert un_fl.status_code == 200
    assert un_fl.json()["following"] is False


def test_share_video_and_stats(client: TestClient, db_session):
    db = db_session()
    user, token = make_user(db, "sharer", "sharer@test.com")
    video = make_video(db, user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Chia sẻ video
    res = client.post(f"/api/videos/{video.id}/share", headers=headers)
    assert res.status_code == 200

    # Thống kê
    stats = client.get(f"/api/videos/{video.id}/stats")
    assert stats.status_code == 200
    assert stats.json()["share_count"] == 1


def test_ai_chat_logs(client: TestClient, db_session):
    db = db_session()
    user, token = make_user(db, "ai_user", "ai@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Tạo nhật ký chat AI
    res = client.post(
        "/api/ai/chat-logs",
        json={"message": "Gợi ý cho tôi sản phẩm tốt"},
        headers=headers,
    )
    assert res.status_code == 201
    assert res.json()["role"] == "user"

    # Lấy lịch sử chat AI
    logs = client.get("/api/ai/chat-logs", headers=headers)
    assert logs.status_code == 200
    assert len(logs.json()) == 1
    assert logs.json()[0]["message"] == "Gợi ý cho tôi sản phẩm tốt"


def test_follow_stats_and_lists(client: TestClient, db_session):
    db = db_session()
    user_a, token_a = make_user(db, "user_a", "a@test.com")
    user_b, token_b = make_user(db, "user_b", "b@test.com")
    user_c, _ = make_user(db, "user_c", "c@test.com")

    ha = {"Authorization": f"Bearer {token_a}"}
    hb = {"Authorization": f"Bearer {token_b}"}

    # Ban đầu user_c chưa có ai follow
    s0 = client.get(f"/api/users/{user_c.id}/follow-stats")
    assert s0.status_code == 200
    assert s0.json()["followers_count"] == 0
    assert s0.json()["following_count"] == 0
    assert s0.json()["is_following"] is False

    # A và B follow C
    client.post(f"/api/users/{user_c.id}/follow", headers=ha)
    client.post(f"/api/users/{user_c.id}/follow", headers=hb)

    # C follow A
    client.post(f"/api/users/{user_a.id}/follow", headers={"Authorization": f"Bearer {make_user(db, 'temp', 'temp@t.com')[1]}"})

    # Stats của C: 2 followers
    sc = client.get(f"/api/users/{user_c.id}/follow-stats", headers=ha)
    assert sc.status_code == 200
    assert sc.json()["followers_count"] == 2
    assert sc.json()["is_following"] is True  # A is viewing, A is following C

    # Danh sách followers của C: có A và B
    followers_res = client.get(f"/api/users/{user_c.id}/followers")
    assert followers_res.status_code == 200
    followers = followers_res.json()
    assert len(followers) == 2
    usernames = [u["username"] for u in followers]
    assert "user_a" in usernames
    assert "user_b" in usernames

    # Danh sách following của A: có C
    following_res = client.get(f"/api/users/{user_a.id}/following")
    assert following_res.status_code == 200
    following = following_res.json()
    assert len(following) == 1
    assert following[0]["username"] == "user_c"


def test_following_feed_flow(client: TestClient, db_session):
    db = db_session()
    viewer, viewer_token = make_user(db, "viewer", "viewer@test.com")
    creator1, _ = make_user(db, "creator1", "cr1@test.com")
    creator2, _ = make_user(db, "creator2", "cr2@test.com")

    v_headers = {"Authorization": f"Bearer {viewer_token}"}

    # Chưa follow ai -> feed rỗng
    feed0 = client.get("/api/videos/feed/following", headers=v_headers)
    assert feed0.status_code == 200
    assert feed0.json() == []

    # Viewer follow creator1 (chưa follow creator2)
    client.post(f"/api/users/{creator1.id}/follow", headers=v_headers)

    # creator1 đăng 2 video, creator2 đăng 1 video
    v1 = make_video(db, creator1.id)
    v2 = make_video(db, creator1.id)
    _ = make_video(db, creator2.id)

    # Viewer like v1
    client.post(f"/api/videos/{v1.id}/likes", headers=v_headers)

    # Lấy feed
    feed = client.get("/api/videos/feed/following", headers=v_headers)
    assert feed.status_code == 200
    items = feed.json()
    assert len(items) == 2  # Chỉ có 2 video của creator1

    # Kiểm tra metadata và trạng thái is_liked
    v1_item = next(item for item in items if item["id"] == v1.id)
    assert v1_item["author_username"] == "creator1"
    assert v1_item["like_count"] == 1
    assert v1_item["is_liked"] is True

    v2_item = next(item for item in items if item["id"] == v2.id)
    assert v2_item["like_count"] == 0
    assert v2_item["is_liked"] is False

    # Unfollow creator1 -> feed trống
    client.delete(f"/api/users/{creator1.id}/follow", headers=v_headers)
    feed_after = client.get("/api/videos/feed/following", headers=v_headers)
    assert feed_after.status_code == 200
    assert feed_after.json() == []
