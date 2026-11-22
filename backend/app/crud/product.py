"""CRUD cho bảng products, shop, category, product_images và video_products."""

import json
import math
import re
from decimal import Decimal

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import settings
from app.models.cart import CartItem
from app.models.category import Category
from app.models.order import OrderItem
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.shop import Shop
from app.models.video import VideoProduct
from app.schemas.product import (
    ProductAiSuggestRequest,
    ProductAiSuggestResponse,
    ProductCreate,
    ProductListItemOut,
    ProductListResponse,
    ProductSortBy,
    ProductUpdate,
)


def get_category(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def get_product(db: Session, product_id: int) -> Product | None:
    return db.get(Product, product_id)


def get_products(
    db: Session,
    *,
    keyword: str | None = None,
    category_id: int | None = None,
    min_price: Decimal | float | None = None,
    max_price: Decimal | float | None = None,
    shop_id: int | None = None,
    sort_by: ProductSortBy | str = ProductSortBy.NEWEST,
    page: int = 1,
    page_size: int = 10,
) -> ProductListResponse:
    """Lấy danh sách sản phẩm theo bộ lọc, phân trang và sắp xếp."""
    stmt = (
        select(Product, Shop.name.label("shop_name"), Category.name.label("category_name"))
        .join(Shop, Product.shop_id == Shop.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(
            func.upper(Product.status) == "ACTIVE",
            func.upper(Shop.status) == "ACTIVE",
        )
    )

    if keyword and keyword.strip():
        search_kw = f"%{keyword.strip()}%"
        stmt = stmt.where(Product.name.ilike(search_kw))

    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)

    if min_price is not None:
        stmt = stmt.where(Product.price >= Decimal(str(min_price)))
    if max_price is not None:
        stmt = stmt.where(Product.price <= Decimal(str(max_price)))

    if shop_id is not None:
        stmt = stmt.where(Product.shop_id == shop_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = db.scalar(count_stmt) or 0

    sort_key = sort_by.value if isinstance(sort_by, ProductSortBy) else sort_by
    if sort_key == ProductSortBy.PRICE_ASC.value:
        stmt = stmt.order_by(Product.price.asc(), Product.id.desc())
    elif sort_key == ProductSortBy.PRICE_DESC.value:
        stmt = stmt.order_by(Product.price.desc(), Product.id.desc())
    elif sort_key == ProductSortBy.BEST_SELLING.value:
        stmt = stmt.order_by(Product.sold_count.desc(), Product.id.desc())
    else:
        stmt = stmt.order_by(Product.created_at.desc(), Product.id.desc())

    safe_page = max(page, 1)
    safe_page_size = max(min(page_size, 100), 1)
    offset = (safe_page - 1) * safe_page_size
    stmt = stmt.offset(offset).limit(safe_page_size)

    results = db.execute(stmt).all()

    items: list[ProductListItemOut] = []
    for product_obj, shop_name, category_name in results:
        items.append(
            ProductListItemOut(
                id=product_obj.id,
                shop_id=product_obj.shop_id,
                shop_name=shop_name,
                category_id=product_obj.category_id,
                category_name=category_name,
                name=product_obj.name,
                price=float(product_obj.price),
                stock=product_obj.stock,
                sold_count=product_obj.sold_count,
                thumbnail_url=product_obj.thumbnail_url,
                status=product_obj.status,
                created_at=product_obj.created_at,
            )
        )

    total_pages = math.ceil(total / safe_page_size) if total > 0 else 0

    return ProductListResponse(
        items=items,
        total=total,
        page=safe_page,
        page_size=safe_page_size,
        total_pages=total_pages,
    )


def get_product_detail(db: Session, product_id: int) -> Product | None:
    """Lấy chi tiết 1 sản phẩm: kèm ảnh, tồn kho, shop, và video có gắn sản phẩm."""
    stmt = (
        select(Product)
        .options(
            joinedload(Product.shop),
            joinedload(Product.category),
            selectinload(Product.images),
            selectinload(Product.videos),
        )
        .join(Shop, Product.shop_id == Shop.id)
        .where(
            Product.id == product_id,
            func.upper(Product.status) == "ACTIVE",
            func.upper(Shop.status) == "ACTIVE",
        )
    )
    return db.scalar(stmt)


def get_shop_products(
    db: Session,
    shop_id: int,
    include_hidden: bool = False,
    status_filter: str | None = None,
    keyword: str | None = None,
    category_id: int | None = None,
) -> list[Product]:
    query = select(Product).where(Product.shop_id == shop_id)

    if status_filter:
        query = query.where(Product.status == status_filter)
    elif not include_hidden:
        query = query.where(Product.status == "ACTIVE")

    if category_id is not None:
        query = query.where(Product.category_id == category_id)

    if keyword:
        query = query.where(Product.name.contains(keyword))

    query = query.order_by(Product.id.desc())
    return list(db.scalars(query))


def create_product(
    db: Session,
    shop_id_or_data: int | ProductCreate,
    data: ProductCreate | None = None,
) -> Product:
    if isinstance(shop_id_or_data, ProductCreate):
        payload = shop_id_or_data
        target_shop_id = payload.shop_id
    else:
        target_shop_id = shop_id_or_data
        payload = data

    product = Product(
        shop_id=target_shop_id,
        category_id=payload.category_id,
        name=payload.name.strip(),
        description=payload.description,
        price=payload.price,
        stock=payload.stock,
        status=getattr(payload, "status", None) or "ACTIVE",
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(
    db: Session, product: Product, data: ProductUpdate
) -> Product:
    update_data = data.model_dump(exclude_unset=True)
    update_data.pop("thumbnail_url", None)
    if "name" in update_data and isinstance(update_data["name"], str):
        update_data["name"] = update_data["name"].strip()

    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


def update_product_stock(
    db: Session, product: Product, stock: int
) -> Product:
    product.stock = stock
    db.commit()
    db.refresh(product)
    return product


def hide_product(db: Session, product: Product) -> Product:
    product.status = "HIDDEN"
    db.commit()
    db.refresh(product)
    return product


def product_has_orders(db: Session, product_id: int) -> bool:
    query = (
        select(OrderItem.id)
        .where(OrderItem.product_id == product_id)
        .limit(1)
    )
    return db.scalar(query) is not None


def delete_or_hide_product(
    db: Session, product: Product
) -> tuple[str, Product | None, list[str]]:
    if product_has_orders(db, product.id):
        product.status = "HIDDEN"
        db.commit()
        db.refresh(product)
        return "hidden", product, []

    image_keys = [img.object_key for img in product.images]

    db.execute(delete(CartItem).where(CartItem.product_id == product.id))
    db.execute(delete(VideoProduct).where(VideoProduct.product_id == product.id))
    db.delete(product)
    db.commit()
    return "deleted", None, image_keys


def get_product_images(db: Session, product_id: int) -> list[ProductImage]:
    query = (
        select(ProductImage)
        .where(ProductImage.product_id == product_id)
        .order_by(
            ProductImage.is_primary.desc(),
            ProductImage.sort_order.asc(),
            ProductImage.id.asc(),
        )
    )
    return list(db.scalars(query))


def add_product_image(
    db: Session,
    product_id: int,
    image_url: str,
    is_primary: bool = False,
    display_order: int = 0,
) -> ProductImage:
    img = ProductImage(
        product_id=product_id,
        object_key=image_url,
        is_primary=is_primary,
        sort_order=display_order,
    )
    db.add(img)
    db.commit()
    db.refresh(img)
    return img


def add_product_images(
    db: Session, product_id: int, object_keys: list[str]
) -> list[ProductImage]:
    existing_images = get_product_images(db, product_id)
    has_primary = any(img.is_primary for img in existing_images)

    max_sort = db.scalar(
        select(func.max(ProductImage.sort_order)).where(
            ProductImage.product_id == product_id
        )
    )
    next_sort = 0 if max_sort is None else int(max_sort) + 1

    created_images: list[ProductImage] = []
    for index, key in enumerate(object_keys):
        is_primary = (not has_primary) and (index == 0)
        image = ProductImage(
            product_id=product_id,
            object_key=key,
            is_primary=is_primary,
            sort_order=next_sort + index,
        )
        db.add(image)
        created_images.append(image)

    db.commit()
    for image in created_images:
        db.refresh(image)

    return created_images


def get_product_image(
    db: Session, product_id: int, image_id: int
) -> ProductImage | None:
    query = select(ProductImage).where(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id,
    )
    return db.scalar(query)


def delete_product_image(db: Session, image: ProductImage) -> str:
    product_id = image.product_id
    was_primary = image.is_primary
    object_key = image.object_key

    db.delete(image)
    db.flush()

    if was_primary:
        remaining = get_product_images(db, product_id)
        if remaining:
            remaining[0].is_primary = True

    db.commit()
    return object_key


def link_product_to_video(
    db: Session, product_id: int, video_id: int
) -> VideoProduct:
    vp = VideoProduct(product_id=product_id, video_id=video_id)
    db.add(vp)
    db.commit()
    return vp


# ---------- TASK T3D2805: TRỢ LÝ AI VIẾT NỘI DUNG CHO NGƯỜI BÁN ----------

def _build_smart_local_seller_suggestion(
    base_name: str,
    cat_name: str,
    price_val: float | None,
    features_text: str | None,
    duration_sec: int,
) -> ProductAiSuggestResponse:
    clean_name = base_name.strip()
    cat_label = cat_name.strip() if cat_name else "Chính Hãng"
    price_str = (
        f"{int(price_val):,}đ".replace(",", ".")
        if price_val and price_val > 0
        else "giá cực kỳ ưu đãi"
    )
    feature_line = (
        features_text.strip()
        if features_text and features_text.strip()
        else "Thiết kế hiện đại, độ bền cao, trải nghiệm vượt trội trong tầm giá"
    )

    suggested_name = f"{clean_name} [{cat_label}] - Hàng Tuyển Chọn Cao Cấp, Chuẩn Form"
    if len(suggested_name) > 190:
        suggested_name = suggested_name[:190]

    alternative_names = [
        f"[Chính Hãng] {clean_name} - Phiên Bản Mới Nhất, Bảo Hành Uy Tín",
        f"{clean_name} Cao Cấp ({cat_label}) - Giá Tốt Nhất Hôm Nay",
        f"Combo / Siêu Phẩm {clean_name} - Chuẩn Chất Lượng ClipShop Mall",
    ]

    suggested_description = (
        f"✨ GIỚI THIỆU SẢN PHẨM: {clean_name.upper()}\n"
        f"• Phân loại / Danh mục: {cat_label}\n"
        f"• Điểm nổi bật: {feature_line}.\n\n"
        f"🔥 ƯU ĐIỂM VƯỢT TRỘI:\n"
        f"1. Chất lượng hoàn thiện tỉ mỉ, kiểm định kỹ lưỡng trước khi đóng gói giao tới tay khách hàng.\n"
        f"2. Thiết kế tối ưu công năng sử dụng thực tế, phù hợp cho cả nhu cầu cá nhân lẫn làm quà tặng.\n"
        f"3. Mức giá cạnh tranh trực tiếp tại gian hàng ({price_str}) đi kèm nhiều ưu đãi độc quyền trên video.\n\n"
        f"🛡️ CAM KẾT TỪ CỬA HÀNG:\n"
        f"• Hàng thật đúng mô tả và hình ảnh/video quay thực tế 100%.\n"
        f"• Hỗ trợ đổi trả nhanh chóng nếu có lỗi từ nhà sản xuất.\n"
        f"• Đóng gói chống sốc cẩn thận, giao hàng hỏa tốc toàn quốc."
    )

    mid_end = max(25, duration_sec - 12)
    video_script = (
        f"🎬 KỊCH BẢN VIDEO NGẮN ({duration_sec} GIÂY) - SẢN PHẨM: {clean_name}\n"
        f"------------------------------------------------------------\n"
        f"⏱ [00s - 05s] HOOK (Thu hút 3 giây đầu):\n"
        f"• Hình ảnh: Cận cảnh {clean_name} dưới ánh sáng đẹp, mở hộp hoặc xoay 360 độ thật sắc nét.\n"
        f"• Lời thoại: \"Đừng vội mua {clean_name} nếu bạn chưa xem hết 30 giây review thực tế này!\"\n\n"
        f"⏱ [05s - 18s] TRẢI NGHIỆM & ĐIỂM ĐẮT GIÁ:\n"
        f"• Hình ảnh: Quay trực tiếp chi tiết bề mặt, thao tác sử dụng thực tế sản phẩm trên tay.\n"
        f"• Lời thoại: \"Điểm mình ưng nhất ở em {clean_name} dòng {cat_label} này là: {feature_line}. Cầm trên tay cực kỳ chắc chắn và xịn sò.\"\n\n"
        f"⏱ [18s - {mid_end}s] BÁO GIÁ & CHỨNG MINH GIÁ TRỊ:\n"
        f"• Hình ảnh: Hiển thị tem nhãn/phụ kiện đi kèm + chèn chữ nổi bật mức giá {price_str} trên màn hình.\n"
        f"• Lời thoại: \"Chất lượng hoàn thiện đỉnh như thế này mà hiện tại trên giỏ hàng của shop chỉ có {price_str}, số lượng trong kho có hạn.\"\n\n"
        f"⏱ [{mid_end}s - {duration_sec}s] CALL TO ACTION (Kêu gọi chốt đơn):\n"
        f"• Hình ảnh: Chỉ tay xuống biểu tượng Giỏ hàng góc trái màn hình video.\n"
        f"• Lời thoại: \"Mình đã gắn sẵn link sản phẩm chính hãng ở giỏ hàng góc trái bên dưới, bấm đặt ngay kẻo hết size/màu đẹp nhé!\""
    )

    slug_tag = re.sub(r"[^a-zA-Z0-9]", "", clean_name.title())[:24] or "SanPhamHot"
    hashtags = [
        "#ClipShopAI",
        f"#{slug_tag}",
        "#ReviewThucTe",
        "#XuHuongMuaSam",
        "#DealHotHomNay",
    ]

    return ProductAiSuggestResponse(
        suggested_name=suggested_name,
        alternative_names=alternative_names,
        suggested_description=suggested_description,
        video_script_30_60s=video_script,
        suggested_hashtags=hashtags,
        provider="clipshop-ai-writer",
    )


def _parse_ai_json_payload(raw_text: str) -> dict | None:
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def generate_seller_ai_content(
    db: Session, data: ProductAiSuggestRequest
) -> ProductAiSuggestResponse:
    """Gọi Gemini hoặc OpenAI (key trong .env) để gợi ý tên, mô tả sản phẩm và kịch bản video 30-60s."""
    raw_name = data.raw_name.strip()
    cat_name = data.category_name or ""
    if not cat_name and data.category_id:
        cat_obj = db.get(Category, data.category_id)
        if cat_obj:
            cat_name = cat_obj.name

    price_val = float(data.price) if data.price is not None else None
    duration_sec = int(data.duration_seconds or 45)
    fallback_res = _build_smart_local_seller_suggestion(
        base_name=raw_name,
        cat_name=cat_name,
        price_val=price_val,
        features_text=data.features,
        duration_sec=duration_sec,
    )

    prompt = (
        "Bạn là Trợ lý AI Copywriter chuyên nghiệp cho người bán trên nền tảng video thương mại điện tử ClipShop AI.\n"
        f"Thông tin sản phẩm đầu vào:\n"
        f"- Tên/ý tưởng ban đầu: {raw_name}\n"
        f"- Danh mục: {cat_name or 'Chưa chỉ định'}\n"
        f"- Giá dự kiến: {int(price_val) if price_val else 'Chưa chỉ định'} VNĐ\n"
        f"- Đặc điểm nổi bật: {data.features or 'Tối ưu chất lượng và giá bán'}\n"
        f"- Thời lượng kịch bản video ngắn yêu cầu: {duration_sec} giây (trong khoảng 30-60 giây).\n\n"
        "Hãy trả về DUY NHẤT một chuỗi JSON hợp lệ (không bọc markdown) với các khóa sau:\n"
        "{\n"
        '  "suggested_name": "Tên sản phẩm chuẩn SEO hấp dẫn (dưới 180 ký tự)",\n'
        '  "alternative_names": ["Phương án tên 1", "Phương án tên 2", "Phương án tên 3"],\n'
        '  "suggested_description": "Mô tả sản phẩm chi tiết, trình bày đẹp bằng tiếng Việt",\n'
        '  "video_script_30_60s": "Kịch bản quay video ngắn 30-60 giây chia theo từng mốc giây [00s-05s] Hook, [05s-20s] Nội dung, [20s-35s] Điểm nổi bật, [35s-45s] CTA kêu gọi bấm giỏ hàng",\n'
        '  "suggested_hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4"]\n'
        "}"
    )

    gemini_key = (settings.GEMINI_API_KEY or "").strip()
    openai_key = (settings.OPENAI_API_KEY or "").strip()
    timeout_sec = max(3.0, float(settings.AI_TIMEOUT_SECONDS or 15.0))

    # 1. Thử gọi Google Gemini API nếu có GEMINI_API_KEY trong .env
    if gemini_key:
        model_name = settings.GEMINI_MODEL or "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
        try:
            with httpx.Client(timeout=timeout_sec) as client:
                resp = client.post(
                    url,
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.6},
                    },
                )
                if resp.status_code < 400:
                    candidates = resp.json().get("candidates") or []
                    if candidates:
                        parts = (
                            (candidates[0].get("content") or {}).get("parts")
                            or []
                        )
                        text_out = "".join(
                            p.get("text", "") for p in parts if isinstance(p, dict)
                        )
                        parsed = _parse_ai_json_payload(text_out)
                        if parsed and parsed.get("suggested_name"):
                            return ProductAiSuggestResponse(
                                suggested_name=str(parsed["suggested_name"])[:200],
                                alternative_names=list(
                                    parsed.get("alternative_names")
                                    or fallback_res.alternative_names
                                )[:3],
                                suggested_description=str(
                                    parsed.get("suggested_description")
                                    or fallback_res.suggested_description
                                ),
                                video_script_30_60s=str(
                                    parsed.get("video_script_30_60s")
                                    or fallback_res.video_script_30_60s
                                ),
                                suggested_hashtags=list(
                                    parsed.get("suggested_hashtags")
                                    or fallback_res.suggested_hashtags
                                )[:6],
                                provider="gemini",
                            )
        except Exception:
            pass

    # 2. Thử gọi OpenAI API nếu có OPENAI_API_KEY trong .env
    if openai_key:
        model_name = settings.OPENAI_MODEL or "gpt-4o-mini"
        try:
            with httpx.Client(timeout=timeout_sec) as client:
                resp = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openai_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.6,
                    },
                )
                if resp.status_code < 400:
                    choices = resp.json().get("choices") or []
                    if choices:
                        text_out = (
                            (choices[0].get("message") or {}).get("content")
                            or ""
                        )
                        parsed = _parse_ai_json_payload(text_out)
                        if parsed and parsed.get("suggested_name"):
                            return ProductAiSuggestResponse(
                                suggested_name=str(parsed["suggested_name"])[:200],
                                alternative_names=list(
                                    parsed.get("alternative_names")
                                    or fallback_res.alternative_names
                                )[:3],
                                suggested_description=str(
                                    parsed.get("suggested_description")
                                    or fallback_res.suggested_description
                                ),
                                video_script_30_60s=str(
                                    parsed.get("video_script_30_60s")
                                    or fallback_res.video_script_30_60s
                                ),
                                suggested_hashtags=list(
                                    parsed.get("suggested_hashtags")
                                    or fallback_res.suggested_hashtags
                                )[:6],
                                provider="openai",
                            )
        except Exception:
            pass

    return fallback_res

