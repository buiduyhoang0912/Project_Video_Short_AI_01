
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    parent_id: int | None = Field(default=None, gt=0)


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    video_id: int
    parent_id: int | None
    content: str
    created_at: datetime


class ChatLogCreate(BaseModel):
    message: str = Field(min_length=1, max_length=5000)


class ChatLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    role: str
    message: str
    created_at: datetime
