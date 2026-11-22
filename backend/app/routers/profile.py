"""API hồ sơ cá nhân (Task T3D1FE9).

Đăng nhập bắt buộc, chỉ tác động tới tài khoản của chính người đăng nhập:
    GET   /api/me/profile        xem hồ sơ của mình
    PATCH /api/me/profile        sửa tên hiển thị + tiểu sử
    POST  /api/me/avatar         upload avatar (JPG/PNG, tối đa 2 MB)
    PUT   /api/me/password       đổi mật khẩu
Công khai (không cần đăng nhập):
    GET   /api/profiles/{username}   hồ sơ công khai theo username

Không có tham số user_id trong các API "me": tài khoản luôn lấy từ token,
nên không thể sửa hồ sơ của người khác.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.avatar import (
    AvatarInvalidError,
    AvatarTooLargeError,
    avatar_url_from_key,
    read_limited,
    remove_avatar_file,
    save_avatar,
    validate_and_reencode,
)
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import PasswordChange, ProfileUpdate, UserPublicRead

router = APIRouter(tags=["Profile"])


def to_public_profile(user: User) -> UserPublicRead:
    """Chỉ lấy các trường công khai; không bao giờ trả email/mật khẩu/role."""
    return UserPublicRead(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        bio=user.bio,
        avatar_url=avatar_url_from_key(user.avatar_key),
    )


@router.get("/me/profile", response_model=UserPublicRead)
def get_my_profile(user: User = Depends(get_current_user)):
    return to_public_profile(user)


@router.patch("/me/profile", response_model=UserPublicRead)
def update_my_profile(
    data: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not data.model_fields_set:
        raise HTTPException(status_code=422, detail="Cần gửi tên hiển thị hoặc tiểu sử để cập nhật")

    if "display_name" in data.model_fields_set:
        user.display_name = data.display_name
    if "bio" in data.model_fields_set:
        user.bio = data.bio

    db.commit()
    db.refresh(user)
    return to_public_profile(user)


@router.post("/me/avatar", response_model=UserPublicRead)
def upload_my_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = read_limited(file.file)
        clean, extension = validate_and_reencode(data)
    except AvatarTooLargeError as error:
        raise HTTPException(status_code=413, detail=str(error)) from error
    except AvatarInvalidError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    old_key = user.avatar_key
    new_key = save_avatar(clean, extension)
    user.avatar_key = new_key
    try:
        db.commit()
    except Exception:
        db.rollback()
        remove_avatar_file(new_key)  # DB lỗi thì không để lại file mồ côi
        raise

    remove_avatar_file(old_key)
    db.refresh(user)
    return to_public_profile(user)


@router.put("/me/password")
def change_my_password(
    data: PasswordChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Dùng 400 (không dùng 401) để frontend không hiểu nhầm là phiên hết hạn.
    if not verify_password(data.current_password.get_secret_value(), user.password_hash):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng")

    user.password_hash = hash_password(data.new_password.get_secret_value())
    db.commit()
    return {"message": "Đổi mật khẩu thành công"}


@router.get("/profiles/{username}", response_model=UserPublicRead)
def get_public_profile(username: str, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == username.strip().lower()))
    if user is None or user.status != "ACTIVE":
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng này")
    return to_public_profile(user)
