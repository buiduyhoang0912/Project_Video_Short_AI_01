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


def test_for_you_feed_and_profile(client: TestClient, db_session):
    db = db_session()
    creator, _ = make_user(db, "creator_demo", "cdemo@test.com")
    v = make_video(db, creator.id)

    # 1. Test For You Feed (Public)
    res_feed = client.get("/api/videos/feed/for-you")
    assert res_feed.status_code == 200
    items = res_feed.json()
    assert len(items) >= 1
    found = next((item for item in items if item["id"] == v.id), None)
    assert found is not None
    assert found["author_username"] == "creator_demo"

    # 2. Test Profile API
    res_prof = client.get(f"/api/users/{creator.id}/profile")
    assert res_prof.status_code == 200
    prof = res_prof.json()
    assert prof["username"] == "creator_demo"
    assert prof["video_count"] == 1
    assert len(prof["videos"]) == 1
    assert prof["videos"][0]["id"] == v.id


def test_search_videos_and_users_and_hashtags(client: TestClient, db_session):
    db = db_session()
    user_a, token_a = make_user(db, "alice_wonder", "alice@test.com")
    user_b, token_b = make_user(db, "bob_builder", "bob@test.com")

    # Tạo 3 video với tiêu đề và hashtag khác nhau
    v1 = Video(
        user_id=user_a.id,
        title="Mẹo nấu ăn siêu ngon #cooking #chef",
        description="Cách làm món ăn gia đình đơn giản",
        hashtags=["cooking", "food"],
        video_url="https://example.com/v1.mp4",
        thumbnail_url="https://example.com/t1.jpg",
        duration_seconds=30,
    )
    v2 = Video(
        user_id=user_b.id,
        title="Lập trình Python cơ bản #python #tech",
        description="Hướng dẫn lập trình cho người mới",
        hashtags=["python", "coding"],
        video_url="https://example.com/v2.mp4",
        thumbnail_url="https://example.com/t2.jpg",
        duration_seconds=45,
    )
    v3 = Video(
        user_id=user_a.id,
        title="Công nghệ AI mới nhất #tech",
        description="Khám phá trí tuệ nhân tạo",
        hashtags=["tech", "ai"],
        video_url="https://example.com/v3.mp4",
        thumbnail_url="https://example.com/t3.jpg",
        duration_seconds=60,
    )
    db.add_all([v1, v2, v3])
    db.commit()

    # User B follow User A và like V1
    h_b = {"Authorization": f"Bearer {token_b}"}
    client.post(f"/api/users/{user_a.id}/follow", headers=h_b)
    client.post(f"/api/videos/{v1.id}/likes", headers=h_b)

    # 1. Tìm kiếm video theo từ khoá (query q="nấu ăn")
    res_v = client.get("/api/search?q=nấu ăn&type=videos")
    assert res_v.status_code == 200
    data_v = res_v.json()
    assert len(data_v["videos"]) == 1
    assert data_v["videos"][0]["id"] == v1.id

    # 2. Tìm kiếm video theo hashtag "tech"
    res_tag = client.get("/api/search?tag=tech&type=videos")
    assert res_tag.status_code == 200
    tag_videos = res_tag.json()["videos"]
    assert len(tag_videos) == 2
    tag_v_ids = {v["id"] for v in tag_videos}
    assert v2.id in tag_v_ids and v3.id in tag_v_ids

    # 3. Endpoint xem video theo hashtag trực tiếp /api/search/hashtags/{tag}
    res_direct_tag = client.get("/api/search/hashtags/cooking", headers=h_b)
    assert res_direct_tag.status_code == 200
    cooking_vids = res_direct_tag.json()
    assert len(cooking_vids) == 1
    assert cooking_vids[0]["id"] == v1.id
    # Kiểm tra is_liked phản ánh đúng cho user_b
    assert cooking_vids[0]["is_liked"] is True

    # 4. Tìm kiếm người dùng theo username/display_name
    res_u = client.get("/api/search?q=alice&type=users", headers=h_b)
    assert res_u.status_code == 200
    users = res_u.json()["users"]
    assert len(users) == 1
    assert users[0]["username"] == "alice_wonder"
    assert users[0]["is_following"] is True
    assert users[0]["followers_count"] == 1

    # 5. Tìm kiếm hashtag
    res_h = client.get("/api/search?q=cook&type=hashtags")
    assert res_h.status_code == 200
    hts = res_h.json()["hashtags"]
    assert any(h["tag"] == "cooking" for h in hts)

    # 6. Tìm kiếm all (tổng hợp 3 loại)
    res_all = client.get("/api/search?q=tech&type=all")
    assert res_all.status_code == 200
    all_data = res_all.json()
    assert len(all_data["videos"]) >= 1
    assert any(h["tag"] == "tech" for h in all_data["hashtags"])

    # 7. Phân trang
    res_page = client.get("/api/search?type=videos&skip=0&limit=1")
    assert res_page.status_code == 200
    assert len(res_page.json()["videos"]) == 1


def test_single_video_view_and_share_count_flow(client: TestClient, db_session):
    db = db_session()
    author, token_author = make_user(db, "video_owner", "owner@test.com")
    viewer, token_viewer = make_user(db, "video_viewer", "viewer2@test.com")
    v = make_video(db, author.id)

    h_viewer = {"Authorization": f"Bearer {token_viewer}"}

    # 1. Xem riêng 1 video qua /api/videos/{id}
    r1 = client.get(f"/api/videos/{v.id}", headers=h_viewer)
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["id"] == v.id
    assert d1["status"] == "VISIBLE"
    assert d1["is_available"] is True
    assert d1["video_url"] == "https://example.com/video.mp4"
    assert d1["share_count"] == 0
    assert d1["view_count"] >= 1

    # 2. Chia sẻ video bởi người dùng đã đăng nhập -> trả về share_count = 1
    s1 = client.post(f"/api/videos/{v.id}/share", headers=h_viewer)
    assert s1.status_code == 200
    assert s1.json()["share_count"] == 1

    # 3. Chia sẻ video bởi khách chưa đăng nhập (dùng link chia sẻ) -> share_count = 2
    s2 = client.post(f"/api/videos/{v.id}/share")
    assert s2.status_code == 200
    assert s2.json()["share_count"] == 2

    # 4. Kiểm tra lại qua alias /api/video/{id}
    r2 = client.get(f"/api/video/{v.id}")
    assert r2.status_code == 200
    assert r2.json()["share_count"] == 2


def test_hidden_video_unavailable_and_visibility_toggle(
    client: TestClient, db_session
):
    db = db_session()
    owner, token_owner = make_user(db, "owner_vid", "ownvid@test.com")
    stranger, token_stranger = make_user(db, "stranger", "stranger@test.com")
    v = make_video(db, owner.id)

    h_owner = {"Authorization": f"Bearer {token_owner}"}
    h_stranger = {"Authorization": f"Bearer {token_stranger}"}

    # 1. Người lạ không được phép ẩn video của người khác -> 403
    forbid = client.patch(
        f"/api/videos/{v.id}/status",
        json={"status": "HIDDEN"},
        headers=h_stranger,
    )
    assert forbid.status_code == 403

    # 2. Chủ video ẩn video -> 200
    hide_res = client.patch(
        f"/api/videos/{v.id}/status",
        json={"status": "HIDDEN"},
        headers=h_owner,
    )
    assert hide_res.status_code == 200
    assert hide_res.json()["status"] == "HIDDEN"
    assert hide_res.json()["is_available"] is False

    # 3. Khi truy cập trang xem riêng video bị ẩn -> trả về thông báo không còn khả dụng, ẩn video_url
    detail_hidden = client.get(f"/api/videos/{v.id}")
    assert detail_hidden.status_code == 200
    dh = detail_hidden.json()
    assert dh["status"] == "HIDDEN"
    assert dh["is_available"] is False
    assert dh["video_url"] is None
    assert "không còn khả dụng" in (dh["unavailable_message"] or "").lower()

    # 4. Không thể chia sẻ video đã bị ẩn -> 400
    share_hidden = client.post(f"/api/videos/{v.id}/share")
    assert share_hidden.status_code == 400

    # 5. Chủ video hiển thị lại video -> khả dụng trở lại
    unhide_res = client.patch(
        f"/api/videos/{v.id}/status",
        json={"status": "VISIBLE"},
        headers=h_owner,
    )
    assert unhide_res.status_code == 200
    assert unhide_res.json()["is_available"] is True

    detail_visible = client.get(f"/api/videos/{v.id}")
    assert detail_visible.status_code == 200
    assert detail_visible.json()["is_available"] is True
    assert detail_visible.json()["video_url"] == "https://example.com/video.mp4"

    # 6. Video không tồn tại -> 404
    not_found = client.get("/api/videos/999999")
    assert not_found.status_code == 404


