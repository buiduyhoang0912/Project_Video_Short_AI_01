// Trang Seller Center: Quản lý sản phẩm, tồn kho và tải lên nhiều ảnh.
// Đáp ứng các yêu cầu:
// - Layout Seller Center (thống kê, thông tin shop, đăng nhập/khởi tạo nhanh Seller)
// - Bảng sản phẩm có tìm kiếm, lọc trạng thái, lọc danh mục, phân trang
// - Form thêm/sửa có upload nhiều ảnh, xem trước (preview) trước khi lưu
// - Sửa nhanh tồn kho trực tiếp trên bảng
// - Cảnh báo sắp hết hàng / hết hàng

const SERVER_BASE_URL = CONFIG.API_BASE_URL.replace(/\/api\/?$/, "");

// DOM Elements - Auth & Shop Banner
const authSection = document.getElementById("auth-section");
const quickLoginForm = document.getElementById("quick-login-form");
const logoutSellerBtn = document.getElementById("btn-logout-seller");
const currentUserBadge = document.getElementById("current-user-badge");
const currentShopBadge = document.getElementById("current-shop-badge");
const shopSubtitle = document.getElementById("shop-subtitle");

// DOM Elements - Stats & Low Stock Alert
const statTotal = document.getElementById("stat-total");
const statActive = document.getElementById("stat-active");
const statHidden = document.getElementById("stat-hidden");
const statLowStock = document.getElementById("stat-low-stock");
const lowStockBanner = document.getElementById("low-stock-banner");
const lowStockSummary = document.getElementById("low-stock-summary");
const lowStockItemsList = document.getElementById("low-stock-items-list");
const filterLowStockBtn = document.getElementById("btn-filter-low-stock");
const lowStockThresholdInput = document.getElementById("low-stock-threshold");

// DOM Elements - Form Thêm / Sửa
const productForm = document.getElementById("product-form");
const formTitle = document.getElementById("form-title");
const nameInput = document.getElementById("product-name");
const categorySelect = document.getElementById("product-category");
const priceInput = document.getElementById("product-price");
const stockInput = document.getElementById("product-stock");
const statusFieldWrap = document.getElementById("status-field-wrap");
const statusSelect = document.getElementById("product-status");
const descriptionInput = document.getElementById("product-description");
const imagesInput = document.getElementById("product-images-input");
const existingImagesWrap = document.getElementById("existing-images-wrap");
const existingImagesGrid = document.getElementById("existing-images-grid");
const newImagesWrap = document.getElementById("new-images-wrap");
const newImagesGrid = document.getElementById("new-images-grid");
const submitBtn = document.getElementById("btn-submit");
const cancelBtn = document.getElementById("btn-cancel");

// DOM Elements - Bảng, Bộ lọc & Phân trang
const searchInput = document.getElementById("search-input");
const statusFilter = document.getElementById("status-filter");
const categoryFilter = document.getElementById("category-filter");
const pageSizeSelect = document.getElementById("page-size-select");
const tableBody = document.getElementById("product-table-body");
const paginationInfo = document.getElementById("pagination-info");
const paginationControls = document.getElementById("pagination-controls");

// Trạng thái ứng dụng (State)
let currentUser = null;
let currentShop = null;
let categories = [];
let allProducts = [];
let editingProductId = null;
let existingImages = []; // Ảnh đã lưu trên server của sản phẩm đang sửa
let selectedNewFiles = []; // Danh sách File ảnh mới người dùng chọn (để xem trước & upload)
let currentPage = 1;

// ---------- Hàm hỗ trợ URL ảnh ----------
function resolveImageUrl(objectKey) {
  if (!objectKey) return "";
  if (objectKey.startsWith("http://") || objectKey.startsWith("https://")) {
    return objectKey;
  }
  return `${SERVER_BASE_URL}${objectKey.startsWith("/") ? "" : "/"}${objectKey}`;
}

function getLowStockThreshold() {
  const val = Number(lowStockThresholdInput.value);
  return Number.isFinite(val) && val >= 1 ? val : 5;
}

// ---------- Xác thực & Khởi tạo Seller ----------
async function callAuthApi(path, method = "GET", body = undefined) {
  const token = localStorage.getItem("token") || localStorage.getItem("access_token");
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await axios({
    url: `${SERVER_BASE_URL}${path}`,
    method,
    data: body,
    headers,
  });
  return response.data;
}

async function checkSellerSession() {
  const token = localStorage.getItem("token") || localStorage.getItem("access_token");
  if (!token) {
    showAuthPanel();
    return false;
  }

  try {
    currentUser = await callAuthApi("/auth/me", "GET");
    if (typeof session !== "undefined") session.setUser(currentUser);
    currentUserBadge.textContent = `👤 ${currentUser.display_name} (${currentUser.role})`;
    logoutSellerBtn.hidden = false;

    try {
      currentShop = await api.get("/shops/me");
    } catch (shopErr) {
      // Đã là Seller nhưng chưa tạo Shop (404) -> giữ nguyên trạng thái đã đăng nhập và nhắc tạo Shop
      const msg = shopErr.status === 404
        ? "Bạn đã được duyệt làm Seller! Hãy bấm 'Đơn đăng ký & Hồ sơ Shop' ở trên để tạo Cửa hàng trước."
        : (shopErr.message || "Tài khoản chưa có cửa hàng. Hãy đăng ký bán hàng và chờ Admin duyệt.");
      showToast(msg, "error");
      currentShop = null;
      currentShopBadge.hidden = true;
      shopSubtitle.innerHTML = `${escapeHtml(msg)} <a href="seller-register.html" style="color:#fff;text-decoration:underline;font-weight:700;">Tạo Shop ngay &rarr;</a>`;
      authSection.hidden = true;
      return false;
    }

    currentShopBadge.textContent = `🏪 ${currentShop.name}`;
    currentShopBadge.hidden = false;
    shopSubtitle.textContent = `Cửa hàng: ${currentShop.name} · Địa chỉ: ${currentShop.address || "Chưa cập nhật"}`;
    authSection.hidden = true;
    return true;
  } catch (error) {
    localStorage.removeItem("token");
    localStorage.removeItem("access_token");
    showAuthPanel();
    return false;
  }
}

function showAuthPanel() {
  currentUser = null;
  currentShop = null;
  currentUserBadge.textContent = "Chưa đăng nhập";
  currentShopBadge.hidden = true;
  logoutSellerBtn.hidden = true;
  authSection.hidden = false;
  tableBody.innerHTML = `
    <tr>
      <td colspan="6" class="muted">
        Vui lòng đăng nhập hoặc bấm <strong>"⚡ Khởi tạo nhanh Seller mẫu"</strong> ở phía trên để quản lý sản phẩm.
      </td>
    </tr>`;
}

quickLoginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const identifier = document.getElementById("login-identifier").value.trim();
  const password = document.getElementById("login-password").value;

  try {
    const res = await callAuthApi("/auth/login", "POST", { identifier, password });
    localStorage.setItem("token", res.access_token);
    if (typeof session !== "undefined") session.save(res.access_token, null);
    showToast("Đăng nhập thành công!");
    await initSellerCenter();
    if (typeof renderLayout === "function") renderLayout();
  } catch (error) {
    const msg = error.response?.data?.detail || "Sai tài khoản hoặc mật khẩu";
    showToast(msg, "error");
  }
});

logoutSellerBtn.addEventListener("click", async () => {
  try {
    await callAuthApi("/auth/logout", "POST");
  } catch (_) {
    // Bỏ qua nếu token hết hạn
  }
  if (typeof session !== "undefined") session.clear();
  localStorage.removeItem("token");
  localStorage.removeItem("access_token");
  if (typeof renderLayout === "function") renderLayout();
  allProducts = [];
  updateStatsAndAlert();
  showAuthPanel();
  showToast("Đã đăng xuất");
});

// ---------- Tải danh mục & sản phẩm của Shop ----------
async function loadCategories() {
  try {
    categories = await api.get("/categories");
    const optionsHtml = categories
      .map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`)
      .join("");

    categorySelect.innerHTML = `<option value="">-- Chọn danh mục --</option>${optionsHtml}`;
    categoryFilter.innerHTML = `<option value="ALL">Tất cả danh mục</option>${optionsHtml}`;
  } catch (error) {
    showToast("Không tải được danh mục: " + error.message, "error");
  }
}

async function loadShopProducts() {
  if (!currentShop) return;
  tableBody.innerHTML = `<tr><td colspan="6" class="muted">Đang tải danh sách sản phẩm...</td></tr>`;

  try {
    allProducts = await api.get("/shops/me/products");
    updateStatsAndAlert();
    renderFilteredTable();
  } catch (error) {
    tableBody.innerHTML = `<tr><td colspan="6" class="text-error">${escapeHtml(error.message)}</td></tr>`;
  }
}

function getCategoryName(categoryId) {
  const found = categories.find((c) => c.id === Number(categoryId));
  return found ? found.name : `Danh mục #${categoryId}`;
}

// ---------- Thống kê & Cảnh báo sắp hết hàng ----------
function updateStatsAndAlert() {
  const threshold = getLowStockThreshold();
  const total = allProducts.length;
  const activeCount = allProducts.filter((p) => p.status === "ACTIVE").length;
  const hiddenCount = allProducts.filter((p) => p.status !== "ACTIVE").length;
  const lowStockProducts = allProducts.filter((p) => Number(p.stock) <= threshold);

  statTotal.textContent = total;
  statActive.textContent = activeCount;
  statHidden.textContent = hiddenCount;
  statLowStock.textContent = lowStockProducts.length;

  if (lowStockProducts.length === 0) {
    lowStockBanner.hidden = true;
    return;
  }

  lowStockBanner.hidden = false;
  const outCount = lowStockProducts.filter((p) => Number(p.stock) === 0).length;
  const nearlyOutCount = lowStockProducts.length - outCount;

  lowStockSummary.textContent = `Có ${lowStockProducts.length} sản phẩm cần nhập thêm hàng (${outCount} hết hàng, ${nearlyOutCount} sắp hết hàng ≤ ${threshold}).`;

  lowStockItemsList.innerHTML = lowStockProducts
    .map((p) => {
      const isOut = Number(p.stock) === 0;
      return `
        <span class="low-stock-chip ${isOut ? "out-of-stock" : ""}">
          ${escapeHtml(p.name)}: <strong>${isOut ? "Hết hàng (0)" : `còn ${p.stock}`}</strong>
        </span>`;
    })
    .join("");
}

filterLowStockBtn.addEventListener("click", () => {
  statusFilter.value = "LOW_STOCK";
  currentPage = 1;
  renderFilteredTable();
});

lowStockThresholdInput.addEventListener("change", () => {
  updateStatsAndAlert();
  renderFilteredTable();
});

// ---------- Tìm kiếm, Lọc trạng thái & Phân trang ----------
function getFilteredProducts() {
  const keyword = searchInput.value.trim().toLowerCase();
  const statusVal = statusFilter.value;
  const catVal = categoryFilter.value;
  const threshold = getLowStockThreshold();

  return allProducts.filter((product) => {
    if (keyword && !product.name.toLowerCase().includes(keyword)) {
      return false;
    }

    if (catVal !== "ALL" && Number(product.category_id) !== Number(catVal)) {
      return false;
    }

    if (statusVal === "ACTIVE" && product.status !== "ACTIVE") return false;
    if (statusVal === "HIDDEN" && product.status === "ACTIVE") return false;
    if (statusVal === "LOW_STOCK" && Number(product.stock) > threshold) return false;
    if (statusVal === "OUT_OF_STOCK" && Number(product.stock) !== 0) return false;

    return true;
  });
}

function renderFilteredTable() {
  const filtered = getFilteredProducts();
  const pageSize = Number(pageSizeSelect.value) || 10;
  const totalItems = filtered.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));

  if (currentPage > totalPages) currentPage = totalPages;
  if (currentPage < 1) currentPage = 1;

  const startIndex = (currentPage - 1) * pageSize;
  const pageItems = filtered.slice(startIndex, startIndex + pageSize);

  renderProductRows(pageItems);
  renderPagination(totalItems, startIndex, pageItems.length, totalPages);
}

function renderProductRows(products) {
  if (products.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="6" class="muted" style="text-align: center; padding: 24px;">
          Không có sản phẩm nào khớp với điều kiện tìm kiếm / bộ lọc.
        </td>
      </tr>`;
    return;
  }

  const threshold = getLowStockThreshold();

  tableBody.innerHTML = products
    .map((product) => {
      const stock = Number(product.stock);
      const isOut = stock === 0;
      const isLow = stock > 0 && stock <= threshold;
      const rowClass = isOut ? "row-out-of-stock" : isLow ? "row-low-stock" : "";

      let stockBadgeHtml = `<span class="stock-badge ok">✓ Còn hàng</span>`;
      if (isOut) {
        stockBadgeHtml = `<span class="stock-badge out">🚨 Hết hàng (0)</span>`;
      } else if (isLow) {
        stockBadgeHtml = `<span class="stock-badge low">⚠️ Sắp hết (còn ${stock})</span>`;
      }

      const images = Array.isArray(product.images) ? product.images : [];
      const primaryImg = images.find((img) => img.is_primary) || images[0];
      const thumbHtml = primaryImg
        ? `<img src="${escapeHtml(resolveImageUrl(primaryImg.object_key))}" alt="${escapeHtml(product.name)}" class="product-thumb">`
        : `<div class="product-thumb-placeholder">Chưa có<br>ảnh</div>`;

      const isActive = product.status === "ACTIVE";
      const statusBadgeHtml = isActive
        ? `<span class="status-badge active">Đang bán</span>`
        : `<span class="status-badge hidden">Đã ẩn (${escapeHtml(product.status)})</span>`;

      return `
        <tr class="${rowClass}">
          <td>#${product.id}</td>
          <td>
            <div class="product-cell">
              ${thumbHtml}
              <div>
                <strong>${escapeHtml(product.name)}</strong>
                <div class="product-meta">
                  📁 ${escapeHtml(getCategoryName(product.category_id))} · 🖼 ${images.length} ảnh
                </div>
                ${product.description ? `<div class="product-meta">${escapeHtml(product.description)}</div>` : ""}
              </div>
            </div>
          </td>
          <td class="text-right"><strong>${formatMoney(product.price)}</strong></td>
          <td>
            <div class="quick-stock-box">
              <div class="quick-stock-controls">
                <button
                  type="button"
                  class="btn btn-small btn-step"
                  data-action="step-stock"
                  data-id="${product.id}"
                  data-delta="-1"
                  title="Giảm 1"
                >-</button>
                <input
                  id="quick-stock-${product.id}"
                  type="number"
                  min="0"
                  step="1"
                  value="${stock}"
                  class="quick-stock-input"
                >
                <button
                  type="button"
                  class="btn btn-small btn-step"
                  data-action="step-stock"
                  data-id="${product.id}"
                  data-delta="1"
                  title="Tăng 1"
                >+</button>
                <button
                  type="button"
                  class="btn btn-small btn-primary"
                  data-action="save-stock"
                  data-id="${product.id}"
                >Lưu</button>
              </div>
              ${stockBadgeHtml}
            </div>
          </td>
          <td>${statusBadgeHtml}</td>
          <td class="actions">
            <button
              type="button"
              class="btn btn-small"
              data-action="edit"
              data-id="${product.id}"
            >Sửa</button>
            <button
              type="button"
              class="btn btn-small"
              data-action="toggle-visibility"
              data-id="${product.id}"
            >${isActive ? "Ẩn SP" : "Hiện SP"}</button>
            <button
              type="button"
              class="btn btn-small btn-danger"
              data-action="delete"
              data-id="${product.id}"
            >Xoá</button>
          </td>
        </tr>`;
    })
    .join("");
}

function renderPagination(totalItems, startIndex, currentCount, totalPages) {
  if (totalItems === 0) {
    paginationInfo.textContent = "Hiển thị 0 / 0 sản phẩm";
    paginationControls.innerHTML = "";
    return;
  }

  const from = startIndex + 1;
  const to = startIndex + currentCount;
  paginationInfo.textContent = `Hiển thị ${from}–${to} trên tổng số ${totalItems} sản phẩm (Trang ${currentPage}/${totalPages})`;

  let buttonsHtml = `
    <button
      type="button"
      class="btn btn-page"
      data-page="${currentPage - 1}"
      ${currentPage <= 1 ? "disabled" : ""}
    >« Trước</button>`;

  for (let p = 1; p <= totalPages; p += 1) {
    buttonsHtml += `
      <button
        type="button"
        class="btn btn-page ${p === currentPage ? "active" : ""}"
        data-page="${p}"
      >${p}</button>`;
  }

  buttonsHtml += `
    <button
      type="button"
      class="btn btn-page"
      data-page="${currentPage + 1}"
      ${currentPage >= totalPages ? "disabled" : ""}
    >Sau »</button>`;

  paginationControls.innerHTML = buttonsHtml;
}

paginationControls.addEventListener("click", (event) => {
  const btn = event.target.closest("button[data-page]");
  if (!btn || btn.disabled) return;
  currentPage = Number(btn.dataset.page);
  renderFilteredTable();
});

// ---------- Xem trước (Preview) nhiều ảnh khi chọn file ----------
imagesInput.addEventListener("change", (event) => {
  const files = Array.from(event.target.files || []);
  for (const file of files) {
    selectedNewFiles.push(file);
  }
  imagesInput.value = "";
  renderImagePreviews();
});

function renderImagePreviews() {
  // 1. Ảnh đã lưu trên server (khi đang sửa sản phẩm)
  if (editingProductId !== null && existingImages.length > 0) {
    existingImagesWrap.hidden = false;
    existingImagesGrid.innerHTML = existingImages
      .map(
        (img) => `
        <div class="preview-item">
          <img src="${escapeHtml(resolveImageUrl(img.object_key))}" alt="Ảnh SP">
          ${img.is_primary ? `<span class="preview-primary-tag">Ảnh chính</span>` : ""}
          <button
            type="button"
            class="preview-remove-btn"
            data-remove-existing="${img.id}"
            title="Xoá ảnh này khỏi sản phẩm"
          >×</button>
        </div>`
      )
      .join("");
  } else {
    existingImagesWrap.hidden = true;
    existingImagesGrid.innerHTML = "";
  }

  // 2. Xem trước ảnh mới chọn từ máy tính
  if (selectedNewFiles.length > 0) {
    newImagesWrap.hidden = false;
    const hasExistingPrimary = existingImages.some((img) => img.is_primary);

    newImagesGrid.innerHTML = selectedNewFiles
      .map((file, idx) => {
        const blobUrl = URL.createObjectURL(file);
        const isFirstPrimary = !hasExistingPrimary && idx === 0;
        return `
          <div class="preview-item">
            <img src="${blobUrl}" alt="${escapeHtml(file.name)}">
            ${isFirstPrimary ? `<span class="preview-primary-tag">Ảnh chính</span>` : ""}
            <button
              type="button"
              class="preview-remove-btn"
              data-remove-new="${idx}"
              title="Bỏ chọn ảnh này"
            >×</button>
          </div>`;
      })
      .join("");
  } else {
    newImagesWrap.hidden = true;
    newImagesGrid.innerHTML = "";
  }
}

newImagesGrid.addEventListener("click", (event) => {
  const btn = event.target.closest("button[data-remove-new]");
  if (!btn) return;
  const idx = Number(btn.dataset.removeNew);
  selectedNewFiles.splice(idx, 1);
  renderImagePreviews();
});

existingImagesGrid.addEventListener("click", async (event) => {
  const btn = event.target.closest("button[data-remove-existing]");
  if (!btn || editingProductId === null) return;
  const imageId = Number(btn.dataset.removeExisting);

  try {
    await api.delete(`/products/${editingProductId}/images/${imageId}`);
    existingImages = await api.get(`/products/${editingProductId}/images`);
    renderImagePreviews();
    await loadShopProducts();
    showToast("Đã xoá ảnh sản phẩm");
  } catch (error) {
    showToast(error.message, "error");
  }
});

// ---------- Submit Form Thêm / Sửa sản phẩm + Upload nhiều ảnh ----------
productForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!currentShop) {
    showToast(
      currentUser
        ? "Bạn chưa hoàn thiện thông tin Cửa hàng! Vui lòng tạo Shop ở mục 'Đơn đăng ký & Hồ sơ Shop' trước."
        : "Vui lòng đăng nhập tài khoản Seller trước",
      "error"
    );
    return;
  }

  const name = nameInput.value.trim();
  const categoryId = Number(categorySelect.value);
  const price = Number(priceInput.value);
  const stock = Number(stockInput.value);
  const description = descriptionInput.value.trim() || null;

  if (!name) {
    showToast("Tên sản phẩm không được để trống", "error");
    return;
  }
  if (!categoryId) {
    showToast("Vui lòng chọn danh mục sản phẩm", "error");
    return;
  }
  if (!(price > 0)) {
    showToast("Giá sản phẩm phải lớn hơn 0", "error");
    return;
  }
  if (!Number.isInteger(stock) || stock < 0) {
    showToast("Tồn kho phải là số nguyên >= 0", "error");
    return;
  }

  submitBtn.disabled = true;

  try {
    let savedProduct;
    if (editingProductId === null) {
      savedProduct = await api.post("/products", {
        category_id: categoryId,
        name,
        description,
        price,
        stock,
      });
    } else {
      savedProduct = await api.put(`/products/${editingProductId}`, {
        category_id: categoryId,
        name,
        description,
        price,
        stock,
        status: statusSelect.value,
      });
    }

    // Nếu người bán có chọn các file ảnh mới -> gọi API upload nhiều ảnh
    if (selectedNewFiles.length > 0) {
      const formData = new FormData();
      for (const file of selectedNewFiles) {
        formData.append("files", file);
      }
      await api.upload(`/products/${savedProduct.id}/images`, formData);
    }

    showToast(
      editingProductId === null
        ? "Đã thêm sản phẩm mới thành công!"
        : `Đã cập nhật sản phẩm #${editingProductId}!`
    );
    resetForm();
    await loadShopProducts();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    submitBtn.disabled = false;
  }
});

function startEditProduct(productId) {
  const product = allProducts.find((p) => p.id === productId);
  if (!product) return;

  editingProductId = product.id;
  nameInput.value = product.name;
  categorySelect.value = String(product.category_id);
  priceInput.value = Number(product.price);
  stockInput.value = Number(product.stock);
  descriptionInput.value = product.description ?? "";
  statusSelect.value = product.status === "ACTIVE" ? "ACTIVE" : "HIDDEN";
  statusFieldWrap.hidden = false;

  existingImages = Array.isArray(product.images) ? [...product.images] : [];
  selectedNewFiles = [];
  renderImagePreviews();

  formTitle.textContent = `Sửa sản phẩm #${product.id}`;
  submitBtn.textContent = "Lưu thay đổi";
  cancelBtn.hidden = false;
  nameInput.focus();
}

function resetForm() {
  editingProductId = null;
  productForm.reset();
  stockInput.value = "10";
  statusFieldWrap.hidden = true;
  existingImages = [];
  selectedNewFiles = [];
  renderImagePreviews();

  formTitle.textContent = "Thêm sản phẩm mới";
  submitBtn.textContent = "Thêm sản phẩm";
  cancelBtn.hidden = true;
}

cancelBtn.addEventListener("click", resetForm);

// ---------- Thao tác trên Bảng: Sửa nhanh tồn kho, Ẩn/Hiện, Xoá/Ẩn ----------
async function saveQuickStock(productId) {
  const inputEl = document.getElementById(`quick-stock-${productId}`);
  if (!inputEl) return;

  const newStock = Number(inputEl.value);
  if (!Number.isInteger(newStock) || newStock < 0) {
    showToast("Tồn kho phải là số nguyên >= 0", "error");
    return;
  }

  try {
    const updated = await api.patch(`/products/${productId}/stock`, {
      stock: newStock,
    });
    const idx = allProducts.findIndex((p) => p.id === productId);
    if (idx !== -1) allProducts[idx] = updated;
    updateStatsAndAlert();
    renderFilteredTable();
    showToast(`Đã cập nhật tồn kho SP #${productId} = ${newStock}`);
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function toggleProductVisibility(productId) {
  const product = allProducts.find((p) => p.id === productId);
  if (!product) return;

  try {
    if (product.status === "ACTIVE") {
      await api.patch(`/products/${productId}/hide`);
      showToast(`Đã ẩn sản phẩm "${product.name}"`);
    } else {
      await api.put(`/products/${productId}`, { status: "ACTIVE" });
      showToast(`Đã mở bán lại sản phẩm "${product.name}"`);
    }
    await loadShopProducts();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function deleteOrHideProduct(productId) {
  const product = allProducts.find((p) => p.id === productId);
  if (!product) return;

  if (
    !confirm(
      `Bạn muốn xoá sản phẩm "${product.name}" (#${productId})?\n(Lưu ý: nếu sản phẩm đã có đơn hàng, hệ thống sẽ chỉ chuyển sang trạng thái ẨN chứ không xoá cứng).`
    )
  ) {
    return;
  }

  try {
    const res = await api.delete(`/products/${productId}`);
    if (res && res.action === "hidden") {
      showToast(res.message || "Sản phẩm đã có đơn nên chỉ chuyển sang trạng thái ẨN");
    } else {
      showToast("Đã xoá sản phẩm thành công");
    }
    if (editingProductId === productId) resetForm();
    await loadShopProducts();
  } catch (error) {
    showToast(error.message, "error");
  }
}

tableBody.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;

  const action = button.dataset.action;
  const productId = Number(button.dataset.id);

  if (action === "step-stock") {
    const delta = Number(button.dataset.delta || 0);
    const inputEl = document.getElementById(`quick-stock-${productId}`);
    if (inputEl) {
      const nextVal = Math.max(0, (Number(inputEl.value) || 0) + delta);
      inputEl.value = String(nextVal);
    }
  } else if (action === "save-stock") {
    saveQuickStock(productId);
  } else if (action === "edit") {
    startEditProduct(productId);
  } else if (action === "toggle-visibility") {
    toggleProductVisibility(productId);
  } else if (action === "delete") {
    deleteOrHideProduct(productId);
  }
});

tableBody.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && event.target.classList.contains("quick-stock-input")) {
    event.preventDefault();
    const idStr = event.target.id.replace("quick-stock-", "");
    saveQuickStock(Number(idStr));
  }
});

// Sự kiện tìm kiếm & lọc
let searchTimer;
searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    currentPage = 1;
    renderFilteredTable();
  }, 250);
});

statusFilter.addEventListener("change", () => {
  currentPage = 1;
  renderFilteredTable();
});

categoryFilter.addEventListener("change", () => {
  currentPage = 1;
  renderFilteredTable();
});

pageSizeSelect.addEventListener("change", () => {
  currentPage = 1;
  renderFilteredTable();
});

// ---------- Khởi chạy trang ----------
const tabBtnProducts = document.getElementById("seller-tab-btn-products");
const tabBtnOrders = document.getElementById("seller-tab-btn-orders");
const tabBtnAnalytics = document.getElementById("seller-tab-btn-analytics");
const tabBtnVouchers = document.getElementById("seller-tab-btn-vouchers");
const panelProducts = document.getElementById("seller-panel-products");
const panelOrders = document.getElementById("seller-panel-orders");
const panelAnalytics = document.getElementById("seller-panel-analytics");
const panelVouchers = document.getElementById("seller-panel-vouchers");
const navOrdersCount = document.getElementById("nav-orders-count");
const navVouchersCount = document.getElementById("nav-vouchers-count");

// DOM Elements - Đơn hàng của Shop
const orderSearchInput = document.getElementById("order-search-input");
const refreshOrdersBtn = document.getElementById("btn-refresh-orders");
const orderStatusTabs = document.getElementById("order-status-tabs");
const shopOrdersContainer = document.getElementById("shop-orders-container");

// DOM Elements - Thống kê Doanh thu & Bán chạy
const analyticsTotalRevenue = document.getElementById("analytics-total-revenue");
const analyticsEstimatedRevenue = document.getElementById("analytics-estimated-revenue");
const analyticsCompletedRatio = document.getElementById("analytics-completed-ratio");
const analyticsPendingCancelled = document.getElementById("analytics-pending-cancelled");
const dailyRevenueTbody = document.getElementById("daily-revenue-tbody");
const bestSellersTbody = document.getElementById("best-sellers-tbody");
const refreshAnalyticsBtn = document.getElementById("btn-refresh-analytics");

let shopOrders = [];
let currentOrderStatusFilter = "ALL";

const ORDER_STATUS_META = {
  pending: { label: "⏳ Chờ xác nhận", cls: "pending" },
  confirmed: { label: "✅ Đã xác nhận", cls: "confirmed" },
  shipping: { label: "🚚 Đang giao", cls: "shipping" },
  completed: { label: "🎉 Hoàn thành", cls: "completed" },
  cancelled: { label: "❌ Đã huỷ", cls: "cancelled" },
};

function switchSellerTab(tabName) {
  if (!panelProducts || !panelOrders || !panelAnalytics) return;

  panelProducts.hidden = tabName !== "products";
  panelOrders.hidden = tabName !== "orders";
  panelAnalytics.hidden = tabName !== "analytics";
  if (panelVouchers) panelVouchers.hidden = tabName !== "vouchers";

  if (tabBtnProducts) tabBtnProducts.classList.toggle("active", tabName === "products");
  if (tabBtnOrders) tabBtnOrders.classList.toggle("active", tabName === "orders");
  if (tabBtnAnalytics) tabBtnAnalytics.classList.toggle("active", tabName === "analytics");
  if (tabBtnVouchers) tabBtnVouchers.classList.toggle("active", tabName === "vouchers");

  if (tabName === "orders" && currentShop) {
    loadShopOrders();
  } else if (tabName === "analytics" && currentShop) {
    loadShopAnalytics();
  } else if (tabName === "vouchers" && currentShop) {
    loadShopVouchers();
  }
}

document.querySelectorAll("[data-seller-tab]").forEach((btn) => {
  btn.addEventListener("click", () => {
    switchSellerTab(btn.dataset.sellerTab);
  });
});

// ---------- Quản lý Đơn hàng của Shop ----------
async function loadShopOrders() {
  if (!currentShop || !shopOrdersContainer) return;
  shopOrdersContainer.innerHTML = `<div class="muted">Đang tải danh sách đơn hàng của shop...</div>`;

  try {
    const params = {};
    if (currentOrderStatusFilter && currentOrderStatusFilter !== "ALL") {
      params.status_filter = currentOrderStatusFilter;
    }
    const kw = orderSearchInput ? orderSearchInput.value.trim() : "";
    if (kw) params.q = kw;

    shopOrders = await api.get("/shops/me/orders", params);
    if (navOrdersCount && currentOrderStatusFilter === "ALL" && !kw) {
      navOrdersCount.textContent = String(shopOrders.length);
    }
    renderShopOrders();
  } catch (error) {
    shopOrdersContainer.innerHTML = `<div class="text-error">${escapeHtml(error.message)}</div>`;
  }
}

function renderOrderStepper(status) {
  const st = (status || "pending").toLowerCase();
  if (st === "cancelled") {
    return `<div class="order-stepper"><span class="order-badge cancelled">❌ Đơn hàng đã bị huỷ (Tồn kho đã được hoàn lại)</span></div>`;
  }

  const steps = [
    { key: "pending", label: "1. Chờ xác nhận" },
    { key: "confirmed", label: "2. Đã xác nhận" },
    { key: "shipping", label: "3. Đang giao" },
    { key: "completed", label: "4. Hoàn thành" },
  ];
  const curIdx = steps.findIndex((s) => s.key === st);

  return `
    <div class="order-stepper">
      ${steps
        .map((step, idx) => {
          let cls = "";
          if (idx < curIdx || st === "completed") cls = "done";
          else if (idx === curIdx) cls = "current";
          const arrow = idx < steps.length - 1 ? `<span class="order-step-arrow">&rarr;</span>` : "";
          return `<span class="order-step ${cls}">${step.label}</span>${arrow}`;
        })
        .join("")}
    </div>`;
}

function renderOrderActionButtons(order) {
  const st = (order.status || "pending").toLowerCase();
  const isBank = (order.payment_method || "").toUpperCase() === "BANK_TRANSFER";

  if (st === "pending") {
    return `
      <button type="button" class="btn btn-small btn-primary" data-order-action="confirmed" data-order-id="${order.id}">
        ${isBank ? "💰 Xác nhận đã nhận tiền (VietQR)" : "✅ Xác nhận đơn"}
      </button>
      <button type="button" class="btn btn-small btn-danger" data-order-action="cancelled" data-order-id="${order.id}">
        ❌ Huỷ đơn
      </button>`;
  }
  if (st === "confirmed") {
    return `
      <button type="button" class="btn btn-small btn-primary" data-order-action="shipping" data-order-id="${order.id}">
        🚚 Bắt đầu giao hàng
      </button>
      <button type="button" class="btn btn-small btn-danger" data-order-action="cancelled" data-order-id="${order.id}">
        ❌ Huỷ đơn
      </button>`;
  }
  if (st === "shipping") {
    return `
      <button type="button" class="btn btn-small btn-primary" data-order-action="completed" data-order-id="${order.id}">
        🎉 Xác nhận Hoàn thành
      </button>`;
  }
  return `<span class="muted">Đơn hàng đã kết thúc</span>`;
}

function renderShopOrders() {
  if (!shopOrdersContainer) return;
  if (!Array.isArray(shopOrders) || shopOrders.length === 0) {
    shopOrdersContainer.innerHTML = `
      <div class="muted" style="text-align: center; padding: 28px;">
        Không có đơn hàng nào khớp với bộ lọc hiện tại.
      </div>`;
    return;
  }

  shopOrdersContainer.innerHTML = shopOrders
    .map((order) => {
      const st = (order.status || "pending").toLowerCase();
      const meta = ORDER_STATUS_META[st] || { label: st, cls: "pending" };
      const items = Array.isArray(order.items) ? order.items : [];

      return `
        <article class="shop-order-card">
          <div class="shop-order-header">
            <div>
              <strong>Đơn hàng #${order.id}</strong>
              <span class="muted">· Đặt lúc: ${formatDateTime(order.created_at)} · Thanh toán: <strong>${escapeHtml(order.payment_method)}</strong></span>
            </div>
            <span class="order-badge ${meta.cls}">${meta.label}</span>
          </div>

          <div class="muted" style="font-size: 13px;">
            👤 Người nhận: <strong>${escapeHtml(order.recipient_name)}</strong> ·
            📞 SĐT: <strong>${escapeHtml(order.recipient_phone)}</strong> ·
            📍 Địa chỉ: <strong>${escapeHtml(order.recipient_address)}</strong>
          </div>

          ${renderOrderStepper(st)}

          <table class="order-items-table">
            <thead>
              <tr>
                <th>Sản phẩm</th>
                <th class="text-right">Đơn giá lúc đặt</th>
                <th class="text-right">Số lượng</th>
                <th class="text-right">Thành tiền</th>
              </tr>
            </thead>
            <tbody>
              ${items
                .map(
                  (it) => `
                  <tr>
                    <td>${escapeHtml(it.product_name || `Sản phẩm #${it.product_id}`)}</td>
                    <td class="text-right">${formatMoney(it.unit_price)}</td>
                    <td class="text-right">x${it.quantity}</td>
                    <td class="text-right"><strong>${formatMoney(it.line_total ?? it.unit_price * it.quantity)}</strong></td>
                  </tr>`
                )
                .join("")}
            </tbody>
          </table>

          <div class="shop-order-footer">
            <div>
              ${
                order.voucher_code && Number(order.discount_amount) > 0
                  ? `<div class="muted" style="font-size: 13px; margin-bottom: 4px;">
                       Tạm tính: ${formatMoney(order.subtotal_amount ?? order.total_amount + order.discount_amount)}
                       · <span class="voucher-tag-inline">🎟️ Mã ${escapeHtml(order.voucher_code)}: -${formatMoney(order.discount_amount)}</span>
                     </div>`
                  : ""
              }
              Tổng tiền đơn: <strong style="font-size: 18px; color: #dc2626;">${formatMoney(order.total_amount)}</strong>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              ${renderOrderActionButtons(order)}
            </div>
          </div>
        </article>`;
    })
    .join("");
}

if (shopOrdersContainer) {
  shopOrdersContainer.addEventListener("click", async (event) => {
    const btn = event.target.closest("button[data-order-action]");
    if (!btn) return;
    const orderId = Number(btn.dataset.orderId);
    const nextStatus = btn.dataset.orderAction;

    if (
      nextStatus === "cancelled" &&
      !confirm(`Bạn có chắc chắn muốn HUỶ đơn hàng #${orderId} không? (Tồn kho sản phẩm sẽ được hoàn lại)`)
    ) {
      return;
    }

    btn.disabled = true;
    try {
      await api.patch(`/shops/me/orders/${orderId}/status`, { status: nextStatus });
      const label = ORDER_STATUS_META[nextStatus]?.label || nextStatus;
      showToast(`Đã cập nhật đơn #${orderId} sang trạng thái: ${label}`);
      await Promise.all([loadShopOrders(), loadShopProducts(), loadShopAnalytics()]);
    } catch (error) {
      showToast(error.message, "error");
      btn.disabled = false;
    }
  });
}

if (orderStatusTabs) {
  orderStatusTabs.addEventListener("click", (event) => {
    const btn = event.target.closest("button[data-order-status]");
    if (!btn) return;
    currentOrderStatusFilter = btn.dataset.orderStatus;
    orderStatusTabs.querySelectorAll(".order-filter-pill").forEach((b) => {
      b.classList.toggle("active", b === btn);
    });
    loadShopOrders();
  });
}

if (orderSearchInput) {
  let orderSearchTimer;
  orderSearchInput.addEventListener("input", () => {
    clearTimeout(orderSearchTimer);
    orderSearchTimer = setTimeout(loadShopOrders, 250);
  });
}

if (refreshOrdersBtn) {
  refreshOrdersBtn.addEventListener("click", loadShopOrders);
}

// ---------- Thống kê Doanh thu theo ngày & Sản phẩm bán chạy ----------
async function loadShopAnalytics() {
  if (!currentShop || !dailyRevenueTbody || !bestSellersTbody) return;

  try {
    const data = await api.get("/shops/me/analytics");
    if (navOrdersCount) navOrdersCount.textContent = String(data.total_orders || 0);

    if (analyticsTotalRevenue) {
      analyticsTotalRevenue.textContent = formatMoney(data.total_revenue || 0);
    }
    if (analyticsEstimatedRevenue) {
      analyticsEstimatedRevenue.textContent = formatMoney(data.estimated_revenue || 0);
    }
    if (analyticsCompletedRatio) {
      analyticsCompletedRatio.textContent = `${data.completed_orders || 0} / ${data.total_orders || 0}`;
    }
    if (analyticsPendingCancelled) {
      const processing =
        (data.pending_orders || 0) +
        (data.confirmed_orders || 0) +
        (data.shipping_orders || 0);
      analyticsPendingCancelled.textContent = `${processing} / ${data.cancelled_orders || 0}`;
    }

    renderDailyRevenueTable(data.daily_revenue || []);
    renderBestSellersTable(data.best_selling_products || []);
  } catch (error) {
    dailyRevenueTbody.innerHTML = `<tr><td colspan="3" class="text-error">${escapeHtml(error.message)}</td></tr>`;
  }
}

function renderDailyRevenueTable(dailyList) {
  if (!Array.isArray(dailyList) || dailyList.length === 0) {
    dailyRevenueTbody.innerHTML = `
      <tr>
        <td colspan="3" class="muted" style="text-align: center; padding: 20px;">
          Chưa có dữ liệu đơn hàng theo ngày.
        </td>
      </tr>`;
    return;
  }

  const maxRev = Math.max(1, ...dailyList.map((d) => Number(d.revenue || 0)));

  dailyRevenueTbody.innerHTML = dailyList
    .map((item) => {
      const rev = Number(item.revenue || 0);
      const pct = Math.min(100, Math.round((rev / maxRev) * 100));
      return `
        <tr>
          <td><strong>${escapeHtml(item.date)}</strong></td>
          <td>
            ${item.completed_orders} hoàn thành / ${item.total_orders} đơn
            <div class="revenue-bar-wrap">
              <div class="revenue-bar-fill" style="width: ${pct}%;"></div>
            </div>
          </td>
          <td class="text-right"><strong>${formatMoney(rev)}</strong></td>
        </tr>`;
    })
    .join("");
}

function renderBestSellersTable(bestList) {
  if (!Array.isArray(bestList) || bestList.length === 0) {
    bestSellersTbody.innerHTML = `
      <tr>
        <td colspan="4" class="muted" style="text-align: center; padding: 20px;">
          Chưa có sản phẩm nào phát sinh doanh số.
        </td>
      </tr>`;
    return;
  }

  bestSellersTbody.innerHTML = bestList
    .map((prod, idx) => {
      const rank = idx + 1;
      const rankCls = rank <= 3 ? `rank-${rank}` : "";
      return `
        <tr>
          <td><span class="rank-badge ${rankCls}">#${rank}</span></td>
          <td>
            <strong>${escapeHtml(prod.product_name)}</strong>
            <div class="product-meta">Giá: ${formatMoney(prod.price)} · Tồn kho: ${prod.stock}</div>
          </td>
          <td class="text-right"><strong>${prod.total_quantity_sold}</strong></td>
          <td class="text-right"><strong>${formatMoney(prod.total_revenue)}</strong></td>
        </tr>`;
    })
    .join("");
}

if (refreshAnalyticsBtn) {
  refreshAnalyticsBtn.addEventListener("click", loadShopAnalytics);
}

// ---------- TASK T3D2805: TRỢ LÝ AI VIẾT NỘI DUNG & KỊCH BẢN VIDEO 30-60S ----------
const aiSuggestBtn = document.getElementById("btn-ai-suggest");
const aiAssistantBox = document.getElementById("ai-assistant-box");
const aiProviderBadge = document.getElementById("ai-provider-badge");
const aiAltNamesList = document.getElementById("ai-alt-names-list");
const aiVideoScriptInput = document.getElementById("ai-video-script");
const aiHashtagsList = document.getElementById("ai-hashtags-list");
const copyScriptBtn = document.getElementById("btn-copy-script");

if (aiSuggestBtn) {
  aiSuggestBtn.addEventListener("click", async () => {
    const rawName = nameInput.value.trim();
    if (!rawName) {
      showToast("Vui lòng nhập tên hoặc ý tưởng sản phẩm vào ô Tên sản phẩm trước khi bấm Gợi ý bằng AI", "error");
      nameInput.focus();
      return;
    }

    const catId = Number(categorySelect.value) || null;
    const catName = catId ? getCategoryName(catId) : null;
    const priceVal = Number(priceInput.value) > 0 ? Number(priceInput.value) : null;
    const currentDesc = descriptionInput.value.trim() || null;

    const origText = aiSuggestBtn.innerHTML;
    aiSuggestBtn.disabled = true;
    aiSuggestBtn.innerHTML = "⏳ AI đang viết...";

    try {
      const res = await api.post("/products/ai-suggest", {
        raw_name: rawName,
        category_id: catId,
        category_name: catName,
        price: priceVal,
        features: currentDesc,
        duration_seconds: 45,
      }, { timeout: 60000 });

      // Điền tên và mô tả gợi ý vào form để người bán có thể chỉnh sửa trước khi bấm Lưu
      nameInput.value = res.suggested_name || rawName;
      descriptionInput.value = res.suggested_description || "";

      if (aiAssistantBox) {
        aiAssistantBox.hidden = false;
      }
      if (aiProviderBadge) {
        aiProviderBadge.textContent = `Nguồn: ${res.provider || "AI"}`;
      }
      if (aiVideoScriptInput) {
        aiVideoScriptInput.value = res.video_script_30_60s || "";
      }

      if (aiAltNamesList) {
        const alts = Array.isArray(res.alternative_names) ? res.alternative_names : [];
        aiAltNamesList.innerHTML = alts
          .map(
            (alt) => `
            <button type="button" class="ai-alt-name-chip" data-alt-name="${escapeHtml(alt)}">
              💡 Chọn tên: ${escapeHtml(alt)}
            </button>`
          )
          .join("");
      }

      if (aiHashtagsList) {
        const tags = Array.isArray(res.suggested_hashtags) ? res.suggested_hashtags : [];
        aiHashtagsList.innerHTML = tags
          .map((t) => `<span class="ai-hashtag-pill">${escapeHtml(t)}</span>`)
          .join("");
      }

      showToast("✨ AI đã gợi ý Tên, Mô tả và Kịch bản video 30–60s! Bạn có thể sửa lại trước khi lưu.");
    } catch (error) {
      showToast(error.message || "Không thể gọi Trợ lý AI lúc này", "error");
    } finally {
      aiSuggestBtn.disabled = false;
      aiSuggestBtn.innerHTML = origText;
    }
  });
}

if (aiAltNamesList) {
  aiAltNamesList.addEventListener("click", (event) => {
    const chip = event.target.closest("button[data-alt-name]");
    if (!chip) return;
    nameInput.value = chip.dataset.altName;
    nameInput.focus();
    showToast("Đã áp dụng phương án tên sản phẩm vào form!");
  });
}

if (copyScriptBtn && aiVideoScriptInput) {
  copyScriptBtn.addEventListener("click", async () => {
    const text = aiVideoScriptInput.value.trim();
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      showToast("📋 Đã sao chép kịch bản video vào bộ nhớ tạm!");
    } catch (_) {
      aiVideoScriptInput.select();
      document.execCommand("copy");
      showToast("📋 Đã sao chép kịch bản video!");
    }
  });
}

// ---------- Quản lý Mã giảm giá của Shop (Task T3D2BFB) ----------
const voucherForm = document.getElementById("voucher-form");
const voucherCodeInput = document.getElementById("voucher-code");
const voucherDescInput = document.getElementById("voucher-description");
const voucherTypeSelect = document.getElementById("voucher-type");
const voucherValueLabel = document.getElementById("voucher-value-label");
const voucherValueInput = document.getElementById("voucher-value");
const voucherMaxWrap = document.getElementById("voucher-max-wrap");
const voucherMaxInput = document.getElementById("voucher-max-discount");
const voucherMinOrderInput = document.getElementById("voucher-min-order");
const voucherUsageLimitInput = document.getElementById("voucher-usage-limit");
const voucherPerUserInput = document.getElementById("voucher-per-user-limit");
const voucherExpiresInput = document.getElementById("voucher-expires-at");
const voucherSubmitBtn = document.getElementById("voucher-submit-btn");
const vouchersTbody = document.getElementById("vouchers-tbody");
const refreshVouchersBtn = document.getElementById("btn-refresh-vouchers");

let shopVouchers = [];

function setDefaultVoucherExpiry() {
  if (!voucherExpiresInput || voucherExpiresInput.value) return;
  const d = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
  const pad = (n) => String(n).padStart(2, "0");
  voucherExpiresInput.value = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T23:59`;
}

if (voucherTypeSelect) {
  voucherTypeSelect.addEventListener("change", () => {
    const isPercent = voucherTypeSelect.value === "PERCENT";
    if (voucherValueLabel) {
      voucherValueLabel.textContent = isPercent ? "Mức giảm (%) *" : "Số tiền giảm (VNĐ) *";
    }
    if (voucherValueInput) {
      if (isPercent) {
        voucherValueInput.max = "100";
        voucherValueInput.placeholder = "VD: 10";
      } else {
        voucherValueInput.removeAttribute("max");
        voucherValueInput.placeholder = "VD: 30000";
      }
    }
    if (voucherMaxWrap) {
      voucherMaxWrap.style.opacity = isPercent ? "1" : "0.45";
    }
    if (voucherMaxInput) {
      voucherMaxInput.disabled = !isPercent;
      if (!isPercent) voucherMaxInput.value = "";
    }
  });
}

const VOUCHER_STATE_META = {
  ACTIVE: { label: "🟢 Đang hoạt động", cls: "confirmed" },
  UPCOMING: { label: "⏳ Sắp diễn ra", cls: "pending" },
  USED_UP: { label: "🟠 Hết lượt", cls: "shipping" },
  EXPIRED: { label: "⚪ Đã hết hạn", cls: "cancelled" },
  INACTIVE: { label: "🔴 Đã tạm ngừng", cls: "cancelled" },
};

async function loadShopVouchers() {
  if (!currentShop || !vouchersTbody) return;
  setDefaultVoucherExpiry();
  try {
    shopVouchers = await api.get("/shops/me/vouchers");
    if (navVouchersCount) navVouchersCount.textContent = String(shopVouchers.length || 0);
    renderShopVouchers();
  } catch (error) {
    vouchersTbody.innerHTML = `<tr><td colspan="6" class="text-error">${escapeHtml(error.message)}</td></tr>`;
  }
}

function renderShopVouchers() {
  if (!vouchersTbody) return;
  if (!Array.isArray(shopVouchers) || shopVouchers.length === 0) {
    vouchersTbody.innerHTML = `
      <tr>
        <td colspan="6" class="muted" style="text-align: center; padding: 24px;">
          Shop chưa có mã giảm giá nào. Hãy tạo mã đầu tiên ở khung bên trái!
        </td>
      </tr>`;
    return;
  }

  vouchersTbody.innerHTML = shopVouchers
    .map((v) => {
      const isPercent = v.discount_type === "PERCENT";
      const discountText = isPercent
        ? `Giảm <strong>${v.discount_value}%</strong>${
            v.max_discount_amount ? ` (tối đa ${formatMoney(v.max_discount_amount)})` : ""
          }`
        : `Giảm <strong>${formatMoney(v.discount_value)}</strong>`;
      const stateMeta = VOUCHER_STATE_META[v.state] || { label: v.state, cls: "pending" };
      const isActiveStatus = (v.status || "").toUpperCase() === "ACTIVE";

      return `
        <tr>
          <td>
            <span class="voucher-code-pill">🎟️ ${escapeHtml(v.code)}</span>
            ${v.description ? `<div class="product-meta" style="margin-top: 4px;">${escapeHtml(v.description)}</div>` : ""}
          </td>
          <td>
            <div>${discountText}</div>
            <div class="product-meta">Đơn tối thiểu: <strong>${formatMoney(v.min_order_amount || 0)}</strong></div>
          </td>
          <td>
            <strong>${v.used_count} / ${v.usage_limit}</strong> lượt
            <div class="product-meta">Còn ${v.remaining_uses} · Tối đa ${v.per_user_limit}/người</div>
          </td>
          <td>
            <div>${formatDateTime(v.expires_at)}</div>
          </td>
          <td>
            <span class="order-badge ${stateMeta.cls}">${stateMeta.label}</span>
          </td>
          <td class="text-right">
            <div style="display: inline-flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end;">
              <button
                type="button"
                class="btn btn-small"
                data-voucher-toggle="${v.id}"
                data-next-status="${isActiveStatus ? "INACTIVE" : "ACTIVE"}"
              >
                ${isActiveStatus ? "⏸ Tạm ngừng" : "▶ Kích hoạt"}
              </button>
              <button
                type="button"
                class="btn btn-small btn-danger"
                data-voucher-delete="${v.id}"
                data-voucher-code="${escapeAttr(v.code)}"
              >
                🗑 Xoá
              </button>
            </div>
          </td>
        </tr>`;
    })
    .join("");
}

if (voucherForm) {
  voucherForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!currentShop) {
      showToast(
        currentUser
          ? "Bạn chưa hoàn thiện thông tin Cửa hàng! Vui lòng tạo Shop ở mục 'Đơn đăng ký & Hồ sơ Shop' trước."
          : "Vui lòng đăng nhập tài khoản Người bán trước.",
        "error"
      );
      return;
    }

    const code = (voucherCodeInput.value || "").trim().toUpperCase();
    const discountType = voucherTypeSelect.value;
    const discountValue = Number(voucherValueInput.value);
    const maxDiscount =
      discountType === "PERCENT" && voucherMaxInput.value
        ? Number(voucherMaxInput.value)
        : null;
    const minOrder = Number(voucherMinOrderInput.value || 0);
    const usageLimit = Number(voucherUsageLimitInput.value || 1);
    const perUserLimit = Number(voucherPerUserInput.value || 1);
    const expiresAt = voucherExpiresInput.value;

    if (!code || code.length < 3) {
      showToast("Mã giảm giá phải có từ 3 ký tự trở lên.", "error");
      return;
    }
    if (!expiresAt) {
      showToast("Vui lòng chọn hạn dùng cho mã giảm giá.", "error");
      return;
    }

    voucherSubmitBtn.disabled = true;
    try {
      const created = await api.post("/shops/me/vouchers", {
        code,
        description: (voucherDescInput.value || "").trim() || null,
        discount_type: discountType,
        discount_value: discountValue,
        max_discount_amount: maxDiscount,
        min_order_amount: minOrder,
        usage_limit: usageLimit,
        per_user_limit: perUserLimit,
        expires_at: expiresAt,
      });
      showToast(`Đã tạo mã giảm giá ${created.code} thành công!`);
      voucherCodeInput.value = "";
      voucherDescInput.value = "";
      voucherValueInput.value = "";
      if (voucherMaxInput) voucherMaxInput.value = "";
      await loadShopVouchers();
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      voucherSubmitBtn.disabled = false;
    }
  });
}

if (vouchersTbody) {
  vouchersTbody.addEventListener("click", async (event) => {
    const toggleBtn = event.target.closest("button[data-voucher-toggle]");
    if (toggleBtn) {
      const vid = Number(toggleBtn.dataset.voucherToggle);
      const nextStatus = toggleBtn.dataset.nextStatus;
      toggleBtn.disabled = true;
      try {
        await api.put(`/shops/me/vouchers/${vid}`, { status: nextStatus });
        showToast(
          nextStatus === "ACTIVE"
            ? "Đã kích hoạt lại mã giảm giá."
            : "Đã tạm ngừng mã giảm giá."
        );
        await loadShopVouchers();
      } catch (error) {
        showToast(error.message, "error");
        toggleBtn.disabled = false;
      }
      return;
    }

    const delBtn = event.target.closest("button[data-voucher-delete]");
    if (delBtn) {
      const vid = Number(delBtn.dataset.voucherDelete);
      const vcode = delBtn.dataset.voucherCode || `#${vid}`;
      if (!confirm(`Bạn có chắc muốn xoá mã giảm giá '${vcode}' không?`)) return;
      delBtn.disabled = true;
      try {
        const res = await api.delete(`/shops/me/vouchers/${vid}`);
        showToast(res.message || `Đã xoá mã ${vcode}`);
        await loadShopVouchers();
      } catch (error) {
        showToast(error.message, "error");
        delBtn.disabled = false;
      }
    }
  });
}

if (refreshVouchersBtn) {
  refreshVouchersBtn.addEventListener("click", loadShopVouchers);
}
async function initSellerCenter() {
  await loadCategories();
  const loggedIn = await checkSellerSession();
  if (loggedIn) {
    await Promise.all([loadShopProducts(), loadShopAnalytics(), loadShopVouchers()]);
    const tabParam = new URLSearchParams(window.location.search).get("tab");
    if (tabParam === "orders" || tabParam === "analytics" || tabParam === "vouchers") {
      switchSellerTab(tabParam);
    }
  }
}

initSellerCenter();
