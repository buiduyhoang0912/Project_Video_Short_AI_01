"""Schema dữ liệu tài khoản và hồ sơ."""

import unicodedata
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    ValidationInfo,
    field_validator,
)


class UserCreate(BaseModel):
    # Từ chối các trường ngoài danh sách, như role hoặc status.
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=255)

    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-z0-9_]+$",
    )

    password: SecretStr = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("email", "username", "display_name", mode="before")
    @classmethod
    def normalize_text(cls, value, info: ValidationInfo):
        if not isinstance(value, str):
            return value

        value = value.strip()

        if info.field_name in ("email", "username"):
            return value.lower()

        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr):
        raw = value.get_secret_value()

        if not raw.strip():
            raise ValueError(
                "Mat khau khong duoc chi gom khoang trang"
            )

        # Kiểm tra số byte vì bcrypt có giới hạn đầu vào.
        if len(raw.encode("utf-8")) > 72:
            raise ValueError(
                "Mat khau khong duoc vuot qua 72 byte UTF-8"
            )

        return value


class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    avatar_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=512,
    )

    bio: str | None = Field(default=None, max_length=500)

    @field_validator("display_name", mode="before")
    @classmethod
    def validate_display_name(cls, value):
        if value is None:
            raise ValueError("Ten hien thi khong duoc la null")

        return value.strip() if isinstance(value, str) else value


class UserRead(BaseModel):
    """Dữ liệu trả cho chính chủ hoặc ADMIN được phép xem."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    display_name: str
    avatar_key: str | None
    bio: str | None

    role: Literal["USER", "SELLER", "ADMIN"]
    status: Literal["ACTIVE", "LOCKED"]

    created_at: datetime
    updated_at: datetime


class UserPublicRead(BaseModel):
    """Hồ sơ công khai, không chứa email hoặc mật khẩu."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    bio: str | None

    # Tầng API tạo URL được phép truy cập từ avatar_key.
    avatar_url: str | None = None

class UserLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Chap nhan email hoac username
    identifier: str = Field(min_length=1, max_length=255)
    password: SecretStr = Field(min_length=1, max_length=72)

    @field_validator("identifier", mode="before")
    @classmethod
    def normalize_identifier(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ---------------- Quản lý hồ sơ cá nhân (T3D1FE9) ----------------

def _has_control_char(value: str, allowed: str = "") -> bool:
    return any(
        unicodedata.category(ch).startswith("C") and ch not in allowed
        for ch in value
    )


class ProfileUpdate(BaseModel):
    """Sửa hồ sơ: chỉ cho đổi tên hiển thị và tiểu sử (không nhận avatar/role/...)."""

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = None
    bio: str | None = None

    @field_validator("display_name", mode="before")
    @classmethod
    def validate_display_name(cls, value):
        if not isinstance(value, str):
            raise ValueError("Tên hiển thị không được để trống")
        value = value.strip()
        if not value:
            raise ValueError("Tên hiển thị không được để trống")
        if len(value) > 100:
            raise ValueError("Tên hiển thị tối đa 100 ký tự")
        if _has_control_char(value):
            raise ValueError("Tên hiển thị chứa ký tự không hợp lệ")
        return value

    @field_validator("bio", mode="before")
    @classmethod
    def validate_bio(cls, value):
        if value is None:
            return None  # cho phép xóa tiểu sử
        if not isinstance(value, str):
            raise ValueError("Tiểu sử phải là chuỗi ký tự")
        value = value.replace("\r\n", "\n").strip()
        if len(value) > 500:
            raise ValueError("Tiểu sử tối đa 500 ký tự")
        if _has_control_char(value, allowed="\n\t"):
            raise ValueError("Tiểu sử chứa ký tự không hợp lệ")
        return value or None


class PasswordChange(BaseModel):
    """Đổi mật khẩu: mật khẩu hiện tại + mật khẩu mới + xác nhận."""

    model_config = ConfigDict(extra="forbid")

    current_password: SecretStr
    new_password: SecretStr
    confirm_password: SecretStr

    @field_validator("current_password")
    @classmethod
    def validate_current(cls, value: SecretStr):
        if not value.get_secret_value():
            raise ValueError("Vui lòng nhập mật khẩu hiện tại")
        return value

    @field_validator("new_password")
    @classmethod
    def validate_new(cls, value: SecretStr, info: ValidationInfo):
        raw = value.get_secret_value()
        if len(raw) < 8:
            raise ValueError("Mật khẩu mới cần ít nhất 8 ký tự")
        if not raw.strip():
            raise ValueError("Mật khẩu mới không được chỉ gồm khoảng trắng")
        if len(raw.encode("utf-8")) > 72:
            raise ValueError("Mật khẩu mới không được vượt quá 72 byte")
        current = info.data.get("current_password")
        if current is not None and current.get_secret_value() == raw:
            raise ValueError("Mật khẩu mới phải khác mật khẩu hiện tại")
        return value

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm(cls, value: SecretStr, info: ValidationInfo):
        new = info.data.get("new_password")
        if new is not None and new.get_secret_value() != value.get_secret_value():
            raise ValueError("Xác nhận mật khẩu không khớp")
        return value
