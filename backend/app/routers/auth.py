"""Auth API: /auth/register, /auth/login, /auth/logout, /auth/me"""

from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.core.dependencies import (
    bearer_scheme,  # noqa: F401
    forbidden,
    get_current_user,
    get_token_payload,
    unauthorized,
)
from app.db.session import get_db
from app.models.revoked_token import RevokedToken
from app.models.user import User
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserRead

router = APIRouter(prefix="/auth", tags=["Auth"])
bearer_scheme = HTTPBearer(auto_error=False)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(status_code=409, detail="Email da ton tai")
    if db.scalar(select(User).where(User.username == data.username)):
        raise HTTPException(status_code=409, detail="Username da ton tai")

    user = User(
        email=data.email,
        username=data.username,
        display_name=data.display_name,
        password_hash=hash_password(data.password.get_secret_value()),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # race condition giua 2 request
        db.rollback()
        raise HTTPException(status_code=409, detail="Email hoac username da ton tai")
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.scalar(
        select(User).where(
            or_(User.email == data.identifier, User.username == data.identifier)
        )
    )
    if user is None or not verify_password(data.password.get_secret_value(), user.password_hash):
        raise unauthorized("Sai email/username hoac mat khau")
    if user.status != "ACTIVE":
        raise forbidden("Tai khoan da bi khoa")

    token, expires_in = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.post("/logout")
def logout(payload: dict = Depends(get_token_payload), db: Session = Depends(get_db)):
    db.add(
        RevokedToken(
            jti=payload["jti"],
            expires_at=datetime.fromtimestamp(payload["exp"], timezone.utc).replace(tzinfo=None),
        )
    )
    try:
        db.commit()
    except IntegrityError:
        # Logout dong thoi: jti da duoc thu hoi boi request khac -> coi nhu thanh cong
        db.rollback()
    return {"message": "Dang xuat thanh cong"}


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user