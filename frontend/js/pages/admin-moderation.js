// Kiểm duyệt video & sản phẩm (T3D201D). Dùng chung hàm của admin.js ($, api, showToast...).

const MOD_STATUS = {
  VISIBLE: { label: "Đang hiển thị", cls: "badge-active" },
  ACTIVE: { label: "Đang bán", cls: "badge-active" },
  HIDDEN: { label: "Đã ẩn vi phạm", cls: "badge-locked" },
  INACTIVE: { label: "Ngừng kinh doanh", cls: "badge-pending" },
};

let hideTarget = null; // { kind: "videos" | "products", id }

function modBadge(status) {
  const st = MOD_STATUS[status] || { label: status, cls: "" };
  return `<span class="badge ${st.cls}">${st.label}</span>`;
}

function modReason(item) {
  if (!item.moderation_reason) return "";
  const time = item.moderated_at ? ` (${formatDateTime(item.moderated_at)})` : "";
  return `<div class="reason">⚠️ <strong>Lý do ẩn:</strong> ${escapeHtml(item.moderation_reason)}${time}</div>`;
}

// ---------- Video ----------
async function loadVideos() {
  const body = $("video-body");
  try {
    const status = $("video-status-filter").value;
    const search = $("video-search").value.trim();
    const params = {};
    if (status) params.status = status;
    if (search) params.search = search;
    const list = await api.get("/admin/videos", params);
    body.innerHTML = list.length
      ? list.map(renderVideoRow).join("")
      : `<tr><td colspan="5" class="muted">Không có video nào.</td></tr>`;
  } catch (err) {
    body.innerHTML = `<tr><td colspan="5" class="muted">${escapeHtml(err.message)}</td></tr>`;
  }
}

function renderVideoRow(v) {
  const action = v.status === "HIDDEN"
    ? `<button class="btn btn-primary btn-small" data-action="show" data-id="${v.id}">Hiện lại</button>`
    : `<button class="btn btn-danger btn-small" data-action="hide" data-id="${v.id}"
               data-name="${escapeAttr(v.title)}">Ẩn vi phạm</button>`;
  return `<tr>
    <td><strong>${escapeHtml(v.title)}</strong><div class="muted">#${v.id} · Đăng lúc ${escapeHtml(formatDateTime(v.created_at))}</div></td>
    <td>${escapeHtml(v.owner.display_name)}<div class="muted">@${escapeHtml(v.owner.username)}</div></td>
    <td>${v.view_count}</td>
    <td>${modBadge(v.status)}${modReason(v)}</td>
    <td>${action}</td>
  </tr>`;
}

// ---------- Sản phẩm ----------
async function loadProducts() {
  const body = $("product-body");
  try {
    const status = $("product-status-filter").value;
    const search = $("product-search").value.trim();
    const params = {};
    if (status) params.status = status;
    if (search) params.search = search;
    const list = await api.get("/admin/products", params);
    body.innerHTML = list.length
      ? list.map(renderProductRow).join("")
      : `<tr><td colspan="6" class="muted">Không có sản phẩm nào.</td></tr>`;
  } catch (err) {
    body.innerHTML = `<tr><td colspan="6" class="muted">${escapeHtml(err.message)}</td></tr>`;
  }
}

function renderProductRow(p) {
  const action = p.status === "HIDDEN"
    ? `<button class="btn btn-primary btn-small" data-action="show" data-id="${p.id}">Hiện lại</button>`
    : `<button class="btn btn-danger btn-small" data-action="hide" data-id="${p.id}"
               data-name="${escapeAttr(p.name)}">Ẩn vi phạm</button>`;

  const thumbHtml = p.thumbnail_url
    ? `<img src="${escapeHtml(p.thumbnail_url)}" alt="${escapeHtml(p.name)}" class="table-thumb" onerror="this.src='../assets/images/logo.svg'">`
    : `<div class="table-thumb-placeholder">🛍️</div>`;

  return `<tr>
    <td>${thumbHtml}</td>
    <td><strong>${escapeHtml(p.name)}</strong><div class="muted">#${p.id}</div></td>
    <td>${escapeHtml(p.shop_name)}</td>
    <td>${escapeHtml(formatMoney(p.price))}</td>
    <td>${modBadge(p.status)}${modReason(p)}</td>
    <td>${action}</td>
  </tr>`;
}

// ---------- Ẩn / Hiện ----------
function reloadKind(kind) {
  return kind === "videos" ? loadVideos() : loadProducts();
}

async function showAgain(kind, id, btn) {
  if (!confirm("Bỏ ẩn và cho phép nội dung này hiển thị công khai trở lại?")) return;
  btn.disabled = true;
  try {
    const targetStatus = kind === "videos" ? "VISIBLE" : "ACTIVE";
    await api.patch(`/admin/${kind}/${id}/visibility`, { status: targetStatus });
    showToast("Đã hiển thị lại nội dung.");
  } catch (err) {
    showToast(err.message, "error");
  }
  reloadKind(kind);
}

function openHideModal(kind, id, name) {
  hideTarget = { kind, id };
  $("hide-title").textContent = kind === "videos" ? "Ẩn video vi phạm" : "Ẩn sản phẩm vi phạm";
  $("hide-target").textContent = `Đối tượng: ${name}`;
  $("hide-reason").value = "";
  $("hide-error").hidden = true;
  $("hide-modal").hidden = false;
  $("hide-reason").focus();
}

function closeHideModal() {
  $("hide-modal").hidden = true;
  hideTarget = null;
}

async function submitHide(e) {
  e.preventDefault();
  const reason = $("hide-reason").value.trim();
  const errBox = $("hide-error");
  if (!reason) {
    errBox.textContent = "Vui lòng nhập lý do ẩn nội dung vi phạm.";
    errBox.hidden = false;
    return;
  }
  const { kind, id } = hideTarget;
  $("hide-submit").disabled = true;
  try {
    await api.patch(`/admin/${kind}/${id}/visibility`, { status: "HIDDEN", reason });
    closeHideModal();
    showToast("Đã ẩn nội dung vi phạm thành công.");
    reloadKind(kind);
  } catch (err) {
    errBox.textContent = getFieldErrors(err).reason || err.message;
    errBox.hidden = false;
    if (err.status === 409 || err.status === 404) reloadKind(kind);
  } finally {
    $("hide-submit").disabled = false;
  }
}

adminTabLoaders.videos = loadVideos;
adminTabLoaders.products = loadProducts;

document.addEventListener("DOMContentLoaded", () => {
  $("video-search-form").addEventListener("submit", (e) => { e.preventDefault(); loadVideos(); });
  $("video-status-filter").addEventListener("change", loadVideos);
  $("product-search-form").addEventListener("submit", (e) => { e.preventDefault(); loadProducts(); });
  $("product-status-filter").addEventListener("change", loadProducts);

  for (const [bodyId, kind] of [["video-body", "videos"], ["product-body", "products"]]) {
    $(bodyId).addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-action]");
      if (!btn) return;
      if (btn.dataset.action === "hide") openHideModal(kind, btn.dataset.id, btn.dataset.name);
      else showAgain(kind, btn.dataset.id, btn);
    });
  }

  $("hide-form").addEventListener("submit", submitHide);
  $("hide-cancel").addEventListener("click", closeHideModal);
});
