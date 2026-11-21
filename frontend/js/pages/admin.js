// Trang quản trị: Đơn đăng ký bán hàng + Tài khoản + Điều hướng Tab.
// Backend kiểm tra quyền ADMIN; data-roles="ADMIN" ở <body> để kiểm tra ở layout frontend.

const APP_STATUS = {
  PENDING: { label: "Chờ duyệt", cls: "badge-pending" },
  APPROVED: { label: "Đã duyệt", cls: "badge-approved" },
  REJECTED: { label: "Từ chối", cls: "badge-rejected" },
};
const USER_STATUS = {
  ACTIVE: { label: "Hoạt động", cls: "badge-active" },
  LOCKED: { label: "Bị khoá", cls: "badge-locked" },
};

const $ = (id) => document.getElementById(id);
let rejectingId = null;
let currentAdminId = null;

// ---------- Chuyển mục ----------
const ADMIN_TABS = ["dashboard", "applications", "users", "videos", "products"];
// Mỗi mục đăng ký hàm tải dữ liệu; admin-moderation.js và admin-dashboard.js bổ sung thêm.
const adminTabLoaders = {
  applications: () => loadApplications(),
  users: () => loadUsers(),
};

function showTab(name) {
  document.querySelectorAll(".admin-tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  ADMIN_TABS.forEach((t) => {
    const el = $(`tab-${t}`);
    if (el) el.hidden = t !== name;
  });
  if (adminTabLoaders[name]) adminTabLoaders[name]();
}

// ---------- Đơn đăng ký ----------
async function loadApplications() {
  const body = $("app-body");
  try {
    const status = $("app-status-filter").value;
    const list = await api.get("/admin/seller-applications", status ? { status } : undefined);
    if (!list.length) {
      body.innerHTML = `<tr><td colspan="4" class="muted">Không có đơn nào.</td></tr>`;
      return;
    }
    body.innerHTML = list.map(renderApplication).join("");
  } catch (err) {
    body.innerHTML = `<tr><td colspan="4" class="muted">${escapeHtml(err.message)}</td></tr>`;
  }
}

function renderApplication(a) {
  const st = APP_STATUS[a.status] || { label: a.status, cls: "" };
  const actions = a.status === "PENDING"
    ? `<div class="admin-actions">
         <button class="btn btn-primary btn-small" data-action="approve" data-id="${a.id}">Duyệt</button>
         <button class="btn btn-danger btn-small" data-action="reject" data-id="${a.id}"
                 data-name="${escapeAttr(a.applicant.username)}">Từ chối</button>
       </div>`
    : `<span class="muted">Đã xử lý</span>`;
  const reason = a.status === "REJECTED" && a.rejection_reason
    ? `<div class="muted">Lý do: ${escapeHtml(a.rejection_reason)}</div>` : "";
  return `<tr>
    <td><strong>${escapeHtml(a.applicant.display_name)}</strong>
        <div class="muted">@${escapeHtml(a.applicant.username)}</div>
        <div class="muted">${escapeHtml(a.applicant.email)}</div></td>
    <td class="app-desc"><strong>${escapeHtml(a.proposed_shop_name)}</strong>
        <div class="muted">SĐT: ${escapeHtml(a.phone)}</div>
        <div>${escapeHtml(a.description)}</div>
        <div class="muted">Gửi lúc ${escapeHtml(formatDateTime(a.created_at))}</div></td>
    <td><span class="badge ${st.cls}">${st.label}</span>${reason}</td>
    <td>${actions}</td>
  </tr>`;
}

async function approveApplication(id, btn) {
  if (!confirm("Duyệt đơn này và cấp quyền SELLER cho tài khoản?")) return;
  btn.disabled = true;
  try {
    await api.patch(`/admin/seller-applications/${id}/approve`);
    showToast("Đã duyệt đơn, tài khoản được cấp quyền SELLER.");
  } catch (err) {
    showToast(err.message, "error");
  }
  loadApplications();
}

function openRejectModal(id, name) {
  rejectingId = id;
  $("reject-target").textContent = `Người đăng ký: @${name}`;
  $("reject-reason").value = "";
  $("reject-error").hidden = true;
  $("reject-modal").hidden = false;
  $("reject-reason").focus();
}

function closeRejectModal() {
  $("reject-modal").hidden = true;
  rejectingId = null;
}

async function submitReject(e) {
  e.preventDefault();
  const reason = $("reject-reason").value.trim();
  const errBox = $("reject-error");
  if (!reason) {
    errBox.textContent = "Vui lòng nhập lý do từ chối.";
    errBox.hidden = false;
    return;
  }
  $("reject-submit").disabled = true;
  try {
    await api.patch(`/admin/seller-applications/${rejectingId}/reject`, { rejection_reason: reason });
    closeRejectModal();
    showToast("Đã từ chối đơn đăng ký.");
    loadApplications();
  } catch (err) {
    const fieldErr = getFieldErrors(err).rejection_reason;
    errBox.textContent = fieldErr || err.message;
    errBox.hidden = false;
    if (err.status === 409 || err.status === 404) loadApplications();
  } finally {
    $("reject-submit").disabled = false;
  }
}

// ---------- Tài khoản ----------
async function loadUsers() {
  const body = $("user-body");
  try {
    const search = $("user-search").value.trim();
    const list = await api.get("/admin/users", search ? { search } : undefined);
    if (!list.length) {
      body.innerHTML = `<tr><td colspan="6" class="muted">Không tìm thấy tài khoản nào.</td></tr>`;
      return;
    }
    body.innerHTML = list.map(renderUser).join("");
  } catch (err) {
    body.innerHTML = `<tr><td colspan="6" class="muted">${escapeHtml(err.message)}</td></tr>`;
  }
}

function renderUser(u) {
  const st = USER_STATUS[u.status] || { label: u.status, cls: "" };
  let action;
  if (u.id === currentAdminId) {
    action = `<span class="muted">Tài khoản của bạn</span>`;
  } else if (u.status === "ACTIVE") {
    action = `<button class="btn btn-danger btn-small" data-action="lock" data-id="${u.id}"
                      data-name="${escapeAttr(u.username)}">Khoá</button>`;
  } else {
    action = `<button class="btn btn-primary btn-small" data-action="unlock" data-id="${u.id}"
                      data-name="${escapeAttr(u.username)}">Mở khoá</button>`;
  }
  return `<tr>
    <td>${escapeHtml(u.username)}</td>
    <td>${escapeHtml(u.display_name)}</td>
    <td>${escapeHtml(u.email)}</td>
    <td><span class="badge badge-role">${escapeHtml(u.role)}</span></td>
    <td><span class="badge ${st.cls}">${st.label}</span></td>
    <td>${action}</td>
  </tr>`;
}

async function changeUserStatus(id, name, action, btn) {
  const lock = action === "lock";
  if (lock && !confirm(`Khoá tài khoản @${name}? Người này sẽ không đăng nhập/dùng API được.`)) return;
  btn.disabled = true;
  try {
    await api.patch(`/admin/users/${id}/${action}`);
    showToast(lock ? `Đã khoá tài khoản @${name}.` : `Đã mở khoá tài khoản @${name}.`);
  } catch (err) {
    showToast(err.message, "error");
  }
  loadUsers();
}

// ---------- Khởi tạo ----------
document.addEventListener("DOMContentLoaded", () => {
  const me = session.getUser();
  currentAdminId = me ? me.id : null;

  document.querySelectorAll(".admin-tab").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));
  $("app-status-filter").addEventListener("change", loadApplications);

  $("app-body").addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;
    if (btn.dataset.action === "approve") approveApplication(btn.dataset.id, btn);
    else openRejectModal(btn.dataset.id, btn.dataset.name);
  });

  $("reject-form").addEventListener("submit", submitReject);
  $("reject-cancel").addEventListener("click", closeRejectModal);

  $("user-search-form").addEventListener("submit", (e) => { e.preventDefault(); loadUsers(); });
  $("user-search-clear").addEventListener("click", () => { $("user-search").value = ""; loadUsers(); });
  $("user-body").addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-action]");
    if (btn) changeUserStatus(btn.dataset.id, btn.dataset.name, btn.dataset.action, btn);
  });

  // Tải tab đang active (mặc định Dashboard)
  const activeBtn = document.querySelector(".admin-tab.active");
  const tabName = activeBtn ? activeBtn.dataset.tab : "dashboard";
  showTab(tabName);
});
