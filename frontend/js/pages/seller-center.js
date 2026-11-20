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
      // Chưa có cửa hàng: không tự cấp quyền/tạo shop; hướng dẫn người dùng.
      showToast(shopErr.response?.data?.detail || "Tài khoản chưa có cửa hàng. Hãy đăng ký bán hàng và chờ Admin duyệt.", "error");
      showAuthPanel();
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
    showToast("Vui lòng đăng nhập tài khoản Seller trước", "error");
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
async function initSellerCenter() {
  await loadCategories();
  const loggedIn = await checkSellerSession();
  if (loggedIn) {
    await loadShopProducts();
  }
}

initSellerCenter();
