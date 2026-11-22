"""Unit & Integration tests cho hệ thống thông báo (Task T3D2BAD).

Kiểm tra:
1. Xác thực: 401 khi chưa đăng nhập.
2. Tạo thông báo 4 loại sự kiện:
   - Thích video -> Chủ video nhận thông báo "LIKE"
   - Bình luận video -> Chủ video nhận thông báo "COMMENT"
   - Theo dõi -> Người được theo dõi nhận thông báo "FOLLOW"
   - Đổi trạng thái đơn hàng -> Người mua nhận thông báo "ORDER_STATUS"
3. Ràng buộc nghiệp vụ:
   - Tự thích/bình luận video của mình: KHÔNG sinh thông báo
   - Thích lại/theo dõi lại đã tồn tại: KHÔNG sinh thông báo trùng
4. API quản lý:
   - GET /api/notifications: Lấy danh sách thông báo theo thứ tự mới nhất
   - GET /api/notifications/unread-count: Đếm đúng số lượng chưa đọc
   - PATCH /api/notifications/{id}/read: Đánh dấu đã đọc thành công
   - Không được xem hoặc đánh dấu thông báo của người khác (bị chặn)
   - PATCH /api/notifications/read-all: Đánh dấu tất cả đã đọc
"""

from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models.category import Category
from app.models.notification import Notification
from app.models.order import Order
from app.models.product import Product
from app.models.shop import Shop
from app.models.social import Follow, Like
from app.models.user import User
from app.models.video import Video


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(db, username, role="USER", display_name=None):
    u = User(
        username=username,
        email=f"{username}@tokflow.com",
        display_name=display_name or f"Tên {username}",
        password_hash=hash_password("Password123!"),
        role=role,
        status="ACTIVE",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def auth_header(user_id: int):
    token, _ = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def test_unauthenticated_notifications_access_401(client):
    """Chưa đăng nhập bị từ chối 401 khi gọi các endpoint thông báo."""
    assert client.get("/api/notifications").status_code == 401
    assert client.get("/api/notifications/unread-count").status_code == 401
    assert client.patch("/api/notifications/1/read").status_code == 401
    assert client.patch("/api/notifications/read-all").status_code == 401


def test_like_video_notification(client, db_session):
    """Người khác thích video sinh thông báo cho chủ video; tự thích video của mình thì không."""
    owner = make_user(db_session, "owner1", display_name="Chủ Video 1")
    viewer = make_user(db_session, "viewer1", display_name="Hoàng")

    # Tạo video của owner
    vid = Video(
        user_id=owner.id,
        title="Video Demo 1",
        video_url="/uploads/videos/test.mp4",
        duration_seconds=10,
        status="VISIBLE",
    )
    db_session.add(vid)
    db_session.commit()
    db_session.refresh(vid)

    # 1. Viewer thích video của owner -> owner nhận thông báo
    h_viewer = auth_header(viewer.id)
    r_like = client.post(f"/api/videos/{vid.id}/likes", headers=h_viewer)
    assert r_like.status_code == 200

    # Kiểm tra owner có thông báo
    h_owner = auth_header(owner.id)
    r_notif = client.get("/api/notifications", headers=h_owner)
    assert r_notif.status_code == 200
    items = r_notif.json()
    assert len(items) == 1
    assert items[0]["type"] == "LIKE"
    assert "Hoàng đã thích video của bạn" in items[0]["content"]
    assert items[0]["is_read"] is False
    assert items[0]["video_id"] == vid.id

    # Đếm unread count của owner
    r_cnt = client.get("/api/notifications/unread-count", headers=h_owner)
    assert r_cnt.json()["unread_count"] == 1

    # Viewer kiểm tra thông báo của mình: không có gì
    r_viewer_notif = client.get("/api/notifications", headers=h_viewer)
    assert len(r_viewer_notif.json()) == 0

    # 2. Thích lại (idempotent) -> Không sinh thông báo trùng lặp
    client.post(f"/api/videos/{vid.id}/likes", headers=h_viewer)
    r_notif_again = client.get("/api/notifications", headers=h_owner)
    assert len(r_notif_again.json()) == 1

    # 3. Owner tự thích video của chính mình -> KHÔNG sinh thông báo
    client.post(f"/api/videos/{vid.id}/likes", headers=h_owner)
    r_notif_self = client.get("/api/notifications", headers=h_owner)
    assert len(r_notif_self.json()) == 1


def test_comment_video_notification(client, db_session):
    """Bình luận video sinh thông báo; tự bình luận video của mình thì không."""
    owner = make_user(db_session, "owner2", display_name="Chủ Kênh 2")
    commenter = make_user(db_session, "commenter1", display_name="Bùi Duy Hoàng")

    vid = Video(
        user_id=owner.id,
        title="Video Hướng Dẫn Nấu Ăn",
        video_url="/uploads/videos/cook.mp4",
        duration_seconds=15,
        status="VISIBLE",
    )
    db_session.add(vid)
    db_session.commit()
    db_session.refresh(vid)

    # 1. Commenter bình luận video
    h_commenter = auth_header(commenter.id)
    r_cmt = client.post(
        f"/api/videos/{vid.id}/comments",
        json={"content": "Món này ngon quá bạn ơi!"},
        headers=h_commenter,
    )
    assert r_cmt.status_code in (200, 201)

    # Owner nhận thông báo
    h_owner = auth_header(owner.id)
    r_owner = client.get("/api/notifications", headers=h_owner)
    items = r_owner.json()
    assert len(items) == 1
    assert items[0]["type"] == "COMMENT"
    assert "Bùi Duy Hoàng đã bình luận video của bạn" in items[0]["content"]
    assert items[0]["video_id"] == vid.id

    # 2. Owner tự bình luận video của mình -> không sinh thông báo
    client.post(
        f"/api/videos/{vid.id}/comments",
        json={"content": "Cảm ơn bạn đã theo dõi!"},
        headers=h_owner,
    )
    r_owner_after = client.get("/api/notifications", headers=h_owner)
    assert len(r_owner_after.json()) == 1


def test_follow_user_notification(client, db_session):
    """Người khác theo dõi sinh thông báo; theo dõi lại không sinh thông báo trùng."""
    user_a = make_user(db_session, "user_a", display_name="Người Dùng A")
    follower = make_user(db_session, "follower_b", display_name="Hoàng")

    h_follower = auth_header(follower.id)
    h_user_a = auth_header(user_a.id)

    # Follower theo dõi User A
    r_follow = client.post(f"/api/users/{user_a.id}/follow", headers=h_follower)
    assert r_follow.status_code == 200

    # User A nhận thông báo
    r_notif = client.get("/api/notifications", headers=h_user_a)
    items = r_notif.json()
    assert len(items) == 1
    assert items[0]["type"] == "FOLLOW"
    assert "Hoàng đã bắt đầu theo dõi bạn" in items[0]["content"]

    # Theo dõi lại lần 2 -> Không sinh thông báo trùng
    client.post(f"/api/users/{user_a.id}/follow", headers=h_follower)
    r_notif2 = client.get("/api/notifications", headers=h_user_a)
    assert len(r_notif2.json()) == 1


def test_order_status_update_notification(client, db_session):
    """Khi shop đổi trạng thái đơn hàng, người mua nhận được thông báo tương ứng."""
    seller = make_user(db_session, "seller_shop", role="SELLER", display_name="Shop Quần Áo")
    buyer = make_user(db_session, "buyer_cust", role="USER", display_name="Khách Hàng")

    shop = Shop(owner_id=seller.id, name="Shop Quần Áo Đẹp", status="ACTIVE")
    cat = Category(name="Thời trang", status="ACTIVE")
    db_session.add_all([shop, cat])
    db_session.commit()
    db_session.refresh(shop)
    db_session.refresh(cat)

    # Tạo đơn hàng của buyer tại shop
    order = Order(
        buyer_id=buyer.id,
        shop_id=shop.id,
        total_amount=Decimal("250000"),
        status="pending",
        recipient_name="Khách Hàng",
        recipient_phone="0912345678",
        recipient_address="Hà Nội",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    h_seller = auth_header(seller.id)
    h_buyer = auth_header(buyer.id)

    # 1. Shop xác nhận đơn: pending -> confirmed
    r_conf = client.post(f"/api/shops/me/orders/{order.id}/confirm", headers=h_seller)
    assert r_conf.status_code == 200

    # Buyer nhận thông báo xác nhận
    r_b1 = client.get("/api/notifications", headers=h_buyer)
    items1 = r_b1.json()
    assert len(items1) == 1
    assert items1[0]["type"] == "ORDER_STATUS"
    assert f"Đơn #{order.id} đã được xác nhận" in items1[0]["content"]
    assert items1[0]["order_id"] == order.id

    # 2. Shop giao hàng: confirmed -> shipping
    r_ship = client.post(f"/api/shops/me/orders/{order.id}/ship", headers=h_seller)
    assert r_ship.status_code == 200

    # Buyer nhận thông báo đang giao hàng
    r_b2 = client.get("/api/notifications", headers=h_buyer)
    items2 = r_b2.json()
    assert len(items2) == 2
    # Thông báo mới nhất ở trên đầu
    assert items2[0]["type"] == "ORDER_STATUS"
    assert f"Đơn #{order.id} đang được giao" in items2[0]["content"]


def test_mark_as_read_and_read_all(client, db_session):
    """Kiểm tra đánh dấu đã đọc một và tất cả thông báo, chặn người khác đọc trộm."""
    user1 = make_user(db_session, "user_notif1")
    user2 = make_user(db_session, "user_notif2")

    # Tạo 3 thông báo thủ công cho user1 và 1 cho user2
    n1 = Notification(recipient_id=user1.id, type="LIKE", content="Thông báo 1", is_read=False)
    n2 = Notification(recipient_id=user1.id, type="COMMENT", content="Thông báo 2", is_read=False)
    n3 = Notification(recipient_id=user1.id, type="FOLLOW", content="Thông báo 3", is_read=False)
    n_other = Notification(recipient_id=user2.id, type="LIKE", content="Của người khác", is_read=False)
    db_session.add_all([n1, n2, n3, n_other])
    db_session.commit()
    db_session.refresh(n1)
    db_session.refresh(n2)
    db_session.refresh(n3)
    db_session.refresh(n_other)

    h1 = auth_header(user1.id)
    h2 = auth_header(user2.id)

    # 1. Ban đầu user1 có 3 thông báo chưa đọc
    assert client.get("/api/notifications/unread-count", headers=h1).json()["unread_count"] == 3

    # 2. Đánh dấu n1 đã đọc
    r_read1 = client.patch(f"/api/notifications/{n1.id}/read", headers=h1)
    assert r_read1.status_code == 200
    assert r_read1.json()["is_read"] is True
    # Còn 2 chưa đọc
    assert client.get("/api/notifications/unread-count", headers=h1).json()["unread_count"] == 2

    # 3. User1 cố đánh dấu thông báo của User2 -> BỊ CHẶN 404
    r_hack = client.patch(f"/api/notifications/{n_other.id}/read", headers=h1)
    assert r_hack.status_code == 404

    # 4. User1 đọc tất cả -> unread_count = 0
    r_all = client.patch("/api/notifications/read-all", headers=h1)
    assert r_all.status_code == 200
    assert r_all.json()["updated_count"] == 2
    assert client.get("/api/notifications/unread-count", headers=h1).json()["unread_count"] == 0

    # User2 vẫn còn 1 thông báo chưa đọc
    assert client.get("/api/notifications/unread-count", headers=h2).json()["unread_count"] == 1


def test_like_and_follow_integrity_error_handled(client, db_session, monkeypatch):
    """Khi có IntegrityError phát sinh đồng thời (ví dụ tại flush hoặc commit), exception được bắt và xử lý an toàn."""
    u1 = make_user(db_session, "user_ie1")
    u2 = make_user(db_session, "user_ie2")

    vid = Video(title="Vid IE", video_url="/uploads/videos/ie.mp4", duration_seconds=10, user_id=u2.id, status="VISIBLE")
    db_session.add(vid)
    db_session.commit()

    # Giả lập trước đã có Like trong DB
    db_session.add(Like(user_id=u1.id, video_id=vid.id))
    db_session.commit()

    # Khi gọi lại, nếu monkeypatch làm find_like trả về None ở lượt kiểm tra đầu tiên để ép vào khối try,
    # nhưng IntegrityError bắn ra vì đã có Like -> khối except phải bắt được và trả về 200 vì đã tồn tại Like.
    import app.routers.social as social_module
    orig_find_like = social_module.crud.find_like

    call_count = {"count": 0}
    def mock_find_like(db, uid, video_id):
        call_count["count"] += 1
        if call_count["count"] == 1:
            return None  # Ép vào khối try
        return orig_find_like(db, uid, video_id)  # Lượt kiểm tra trong except

    monkeypatch.setattr(social_module.crud, "find_like", mock_find_like)

    res = client.post(f"/api/videos/{vid.id}/likes", headers=auth_header(u1.id))
    assert res.status_code == 200
    assert res.json()["liked"] is True

