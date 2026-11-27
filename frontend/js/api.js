// Module gọi API bằng axios: cấu hình 1 lần, mọi trang dùng chung.
// (axios được nạp từ CDN bằng thẻ <script> trong từng trang HTML, trước file này)
//
// Cách dùng (trong các file js/pages/*.js):
//   const items = await api.get("/items");
//   const created = await api.post("/items", { name: "Trà đá", price: 5000 });
//   const me = await api.get("/auth/me");   // đường dẫn /auth/* tự dùng CONFIG.AUTH_BASE_URL
//
// Các hàm trả về thẳng dữ liệu JSON (đã lấy sẵn response.data).
// Nếu lỗi, hàm sẽ throw ApiError -> bắt bằng try/catch và hiện error.message cho người dùng.

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status; // mã HTTP: 404, 422, 500... (0 = không gọi được server)
    this.data = data; // nội dung lỗi gốc server trả về
  }
}

// ---------- QUẢN LÝ PHIÊN ĐĂNG NHẬP (một khóa token duy nhất: CONFIG.TOKEN_KEY) ----------
const session = {
  getToken() {
    return localStorage.getItem(CONFIG.TOKEN_KEY);
  },
  getUser() {
    try {
      const raw = localStorage.getItem(CONFIG.USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  },
  save(token, user) {
    localStorage.setItem(CONFIG.TOKEN_KEY, token);
    if (user) localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(user));
  },
  setUser(user) {
    localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem(CONFIG.TOKEN_KEY);
    localStorage.removeItem(CONFIG.USER_KEY);
    localStorage.removeItem("token"); // khóa cũ, dọn cho sạch
  },
};

// Instance axios dùng chung: mọi request tự nối thêm baseURL phía trước
const http = axios.create({
  baseURL: CONFIG.API_BASE_URL,
  timeout: 20000, // quá 20 giây không phản hồi thì báo lỗi
  headers: { "Content-Type": "application/json" },
});

const isAuthPath = (url) => typeof url === "string" && url.startsWith("/auth/");

// Request: /auth/* gọi vào AUTH_BASE_URL; có token thì tự đính kèm Authorization: Bearer
http.interceptors.request.use((config) => {
  if (isAuthPath(config.url)) config.baseURL = CONFIG.AUTH_BASE_URL;
  const token = session.getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Lấy câu thông báo lỗi dễ đọc từ response của FastAPI
function getErrorMessage(data, status) {
  if (data && typeof data.detail === "string") return data.detail;
  // Lỗi 422 (dữ liệu không hợp lệ): detail là mảng [{ loc: [...], msg: "..." }]
  if (data && Array.isArray(data.detail)) {
    return data.detail.map((e) => `${e.loc[e.loc.length - 1]}: ${e.msg}`).join("; ");
  }
  return `Lỗi ${status}`;
}

// Tiền tố đường dẫn về thư mục gốc frontend ("../" nếu đang ở /pages/, "./" nếu ở gốc)
function getRootPrefix() {
  if (document.body && document.body.dataset.root) {
    return document.body.dataset.root;
  }
  return window.location.pathname.includes("/pages/") ? "../" : "./";
}

// Đường dẫn trang đăng nhập (tính theo vị trí trang hiện tại) + trang đang mở để quay lại
function loginUrl(extra = "") {
  const root = getRootPrefix();
  // trang trong /pages/ (root = "../") thì login.html nằm cùng thư mục; trang gốc thì vào pages/
  const path = window.location.pathname;
  const rel = path.includes("/pages/") ? "pages/" + path.split("/pages/")[1] : path.split("/").pop();
  const next = rel && rel !== "login.html" ? `${rel}${window.location.search}` : "";
  const q = [next ? `next=${encodeURIComponent(next)}` : "", extra].filter(Boolean).join("&");
  const base = root === "./" ? "pages/login.html" : "login.html";
  return `${base}${q ? "?" + q : ""}`;
}

// Trang có bắt buộc đăng nhập không (khai báo bằng data-auth / data-roles trên <body>)
function pageNeedsAuth() {
  const b = document.body.dataset;
  if (b.roles || b.auth === "required") return true;
  if (b.auth === "self") {
    const p = new URLSearchParams(window.location.search);
    // feed dùng ?user_id=, nơi khác dùng ?id=, hồ sơ công khai theo tên dùng ?username=
    return !(p.get("id") || p.get("user_id") || p.get("username"));
  }
  return false;
}

function showNetworkBanner() {
  if (document.getElementById("net-banner")) return;
  const el = document.createElement("div");
  el.id = "net-banner";
  el.className = "net-banner";
  el.innerHTML = `<span>Mất kết nối tới máy chủ. Vui lòng kiểm tra mạng.</span>
    <button type="button" class="btn btn-small" id="net-retry">Thử lại</button>`;
  document.body.appendChild(el);
  document.getElementById("net-retry").addEventListener("click", () => window.location.reload());
}

// Gom xử lý lỗi một chỗ: đổi lỗi của axios thành ApiError dễ dùng
http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server có trả lời nhưng là lỗi (4xx, 5xx)
      const { status, data } = error.response;
      const message = getErrorMessage(data, status);
      const url = error.config && error.config.url;
      const isCredentialCall = url === "/auth/login" || url === "/auth/register";
      const hadToken = !!session.getToken();

      if (!isCredentialCall) {
        if (status === 401 && hadToken) {
          // Phiên hết hạn / token sai / đã đăng xuất -> xóa phiên
          session.clear();
          if (pageNeedsAuth()) {
            window.location.href = loginUrl("expired=1");
          } else if (typeof showToast === "function") {
            showToast("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.", "error");
            setTimeout(() => window.location.reload(), 1500);
          }
        } else if (status === 403 && /kh[oó]a/i.test(message)) {
          // Tài khoản bị khóa
          session.clear();
          window.location.href = loginUrl("locked=1");
        } else if (status === 403 && typeof showToast === "function") {
          showToast("Bạn không có quyền thực hiện thao tác này.", "error");
        }
      }
      return Promise.reject(new ApiError(message, status, data));
    }
    if (error.code === "ECONNABORTED") {
      return Promise.reject(new ApiError(
        "Máy chủ phản hồi quá thời gian chờ. Vui lòng thử lại sau.", 408,
      ));
    }
    // Không có response: server tắt, sai URL, bị chặn CORS
    showNetworkBanner();
    return Promise.reject(new ApiError(
      "Không kết nối được máy chủ. Hãy kiểm tra mạng/backend rồi thử lại.", 0,
    ));
  },
);

const api = {
  get: (path, params, config = {}) => http.get(path, { params, ...config }).then((res) => res.data),
  post: (path, body, config = {}) => http.post(path, body, config).then((res) => res.data),
  put: (path, body, config = {}) => http.put(path, body, config).then((res) => res.data),
  patch: (path, body, config = {}) => http.patch(path, body, config).then((res) => res.data),
  delete: (path, config = {}) => http.delete(path, config).then((res) => res.data),
  // Upload tệp (FormData): để trình duyệt tự gắn boundary cho multipart
    // Upload tệp (FormData): hỗ trợ config (như onUploadProgress) và timeout 60s cho video
  upload: (path, formData, config = {}) =>
    http
      .post(path, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 60000,
        ...config,
      })
      .then((res) => res.data),
};

