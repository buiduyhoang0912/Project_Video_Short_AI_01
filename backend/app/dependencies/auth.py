"""Dependency xac thuc & phan quyen dung chung cho moi API.

Dung:
    from app.dependencies.auth import (
        get_current_user, get_optional_user, require_seller, require_admin,
    )
Xem huong dan: backend/docs/auth_dependencies.md
"""

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.revoked_token import RevokedToken
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

MSG_NOT_LOGGED_IN = "Chưa đăng nhập"
MSG_INVALID_TOKEN = "Token không hợp lệ"
MSG_LOCKED = "Tài khoản đã bị khóa"
MSG_FORBIDDEN = "Không đủ quyền truy cập"


def _unauthorized(detail: str = MSG_INVALID_TOKEN) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _has_auth_header(request: Request) -> bool:
    return request.headers.get("authorization") is not None


def get_token_payload(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict:
    """Bat buoc co token hop le (chua het han, chua logout). Tra ve payload."""
    if credentials is None:
        if _has_auth_header(request):  # header sai dinh dang (Basic, "Bearer " rong...)
            raise _unauthorized()
        raise _unauthorized(MSG_NOT_LOGGED_IN)
    return _decode_and_check(credentials.credentials, db)


def _decode_and_check(token: str, db: Session) -> dict:
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise _unauthorized()
    jti = payload.get("jti")
    if jti is None or db.get(RevokedToken, jti) is not None:
        raise _unauthorized()
    return payload


def _load_active_user(payload: dict, db: Session) -> User:
    """Doc user tu DB moi lan (role/status luon moi nhat)."""
    try:
        user = db.get(User, int(payload["sub"]))
    except (KeyError, TypeError, ValueError):
        raise _unauthorized()
    if user is None:
        raise _unauthorized()
    if user.status != "ACTIVE":
        raise _forbidden(MSG_LOCKED)
    return user


def get_current_user(
    payload: dict = Depends(get_token_payload),
    db: Session = Depends(get_db),
) -> User:
    """Bat buoc dang nhap. 401 neu thieu/sai token, 403 neu tai khoan bi khoa."""
    return _load_active_user(payload, db)


def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Khong gui token -> None (khach). Co token -> kiem tra nhu get_current_user."""
    if credentials is None:
        if _has_auth_header(request):  # co gui header nhung sai dinh dang -> 401
            raise _unauthorized()
        return None
    payload = _decode_and_check(credentials.credentials, db)
    return _load_active_user(payload, db)


def require_seller(user: User = Depends(get_current_user)) -> User:
    """Chi role SELLER. (ADMIN khong duoc dung API seller.)"""
    if user.role != "SELLER":
        raise _forbidden(MSG_FORBIDDEN)
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Chi role ADMIN."""
    if user.role != "ADMIN":
        raise _forbidden(MSG_FORBIDDEN)
    return user
