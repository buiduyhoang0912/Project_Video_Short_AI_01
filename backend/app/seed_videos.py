from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.user import User
from app.models.video import Video


def seed_demo_videos():
    with SessionLocal.begin() as db:
        query = select(User.id).where(User.username == "seller01").with_for_update()
        user_id = db.scalar(query)

        if user_id is None:
            raise ValueError("Chưa có tài khoản seller01. Hãy chạy app.seed trước.")

        video_url = "/uploads/videos/demo.mp4"

        for number in range(1, 21):
            title = f"Video demo {number:02d}"
            query = select(Video.id).where(
                Video.user_id == user_id,
                Video.title == title,
                Video.video_url == video_url,
            )

            if db.scalar(query) is not None:
                continue

            video = Video(
                user_id=user_id,
                title=title,
                description="Video mẫu để kiểm thử ClipShop AI",
                hashtags=["demo", "clipshop"],
                video_url=video_url,
                duration_seconds=12,
            )
            db.add(video)

if __name__ == "__main__":
    seed_demo_videos()
    print("Seed video demo hoàn tất.")