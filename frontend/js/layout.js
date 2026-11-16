// Layout chung: tự chèn header (menu) và footer vào mọi trang

const MENU = [
  { href: "index.html", label: "Trang chủ" },
  { href: "pages/feed.html", label: "🔥 Feed Video" },
  { href: "pages/profile.html", label: "👤 Hồ sơ" },
  { href: "pages/items.html", label: "Items (Mẫu)" },
];

function getCurrentUser() {
  try {
    const raw = localStorage.getItem("current_user");
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

function renderLayout() {
  const root = document.body.dataset.root || "./";
  const currentPath = window.location.pathname;

  const links = MENU.map((item) => {
    const isActive =
      currentPath.endsWith("/" + item.href) ||
      (item.href === "index.html" && (currentPath.endsWith("/") || currentPath.endsWith("/index.html")));
    return `<a href="${root}${item.href}" class="${isActive ? "active" : ""}">${item.label}</a>`;
  }).join("");

  const user = getCurrentUser();
  const token = localStorage.getItem("token") || localStorage.getItem("access_token");

  let authHtml = "";
  if (token && user) {
    authHtml = `
      <div class="header-user">
        <span class="user-greeting">Hi, <strong>${user.display_name || user.username}</strong></span>
        <button id="btn-header-logout" class="btn btn-small">Đăng xuất</button>
      </div>
    `;
  } else {
    authHtml = `
      <button id="btn-quick-login" class="btn btn-primary btn-small">Đăng nhập</button>
    `;
  }

  const headerEl = document.getElementById("app-header");
  if (headerEl) {
    headerEl.innerHTML = `
      <div class="container header-inner">
        <a href="${root}pages/feed.html" class="brand">
          <img src="${root}assets/images/logo.svg" alt="logo" width="28" height="28">
          <span>ClipShop AI</span>
        </a>
        <nav class="nav">${links}</nav>
        <div class="header-right">${authHtml}</div>
      </div>`;

    const btnLogout = document.getElementById("btn-header-logout");
    if (btnLogout) {
      btnLogout.addEventListener("click", () => {
        localStorage.removeItem("token");
        localStorage.removeItem("access_token");
        localStorage.removeItem("current_user");
        window.location.reload();
      });
    }

    const btnLogin = document.getElementById("btn-quick-login");
    if (btnLogin) {
      btnLogin.addEventListener("click", () => {
        showLoginModal();
      });
    }
  }

  const footerEl = document.getElementById("app-footer");
  if (footerEl) {
    footerEl.innerHTML = `
      <div class="container">© ${new Date().getFullYear()} ClipShop AI · Nền tảng video ngắn & thương mại điện tử</div>`;
  }
}

function showLoginModal() {
  let modal = document.getElementById("global-login-modal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "global-login-modal";
    modal.className = "modal-overlay";
    modal.innerHTML = `
      <div class="modal-card">
        <div class="modal-header">
          <h3>Đăng nhập nhanh</h3>
          <button class="modal-close-btn" onclick="document.getElementById('global-login-modal').classList.remove('active')">&times;</button>
        </div>
        <div class="modal-body">
          <div style="margin-bottom:12px;">
            <label>Tài khoản (Username hoặc Email):</label>
            <input type="text" id="modal-login-user" value="seller01" placeholder="vd: user01, seller01">
          </div>
          <div style="margin-bottom:16px;">
            <label>Mật khẩu:</label>
            <input type="password" id="modal-login-pass" value="123456" placeholder="Mật khẩu">
          </div>
          <div id="modal-login-error" style="color:var(--color-danger);font-size:13px;margin-bottom:10px;display:none;"></div>
          <button id="modal-login-submit" class="btn btn-primary" style="width:100%;">Đăng nhập</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    document.getElementById("modal-login-submit").addEventListener("click", async () => {
      const u = document.getElementById("modal-login-user").value.trim();
      const p = document.getElementById("modal-login-pass").value;
      const errEl = document.getElementById("modal-login-error");
      try {
        const res = await api.post("/auth/login", { identifier: u, password: p });
        localStorage.setItem("token", res.access_token);
        localStorage.setItem("access_token", res.access_token);
        // Lấy thông tin user
        const me = await api.get("/auth/me");
        localStorage.setItem("current_user", JSON.stringify(me));
        modal.classList.remove("active");
        window.location.reload();
      } catch (err) {
        errEl.innerText = err.message || "Đăng nhập thất bại";
        errEl.style.display = "block";
      }
    });
  }
  modal.classList.add("active");
}

renderLayout();
