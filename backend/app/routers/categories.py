"""API danh mục sản phẩm: /api/categories"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryOut

router = APIRouter(prefix="/categories", tags=["Categories"])

DEFAULT_CATEGORIES = [
    ("Thời trang", "Quần áo, giày dép và phụ kiện thời trang"),
    ("Điện tử & Phụ kiện", "Thiết bị công nghệ, tai nghe, cáp sạc"),
    ("Mỹ phẩm & Làm đẹp", "Chăm sóc da, trang điểm, nước hoa"),
    ("Đồ gia dụng", "Tiện ích nhà cửa và đời sống"),
    ("Thực phẩm & Đồ uống", "Đồ ăn vặt, đặc sản, thức uống"),
]


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    categories = list(
        db.scalars(
            select(Category)
            .where(Category.status == "ACTIVE")
            .order_by(Category.id.asc())
        )
    )
    if not categories:
        for name, desc in DEFAULT_CATEGORIES:
            db.add(Category(name=name, description=desc, status="ACTIVE"))
        db.commit()
        categories = list(
            db.scalars(
                select(Category)
                .where(Category.status == "ACTIVE")
                .order_by(Category.id.asc())
            )
        )
    return categories


@router.post(
    "", response_model=CategoryOut, status_code=status.HTTP_201_CREATED
)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    if not data.name or not data.name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tên danh mục không được để trống",
        )
    category = Category(
        name=data.name.strip(),
        description=data.description,
        status="ACTIVE",
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
