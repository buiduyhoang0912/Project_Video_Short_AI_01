# Import mọi model ở đây để Base.metadata.create_all() "nhìn thấy" và tạo bảng.
# Thêm model mới -> nhớ thêm 1 dòng import vào file này.
from app.models.item import Item  # noqa: F401
from app.models.item import Item  # noqa: F401
from app.models.user import User
from app.models.seller_application import SellerApplication

from app.models.shop import Shop
from app.models.category import Category
from app.models.product import Product
from app.models.product_image import ProductImage

from app.models.video import Video, VideoProduct
