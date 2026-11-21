// Trang Cửa hàng công khai (Task T3D27D1):
// Hiển thị Logo, Mô tả cửa hàng, Danh sách sản phẩm của shop và Video của shop.

const SERVER_BASE_URL = CONFIG.API_BASE_URL.replace(/\/api\/?$/, "");
const DEFAULT_SHOP_LOGO =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='96' height='96'%3E%3Crect fill='%23dbeafe' width='96' height='96' rx='48'/%3E%3Ctext x='50%25' y='54%25' dominant-baseline='middle' text-anchor='middle' font-size='42'%3E🏪%3C/text%3E%3C/svg%3E";
const DEFAULT_PRODUCT_IMG =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Crect fill='%23f3f4f6' width='300' height='300'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%239ca3af' font-size='44'%3E🛍️%3C/text%3E%3C/svg%3E";

// DOM Elements - Danh sách cửa hàng
const shopSearchInput = document.getElementById("shop-search-input");
const shopsPillsList = document.getElementById("shops-pills-list");
const noShopCard = document.getElementById("no-shop-card");
const shopPublicView = document.getElementById("shop-public-view");

// DOM Elements - Hồ sơ cửa hàng công khai
const publicShopLogo = document.getElementById("public-shop-logo");
const publicShopName = document.getElementById("public-shop-name");
const publicShopAddress = document.getElementById("public-shop-address");
const publicShopDate = document.getElementById("public-shop-date");
const publicShopId = document.getElementById("public-shop-id");
const publicShopDescription = document.getElementById("public-shop-description");
const ownerQuickActions = document.getElementById("owner-quick-actions");
const publicStatProducts = document.getElementById("public-stat-products");
const publicStatVideos = document.getElementById("public-stat-videos");

// DOM Elements - Tabs
const tabBtnProducts = document.getElementById("tab-btn-products");
const tabBtnVideos = document.getElementById("tab-btn-videos");
const tabCountProducts = document.getElementById("tab-count-products");
const tabCountVideos = document.getElementById("tab-count-videos");
const tabPanelProducts = document.getElementById("tab-panel-products");
const tabPanelVideos = document.getElementById("tab-panel-videos");

// DOM Elements - Sản phẩm & Video của shop
const shopProductSearch = document.getElementById("shop-product-search");
const shopProductCategory = document.getElementById("shop-product-category");
const shopProductSort = document.getElementById("shop-product-sort");
const shopProductsSummary = document.getElementById("shop-products-summary");
const shopProductsGrid = document.getElementById("shop-products-grid");
const shopVideosGrid = document.getElementById("shop-videos-grid");

// State
let allShops = [];
let categories = [];
let selectedShop = null;
let shopProducts = [];
let shopVideos = [];

function resolveMediaUrl(key, fallback = "") {
  if (!key) return fallback;
  if (key.startsWith("http://") || key.startsWith("https://") || key.startsWith("data:")) {
    return key;
  }
  return `${SERVER_BASE_URL}${key.startsWith("/") ? "" : "/"}${key}`;
}

function getQueryShopId() {
  const params = new URLSearchParams(window.location.search);
  const raw = params.get("shop_id") || params.get("id");
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

// ---------- Tải danh mục & danh sách cửa hàng ----------
async function loadCategories() {
  try {
    categories = await api.get("/categories");
    const options = categories
      .map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`)
      .join("");
    shopProductCategory.innerHTML = `<option value="ALL">Tất cả danh mục</option>${options}`;
  } catch (_) {
    categories = [];
  }
}

function getCategoryName(categoryId) {
  const found = categories.find((c) => c.id === Number(categoryId));
  return found ? found.name : `Danh mục #${categoryId}`;
}

async function loadPublicShops(keyword = "") {
  try {
    allShops = await api.get("/shops", keyword ? { q: keyword } : undefined);
  } catch (error) {
    allShops = [];
  }

  renderShopPills();

  if (allShops.length === 0) {
    shopPublicView.hidden = true;
    noShopCard.hidden = false;
    return;
  }

  noShopCard.hidden = true;
  const queryId = getQueryShopId();
  const targetShop =
    allShops.find((s) => s.id === queryId) ||
    (selectedShop && allShops.find((s) => s.id === selectedShop.id)) ||
    allShops[0];

  await selectPublicShop(targetShop.id);
}

function renderShopPills() {
  if (allShops.length === 0) {
    shopsPillsList.innerHTML = `<span class="muted">Không có cửa hàng nào.</span>`;
    return;
  }

  shopsPillsList.innerHTML = allShops
    .map((shop) => {
      const isActive = selectedShop && selectedShop.id === shop.id;
      return `
        <button
          type="button"
          class="shop-pill-btn ${isActive ? "active" : ""}"
          data-shop-id="${shop.id}"
        >
          🏪 ${escapeHtml(shop.name)}
        </button>`;
    })
    .join("");
}

shopsPillsList.addEventListener("click", (event) => {
  const btn = event.target.closest("button[data-shop-id]");
  if (!btn) return;
  const shopId = Number(btn.dataset.shopId);
  const url = new URL(window.location.href);
  url.searchParams.set("shop_id", String(shopId));
  window.history.replaceState({}, "", url.toString());
  selectPublicShop(shopId);
});

// ---------- Hiển thị chi tiết Cửa hàng công khai ----------
async function selectPublicShop(shopId) {
  try {
    selectedShop = await api.get(`/shops/${shopId}`);
  } catch (error) {
    showToast(error.message, "error");
    return;
  }

  shopPublicView.hidden = false;
  renderShopPills();
  renderShopHeader(selectedShop);

  await Promise.all([
    loadShopProducts(selectedShop.id),
    loadShopVideos(selectedShop.id, selectedShop.owner_id),
    loadPublicShopVouchers(selectedShop.id),
  ]);
}

async function loadPublicShopVouchers(shopId) {
  const card = document.getElementById("public-shop-vouchers-card");
  const listEl = document.getElementById("public-shop-vouchers-list");
  if (!card || !listEl) return;
  try {
    const vouchers = await api.get(`/shops/${shopId}/vouchers`);
    if (!Array.isArray(vouchers) || vouchers.length === 0) {
      card.hidden = true;
      return;
    }
    card.hidden = false;
    listEl.innerHTML = vouchers
      .map((v) => {
        const discountLabel =
          v.discount_type === "PERCENT"
            ? `Giảm ${v.discount_value}%${
                v.max_discount_amount ? ` (tối đa ${formatMoney(v.max_discount_amount)})` : ""
              }`
            : `Giảm ${formatMoney(v.discount_value)}`;
        return `
          <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 14px;border-radius:10px;background:#fff1f2;border:1.5px dashed #f43f5e;min-width:260px;">
            <div>
              <div style="font-weight:800;color:#be123c;font-size:14px;">🎟️ ${escapeHtml(v.code)} · ${discountLabel}</div>
              <div class="muted" style="font-size:12px;">
                Đơn tối thiểu: ${formatMoney(v.min_order_amount || 0)} · Còn ${v.remaining_uses} lượt
              </div>
            </div>
            <button type="button" class="btn btn-small btn-primary" data-copy-voucher="${escapeAttr(v.code)}">
              Sao chép
            </button>
          </div>`;
      })
      .join("");
  } catch (_) {
    card.hidden = true;
  }
}

document.addEventListener("click", (event) => {
  const btn = event.target.closest("button[data-copy-voucher]");
  if (!btn) return;
  const code = btn.dataset.copyVoucher;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(code);
  }
  showToast(`Đã sao chép mã giảm giá: ${code}`);
});

function renderShopHeader(shop) {
  document.title = `${shop.name} - Cửa hàng công khai | ClipShop AI`;
  publicShopLogo.src = resolveMediaUrl(shop.avatar_key, DEFAULT_SHOP_LOGO);
  publicShopLogo.onerror = () => {
    publicShopLogo.src = DEFAULT_SHOP_LOGO;
  };
  publicShopName.textContent = shop.name;
  publicShopAddress.textContent = shop.address || "Việt Nam";
  publicShopDate.textContent = formatDateTime(shop.created_at);
  publicShopId.textContent = `#${shop.id}`;
  publicShopDescription.textContent =
    shop.description || "Chào mừng bạn đến với gian hàng chính thức trên ClipShop AI!";

  const me = session.getUser();
  ownerQuickActions.hidden = !(me && Number(me.id) === Number(shop.owner_id));
}

// ---------- Tải & Hiển thị Danh sách Sản phẩm của Shop ----------
async function loadShopProducts(shopId) {
  shopProductsGrid.innerHTML = `<div class="muted">Đang tải danh sách sản phẩm của shop...</div>`;
  try {
    shopProducts = await api.get(`/shops/${shopId}/products`);
  } catch (error) {
    shopProducts = [];
  }

  publicStatProducts.textContent = shopProducts.length;
  tabCountProducts.textContent = shopProducts.length;
  renderShopProducts();
}

function renderShopProducts() {
  const keyword = shopProductSearch.value.trim().toLowerCase();
  const catVal = shopProductCategory.value;
  const sortVal = shopProductSort.value;

  let filtered = shopProducts.filter((p) => {
    if (keyword && !p.name.toLowerCase().includes(keyword)) return false;
    if (catVal !== "ALL" && Number(p.category_id) !== Number(catVal)) return false;
    return true;
  });

  if (sortVal === "price_asc") {
    filtered.sort((a, b) => Number(a.price) - Number(b.price));
  } else if (sortVal === "price_desc") {
    filtered.sort((a, b) => Number(b.price) - Number(a.price));
  } else {
    filtered.sort((a, b) => Number(b.id) - Number(a.id));
  }

  shopProductsSummary.textContent = `Hiển thị ${filtered.length} / ${shopProducts.length} sản phẩm`;

  if (filtered.length === 0) {
    shopProductsGrid.innerHTML = `
      <div class="card" style="grid-column: 1 / -1; text-align: center; padding: 32px;">
        <strong>Cửa hàng chưa có sản phẩm nào phù hợp.</strong>
        <p class="muted">Hãy thử đổi bộ lọc hoặc quay lại sau nhé!</p>
      </div>`;
    return;
  }

  shopProductsGrid.innerHTML = filtered
    .map((p) => {
      const images = Array.isArray(p.images) ? p.images : [];
      const primaryImg = images.find((i) => i.is_primary) || images[0];
      const imgUrl = primaryImg
        ? resolveMediaUrl(primaryImg.object_key || primaryImg.image_url, DEFAULT_PRODUCT_IMG)
        : DEFAULT_PRODUCT_IMG;
      const stock = Number(p.stock || 0);
      const soldCount = Number(p.sold_count || 12 + (p.id * 5) % 90);
      const oldPrice = Math.round((Number(p.price) * 1.18) / 1000) * 1000;

      return `
        <article class="shop-product-card">
          <div class="shop-product-img-wrap">
            <span class="card-badge-mall">MALL</span>
            <span class="card-badge-discount">-15%</span>
            <img
              src="${escapeHtml(imgUrl)}"
              alt="${escapeHtml(p.name)}"
              onerror="this.src='${DEFAULT_PRODUCT_IMG}'"
            >
          </div>
          <div class="shop-product-body">
            <span class="shop-product-category-pill">
              📁 ${escapeHtml(getCategoryName(p.category_id))}
            </span>
            <div class="shop-product-title" title="${escapeHtml(p.name)}">
              ${escapeHtml(p.name)}
            </div>
            <div class="shop-product-price-row">
              <span class="shop-product-price">${formatMoney(p.price)}</span>
              <span class="shop-product-old-price">${formatMoney(oldPrice)}</span>
            </div>
            <div class="shop-product-rating-row">
              <span><span class="stars-gold">★★★★★</span> 4.9</span>
              <span>Đã bán <strong>${soldCount}</strong> · ${stock > 0 ? `Kho: ${stock}` : "Hết hàng"}</span>
            </div>
            ${
              p.description
                ? `<div class="muted" style="font-size: 12px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                     ${escapeHtml(p.description)}
                   </div>`
                : ""
            }
            <div style="margin-top: auto; padding-top: 10px;">
              <button
                type="button"
                class="btn-mall-cart"
                data-add-cart="${p.id}"
                ${stock <= 0 ? "disabled" : ""}
              >
                ${stock > 0 ? "🛒 Thêm vào giỏ hàng" : "Tạm hết hàng"}
              </button>
            </div>
          </div>
        </article>`;
    })
    .join("");
}

shopProductsGrid.addEventListener("click", async (event) => {
  const btn = event.target.closest("button[data-add-cart]");
  if (!btn) return;
  const productId = Number(btn.dataset.addCart);

  if (!session.getToken()) {
    showToast("Vui lòng đăng nhập để thêm sản phẩm vào giỏ hàng", "error");
    return;
  }

  btn.disabled = true;
  try {
    await api.post("/cart/items", { product_id: productId, quantity: 1 });
    showToast("Đã thêm sản phẩm vào giỏ hàng!");
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    btn.disabled = false;
  }
});

// ---------- Tải & Hiển thị Danh sách Video của Shop ----------
async function loadShopVideos(shopId, ownerId) {
  shopVideosGrid.innerHTML = `<div class="muted">Đang tải danh sách video của shop...</div>`;

  try {
    shopVideos = await api.get(`/shops/${shopId}/videos`);
  } catch (_) {
    // Fallback sang /api/videos/users/{owner_id} nếu cần
    try {
      const res = await api.get(`/videos/users/${ownerId}`);
      shopVideos = Array.isArray(res?.items) ? res.items : [];
    } catch (__) {
      shopVideos = [];
    }
  }

  publicStatVideos.textContent = shopVideos.length;
  tabCountVideos.textContent = shopVideos.length;
  renderShopVideos();
}

function renderShopVideos() {
  if (!Array.isArray(shopVideos) || shopVideos.length === 0) {
    shopVideosGrid.innerHTML = `
      <div class="card" style="grid-column: 1 / -1; text-align: center; padding: 32px;">
        <strong>🎬 Cửa hàng chưa có video giới thiệu sản phẩm nào.</strong>
        <p class="muted">Chủ cửa hàng có thể đăng video ngắn tại mục <strong>➕ Đăng video</strong> trên thanh menu.</p>
      </div>`;
    return;
  }

  shopVideosGrid.innerHTML = shopVideos
    .map((v) => {
      const videoSrc = resolveMediaUrl(v.video_url);
      const posterSrc = v.thumbnail_url ? resolveMediaUrl(v.thumbnail_url) : "";
      const tagged = Array.isArray(v.tagged_products) ? v.tagged_products : [];

      return `
        <article class="shop-video-card">
          <div class="shop-video-player-wrap">
            <video
              controls
              preload="metadata"
              ${posterSrc ? `poster="${escapeHtml(posterSrc)}"` : ""}
              src="${escapeHtml(videoSrc)}"
            ></video>
            <span class="video-badge-overlay">
              👁 ${Number(v.view_count || 0)} lượt xem · ⏱ ${Number(v.duration_seconds || 0)}s
            </span>
          </div>
          <div class="shop-video-body">
            <h3 class="shop-video-title">${escapeHtml(v.title)}</h3>
            ${
              v.description
                ? `<div class="muted" style="font-size: 13px;">${escapeHtml(v.description)}</div>`
                : ""
            }
            ${
              tagged.length > 0
                ? `<div class="tagged-products-box">
                     <span class="muted" style="font-size: 11px; font-weight: 600;">🛍️ Sản phẩm gắn trong video:</span>
                     ${tagged
                       .map(
                         (tp) => `
                         <div class="tagged-product-pill">
                           <span>${escapeHtml(tp.name)}</span>
                           <strong>${formatMoney(tp.price)}</strong>
                         </div>`
                       )
                       .join("")}
                   </div>`
                : ""
            }
            <div style="margin-top: auto; padding-top: 8px;">
              <a
                href="video.html?id=${v.id}"
                class="btn btn-small"
                style="display: block; text-align: center; text-decoration: none;"
              >
                ▶ Xem chi tiết &amp; Bình luận video
              </a>
            </div>
          </div>
        </article>`;
    })
    .join("");
}

// ---------- Sự kiện chuyển Tab & Tìm kiếm ----------
function switchTab(tabName) {
  const isProducts = tabName === "products";
  tabBtnProducts.classList.toggle("active", isProducts);
  tabBtnVideos.classList.toggle("active", !isProducts);
  tabPanelProducts.hidden = !isProducts;
  tabPanelVideos.hidden = isProducts;
}

tabBtnProducts.addEventListener("click", () => switchTab("products"));
tabBtnVideos.addEventListener("click", () => switchTab("videos"));

shopProductSearch.addEventListener("input", renderShopProducts);
shopProductCategory.addEventListener("change", renderShopProducts);
shopProductSort.addEventListener("change", renderShopProducts);

let shopSearchTimer;
shopSearchInput.addEventListener("input", () => {
  clearTimeout(shopSearchTimer);
  shopSearchTimer = setTimeout(() => {
    loadPublicShops(shopSearchInput.value.trim());
  }, 300);
});

// ---------- Khởi chạy ----------
async function initPublicShopPage() {
  await loadCategories();
  await loadPublicShops();
}

initPublicShopPage();
