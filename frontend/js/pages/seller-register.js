// Trang Đăng ký bán hàng, theo dõi trạng thái đơn & thiết lập hồ sơ cửa hàng (Task T3D27D1)

const SERVER_BASE_URL = CONFIG.API_BASE_URL.replace(/\/api\/?$/, "");
const DEFAULT_LOGO_SVG =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='96' height='96'%3E%3Crect fill='%23dbeafe' width='96' height='96' rx='48'/%3E%3Ctext x='50%25' y='54%25' dominant-baseline='middle' text-anchor='middle' font-size='40'%3E🏪%3C/text%3E%3C/svg%3E";

// DOM Elements
const guestAuthCard = document.getElementById("guest-auth-card");
const sellerRegisterContent = document.getElementById("seller-register-content");
const demoApplicantBtn = document.getElementById("btn-demo-applicant");
const gotoSellerCenterBtn = document.getElementById("btn-goto-seller-center");

// Form gửi đơn đăng ký bán hàng
const appFormCard = document.getElementById("application-form-card");
const appFormHint = document.getElementById("application-form-hint");
const appForm = document.getElementById("seller-application-form");
const proposedNameInput = document.getElementById("proposed-shop-name");
const phoneInput = document.getElementById("applicant-phone");
const descInput = document.getElementById("applicant-description");
const submitAppBtn = document.getElementById("btn-submit-application");

// Form Tạo / Cập nhật Cửa hàng
const shopSetupCard = document.getElementById("shop-setup-card");
const shopSetupTitle = document.getElementById("shop-setup-title");
const shopProfileForm = document.getElementById("shop-profile-form");
const shopLogoPreview = document.getElementById("shop-logo-preview");
const shopLogoFileInput = document.getElementById("shop-logo-file");
const shopNameInput = document.getElementById("shop-name-input");
const shopAddressInput = document.getElementById("shop-address-input");
const shopDescInput = document.getElementById("shop-description-input");
const saveShopBtn = document.getElementById("btn-save-shop");
const viewPublicShopBtn = document.getElementById("btn-view-my-public-shop");

// Danh sách trạng thái đơn
const applicationsListContainer = document.getElementById("applications-list-container");
const refreshAppsBtn = document.getElementById("btn-refresh-applications");

// State
let currentUser = null;
let myApplications = [];
let myShop = null;
let selectedLogoFile = null;

function resolveAssetUrl(key) {
  if (!key) return DEFAULT_LOGO_SVG;
  if (key.startsWith("http://") || key.startsWith("https://") || key.startsWith("data:")) {
    return key;
  }
  return `${SERVER_BASE_URL}${key.startsWith("/") ? "" : "/"}${key}`;
}

function getStatusBadgeHtml(status) {
  if (status === "PENDING") {
    return `<span class="app-badge PENDING">⏳ Đang chờ duyệt (PENDING)</span>`;
  }
  if (status === "APPROVED") {
    return `<span class="app-badge APPROVED">✅ Đã duyệt (APPROVED)</span>`;
  }
  if (status === "REJECTED") {
    return `<span class="app-badge REJECTED">❌ Đã từ chối (REJECTED)</span>`;
  }
  return `<span class="app-badge">${escapeHtml(status)}</span>`;
}

// ---------- Khởi tạo & Kiểm tra phiên đăng nhập ----------
async function initPage() {
  const token = session.getToken();
  if (!token) {
    guestAuthCard.hidden = false;
    sellerRegisterContent.hidden = true;
    return;
  }

  try {
    currentUser = await api.get("/auth/me");
    session.setUser(currentUser);
    if (typeof renderLayout === "function") renderLayout();

    guestAuthCard.hidden = true;
    sellerRegisterContent.hidden = false;
    await loadMyApplicationsAndShop();
  } catch (error) {
    guestAuthCard.hidden = false;
    sellerRegisterContent.hidden = true;
  }
}

// Tạo nhanh tài khoản User để thử gửi đơn đăng ký bán hàng
if (demoApplicantBtn) {
  demoApplicantBtn.addEventListener("click", async () => {
    demoApplicantBtn.disabled = true;
    const rand = Math.floor(1000 + Math.random() * 9000);
    const username = `user_banhang_${rand}`;
    const password = "password123";

    try {
      await api.post("/auth/register", {
        email: `${username}@clipshop.ai`,
        username,
        password,
        display_name: `Người dùng ${rand}`,
      });
      const loginRes = await api.post("/auth/login", {
        identifier: username,
        password,
      });
      session.save(loginRes.access_token, null);
      showToast(`Đã tạo và đăng nhập tài khoản ${username}!`);
      await initPage();
    } catch (error) {
      showToast(error.message || "Không thể tạo tài khoản thử nghiệm", "error");
    } finally {
      demoApplicantBtn.disabled = false;
    }
  });
}

// ---------- Tải danh sách đơn đăng ký & thông tin Shop ----------
async function loadMyApplicationsAndShop() {
  applicationsListContainer.innerHTML = `<div class="muted">Đang tải trạng thái đơn...</div>`;

  try {
    myApplications = await api.get("/seller-applications/me");
  } catch (error) {
    myApplications = [];
  }

  const user = typeof session !== "undefined" ? session.getUser() : null;
  const hasApprovedApp = Array.isArray(myApplications) && myApplications.some((a) => a.status === "APPROVED");
  if ((user && user.role === "SELLER") || hasApprovedApp) {
    try {
      myShop = await api.get("/shops/me");
    } catch (_) {
      myShop = null;
    }
  } else {
    myShop = null;
  }

  renderApplicationsList();
  updateFormVisibility();
}

function renderApplicationsList() {
  if (!Array.isArray(myApplications) || myApplications.length === 0) {
    applicationsListContainer.innerHTML = `
      <div class="app-status-card">
        <strong>Bạn chưa gửi đơn đăng ký bán hàng nào.</strong>
        <div class="muted" style="margin-top: 4px;">
          Hãy điền thông tin ở biểu mẫu bên trái và bấm <strong>"Gửi đơn đăng ký bán hàng"</strong>.
        </div>
      </div>`;
    return;
  }

  applicationsListContainer.innerHTML = myApplications
    .map((app) => {
      const createdStr = formatDateTime(app.created_at);
      const reviewedStr = app.reviewed_at ? formatDateTime(app.reviewed_at) : null;

      return `
        <div class="app-status-card status-${escapeHtml(app.status)}">
          <div class="app-status-header">
            <strong>Đơn #${app.id} · ${escapeHtml(app.proposed_shop_name)}</strong>
            ${getStatusBadgeHtml(app.status)}
          </div>
          <div class="muted">
            📞 SĐT: <strong>${escapeHtml(app.phone)}</strong> · 🕒 Ngày gửi: ${createdStr}
            ${reviewedStr ? ` · ✔ Ngày duyệt: ${reviewedStr}` : ""}
          </div>
          <div style="margin-top: 8px; font-size: 14px;">
            ${escapeHtml(app.description)}
          </div>
          ${
            app.status === "REJECTED" && app.rejection_reason
              ? `<div class="app-rejection-box">
                   <strong>Lý do từ chối:</strong> ${escapeHtml(app.rejection_reason)}
                 </div>`
              : ""
          }
        </div>`;
    })
    .join("");
}

function updateFormVisibility() {
  const hasPending = myApplications.some((a) => a.status === "PENDING");
  const approvedApp = myApplications.find((a) => a.status === "APPROVED");
  const isApprovedSeller =
    (currentUser && currentUser.role === "SELLER") || !!approvedApp || !!myShop;

  gotoSellerCenterBtn.hidden = !isApprovedSeller;

  if (isApprovedSeller) {
    // Đã được duyệt -> Hiển thị form Tạo / Sửa cửa hàng
    shopSetupCard.hidden = false;
    submitAppBtn.disabled = true;
    submitAppBtn.textContent = "Tài khoản đã là Người bán (SELLER)";
    appFormHint.innerHTML =
      "🎉 <strong>Chúc mừng!</strong> Đơn đăng ký của bạn đã được duyệt. Bạn có thể tạo hoặc cập nhật thông tin cửa hàng ở khung bên dưới.";

    if (myShop) {
      shopSetupTitle.textContent = `🏪 Cập nhật Cửa hàng: ${myShop.name}`;
      shopNameInput.value = myShop.name || "";
      shopAddressInput.value = myShop.address || "";
      shopDescInput.value = myShop.description || "";
      shopLogoPreview.src = resolveAssetUrl(myShop.avatar_key);
      saveShopBtn.textContent = "💾 Lưu cập nhật Cửa hàng";
      viewPublicShopBtn.href = `shop-public.html?shop_id=${myShop.id}`;
      viewPublicShopBtn.hidden = false;
    } else {
      shopSetupTitle.textContent = "🏪 Tạo Cửa hàng mới của bạn";
      shopNameInput.value = approvedApp ? approvedApp.proposed_shop_name : "";
      shopDescInput.value = approvedApp ? approvedApp.description : "";
      shopLogoPreview.src = DEFAULT_LOGO_SVG;
      saveShopBtn.textContent = "🚀 Tạo Cửa hàng ngay";
      viewPublicShopBtn.hidden = true;
    }
    return;
  }

  shopSetupCard.hidden = true;

  if (hasPending) {
    submitAppBtn.disabled = true;
    submitAppBtn.textContent = "⏳ Đang có đơn chờ Admin xét duyệt";
    appFormHint.innerHTML =
      "⚠️ Bạn đang có <strong>1 đơn ở trạng thái chờ duyệt (PENDING)</strong>. Vui lòng đợi kết quả xét duyệt trước khi gửi đơn khác.";
  } else {
    submitAppBtn.disabled = false;
    submitAppBtn.textContent = "📨 Gửi đơn đăng ký bán hàng";
    appFormHint.textContent =
      "Mỗi tài khoản chỉ gửi 1 đơn đang chờ duyệt (PENDING). Nếu đơn trước bị từ chối, bạn có thể chỉnh sửa thông tin và gửi lại.";
  }
}

// ---------- Xử lý gửi đơn đăng ký bán hàng ----------
appForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const proposed_shop_name = proposedNameInput.value.trim();
  const phone = phoneInput.value.trim();
  const description = descInput.value.trim();

  if (!proposed_shop_name) {
    showToast("Vui lòng nhập tên cửa hàng dự kiến", "error");
    return;
  }
  if (!/^\+?[0-9]{10,15}$/.test(phone)) {
    showToast("Số điện thoại phải gồm 10–15 chữ số hợp lệ", "error");
    return;
  }
  if (!description) {
    showToast("Vui lòng nhập mô tả cửa hàng", "error");
    return;
  }

  submitAppBtn.disabled = true;
  try {
    await api.post("/seller-applications", {
      proposed_shop_name,
      phone,
      description,
    });
    showToast("Đã gửi đơn đăng ký bán hàng thành công!");
    appForm.reset();
    await loadMyApplicationsAndShop();
  } catch (error) {
    showToast(error.message, "error");
    submitAppBtn.disabled = false;
  }
});

// ---------- Xem trước Logo & Lưu thông tin Cửa hàng ----------
shopLogoFileInput.addEventListener("change", (event) => {
  const file = event.target.files && event.target.files[0];
  if (!file) return;
  selectedLogoFile = file;
  shopLogoPreview.src = URL.createObjectURL(file);
});

shopProfileForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const name = shopNameInput.value.trim();
  const address = shopAddressInput.value.trim() || null;
  const description = shopDescInput.value.trim() || null;

  if (!name) {
    showToast("Tên cửa hàng không được để trống", "error");
    return;
  }

  saveShopBtn.disabled = true;
  try {
    if (!myShop) {
      myShop = await api.post("/shops", { name, address, description });
    } else {
      myShop = await api.put(`/shops/${myShop.id}`, {
        name,
        address,
        description,
      });
    }

    if (selectedLogoFile) {
      const formData = new FormData();
      formData.append("file", selectedLogoFile);
      myShop = await api.upload(`/shops/${myShop.id}/logo`, formData);
      selectedLogoFile = null;
      shopLogoFileInput.value = "";
    }

    showToast("Đã lưu thông tin cửa hàng thành công!");
    await loadMyApplicationsAndShop();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    saveShopBtn.disabled = false;
  }
});

// ---------- Nút làm mới ----------
refreshAppsBtn.addEventListener("click", loadMyApplicationsAndShop);


initPage();
