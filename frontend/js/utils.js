// Các hàm tiện ích dùng chung cho nhiều trang.

// Chống XSS: luôn dùng hàm này khi chèn dữ liệu người dùng nhập vào innerHTML hoặc thuộc tính
function escapeHtml(value) {
  if (value == null) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Chống XSS chuyên biệt khi chèn giá trị vào thuộc tính HTML (data-*, title, value...)
function escapeAttr(value) {
  if (value == null) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// 45000 -> "45.000 ₫"
function formatMoney(value) {
  return Number(value).toLocaleString("vi-VN") + " ₫";
}

// "2026-11-04T09:30:00" -> "09:30 4/11/2026"
function formatDateTime(value) {
  const d = new Date(value);
  return d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }) + " " +
    d.toLocaleDateString("vi-VN");
}

// Hiện thông báo nhỏ ở góc trên phải màn hình (tránh đè nút Chat AI). type: "success" | "error"
function showToast(message, type = "success") {
  document.querySelectorAll(".toast").forEach((el) => el.remove());
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  toast.style.top = "108px";
  toast.style.right = "20px";
  toast.style.bottom = "auto";
  toast.style.zIndex = "9999";
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}


// Lấy lỗi theo từng ô nhập từ lỗi 422 của FastAPI -> { ten_truong: "thông báo" }
function getFieldErrors(err) {
  const result = {};
  const detail = err && err.data && err.data.detail;
  if (!Array.isArray(detail)) return result;
  detail.forEach((e) => {
    const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : null;
    if (field && !result[field]) result[field] = String(e.msg).replace(/^Value error,\s*/i, "");
  });
  return result;
}
