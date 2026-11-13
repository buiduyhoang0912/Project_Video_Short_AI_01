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


class FollowStats(BaseModel):
    user_id: int
    followers_count: int
    following_count: int
    is_following: bool = False


class UserFollowItem(BaseModel):
    id: int
    username: str
    display_name: str
    avatar_key: str | None = None
    avatar_url: str | None = None
    followed_at: datetime


class FollowingFeedItem(BaseModel):
    id: int
    user_id: int
    author_name: str
    author_username: str
    author_avatar_key: str | None = None
    author_avatar_url: str | None = None
    title: str
    description: str | None = None
    video_url: str
    thumbnail_url: str | None = None
    duration_seconds: int
    created_at: datetime
    like_count: int = 0
    comment_count: int = 0
    is_liked: bool = False
