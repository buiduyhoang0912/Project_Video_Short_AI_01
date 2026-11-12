from decimal import Decimal

from sqlalchemy import select

from app.db.session import Base, SessionLocal, engine
from app.models.user import User
from app.models.shop import Shop
from app.models.category import Category
from app.models.product import Product
from app.models.product_image import ProductImage


def seed_data():
    Base.metadata.create_all(bind=engine)

    shop_names = [
    "Van Gaming Store",
    "Hoang Fashion",
    "ClipShop Home",
    ]

    category_names = [
        "Dien thoai",
        "Laptop",
        "Tai nghe",
        "Ban phim",
        "Chuot",
        "Quan ao",
        "Giay dep",
        "Do gia dung",
    ]

    product_names = [
        ["iPhone 15", "Samsung Galaxy S24", "Xiaomi 14", "OPPO Reno", "Vivo V30"],
        ["ASUS TUF Gaming", "Lenovo LOQ", "Acer Nitro 5", "Dell Inspiron", "HP Victus"],
        ["Sony WH-1000XM5", "AirPods Pro", "JBL Tune 520BT", "Soundcore Q20", "HyperX Cloud"],
        ["Logitech G Pro", "Akko 5075B", "Keychron K2", "DareU EK87", "Razer BlackWidow"],
        ["Logitech G304", "Razer DeathAdder", "DareU EM908", "Corsair Harpoon", "ASUS TUF M3"],
        ["Ao thun nam", "Ao polo", "Ao khoac", "Quan jeans", "Ao hoodie"],
        ["Giay sneaker", "Giay chay bo", "Giay da", "Dep sandal", "Giay the thao"],
        ["Noi chien", "May xay sinh to", "Am sieu toc", "Quat mini", "Den ban"],
    ]

    with SessionLocal.begin() as db:

        # 1. Lay 3 tai khoan SELLER cua Hoang
        sellers = []

        for i in range(1, 4):
            username = f"seller{i:02d}"

            seller = db.scalar(
                select(User).where(User.username == username)
            )

            if seller is None:
                raise ValueError(f"Chua co tai khoan {username}")

            sellers.append(seller)

        # 2. Tao 3 shop
        shops = []

        for i in range(3):
            shop = db.scalar(
                select(Shop).where(Shop.owner_id == sellers[i].id)
            )

            if shop is None:
                shop = Shop(
                    owner_id=sellers[i].id,
                    name=shop_names[i],
                    description="Cua hang demo ClipShop AI",
                    address="Ha Noi",
                    status="ACTIVE",
                )
                db.add(shop)
                db.flush()

            shops.append(shop)

        # 3. Tao 8 danh muc
        categories = []

        for name in category_names:
            category = db.scalar(
                select(Category).where(Category.name == name)
            )

            if category is None:
                category = Category(
                    name=name,
                    description=f"Danh muc {name}",
                    status="ACTIVE",
                )
                db.add(category)
                db.flush()

            categories.append(category)

        # 4. Tao 40 san pham
        created = 0

        for i in range(8):
            for j in range(5):
                name = product_names[i][j]
                shop = shops[(i * 5 + j) % 3]

                product = db.scalar(
                    select(Product).where(
                        Product.shop_id == shop.id,
                        Product.name == name,
                    )
                )

                if product is None:
                    product = Product(
                        shop_id=shop.id,
                        category_id=categories[i].id,
                        name=name,
                        description=f"San pham demo {name}",
                        price=Decimal(100000 * (j + 1)),
                        stock=20 + j,
                        status="ACTIVE",
                    )

                    db.add(product)
                    created += 1

        print("Da xu ly 3 shop")
        print("Da xu ly 8 danh muc")
        print(f"San pham tao moi: {created}")


if __name__ == "__main__":
    seed_data()
