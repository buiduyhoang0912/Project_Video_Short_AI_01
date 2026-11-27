// Layout chung: tự chèn header (menu) và footer vào mọi trang, đồng thời kiểm tra quyền truy cập trang.
//
// Khai báo trên <body> của trang cần bảo vệ:
//   data-auth="required"        -> phải đăng nhập
//   data-auth="self"            -> phải đăng nhập, trừ khi URL có ?id= / ?user_id= / ?username= (xem hồ sơ công khai)
//   data-roles="SELLER"         -> phải đăng nhập và đúng role (nhiều role: "SELLER,ADMIN")

// access: "all" = mọi người | "auth" = đã đăng nhập | "role:X" = chỉ role X
const MENU = [
  { href: "pages/feed.html", label: "🔥 Dành cho bạn", access: "all", id: "for-you" },
  { href: "pages/feed.html?tab=following", label: "👥 Đang theo dõi", access: "auth", id: "following" },
  { href: "pages/search.html", label: "🔍 Tìm kiếm", access: "all" },
  { href: "pages/shop.html", label: "🏬 Shop", access: "all" },
  { href: "pages/shop-public.html", label: "🏪 Cửa hàng", access: "all" },
  { href: "pages/cart.html", label: "🛒 Giỏ hàng", access: "auth" },
  { href: "pages/upload.html", label: "➕ Đăng video", access: "auth", id: "upload" },
  { href: "pages/my-videos.html", label: "🎬 Video của tôi", access: "auth", id: "my-videos" },
  { href: "pages/profile.html", label: "👤 Hồ sơ cá nhân", access: "auth", id: "profile" },
  { href: "pages/seller-register.html", label: "📝 Đăng ký bán", access: "auth" },
  { href: "pages/seller.html", label: "🧾 Seller Center", access: "role:SELLER" },
  { href: "pages/admin.html", label: "🛡️ Admin", access: "role:ADMIN" },
];

// TASK T3D2BAD: Biến lưu timer polling thông báo (phải khai báo trước khi renderLayout() chạy)
let notifPollingTimer = null;

function resolveRootPrefix() {
  if (typeof getRootPrefix === "function") return getRootPrefix();
  if (document.body && document.body.dataset.root) return document.body.dataset.root;
  return window.location.pathname.includes("/pages/") ? "../" : "./";
}

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
  if (item.id === "profile") {
    const byId = params.get("id") || params.get("user_id");
    const byName = params.get("username");
    if (byName) return !!(user && user.username === byName.toLowerCase());
    return !byId || (user && String(user.id) === byId);
  }
  return true;
}

function roleLabel(role) {
  return { USER: "Người dùng", SELLER: "Seller", ADMIN: "Admin" }[role] || role;
}

function renderLayout() {
  const root = resolveRootPrefix();
  const user = session.getToken() ? session.getUser() : null;

  const links = MENU.filter((item) => canSee(item.access, user))
    .map((item) => {
      const active = isMenuActive(item, user);
      return `<a href="${root}${item.href}" class="${active ? "active" : ""}"${active ? ' aria-current="page"' : ""}>${item.label}</a>`;
    })
    .join("");

  const authHtml = user
    ? `<div class="header-user">
         <div class="notif-bell-container" id="notif-bell-container">
           <button id="btn-notif-bell" class="btn-notif-bell" type="button" aria-label="Thông báo" title="Thông báo">
             <span class="bell-icon">🔔</span>
             <span id="notif-badge" class="notif-badge" style="display: none;">0</span>
           </button>
           <div id="notif-dropdown" class="notif-dropdown" style="display: none;">
             <div class="notif-header">
               <div class="notif-header-title">🔔 Thông báo</div>
               <button id="btn-notif-read-all" class="btn-notif-read-all" type="button">Đọc tất cả</button>
             </div>
             <div id="notif-list" class="notif-list">
               <div class="notif-empty">Đang tải...</div>
             </div>
           </div>
         </div>
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

    if (user) {
      initNotificationBell();
    }
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
  if (notifPollingTimer) clearInterval(notifPollingTimer);
  const btn = document.getElementById("btn-header-logout");
  if (btn) btn.disabled = true;
  try {
    await api.post("/auth/logout");
  } catch (e) {
    // token đã hết hạn/đã logout cũng coi như đăng xuất xong
  }
  session.clear();
  const root = resolveRootPrefix();
  window.location.href = `${root}pages/feed.html`;
}

// Các trang cũ gọi showLoginModal() khi khách thao tác cần đăng nhập -> chuyển sang trang đăng nhập
function showLoginModal() {
  window.location.href = loginUrl();
}

// Trang đích sau khi đăng nhập: ưu tiên ?next=, nếu không thì theo role
function pageAfterLogin(user) {
  const root = resolveRootPrefix();
  const next = new URLSearchParams(window.location.search).get("next");
  if (next && /^[\w\-\/]+\.html(\?[\w=&%\-]*)?$/.test(next)) return `${root}${next}`;
  if (user.role === "ADMIN") return `${root}pages/admin.html`;
  if (user.role === "SELLER") return `${root}pages/seller.html`;
  return `${root}pages/feed.html`;
}

function showAccessDenied(message, user) {
  const main = document.querySelector("main");
  const root = resolveRootPrefix();
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
initAiChatbotWidget();

// ==========================================================
// TASK T3D2476: UI KHUNG CHAT NỔI - CHATBOT AI TƯ VẤN MUA SẮM
// ==========================================================
function initAiChatbotWidget() {
  if (document.getElementById("ai-chatbot-widget")) return;

  const root = resolveRootPrefix();
  const widget = document.createElement("div");
  widget.id = "ai-chatbot-widget";
  widget.className = "ai-chatbot-widget";

  widget.innerHTML = `
    <!-- Nút mở khung chat nổi (FAB) -->
    <button type="button" id="ai-chat-fab" class="ai-chat-fab" aria-label="Mở Trợ lý Mua sắm AI">
      <span class="ai-fab-icon">🤖</span>
      <span class="ai-fab-label">Tư vấn AI</span>
    </button>

    <!-- Khung chat nổi -->
    <section id="ai-chat-panel" class="ai-chat-panel" aria-label="Khung chat tư vấn mua sắm AI">
      <header class="ai-chat-header">
        <div class="ai-chat-header-left">
          <div class="ai-bot-avatar">🛍️</div>
          <div>
            <div class="ai-chat-title">Trợ lý Mua sắm AI</div>
            <div class="ai-chat-quota" id="ai-quota-badge">Chỉ gợi ý sản phẩm thật tại Shop</div>
          </div>
        </div>
        <button type="button" id="ai-chat-close" class="ai-chat-close-btn" title="Đóng">&times;</button>
      </header>

      <!-- Gợi ý câu hỏi nhanh -->
      <div class="ai-quick-prompts">
        <button type="button" class="ai-chip-btn" data-prompt="Gợi ý cho tôi các sản phẩm bán chạy nhất">🔥 Bán chạy</button>
        <button type="button" class="ai-chip-btn" data-prompt="Tư vấn điện thoại giá tốt">📱 Điện thoại</button>
        <button type="button" class="ai-chip-btn" data-prompt="Tìm tai nghe dưới 500k">🎧 Tai nghe &lt;500k</button>
        <button type="button" class="ai-chip-btn" data-prompt="Shop có áo thun nam nào không?">👕 Áo thun</button>
        <button type="button" class="ai-chip-btn" data-prompt="Tư vấn laptop gaming">💻 Laptop</button>
      </div>

      <!-- Danh sách tin nhắn -->
      <div id="ai-chat-messages" class="ai-chat-messages">
        <div class="ai-msg-row assistant">
          <div class="ai-msg-bubble">
            Xin chào! 👋 Mình là <strong>Trợ lý AI của ClipShop</strong>.<br>
            Mình sẽ tìm sản phẩm <strong>có thật trong hệ thống</strong> và gửi kèm link cho bạn. Bạn đang muốn tìm mua mặt hàng gì hay tầm giá bao nhiêu?
          </div>
        </div>
      </div>

      <!-- Khung nhập câu hỏi -->
      <form id="ai-chat-form" class="ai-chat-input-bar" onsubmit="return false;">
        <input
          type="text"
          id="ai-chat-input"
          placeholder="Nhập nhu cầu mua sắm (vd: tai nghe dưới 500k)..."
          maxlength="2000"
          autocomplete="off"
        >
        <button type="submit" id="ai-chat-send" class="ai-chat-send-btn">Gửi</button>
      </form>
    </section>

    <!-- Modal xem nhanh chi tiết sản phẩm -->
    <div id="ai-product-modal" class="modal-overlay">
      <div class="modal-card" style="max-width:460px;">
        <div class="modal-header">
          <h3 style="margin:0;" id="ai-modal-title">Chi tiết sản phẩm</h3>
          <button type="button" id="ai-modal-close" class="modal-close-btn">&times;</button>
        </div>
        <div id="ai-modal-body"></div>
      </div>
    </div>
  `;

  document.body.appendChild(widget);

  const fabBtn = document.getElementById("ai-chat-fab");
  const panelEl = document.getElementById("ai-chat-panel");
  const closeBtn = document.getElementById("ai-chat-close");
  const formEl = document.getElementById("ai-chat-form");
  const inputEl = document.getElementById("ai-chat-input");
  const modalEl = document.getElementById("ai-product-modal");
  const modalCloseBtn = document.getElementById("ai-modal-close");

  let historyLoaded = false;

  fabBtn.addEventListener("click", () => {
    const isOpen = panelEl.classList.toggle("open");
    fabBtn.classList.toggle("hidden-fab", isOpen);
    if (isOpen) {
      inputEl.focus();
      if (!historyLoaded) {
        historyLoaded = true;
        loadAiQuotaAndHistory();
      }
    }
  });

  closeBtn.addEventListener("click", () => {
    panelEl.classList.remove("open");
    fabBtn.classList.remove("hidden-fab");
  });

  if (modalCloseBtn && modalEl) {
    modalCloseBtn.addEventListener("click", () => modalEl.classList.remove("active"));
    modalEl.addEventListener("click", (e) => {
      if (e.target === modalEl) modalEl.classList.remove("active");
    });
  }

  widget.querySelectorAll(".ai-chip-btn").forEach((chip) => {
    chip.addEventListener("click", () => {
      const promptText = chip.dataset.prompt || "";
      if (!promptText) return;
      inputEl.value = promptText;
      sendAiChatMessage();
    });
  });

  formEl.addEventListener("submit", (e) => {
    e.preventDefault();
    sendAiChatMessage();
  });

  async function loadAiQuotaAndHistory() {
    if (!session.getToken()) {
      updateAiQuotaUI(null);
      return;
    }

    try {
      const [quota, logs] = await Promise.all([
        api.get("/ai/quota"),
        api.get("/ai/chat-logs", { limit: 20 }),
      ]);
      updateAiQuotaUI(quota);

      if (Array.isArray(logs) && logs.length > 0) {
        const ordered = logs.slice().reverse();
        ordered.forEach((log) => {
          appendAiMessage(log.role, log.message, []);
        });
      }
    } catch (_) {
      // Bỏ qua nếu chưa đăng nhập hoặc lỗi mạng tạm thời
    }
  }

  function updateAiQuotaUI(quota) {
    const badgeEl = document.getElementById("ai-quota-badge");
    const sendBtn = document.getElementById("ai-chat-send");
    if (!badgeEl) return;

    if (!quota) {
      badgeEl.textContent = "Đăng nhập để nhận tư vấn mua sắm AI";
      return;
    }

    badgeEl.textContent = `Còn ${quota.remaining_today}/${quota.daily_limit} câu hỏi hôm nay`;
    if (quota.remaining_today <= 0) {
      badgeEl.classList.add("quota-empty");
      if (inputEl) {
        inputEl.disabled = true;
        inputEl.placeholder = "Đã hết lượt hỏi hôm nay. Hẹn gặp lại ngày mai!";
      }
      if (sendBtn) sendBtn.disabled = true;
    } else {
      badgeEl.classList.remove("quota-empty");
      if (inputEl) {
        inputEl.disabled = false;
        inputEl.placeholder = "Nhập nhu cầu mua sắm (vd: tai nghe dưới 500k)...";
      }
      if (sendBtn) sendBtn.disabled = false;
    }
  }

  function formatAiTextToHtml(rawText) {
    let safe = escapeHtml(rawText || "");
    // Đổi **chữ đậm**
    safe = safe.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    // Đổi đường dẫn pages/product.html?id=X thành thẻ <a> bấm được
    safe = safe.replace(
      /pages\/product\.html\?id=(\d+)/g,
      (match, pid) =>
        `<a href="${root}pages/product.html?id=${pid}" class="ai-inline-link" data-product-id="${pid}">🔗 Xem sản phẩm #${pid} &rarr;</a>`
    );
    return safe.replace(/\n/g, "<br>");
  }

  function appendAiMessage(role, text, products = [], isError = false) {
    const listEl = document.getElementById("ai-chat-messages");
    if (!listEl) return;

    const row = document.createElement("div");
    row.className = `ai-msg-row ${role === "user" ? "user" : "assistant"}`;

    const bubble = document.createElement("div");
    bubble.className = `ai-msg-bubble${isError ? " ai-msg-error" : ""}`;
    bubble.innerHTML =
      role === "user" ? escapeHtml(text) : formatAiTextToHtml(text);

    if (Array.isArray(products) && products.length > 0) {
      const cardsWrap = document.createElement("div");
      cardsWrap.className = "ai-rec-products-list";

      products.forEach((p) => {
        const card = document.createElement("div");
        card.className = "ai-rec-product-card";
        const priceFormatted = Number(p.price || 0).toLocaleString("vi-VN") + " ₫";
        const productHref = `${root}${p.link || `pages/product.html?id=${p.id}`}`;

        card.innerHTML = `
          <div class="ai-rec-prod-info">
            <div class="ai-rec-prod-name">${escapeHtml(p.name)}</div>
            <div class="ai-rec-prod-price">${priceFormatted}</div>
            <div class="ai-rec-prod-meta">
              🏪 ${escapeHtml(p.shop_name || "ClipShop")} · Kho: ${p.stock || 0}
            </div>
          </div>
          <div class="ai-rec-prod-actions">
            <a href="${productHref}" class="btn btn-primary btn-small ai-prod-link-btn" data-product-id="${p.id}">
              Xem SP &rarr;
            </a>
          </div>
        `;
        cardsWrap.appendChild(card);
      });

      bubble.appendChild(cardsWrap);
    }

    // Hỗ trợ mở modal chi tiết sản phẩm hoặc chuyển trang
    bubble.querySelectorAll("[data-product-id]").forEach((linkEl) => {
      linkEl.addEventListener("click", async (e) => {
        const pid = linkEl.dataset.productId;
        if (!pid) return;
        // Kiểm tra thử trang product.html có sẵn không; nếu chưa merge thì mở modal chi tiết ngay
        e.preventDefault();
        await openProductQuickModal(pid, linkEl.getAttribute("href"));
      });
    });

    row.appendChild(bubble);
    listEl.appendChild(row);
    listEl.scrollTop = listEl.scrollHeight;
  }

  async function openProductQuickModal(productId, targetHref) {
    const modal = document.getElementById("ai-product-modal");
    const body = document.getElementById("ai-modal-body");
    const title = document.getElementById("ai-modal-title");
    if (!modal || !body) {
      if (targetHref) window.location.href = targetHref;
      return;
    }

    modal.classList.add("active");
    title.textContent = `Sản phẩm #${productId}`;
    body.innerHTML = `<div class="muted" style="text-align:center;padding:24px;">⏳ Đang tải thông tin sản phẩm từ MySQL...</div>`;

    try {
      const p = await api.get(`/products/${productId}`);
      const priceFmt = Number(p.price || 0).toLocaleString("vi-VN") + " ₫";
      title.textContent = p.name || `Sản phẩm #${productId}`;
      body.innerHTML = `
        <div style="display:flex;flex-direction:column;gap:10px;">
          <div style="font-size:22px;font-weight:700;color:var(--color-danger);">${priceFmt}</div>
          <div class="muted">
            🏪 Cửa hàng: <strong>${escapeHtml(p.shop?.name || "ClipShop")}</strong> ·
            📦 Tồn kho: <strong>${p.stock}</strong> ·
            🔥 Đã bán: <strong>${p.sold_count || 0}</strong>
          </div>
          ${
            p.category?.name
              ? `<div>🏷️ Danh mục: <span class="role-badge">${escapeHtml(p.category.name)}</span></div>`
              : ""
          }
          <p style="margin:8px 0;font-size:14px;line-height:1.5;">
            ${escapeHtml(p.description || "Sản phẩm chính hãng tại ClipShop AI.")}
          </p>
          <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:8px;">
            <a href="${root}pages/shop.html?product_id=${p.id}" class="btn btn-primary btn-small">Đi tới Shop</a>
          </div>
        </div>
      `;
    } catch (err) {
      body.innerHTML = `<div class="text-error">${escapeHtml(
        err.message || "Không tải được chi tiết sản phẩm."
      )}</div>`;
    }
  }

  async function sendAiChatMessage() {
    const text = (inputEl.value || "").trim();
    if (!text) return;

    if (!session.getToken()) {
      appendAiMessage("user", text);
      inputEl.value = "";
      appendAiMessage(
        "assistant",
        "Vui lòng đăng nhập tài khoản để sử dụng Trợ lý AI tư vấn mua sắm (miễn phí mỗi ngày)!",
        [],
        true
      );
      return;
    }

    inputEl.value = "";
    appendAiMessage("user", text);

    const sendBtn = document.getElementById("ai-chat-send");
    if (sendBtn) sendBtn.disabled = true;

    // Hiển thị bong bóng đang xử lý
    const listEl = document.getElementById("ai-chat-messages");
    const typingRow = document.createElement("div");
    typingRow.className = "ai-msg-row assistant";
    typingRow.innerHTML = `<div class="ai-msg-bubble ai-typing">⏳ AI đang tìm sản phẩm trong MySQL và tư vấn...</div>`;
    listEl.appendChild(typingRow);
    listEl.scrollTop = listEl.scrollHeight;

    try {
      const res = await api.post("/ai/chat", { message: text }, { timeout: 60000 });
      typingRow.remove();

      appendAiMessage(
        "assistant",
        res.reply,
        res.recommended_products || []
      );

      updateAiQuotaUI({
        daily_limit: res.daily_limit,
        used_today: res.used_today,
        remaining_today: res.remaining_today,
      });
    } catch (err) {
      typingRow.remove();
      let friendlyMsg =
        err.message ||
        "Không thể kết nối tới Trợ lý AI lúc này. Vui lòng thử lại sau.";

      if (err.status === 504 || err.status === 408) {
        friendlyMsg =
          "⏱️ Trợ lý AI phản hồi quá thời gian chờ (timeout). Vui lòng thử lại sau giây lát.";
      } else if (err.status === 429) {
        friendlyMsg = `⚠️ ${err.message}`;
        // Làm mới lại thông tin giới hạn câu hỏi trong ngày
        try {
          const q = await api.get("/ai/quota");
          updateAiQuotaUI(q);
        } catch (_) {}
      }

      appendAiMessage("assistant", friendlyMsg, [], true);
    } finally {
      const sendBtnAfter = document.getElementById("ai-chat-send");
      if (sendBtnAfter && !inputEl.disabled) {
        sendBtnAfter.disabled = false;
      }
    }
  }
}

// ==========================================================
// TASK T3D2BAD: QUẢN LÝ CHUÔNG THÔNG BÁO VÀ DANH SÁCH DROPDOWN
// ==========================================================

function formatNotifTime(dateStr) {
  if (!dateStr) return "";
  let normalized = String(dateStr).trim().replace(" ", "T");
  if (!/[zZ]|[+-]\d{2}:?\d{2}$/.test(normalized)) normalized += "Z";
  const d = new Date(normalized);
  if (isNaN(d.getTime())) return "";
  const now = new Date();
  const diffSec = Math.max(0, Math.floor((now - d) / 1000));
  if (diffSec < 60) return "Vừa xong";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} phút trước`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} giờ trước`;
  if (diffSec < 86400 * 7) return `${Math.floor(diffSec / 86400)} ngày trước`;
  return `${d.getDate()}/${d.getMonth() + 1}/${d.getFullYear()}`;
}

function getNotifIcon(type) {
  switch (type) {
    case "LIKE":
      return "❤️";
    case "COMMENT":
      return "💬";
    case "FOLLOW":
      return "👤";
    case "ORDER_STATUS":
      return "📦";
    case "ORDER_NEW":
      return "🛒";
    case "ORDER_CANCELLED":
      return "🚫";
    case "SELLER_APPROVED":
      return "✅";
    case "SELLER_REJECTED":
      return "❌";
    case "MODERATION_VIDEO":
      return "🎬";
    case "MODERATION_PRODUCT":
      return "⚠️";
    default:
      return "🔔";
  }
}

async function updateNotificationBadge() {
  if (!session.getToken()) return;
  const badgeEl = document.getElementById("notif-badge");
  if (!badgeEl) return;
  try {
    const res = await api.get("/notifications/unread-count");
    const count =
      res && typeof res.unread_count === "number" ? res.unread_count : 0;
    if (count > 0) {
      badgeEl.textContent = count > 99 ? "99+" : count;
      badgeEl.style.display = "flex";
    } else {
      badgeEl.style.display = "none";
    }
  } catch (err) {
    // Không làm gián đoạn UI nếu request lỗi
  }
}

async function loadNotificationsDropdown() {
  const listEl = document.getElementById("notif-list");
  if (!listEl) return;
  listEl.innerHTML = `<div class="notif-empty">Đang tải thông báo...</div>`;

  try {
    const items = await api.get("/notifications?limit=30");
    if (!Array.isArray(items) || items.length === 0) {
      listEl.innerHTML = `<div class="notif-empty">Chưa có thông báo nào</div>`;
      return;
    }

    const root = resolveRootPrefix();
    listEl.innerHTML = items
      .map((item) => {
        const icon = getNotifIcon(item.type);
        const timeStr = formatNotifTime(item.created_at);
        const unreadClass = item.is_read ? "read" : "unread";
        return `
          <div class="notif-item ${unreadClass}" data-id="${item.id}" data-type="${escapeHtml(item.type)}" data-video-id="${item.video_id || ""}" data-order-id="${item.order_id || ""}" data-actor-username="${escapeHtml((item.actor && item.actor.username) || "")}">
            <div class="notif-icon-wrap">${icon}</div>
            <div class="notif-body">
              <div class="notif-content">${escapeHtml(item.content)}</div>
              <div class="notif-time">${escapeHtml(timeStr)}</div>
            </div>
            ${!item.is_read ? '<span class="notif-unread-dot"></span>' : ""}
          </div>`;
      })
      .join("");

    listEl.querySelectorAll(".notif-item").forEach((el) => {
      el.addEventListener("click", () => handleNotificationClick(el, root));
    });
  } catch (err) {
    listEl.innerHTML = `<div class="notif-empty">Không thể tải thông báo. Vui lòng thử lại.</div>`;
  }
}

async function handleNotificationClick(el, root) {
  const notifId = el.dataset.id;
  const isUnread = el.classList.contains("unread");
  const type = el.dataset.type;
  const videoId = el.dataset.videoId;
  const orderId = el.dataset.orderId;
  const actorUsername = el.dataset.actorUsername;

  // Nếu chưa đọc, đánh dấu đã đọc trên server
  if (isUnread && notifId) {
    try {
      await api.patch(`/notifications/${notifId}/read`);
      el.classList.remove("unread");
      el.classList.add("read");
      const dot = el.querySelector(".notif-unread-dot");
      if (dot) dot.remove();
      updateNotificationBadge();
    } catch (_) {}
  }

  // Đóng dropdown
  const dropdown = document.getElementById("notif-dropdown");
  if (dropdown) dropdown.style.display = "none";

  // Điều hướng tương ứng
  if (type === "ORDER_NEW" || type === "ORDER_CANCELLED" || type === "MODERATION_PRODUCT") {
    window.location.href = `${root}pages/seller.html`;
  } else if (type === "MODERATION_VIDEO") {
    window.location.href = `${root}pages/my-videos.html`;
  } else if (videoId) {
    window.location.href = `${root}pages/video.html?id=${videoId}`;
  } else if (orderId) {
    window.location.href = `${root}pages/cart.html?order_id=${encodeURIComponent(orderId)}#order-${encodeURIComponent(orderId)}`;
  } else if (type === "FOLLOW" && actorUsername) {
    window.location.href = `${root}pages/profile.html?username=${encodeURIComponent(actorUsername)}`;
  } else if (type === "SELLER_APPROVED" || type === "SELLER_REJECTED") {
    window.location.href = `${root}pages/seller-register.html`;
  }
}

async function markAllNotificationsRead() {
  try {
    await api.patch("/notifications/read-all");
    const listEl = document.getElementById("notif-list");
    if (listEl) {
      listEl.querySelectorAll(".notif-item.unread").forEach((el) => {
        el.classList.remove("unread");
        el.classList.add("read");
        const dot = el.querySelector(".notif-unread-dot");
        if (dot) dot.remove();
      });
    }
    const badgeEl = document.getElementById("notif-badge");
    if (badgeEl) badgeEl.style.display = "none";
    if (typeof showToast === "function") {
      showToast("Đã đánh dấu tất cả thông báo là đã đọc", "success");
    }
  } catch (err) {
    if (typeof showToast === "function") {
      showToast("Không thể cập nhật thông báo", "error");
    }
  }
}

function initNotificationBell() {
  const bellBtn = document.getElementById("btn-notif-bell");
  const dropdown = document.getElementById("notif-dropdown");
  const readAllBtn = document.getElementById("btn-notif-read-all");

  if (!bellBtn || !dropdown) return;

  // Bấm chuông mở/đóng dropdown
  bellBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const isHidden = dropdown.style.display === "none";
    dropdown.style.display = isHidden ? "flex" : "none";
    if (isHidden) {
      loadNotificationsDropdown();
    }
  });

  // Bấm nút Đọc tất cả
  if (readAllBtn) {
    readAllBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      markAllNotificationsRead();
    });
  }

  // Bấm bên trong dropdown không đóng
  dropdown.addEventListener("click", (e) => e.stopPropagation());

  // Bấm ngoài đóng dropdown
  document.addEventListener("click", () => {
    if (dropdown.style.display !== "none") {
      dropdown.style.display = "none";
    }
  });

  // Khởi chạy đếm chưa đọc lần đầu
  updateNotificationBadge();

  // Polling mỗi 25 giây
  if (notifPollingTimer) clearInterval(notifPollingTimer);
  notifPollingTimer = setInterval(updateNotificationBadge, 25000);
}
