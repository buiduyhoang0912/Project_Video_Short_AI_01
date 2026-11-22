from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductListItemOut


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
    share_count: int = 0
    is_liked: bool = False
    is_following: bool = False
    products: list[ProductListItemOut] = []


class ProfileVideoItem(BaseModel):
    id: int
    title: str
    thumbnail_url: str | None = None
    video_url: str
    view_count: int = 0
    created_at: datetime


class UserProfileOut(BaseModel):
    id: int
    username: str
    display_name: str
    avatar_key: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    role: str = "USER"
    created_at: datetime
    followers_count: int = 0
    following_count: int = 0
    is_following: bool = False
    video_count: int = 0
    videos: list[ProfileVideoItem] = []


class SearchVideoItem(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None = None
    hashtags: list[str] | None = None
    video_url: str
    thumbnail_url: str | None = None
    duration_seconds: int
    view_count: int = 0
    created_at: datetime
    author_name: str
    author_username: str
    author_avatar_url: str | None = None
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    is_liked: bool = False


class VideoDetailOut(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None = None
    hashtags: list[str] = []
    video_url: str | None = None
    thumbnail_url: str | None = None
    duration_seconds: int
    view_count: int = 0
    status: Literal["VISIBLE", "HIDDEN"] = "VISIBLE"
    is_available: bool = True
    unavailable_message: str | None = None
    created_at: datetime
    author_name: str
    author_username: str
    author_avatar_key: str | None = None
    author_avatar_url: str | None = None
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    is_liked: bool = False
    is_following: bool = False
    products: list[ProductListItemOut] = []


class VideoStatusUpdate(BaseModel):
    status: Literal["VISIBLE", "HIDDEN"]


class VideoShareOut(BaseModel):
    message: str
    video_id: int
    share_count: int


class SearchUserItem(BaseModel):
    id: int
    username: str
    display_name: str
    avatar_url: str | None = None
    bio: str | None = None
    role: str = "USER"
    followers_count: int = 0
    following_count: int = 0
    video_count: int = 0
    is_following: bool = False


class HashtagItem(BaseModel):
    tag: str
    video_count: int = 0


class TrendingHashtagItem(BaseModel):
    rank: int
    tag: str
    video_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    view_count: int = 0
    interaction_count: int = 0
    score: int = 0


class SearchResultOut(BaseModel):
    query: str
    type: str
    videos: list[SearchVideoItem] = []
    users: list[SearchUserItem] = []
    hashtags: list[HashtagItem] = []


class AiProductRecommendation(BaseModel):
    id: int
    name: str
    description: str | None = None
    price: float
    stock: int = 0
    sold_count: int = 0
    shop_id: int
    shop_name: str | None = None
    category_name: str | None = None
    thumbnail_url: str | None = None
    link: str


class AiQuotaOut(BaseModel):
    daily_limit: int
    used_today: int
    remaining_today: int


class AiChatResponse(BaseModel):
    reply: str
    user_message: ChatLogOut
    assistant_message: ChatLogOut
    recommended_products: list[AiProductRecommendation] = []
    provider: str = "mysql-advisor"
    daily_limit: int
    used_today: int
    remaining_today: int
