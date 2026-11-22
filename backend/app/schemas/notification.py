"""Schemas dữ liệu cho hệ thống thông báo (Task T3D2BAD)."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class NotificationActor(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificationOut(BaseModel):
    id: int
    recipient_id: int
    actor_id: int | None = None
    actor: NotificationActor | None = None
    type: str  # LIKE, COMMENT, FOLLOW, ORDER_STATUS
    content: str
    video_id: int | None = None
    order_id: int | None = None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationUnreadCount(BaseModel):
    unread_count: int


class NotificationBatchReadResponse(BaseModel):
    message: str
    updated_count: int
