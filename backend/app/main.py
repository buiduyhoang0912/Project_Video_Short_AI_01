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
    orders,
    products,
    profile,
    seller_applications,
    shops,
    social,
    videos,
)



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tự tạo các bảng còn thiếu khi server khởi động (bảng đã có thì bỏ qua).
    # Lưu ý: create_all KHÔNG sửa bảng đã tồn tại. Đổi cột -> sửa bằng SQL hoặc xoá bảng tạo lại.
    try:
        Base.metadata.create_all(bind=engine)
        insp = inspect(engine)
        if insp.has_table("products"):
            prod_cols = {c["name"] for c in insp.get_columns("products")}
            if "sold_count" not in prod_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            "ALTER TABLE products ADD COLUMN sold_count INTEGER UNSIGNED NOT NULL DEFAULT 0"
                        )
                    )
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

# Mọi API đều bắt đầu bằng /api. Thêm router mới thì include ở đây.
app.include_router(health.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(admin_moderation.router, prefix="/api")
app.include_router(items.router, prefix="/api")
app.include_router(videos.router, prefix="/api")
app.include_router(seller_applications.router, prefix="/api")
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
