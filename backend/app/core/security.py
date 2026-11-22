"""Băm và kiểm tra mật khẩu bằng bcrypt."""

import bcrypt


def hash_password(password: str) -> str:
    """Nhận mật khẩu gốc và trả về chuỗi băm."""

    if not isinstance(password, str):
        raise ValueError("Mat khau phai la chuoi")

    if len(password) < 8 or not password.strip():
        raise ValueError(
            "Mat khau can it nhat 8 ky tu "
            "va khong chi gom khoang trang"
        )

    raw = password.encode("utf-8")

    if len(raw) > 72:
        raise ValueError(
            "Mat khau khong duoc vuot qua 72 byte UTF-8"
        )

    return bcrypt.hashpw(
        raw,
        bcrypt.gensalt(rounds=12),
    ).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Kiểm tra mật khẩu gốc có khớp chuỗi băm không."""

    if not isinstance(password, str):
        return False

    if not isinstance(password_hash, str):
        return False

    try:
        raw = password.encode("utf-8")

        if len(raw) > 72:
            return False

        return bcrypt.checkpw(
            raw,
            password_hash.encode("ascii"),
        )

    except (ValueError, TypeError):
        return False

# ---------------- JWT ----------------
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings


def create_access_token(user_id: int) -> tuple[str, int]:
    """Tra ve (token, so giay het han)."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "jti": uuid.uuid4().hex, "iat": now, "exp": exp}
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, settings.JWT_EXPIRE_MINUTES * 60


def decode_access_token(token: str) -> dict:
    """Raise jwt.PyJWTError neu token sai/het han."""
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["sub", "jti", "exp"]},
    )
    if not isinstance(payload["jti"], str) or not str(payload["sub"]).isdigit():
        raise jwt.InvalidTokenError("claim khong hop le")
    return payload
