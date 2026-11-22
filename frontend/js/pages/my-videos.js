// ==========================================================
// T3D226A: Xử lý Trang Quản lý video của tôi (My Videos UI)
// Chức năng: Sửa mô tả, Ẩn/Hiện video, Xoá video, Lọc & Tìm kiếm
// ==========================================================

let myVideosList = [];
let activeFilter = "ALL"; // "ALL" | "VISIBLE" | "HIDDEN"
let searchQuery = "";
let currentEditingVideoId = null;
let currentDeletingVideoId = null;

// DOM Elements
const loadingEl = document.getElementById("manage-loading");
const emptyNoticeEl = document.getElementById("manage-empty-notice");
const listContainerEl = document.getElementById("manage-videos-list-container");

const statTotalEl = document.getElementById("stat-total-count");
const statVisibleEl = document.getElementById("stat-visible-count");
const statHiddenEl = document.getElementById("stat-hidden-count");
const statViewsEl = document.getElementById("stat-views-count");

const tabAllNum = document.getElementById("tab-all-num");
const tabVisibleNum = document.getElementById("tab-visible-num");
const tabHiddenNum = document.getElementById("tab-hidden-num");
const inputSearch = document.getElementById("input-search-video");
const filterTabs = document.querySelectorAll(".manage-tab-btn");

// Modal Sửa mô tả
const modalEdit = document.getElementById("modal-edit-desc");
const editTitlePreview = document.getElementById("edit-video-title-text");
const editTextarea = document.getElementById("edit-desc-textarea");
const editCharCounter = document.getElementById("edit-desc-counter");
const editErrorBox = document.getElementById("edit-desc-error");
const btnSaveDesc = document.getElementById("btn-save-desc");
const btnCancelEdit = document.getElementById("btn-cancel-edit");
const btnCloseEditModal = document.getElementById("btn-close-edit-modal");

// Modal Xóa
const modalDelete = document.getElementById("modal-confirm-delete");
const deleteTitlePreview = document.getElementById("delete-video-title-text");
const deleteErrorBox = document.getElementById("delete-video-error");
const btnConfirmDelete = document.getElementById("btn-confirm-delete");
const btnCancelDelete = document.getElementById("btn-cancel-delete");
const btnCloseDeleteModal = document.getElementById("btn-close-delete-modal");

// ---------- KHỞI TẠO DỮ LIỆU ----------
document.addEventListener("DOMContentLoaded", async () => {
  if (!session.getToken()) {
    return; // layout.js sẽ tự chuyển hướng về login
  }
  await fetchMyVideos();
  initEvents();
});

async function fetchMyVideos() {
  loadingEl.style.display = "block";
  listContainerEl.style.display = "none";
  emptyNoticeEl.style.display = "none";

  try {
    let currentUser = getCurrentUser();
    if (!currentUser || !currentUser.id) {
      currentUser = await api.get("/auth/me");
      session.setUser(currentUser);
    }

    // Gọi API lấy toàn bộ video của chính mình (bao gồm cả video đang ẩn)
    const res = await api.get(`/videos/users/${currentUser.id}`, {
      limit: 50,
      include_hidden: true,
    });

    myVideosList = (res && res.items) ? res.items : (Array.isArray(res) ? res : []);
    updateStats();
    renderFilteredVideos();
  } catch (err) {
    console.error("Lỗi tải danh sách video của tôi:", err);
    loadingEl.innerHTML = `
      <div style="color:var(--color-danger);margin-bottom:12px;">⚠️ ${escapeHtml(err.message || "Không thể tải danh sách video.")}</div>
      <button type="button" class="btn btn-small" onclick="fetchMyVideos()">Thử lại</button>
    `;
  }
}

// ---------- CẬP NHẬT SỐ LIỆU THỐNG KÊ ----------
function updateStats() {
  const total = myVideosList.length;
  const visible = myVideosList.filter((v) => v.status === "VISIBLE").length;
  const hidden = myVideosList.filter((v) => v.status === "HIDDEN").length;
  const totalViews = myVideosList.reduce((sum, v) => sum + (v.view_count || 0), 0);

  statTotalEl.textContent = total;
  statVisibleEl.textContent = visible;
  statHiddenEl.textContent = hidden;
  statViewsEl.textContent = Number(totalViews).toLocaleString("vi-VN");

  tabAllNum.textContent = total;
  tabVisibleNum.textContent = visible;
  tabHiddenNum.textContent = hidden;
}

// ---------- LỌC & RENDER DANH SÁCH VIDEO ----------
function renderFilteredVideos() {
  loadingEl.style.display = "none";

  let filtered = myVideosList.slice();

  // 1. Lọc theo Tab trạng thái
  if (activeFilter === "VISIBLE") {
    filtered = filtered.filter((v) => v.status === "VISIBLE");
  } else if (activeFilter === "HIDDEN") {
    filtered = filtered.filter((v) => v.status === "HIDDEN");
  }

  // 2. Lọc theo Từ khóa tìm kiếm
  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    filtered = filtered.filter(
      (v) => (v.title && v.title.toLowerCase().includes(q)) ||
             (v.description && v.description.toLowerCase().includes(q))
    );
  }

  if (filtered.length === 0) {
    emptyNoticeEl.style.display = "block";
    listContainerEl.style.display = "none";
    return;
  }

  emptyNoticeEl.style.display = "none";
  listContainerEl.style.display = "flex";
  listContainerEl.innerHTML = "";

  filtered.forEach((video) => {
    const card = document.createElement("div");
    card.className = "card manage-video-card";
    card.id = `manage-video-item-${video.id}`;

    let thumbSrc = video.thumbnail_url || "";
    if (thumbSrc && thumbSrc.startsWith("/uploads/")) {
      thumbSrc = `${CONFIG.API_BASE_URL.replace("/api", "")}${thumbSrc}`;
    } else if (!thumbSrc) {
      thumbSrc = "../assets/images/logo.svg";
    }

    const isVisible = video.status === "VISIBLE";
    const statusBadge = isVisible
      ? `<span class="badge-status badge-status-visible">🟢 Đang hiển thị</span>`
      : `<span class="badge-status badge-status-hidden">🟡 Đang ẩn</span>`;

    const toggleBtnText = isVisible ? "👁️ Ẩn video" : "👁️‍🗨️ Hiện lại";
    const toggleBtnClass = isVisible ? "btn-small btn-warning" : "btn-small btn-success";

    card.innerHTML = `
      <div class="manage-card-left">
        <a href="video.html?id=${video.id}" class="manage-thumb-link" title="Bấm để xem video">
          <img src="${escapeHtml(thumbSrc)}" alt="${escapeHtml(video.title || "")}" onerror="this.src='../assets/images/logo.svg'">
          <span class="manage-thumb-duration">${video.duration_seconds ? video.duration_seconds + "s" : ""}</span>
        </a>
      </div>

      <div class="manage-card-body">
        <div class="manage-card-title-row">
          <a href="video.html?id=${video.id}" class="manage-card-title">${escapeHtml(video.title || "Video không có tiêu đề")}</a>
          ${statusBadge}
        </div>

        <div class="manage-card-meta">
          <span>👁️ <strong>${Number(video.view_count || 0).toLocaleString("vi-VN")}</strong> lượt xem</span>
          <span>•</span>
          <span>📅 ${formatDateTime(video.created_at)}</span>
          ${(video.products && video.products.length > 0) ? `<span>•</span> <span class="badge-status" style="background:#e0e7ff;color:#4338ca;">🛍️ ${video.products.length} sản phẩm</span>` : ""}
        </div>

        <div class="manage-card-desc-box">
          <span class="muted" style="font-size:12px;">Mô tả:</span>
          <p class="manage-card-desc-text" id="desc-text-${video.id}">
            ${escapeHtml(video.description || "Chưa có mô tả.")}
          </p>
        </div>
      </div>

      <div class="manage-card-actions">
        <button type="button" class="btn btn-small btn-edit-desc" data-id="${video.id}">
          ✏️ Sửa mô tả
        </button>
        <button type="button" class="btn btn-small btn-tag-prods" data-id="${video.id}" style="background:#4f46e5;color:#fff;border-color:#4338ca;">
          🛍️ Gắn sản phẩm
        </button>
        <button type="button" class="btn ${toggleBtnClass} btn-toggle-status" data-id="${video.id}" data-current="${video.status}">
          ${toggleBtnText}
        </button>
        <button type="button" class="btn btn-small btn-danger btn-delete-video" data-id="${video.id}">
          🗑️ Xoá
        </button>
      </div>
    `;

    listContainerEl.appendChild(card);
  });
}

// ---------- 1. SỬA MÔ TẢ VIDEO (TASK T3D226A) ----------
function openEditDescModal(videoId) {
  const video = myVideosList.find((v) => v.id === videoId);
  if (!video) return;

  currentEditingVideoId = videoId;
  editTitlePreview.textContent = video.title || `Video #${videoId}`;
  editTextarea.value = video.description || "";
  updateEditCharCount();
  editErrorBox.style.display = "none";
  modalEdit.style.display = "flex";
  editTextarea.focus();
}

function closeEditModal() {
  modalEdit.style.display = "none";
  currentEditingVideoId = null;
  editErrorBox.textContent = "";
  editErrorBox.style.display = "none";
}

function updateEditCharCount() {
  const len = editTextarea.value.length;
  editCharCounter.textContent = `${len} / 1000`;
}

async function handleSaveDesc() {
  if (!currentEditingVideoId) return;

  const newDesc = editTextarea.value.trim();
  btnSaveDesc.disabled = true;
  btnSaveDesc.textContent = "⏳ Đang lưu...";
  editErrorBox.style.display = "none";

  try {
    const res = await api.patch(`/videos/${currentEditingVideoId}`, {
      description: newDesc,
    });

    // Cập nhật mảng local
    const target = myVideosList.find((v) => v.id === currentEditingVideoId);
    if (target) {
      target.description = newDesc;
    }

    // Cập nhật text trên giao diện
    const descEl = document.getElementById(`desc-text-${currentEditingVideoId}`);
    if (descEl) {
      descEl.textContent = newDesc || "Chưa có mô tả.";
    }

    showToast("Đã cập nhật mô tả video thành công!", "success");
    closeEditModal();
  } catch (err) {
    console.error("Lỗi sửa mô tả video:", err);
    editErrorBox.textContent = err.message || "Không thể cập nhật mô tả.";
    editErrorBox.style.display = "block";
  } finally {
    btnSaveDesc.disabled = false;
    btnSaveDesc.textContent = "💾 Lưu thay đổi";
  }
}

// ---------- 2. ẨN / HIỆN VIDEO (TASK T3D226A) ----------
async function handleToggleVideoStatus(videoId, currentStatus) {
  const targetStatus = currentStatus === "VISIBLE" ? "HIDDEN" : "VISIBLE";
  const actionLabel = targetStatus === "HIDDEN" ? "Ẩn video" : "Hiển thị video";

  try {
    const res = await api.patch(`/videos/${videoId}/status`, {
      status: targetStatus,
    });

    // Cập nhật mảng local
    const target = myVideosList.find((v) => v.id === videoId);
    if (target) {
      target.status = targetStatus;
    }

    updateStats();
    renderFilteredVideos();
    showToast(res.message || `Đã chuyển sang ${actionLabel}!`, "success");
  } catch (err) {
    console.error("Lỗi thay đổi trạng thái video:", err);
    showToast(err.message || "Không thể thay đổi trạng thái video.", "error");
  }
}

// ---------- 3. XOÁ VIDEO (TASK T3D226A) ----------
function openDeleteModal(videoId) {
  const video = myVideosList.find((v) => v.id === videoId);
  if (!video) return;

  currentDeletingVideoId = videoId;
  deleteTitlePreview.textContent = video.title || `Video #${videoId}`;
  deleteErrorBox.style.display = "none";
  modalDelete.style.display = "flex";
}

function closeDeleteModal() {
  modalDelete.style.display = "none";
  currentDeletingVideoId = null;
  deleteErrorBox.textContent = "";
  deleteErrorBox.style.display = "none";
}

async function handleConfirmDelete() {
  if (!currentDeletingVideoId) return;

  btnConfirmDelete.disabled = true;
  btnConfirmDelete.textContent = "⏳ Đang xoá...";
  deleteErrorBox.style.display = "none";

  try {
    await api.delete(`/videos/${currentDeletingVideoId}`);

    // Xóa khỏi danh sách local
    myVideosList = myVideosList.filter((v) => v.id !== currentDeletingVideoId);
    updateStats();
    renderFilteredVideos();

    showToast("Đã xoá video thành công!", "success");
    closeDeleteModal();
  } catch (err) {
    console.error("Lỗi xoá video:", err);
    deleteErrorBox.textContent = err.message || "Không thể xoá video.";
    deleteErrorBox.style.display = "block";
  } finally {
    btnConfirmDelete.disabled = false;
    btnConfirmDelete.textContent = "Xác nhận xóa";
  }
}

// ---------- 4. GẮN SẢN PHẨM VÀO VIDEO (TASK T3D2296) ----------
let currentProdsVideoId = null;
let manageShopProducts = [];
let manageSelectedProductIds = new Set();

const modalVideoProds = document.getElementById("modal-video-products");
const prodsVideoTitleText = document.getElementById("prods-video-title-text");
const manageProdsPickerList = document.getElementById("manage-prods-picker-list");
const manageProdsError = document.getElementById("manage-prods-error");
const manageProdsCounter = document.getElementById("manage-prods-counter");
const btnSaveProds = document.getElementById("btn-save-prods");
const btnCancelProds = document.getElementById("btn-cancel-prods");
const btnCloseProdsModal = document.getElementById("btn-close-prods-modal");

async function openVideoProductsModal(videoId) {
  const video = myVideosList.find((v) => v.id === videoId);
  if (!video) return;

  currentProdsVideoId = videoId;
  prodsVideoTitleText.textContent = video.title || `Video #${videoId}`;
  manageProdsError.style.display = "none";
  manageProdsPickerList.innerHTML = `<div class="muted" style="text-align:center;padding:20px;">Đang tải sản phẩm của shop...</div>`;
  modalVideoProds.style.display = "flex";

  try {
    // 1. Tải danh sách sản phẩm thuộc shop của mình
    if (manageShopProducts.length === 0) {
      const prods = await api.get("/shops/me/products");
      manageShopProducts = Array.isArray(prods) ? prods.filter((p) => p.status === "ACTIVE") : [];
    }

    if (manageShopProducts.length === 0) {
      manageProdsPickerList.innerHTML = `
        <div class="muted" style="text-align:center;padding:24px;">
          Shop của bạn chưa có sản phẩm nào đang hoạt động.
          <br><br>
          <a href="seller.html" class="btn btn-small btn-primary">Thêm sản phẩm tại Seller Center</a>
        </div>`;
      return;
    }

    // 2. Lấy danh sách sản phẩm đang được gắn vào video này
    let attached = [];
    try {
      attached = await api.get(`/videos/${videoId}/products`);
    } catch (_) {
      attached = video.products || [];
    }

    manageSelectedProductIds = new Set((attached || []).map((p) => p.id));
    renderManageProdsList();
  } catch (err) {
    manageProdsPickerList.innerHTML = `<div style="color:var(--color-danger);text-align:center;padding:20px;">⚠️ ${escapeHtml(err.message || "Không thể tải sản phẩm")}</div>`;
  }
}

function updateManageProdsCounter() {
  if (manageProdsCounter) {
    manageProdsCounter.textContent = `Đã chọn: ${manageSelectedProductIds.size}/3 sản phẩm`;
  }
}

function renderManageProdsList() {
  if (!manageProdsPickerList) return;
  manageProdsPickerList.innerHTML = "";
  updateManageProdsCounter();

  manageShopProducts.forEach((p) => {
    const isChecked = manageSelectedProductIds.has(p.id);
    const item = document.createElement("div");
    item.className = `picker-product-item ${isChecked ? "selected" : ""}`;

    let thumb = p.thumbnail_url || "";
    if (p.images && p.images.length > 0) {
      const primary = p.images.find((img) => img.is_primary) || p.images[0];
      thumb = primary.image_url || primary.object_key || thumb;
    }
    if (thumb && thumb.startsWith("/uploads/")) {
      thumb = `${CONFIG.API_BASE_URL.replace("/api", "")}${thumb}`;
    } else if (!thumb) {
      thumb = "../assets/images/logo.svg";
    }

    const priceText = Number(p.price || 0).toLocaleString("vi-VN") + " ₫";

    item.innerHTML = `
      <input type="checkbox" class="picker-checkbox" data-id="${p.id}" ${isChecked ? "checked" : ""}>
      <img src="${escapeHtml(thumb)}" alt="${escapeHtml(p.name)}" class="picker-item-thumb" onerror="this.src='../assets/images/logo.svg'">
      <div class="picker-item-info">
        <div class="picker-item-name">${escapeHtml(p.name)}</div>
        <div class="picker-item-price">${priceText}</div>
      </div>
    `;

    item.addEventListener("click", (e) => {
      if (e.target.tagName !== "INPUT") {
        const cb = item.querySelector(".picker-checkbox");
        cb.checked = !cb.checked;
        cb.dispatchEvent(new Event("change"));
      }
    });

    const checkbox = item.querySelector(".picker-checkbox");
    checkbox.addEventListener("change", (e) => {
      const pid = parseInt(e.target.dataset.id, 10);
      if (e.target.checked) {
        if (manageSelectedProductIds.size >= 3) {
          e.target.checked = false;
          manageProdsError.textContent = "Một video chỉ được gắn tối đa 3 sản phẩm!";
          manageProdsError.style.display = "block";
          return;
        }
        manageSelectedProductIds.add(pid);
        item.classList.add("selected");
      } else {
        manageSelectedProductIds.delete(pid);
        item.classList.remove("selected");
        manageProdsError.style.display = "none";
      }
      updateManageProdsCounter();
    });

    manageProdsPickerList.appendChild(item);
  });
}

function closeVideoProductsModal() {
  if (modalVideoProds) modalVideoProds.style.display = "none";
  currentProdsVideoId = null;
}

async function handleSaveVideoProducts() {
  if (!currentProdsVideoId) return;

  btnSaveProds.disabled = true;
  btnSaveProds.textContent = "⏳ Đang lưu...";
  manageProdsError.style.display = "none";

  try {
    const productIdsArray = Array.from(manageSelectedProductIds);
    const updatedProducts = await api.post(`/videos/${currentProdsVideoId}/products`, {
      product_ids: productIdsArray,
    });

    // Cập nhật video trong danh sách local
    const target = myVideosList.find((v) => v.id === currentProdsVideoId);
    if (target) {
      target.products = updatedProducts;
    }

    renderFilteredVideos();
    showToast("Đã cập nhật sản phẩm gắn trong video thành công!", "success");
    closeVideoProductsModal();
  } catch (err) {
    console.error("Lỗi gắn sản phẩm vào video:", err);
    manageProdsError.textContent = err.message || "Không thể lưu sản phẩm gắn vào video.";
    manageProdsError.style.display = "block";
  } finally {
    btnSaveProds.disabled = false;
    btnSaveProds.textContent = "💾 Lưu sản phẩm";
  }
}

// ---------- GẮN SỰ KIỆN ----------
function initEvents() {
  // Tabs lọc trạng thái
  filterTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      filterTabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      activeFilter = tab.dataset.filter;
      renderFilteredVideos();
    });
  });

  // Tìm kiếm
  inputSearch.addEventListener("input", (e) => {
    searchQuery = e.target.value.trim();
    renderFilteredVideos();
  });

  // Delegate sự kiện cho danh sách video
  listContainerEl.addEventListener("click", (e) => {
    const btnEdit = e.target.closest(".btn-edit-desc");
    if (btnEdit) {
      const id = parseInt(btnEdit.dataset.id, 10);
      openEditDescModal(id);
      return;
    }

    const btnTagProds = e.target.closest(".btn-tag-prods");
    if (btnTagProds) {
      const id = parseInt(btnTagProds.dataset.id, 10);
      openVideoProductsModal(id);
      return;
    }

    const btnToggle = e.target.closest(".btn-toggle-status");
    if (btnToggle) {
      const id = parseInt(btnToggle.dataset.id, 10);
      const cur = btnToggle.dataset.current;
      handleToggleVideoStatus(id, cur);
      return;
    }

    const btnDel = e.target.closest(".btn-delete-video");
    if (btnDel) {
      const id = parseInt(btnDel.dataset.id, 10);
      openDeleteModal(id);
      return;
    }
  });

  // Modal Sửa mô tả
  editTextarea.addEventListener("input", updateEditCharCount);
  btnSaveDesc.addEventListener("click", handleSaveDesc);
  btnCancelEdit.addEventListener("click", closeEditModal);
  btnCloseEditModal.addEventListener("click", closeEditModal);

  // Modal Xóa
  btnConfirmDelete.addEventListener("click", handleConfirmDelete);
  btnCancelDelete.addEventListener("click", closeDeleteModal);
  btnCloseDeleteModal.addEventListener("click", closeDeleteModal);

  // Modal Gắn sản phẩm (Task T3D2296)
  if (btnSaveProds) btnSaveProds.addEventListener("click", handleSaveVideoProducts);
  if (btnCancelProds) btnCancelProds.addEventListener("click", closeVideoProductsModal);
  if (btnCloseProdsModal) btnCloseProdsModal.addEventListener("click", closeVideoProductsModal);

  // Đóng modal khi bấm ra ngoài backdrop
  window.addEventListener("click", (e) => {
    if (e.target === modalEdit) closeEditModal();
    if (e.target === modalDelete) closeDeleteModal();
    if (e.target === modalVideoProds) closeVideoProductsModal();
  });
}