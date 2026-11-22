from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.item import Item
from app.models.user import User
from app.models.seller_application import SellerApplication
from app.models.shop import Shop
from app.models.category import Category
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.order import Address, Order, OrderItem
from app.models.cart import Cart, CartItem
from app.models.video import Video, VideoProduct
from app.models.revoked_token import RevokedToken
from app.models.social import AiChatLog, Comment, Follow, Like, VideoShare
from app.models.voucher import ShopVoucher, VoucherUsage
from app.models.notification import Notification

if not hasattr(User, "addresses"):
    User.addresses = relationship("Address", back_populates="user")
if not hasattr(User, "orders"):
    User.orders = relationship("Order", back_populates="buyer")
if not hasattr(User, "cart"):
    User.cart = relationship("Cart", back_populates="user", uselist=False)
if not hasattr(Shop, "orders"):
    Shop.orders = relationship("Order", back_populates="shop")


