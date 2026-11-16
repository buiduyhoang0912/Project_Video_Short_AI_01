// Form đăng nhập & đăng ký (pages/login.html, pages/register.html)

const $ = (id) => document.getElementById(id);

function setFieldError(name, msg) {
  const el = $("err-" + name);
  if (el) el.textContent = msg || "";
}
function clearErrors(names) {
  names.forEach((n) => setFieldError(n, ""));
  $("form-error").textContent = "";
}
function setBusy(busy, label) {
  const btn = $("btn-submit");
  btn.disabled = busy;
  btn.textContent = busy ? "Đang xử lý..." : label;
}

// Đăng nhập: lưu token -> GET /auth/me -> lưu thông tin & role -> chuyển trang phù hợp
async function loginAndRedirect(identifier, password) {
  const res = await api.post("/auth/login", { identifier, password });
  session.save(res.access_token); // chỉ lưu token, KHÔNG lưu mật khẩu
  try {
    const me = await api.get("/auth/me");
    session.setUser(me);
    window.location.href = pageAfterLogin(me);
  } catch (err) {
    session.clear();
    throw err;
  }
}

function friendlyLoginError(err) {
  if (err.status === 401) return "Sai email/username hoặc mật khẩu.";
  if (err.status === 403) return "Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên.";
  if (err.status === 422) return "Dữ liệu nhập chưa hợp lệ. Hãy kiểm tra lại.";
  return err.message || "Đăng nhập thất bại, vui lòng thử lại.";
}

// ---------- ĐĂNG NHẬP ----------
const loginForm = $("login-form");
if (loginForm) {
  const params = new URLSearchParams(window.location.search);
  const notice = $("auth-notice");
  if (params.get("locked")) notice.textContent = "Tài khoản của bạn đã bị khóa.";
  else if (params.get("expired")) notice.textContent = "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.";
  if (notice.textContent) notice.style.display = "block";

  let submitting = false;
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (submitting) return; // chống bấm gửi nhiều lần
    clearErrors(["identifier", "password"]);
    const identifier = $("identifier").value.trim();
    const password = $("password").value;
    let ok = true;
    if (!identifier) { setFieldError("identifier", "Nhập email hoặc username."); ok = false; }
    if (!password) { setFieldError("password", "Nhập mật khẩu."); ok = false; }
    if (!ok) return;

    submitting = true;
    setBusy(true, "Đăng nhập");
    try {
      await loginAndRedirect(identifier, password);
    } catch (err) {
      $("form-error").textContent = friendlyLoginError(err);
      submitting = false;
      setBusy(false, "Đăng nhập");
    }
  });
}

// ---------- ĐĂNG KÝ ----------
const registerForm = $("register-form");
if (registerForm) {
  const FIELDS = ["display_name", "username", "email", "password", "confirm_password"];
  let submitting = false;

  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (submitting) return;
    clearErrors(FIELDS);

    const display_name = $("display_name").value.trim();
    const username = $("username").value.trim().toLowerCase();
    const email = $("email").value.trim().toLowerCase();
    const password = $("password").value;
    const confirm = $("confirm_password").value;

    let ok = true;
    const fail = (f, m) => { setFieldError(f, m); ok = false; };
    if (!display_name) fail("display_name", "Nhập tên hiển thị.");
    else if (display_name.length > 100) fail("display_name", "Tên hiển thị tối đa 100 ký tự.");
    if (!/^[a-z0-9_]{3,50}$/.test(username)) fail("username", "Username 3-50 ký tự: chữ thường, số hoặc dấu _.");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) fail("email", "Email không hợp lệ.");
    if (password.length < 8) fail("password", "Mật khẩu tối thiểu 8 ký tự.");
    else if (new TextEncoder().encode(password).length > 72) fail("password", "Mật khẩu quá dài (tối đa 72 byte).");
    else if (!password.trim()) fail("password", "Mật khẩu không được chỉ gồm khoảng trắng.");
    if (confirm !== password) fail("confirm_password", "Mật khẩu xác nhận không khớp."); // chỉ kiểm tra ở frontend
    if (!ok) return;

    submitting = true;
    setBusy(true, "Đăng ký");
    try {
      await api.post("/auth/register", { display_name, username, email, password });
    } catch (err) {
      if (err.status === 409) {
        const m = err.message.toLowerCase();
        if (m.includes("email") && !m.includes("username")) setFieldError("email", "Email này đã được đăng ký.");
        else if (m.includes("username") && !m.includes("email")) setFieldError("username", "Username này đã có người dùng.");
        else $("form-error").textContent = "Email hoặc username đã tồn tại.";
      } else {
        $("form-error").textContent = err.message || "Đăng ký thất bại, vui lòng thử lại.";
      }
      submitting = false;
      setBusy(false, "Đăng ký");
      return;
    }
    // Đăng ký xong -> tự đăng nhập
    try {
      await loginAndRedirect(username, password);
    } catch (err) {
      window.location.href = "login.html";
    }
  });
}