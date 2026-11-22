from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.db.session import get_db
from app.models.user import User

basic_auth = HTTPBasic()


def get_video_user(
    credentials: HTTPBasicCredentials = Depends(basic_auth),
    db: Session = Depends(get_db),
) -> User:
    user = db.scalar(
        select(User).where(User.username == credentials.username)
    )

    if (
        user is None
        or user.status != "ACTIVE"
        or not verify_password(credentials.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=401,
            detail="Thông tin đăng nhập không hợp lệ.",
            headers={"WWW-Authenticate": "Basic"},
        )

    return user