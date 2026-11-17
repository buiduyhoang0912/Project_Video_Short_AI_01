// Layout chung: tự chèn header (menu) và footer vào mọi trang, đồng thời kiểm tra quyền truy cập trang.
//
// Khai báo trên <body> của trang cần bảo vệ:
//   data-auth="required"        -> phải đăng nhập
//   data-auth="self"            -> phải đăng nhập, trừ khi URL có ?id= (xem hồ sơ công khai)
//   data-roles="SELLER"         -> phải đăng nhập và đúng role (nhiều role: "SELLER,ADMIN")

// access: "all" = mọi người | "auth" = đã đăng nhập | "role:X" = chỉ role X
const MENU = [
  { href: "pages/feed.html", label: "🔥 Dành cho bạn", access: "all", id: "for-you" },
  { href: "pages/feed.html?tab=following", label: "👥 Đang theo dõi", access: "auth", id: "following" },
  { href: "pages/search.html", label: "🔍 Tìm kiếm", access: "all" },
  { href: "pages/shop.html", label: "🏬 Shop", access: "all" },
  { href: "pages/cart.html", label: "🛒 Giỏ hàng", access: "auth" },
  { href: "pages/profile.html", label: "👤 Hồ sơ cá nhân", access: "auth", id: "profile" },
  { href: "pages/seller.html", label: "🧾 Seller Center", access: "role:SELLER" },
  { href: "pages/admin.html", label: "🛡️ Admin", access: "role:ADMIN" },
];

function getCurrentUser() {
  return session.getUser();
}

function canSee(access, user) {
  if (access === "all") return true;
  if (!user) return false;
  if (access === "auth") return true;
  if (access.startsWith("role:")) return user.role === access.slice(5);
  return false;
}

function isMenuActive(item, user) {
  const path = window.location.pathname;
  const params = new URLSearchParams(window.location.search);
  const file = item.href.split("?")[0];
  if (file === "pages/seller.html" && path.endsWith("/pages/seller-center.html")) {
    return true;
  }
  if (!path.endsWith("/" + file)) return false;
  if (item.id === "following") return params.get("tab") === "following";
  if (item.id === "for-you") return params.get("tab") !== "following";
  if (item.id === "profile") return !params.get("id") || (user && String(user.id) === params.get("id"));
  return true;
}

function roleLabel(role) {
  return { USER: "Người dùng", SELLER: "Seller", ADMIN: "Admin" }[role] || role;
}

function renderLayout() {
  const root = document.body.dataset.root || "./";
  const user = session.getToken() ? session.getUser() : null;

  const links = MENU.filter((item) => canSee(item.access, user))
    .map((item) => {
      const active = isMenuActive(item, user);
      return `<a href="${root}${item.href}" class="${active ? "active" : ""}"${active ? ' aria-current="page"' : ""}>${item.label}</a>`;
    })
    .join("");

  const authHtml = user
    ? `<div class="header-user">
         <span class="user-greeting">Hi, <strong>${escapeHtml(user.display_name || user.username)}</strong>
           <span class="role-badge role-${escapeHtml(user.role)}">${escapeHtml(roleLabel(user.role))}</span></span>
         <button id="btn-header-logout" class="btn btn-small">Đăng xuất</button>
       </div>`
    : `<a href="${loginUrlFromRoot(root)}" class="btn btn-small">Đăng nhập</a>
       <a href="${root}pages/register.html" class="btn btn-primary btn-small">Đăng ký</a>`;

  const headerEl = document.getElementById("app-header");
  if (headerEl) {
    headerEl.innerHTML = `
      <div class="container header-inner">
        <a href="${root}pages/feed.html" class="brand">
          <img src="${root}assets/images/logo.svg" alt="logo" width="28" height="28">
          <span>ClipShop AI</span>
        </a>
        <div class="header-right">${authHtml}</div>
        <nav class="nav" aria-label="Menu chính">${links}</nav>
      </div>`;

    const btnLogout = document.getElementById("btn-header-logout");
    if (btnLogout) btnLogout.addEventListener("click", logout);
  }

  const footerEl = document.getElementById("app-footer");
  if (footerEl) {
    footerEl.innerHTML = `
      <div class="container">© ${new Date().getFullYear()} ClipShop AI · Nền tảng video ngắn & thương mại điện tử</div>`;
  }
}

function loginUrlFromRoot() {
  return loginUrl();
}

// Đăng xuất: gọi POST /auth/logout, rồi xóa token + thông tin người dùng (kể cả khi gọi API lỗi)
async function logout() {
  const btn = document.getElementById("btn-header-logout");
  if (btn) btn.disabled = true;
  try {
    await api.post("/auth/logout");
  } catch (e) {
    // token đã hết hạn/đã logout cũng coi như đăng xuất xong
  }
  session.clear();
  const root = document.body.dataset.root || "./";
  window.location.href = `${root}pages/feed.html`;
}

// Các trang cũ gọi showLoginModal() khi khách thao tác cần đăng nhập -> chuyển sang trang đăng nhập
function showLoginModal() {
  window.location.href = loginUrl();
}

// Trang đích sau khi đăng nhập: ưu tiên ?next=, nếu không thì theo role
function pageAfterLogin(user) {
  const root = document.body.dataset.root || "./";
  const next = new URLSearchParams(window.location.search).get("next");
  if (next && /^[\w\-\/]+\.html(\?[\w=&%\-]*)?$/.test(next)) return `${root}${next}`;
  if (user.role === "ADMIN") return `${root}pages/admin.html`;
  if (user.role === "SELLER") return `${root}pages/seller.html`;
  return `${root}pages/feed.html`;
}

function showAccessDenied(message, user) {
  const main = document.querySelector("main");
  const root = document.body.dataset.root || "./";
  if (main) {
    main.innerHTML = `
      <section class="card access-denied">
        <h2>🚫 Không đủ quyền truy cập</h2>
        <p>${escapeHtml(message)}</p>
        <a class="btn btn-primary" href="${root}pages/feed.html">Về trang chủ</a>
      </section>`;
  }
  document.body.classList.remove("auth-checking");
}

// Lỗi khi xác nhận phiên (mạng/500): vẫn chặn nội dung riêng, hiện thông báo + nút thử lại
function showGuardError(message) {
  const main = document.querySelector("main");
  if (main) {
    main.innerHTML = `
      <section class="card access-denied">
        <h2>⚠️ Không xác nhận được phiên đăng nhập</h2>
        <p>${escapeHtml(message)}</p>
        <button type="button" class="btn btn-primary" id="btn-guard-retry">Thử lại</button>
      </section>`;
    document.getElementById("btn-guard-retry").addEventListener("click", () => window.location.reload());
  }
  document.body.classList.remove("auth-checking"); // main chỉ còn thông báo lỗi, không còn nội dung riêng
}

// Kiểm tra quyền trang: xác nhận phiên bằng GET /auth/me rồi mới hiện nội dung riêng
async function guardPage() {
  const needs = pageNeedsAuth();
  const token = session.getToken();

  if (needs) document.body.classList.add("auth-checking");
  if (needs && !token) {
    window.location.href = loginUrl();
    return;
  }
  if (!token) return;

  try {
    const me = await api.get("/auth/me");
    session.setUser(me);
    renderLayout(); // cập nhật menu theo role mới nhất từ server
    const roles = (document.body.dataset.roles || "").split(",").map((s) => s.trim()).filter(Boolean);
    if (roles.length && !roles.includes(me.role)) {
      showAccessDenied(`Trang này chỉ dành cho: ${roles.join(", ")}. Tài khoản của bạn là ${me.role}.`, me);
      return;
    }
    document.body.classList.remove("auth-checking");
  } catch (err) {
    // 401 và 403(khóa) đã được interceptor xóa phiên + chuyển trang; còn lại là lỗi mạng/server (500...)
    if (!needs) {
      renderLayout();
    } else if (err.status !== 401 && !(err.status === 403 && /kh[oó]a/i.test(err.message))) {
      showGuardError(err.status === 0
        ? "Không kiểm tra được phiên đăng nhập do mất kết nối."
        : `Không kiểm tra được phiên đăng nhập (lỗi ${err.status}). Vui lòng thử lại sau.`);
    }
  }
}

renderLayout();
guardPage();
