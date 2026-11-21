"""Test Task T3D2805: [AI] Trợ lý viết nội dung cho người bán.
Kiểm tra:
1. POST /api/products/ai-suggest gợi ý tên, mô tả sản phẩm và kịch bản video 30-60s.
2. Người bán có thể chỉnh sửa tên và mô tả gợi ý trước khi gọi POST/PUT /api/products để lưu.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import BIGINT, ENUM, INTEGER
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.core.security import create_access_token, hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models.category import Category
from app.models.shop import Shop
from app.models.user import User


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


def test_ai_suggest_product_content_and_seller_edit_before_save(
    client, db_session
):
    db = db_session()
    seller = User(
        id=1,
        email="seller_ai@shop.com",
        username="seller_ai",
        password_hash=hash_password("password123"),
        display_name="Seller AI",
        role="SELLER",
        status="ACTIVE",
    )
    shop = Shop(id=1, owner_id=1, name="Shop Công Nghệ AI", status="ACTIVE")
    cat = Category(id=1, name="Điện tử & Phụ kiện", status="ACTIVE")
    db.add_all([seller, shop, cat])
    db.commit()
    token, _ = create_access_token(seller.id)
    db.close()

    headers = {"Authorization": f"Bearer {token}"}

    # 1. Gọi API gợi ý nội dung bằng AI từ thông tin sản phẩm
    r_ai = client.post(
        "/api/products/ai-suggest",
        json={
            "raw_name": "Tai nghe Bluetooth chống ồn",
            "category_id": 1,
            "price": 590000,
            "features": "Pin 30 giờ, chống ồn chủ động ANC, âm bass ấm",
            "duration_seconds": 45,
        },
        headers=headers,
    )
    assert r_ai.status_code == 200
    ai_data = r_ai.json()

    assert "Tai nghe Bluetooth chống ồn" in ai_data["suggested_name"]
    assert len(ai_data["alternative_names"]) >= 2
    assert len(ai_data["suggested_description"]) > 50
    assert "00s - 05s" in ai_data["video_script_30_60s"]
    assert "45s" in ai_data["video_script_30_60s"]
    assert len(ai_data["suggested_hashtags"]) >= 3

    # 2. Người bán chỉnh sửa lại tên và mô tả gợi ý trước khi bấm Lưu sản phẩm
    edited_name = ai_data["suggested_name"][:120] + " (Bản Đặc Biệt)"
    edited_desc = (
        ai_data["suggested_description"]
        + "\n• Ghi chú của Shop: Tặng kèm bao da bảo vệ."
    )

    r_save = client.post(
        "/api/products",
        json={
            "category_id": 1,
            "name": edited_name,
            "description": edited_desc,
            "price": 590000,
            "stock": 20,
        },
        headers=headers,
    )
    assert r_save.status_code == 201
    saved = r_save.json()
    assert saved["name"] == edited_name
    assert "Tặng kèm bao da bảo vệ" in saved["description"]


def test_ai_suggest_unauthenticated_and_invalid_payload(client, db_session):
    db = db_session()
    seller = User(
        id=10,
        email="seller_ai2@shop.com",
        username="seller_ai2",
        password_hash=hash_password("password123"),
        display_name="Seller AI 2",
        role="SELLER",
        status="ACTIVE",
    )
    db.add(seller)
    db.commit()
    token, _ = create_access_token(seller.id)
    db.close()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Chưa đăng nhập -> 401 Unauthorized
    r_unauth = client.post(
        "/api/products/ai-suggest",
        json={"raw_name": "Áo khoác bomber"},
    )
    assert r_unauth.status_code == 401

    # 2. Sai dữ liệu: raw_name rỗng ("") hoặc duration_seconds ngoài khoảng 30-60s -> 422
    r_empty_name = client.post(
        "/api/products/ai-suggest",
        json={"raw_name": ""},
        headers=headers,
    )
    assert r_empty_name.status_code == 422

    r_bad_duration = client.post(
        "/api/products/ai-suggest",
        json={"raw_name": "Áo khoác bomber", "duration_seconds": 120},
        headers=headers,
    )
    assert r_bad_duration.status_code == 422

