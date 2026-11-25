from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token, verify_password
from app.db.session import get_db
from app.models.revoked_token import RevokedToken
from app.models.user import User

basic_auth = HTTPBasic(auto_error=False)


def get_video_user(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(basic_auth),
    db: Session = Depends(get_db),
) -> User:
    # 1. Xác thực qua JWT Bearer token (chuẩn cho web frontend)
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.strip().lower().startswith("bearer "):
        token = auth_header.strip()[7:].strip()
        try:
            payload = decode_access_token(token)
            jti = payload.get("jti")
            if jti and db.get(RevokedToken, jti) is None:
                user_id = int(payload.get("sub", 0))
                user = db.get(User, user_id)
                if user and user.status == "ACTIVE":
                    return user
        except Exception:
            pass

    # 2. Hỗ trợ dự phòng qua HTTP Basic Auth (cho các script / test cũ nếu có)
    if credentials and credentials.username and credentials.password:
        user = db.scalar(
            select(User).where(User.username == credentials.username)
        )
        if (
            user is not None
            and user.status == "ACTIVE"
            and verify_password(credentials.password, user.password_hash)
        ):
            return user

    # 3. Chưa đăng nhập -> Trả về 401 với Bearer để trình duyệt KHÔNG hiện popup Basic Auth
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Vui lòng đăng nhập để thực hiện hành động này.",
        headers={"WWW-Authenticate": "Bearer"},
    )
