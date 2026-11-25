"""Điểm khởi động của backend.

Chạy:  uvicorn app.main:app --reload
Tài liệu API tự sinh: http://127.0.0.1:8000/docs
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app import models  # noqa: F401 - import để SQLAlchemy biết các bảng
from app.core.config import settings
from app.db.session import Base, engine
from app.routers import (
    admin,
    admin_moderation,
    auth,
    cart,
    categories,
    health,
    items,
    notifications,
    orders,
    products,
    profile,
    seller_applications,
    shops,
    social,
    videos,
    vouchers,
)



def ensure_schema_columns(db_engine) -> None:
    """Tự động bổ sung các cột mới thêm ở Sprint 2-3 (sold_count, moderation_*) cho MySQL cũ."""
    insp = inspect(db_engine)
    alter_stmts: list[str] = []

    if insp.has_table("products"):
        prod_cols = {c["name"] for c in insp.get_columns("products")}
        if "sold_count" not in prod_cols:
            alter_stmts.append(
                "ALTER TABLE products ADD COLUMN sold_count INTEGER UNSIGNED NOT NULL DEFAULT 0"
            )
        if "moderation_reason" not in prod_cols:
            alter_stmts.append(
                "ALTER TABLE products ADD COLUMN moderation_reason VARCHAR(500) NULL"
            )
        if "moderated_by" not in prod_cols:
            alter_stmts.append(
                "ALTER TABLE products ADD COLUMN moderated_by BIGINT UNSIGNED NULL"
            )
        if "moderated_at" not in prod_cols:
            alter_stmts.append(
                "ALTER TABLE products ADD COLUMN moderated_at DATETIME NULL"
            )

    if insp.has_table("shops"):
        shop_cols = {c["name"] for c in insp.get_columns("shops")}
        if "bank_name" not in shop_cols:
            alter_stmts.append(
                "ALTER TABLE shops ADD COLUMN bank_name VARCHAR(100) NULL"
            )
        if "bank_account_number" not in shop_cols:
            alter_stmts.append(
                "ALTER TABLE shops ADD COLUMN bank_account_number VARCHAR(50) NULL"
            )
        if "bank_account_holder" not in shop_cols:
            alter_stmts.append(
                "ALTER TABLE shops ADD COLUMN bank_account_holder VARCHAR(100) NULL"
            )

    if insp.has_table("videos"):
        vid_cols = {c["name"] for c in insp.get_columns("videos")}
        if "moderation_reason" not in vid_cols:
            alter_stmts.append(
                "ALTER TABLE videos ADD COLUMN moderation_reason VARCHAR(500) NULL"
            )
        if "moderated_by" not in vid_cols:
            alter_stmts.append(
                "ALTER TABLE videos ADD COLUMN moderated_by BIGINT UNSIGNED NULL"
            )
        if "moderated_at" not in vid_cols:
            alter_stmts.append(
                "ALTER TABLE videos ADD COLUMN moderated_at DATETIME NULL"
            )

    if alter_stmts:
        with db_engine.begin() as conn:
            for stmt in alter_stmts:
                conn.execute(text(stmt))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tự tạo các bảng còn thiếu khi server khởi động (bảng đã có thì bỏ qua).
    try:
        Base.metadata.create_all(bind=engine)
        ensure_schema_columns(engine)
        print(f"[DB] Đã kết nối MySQL {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    except OperationalError as error:
        print("[DB] KHÔNG kết nối được MySQL! Kiểm tra MySQL đã bật chưa và file .env.")
        if "Unknown database" in str(error.orig):
            print("[DB] Chưa có database -> mở MySQL Workbench, chạy file sql/init.sql")
        print(f"[DB] Chi tiết: {error.orig}")
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

uploads_dir = Path(__file__).resolve().parents[1] / "uploads"
(uploads_dir / "videos").mkdir(parents=True, exist_ok=True)
(uploads_dir / "thumbnails").mkdir(parents=True, exist_ok=True)
(uploads_dir / "covers").mkdir(parents=True, exist_ok=True)
(uploads_dir / "products").mkdir(parents=True, exist_ok=True)
(uploads_dir / "avatars").mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# CORS: cho phép trang FE (khác cổng/khác domain) gọi được API này
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def disable_stale_frontend_cache(request: Request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.endswith((".html", ".css", ".js")):
        response.headers.setdefault("Cache-Control", "no-cache")
    return response

# Mọi API đều bắt đầu bằng /api. Thêm router mới thì include ở đây.
app.include_router(health.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(admin_moderation.router, prefix="/api")
app.include_router(items.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(videos.router, prefix="/api")
app.include_router(seller_applications.router, prefix="/api")
app.include_router(vouchers.router, prefix="/api")  # T3D2BFB: đặt trước shops để /shops/me/vouchers khớp đúng
app.include_router(shops.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(cart.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(social.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(auth.router)


@app.get("/video/{video_id}", include_in_schema=False)
def redirect_share_video_page(video_id: int):
    return RedirectResponse(url=f"/pages/video.html?id={video_id}")


frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
if frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {"message": f"{settings.APP_NAME} đang chạy. Xem tài liệu API tại /docs"}
