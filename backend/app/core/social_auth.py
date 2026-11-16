import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.revoked_token import RevokedToken
from app.models.user import User
from app.routers.auth import get_current_user

bearer_scheme = HTTPBearer(auto_error=False)


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        if db.get(RevokedToken, payload.get("jti")) is not None:
            return None
        user = db.get(User, int(payload["sub"]))
        if user and user.status == "ACTIVE":
            return user
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
    return None
