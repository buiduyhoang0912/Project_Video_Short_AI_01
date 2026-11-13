"""Dependency xac thuc/phan quyen DUNG CHUNG (JWT Bearer).

Import:  from app.core.dependencies import get_current_user, get_optional_user, require_seller, require_admin
Huong dan: backend/docs/auth_permissions.md

Quy tac loi:
- 401: chua dang nhap / token sai / token het han / token da logout / user khong ton tai.
- 403: da xac thuc nhung thieu quyen hoac tai khoan bi khoa (LOCKED).
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.revoked_token import RevokedToken
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def unauthorized(detail: str = "Chua dang nhap hoac token khong hop le") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _payload_from_token(token: str, db: Session) -> dict:
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise unauthorized()
    if db.get(RevokedToken, payload.get("jti")) is not None:
        raise unauthorized("Token da bi dang xuat")
    return payload


def _user_from_payload(payload: dict, db: Session) -> User:
    try:
        user = db.get(User, int(payload["sub"]))
    except (KeyError, ValueError):
        raise unauthorized()
    if user is None:
        raise unauthorized()
    if user.status != "ACTIVE":
        raise forbidden("Tai khoan da bi khoa")
    return user


def get_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict:
    """Bat buoc co token hop le (dung cho logout)."""
    if credentials is None:
        raise unauthorized()
    return _payload_from_token(credentials.credentials, db)


def get_current_user(
    payload: dict = Depends(get_token_payload),
    db: Session = Depends(get_db),
) -> User:
    """Bat buoc dang nhap. 401 neu thieu/sai/het han token; 403 neu bi khoa."""
    return _user_from_payload(payload, db)


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Khong co token -> None (khach). Co token sai/het han -> 401, khong coi la khach."""
    if credentials is None:
        return None
    payload = _payload_from_token(credentials.credentials, db)
    return _user_from_payload(payload, db)


def require_seller(user: User = Depends(get_current_user)) -> User:
    if user.role != "SELLER":
        raise forbidden("Chi tai khoan SELLER moi co quyen thuc hien thao tac nay")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "ADMIN":
        raise forbidden("Chi Admin moi co quyen thuc hien thao tac nay")
    return user
