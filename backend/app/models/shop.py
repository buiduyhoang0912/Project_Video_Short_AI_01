from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Shop(Base):
    __tablename__ = "shops"

    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
    }

    id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    owner_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    avatar_key: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    address: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
    )

    bank_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default="MB",
    )

    bank_account_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default="0987654321",
    )

    bank_account_holder: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default="CHU CUA HANG",
    )

    created_at: Mapped[datetime] = mapped_column(

        DateTime,
        nullable=False,
        default=utc_now,
    )

    products: Mapped[list["Product"]] = relationship("Product", back_populates="shop")  # noqa: F821

    @property
    def logo_url(self) -> str | None:
        return self.avatar_key

    def generate_vietqr_url(self, amount: float, order_id: int) -> str:
        """Tạo đường dẫn ảnh QR VietQR chuẩn dựa trên thông tin ngân hàng của Shop."""
        import urllib.parse
        bank = self.bank_name or "MB"
        account = self.bank_account_number or "0987654321"
        holder = self.bank_account_holder or (self.name.upper() if self.name else "SHOP")
        amt = int(amount)
        encoded_holder = urllib.parse.quote(holder)
        encoded_memo = urllib.parse.quote(f"DH{order_id}")
        return f"https://img.vietqr.io/image/{bank}-{account}-compact2.png?amount={amt}&addInfo={encoded_memo}&accountName={encoded_holder}"

    orders = relationship("Order", back_populates="shop")  # noqa: F821
