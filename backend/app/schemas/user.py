"""Schema dữ liệu tài khoản và hồ sơ."""

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
