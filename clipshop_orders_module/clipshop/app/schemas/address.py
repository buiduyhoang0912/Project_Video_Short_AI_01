import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

PHONE_RE = re.compile(r"^(?:\+84|0)\d{9}$")


def validate_phone(v: str) -> str:
    v = re.sub(r"[\s.\-]", "", v)
    if not PHONE_RE.match(v):
        raise ValueError("Số điện thoại không hợp lệ")
    return v


class AddressBase(BaseModel):
    recipient_name: str = Field(min_length=1, max_length=100)
    phone: str
    address: str = Field(min_length=5, max_length=500)

    @field_validator("recipient_name", "address")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Không được để trống")
        return v

    _phone = field_validator("phone")(validate_phone)


class AddressCreate(AddressBase):
    is_default: bool = False


class AddressUpdate(BaseModel):
    recipient_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = None
    address: str | None = Field(default=None, min_length=5, max_length=500)
    is_default: bool | None = None

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return None if v is None else validate_phone(v)


class AddressRead(AddressBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    is_default: bool
