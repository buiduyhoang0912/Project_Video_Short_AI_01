# Import mọi model ở đây để Base.metadata.create_all() "nhìn thấy" và tạo bảng.
# Thêm model mới -> nhớ thêm 1 dòng import vào file này.
from app.models.item import Item  # noqa: F401

from app.models.social import Like, Comment, Follow, AiChatLog
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

#class video
like_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
comment_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
share_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
