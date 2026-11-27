// Cấu hình chung của frontend: kết nối trực tiếp tới Backend/Database chung của nhóm trên clipshopai.phancopako.com
// để dữ liệu video (Cloudflare R2), sản phẩm, shop, bình luận và tài khoản giống hệt 100% với bản nhóm đang chạy.
const BASE_ORIGIN =
  window.location.hostname === "127.0.0.1" ||
  window.location.hostname === "localhost" ||
  window.location.protocol === "file:"
    ? "https://clipshopai.phancopako.com"
    : window.location.origin;

const CONFIG = {
  // Các API nghiệp vụ nằm dưới /api
  API_BASE_URL: `${BASE_ORIGIN}/api`,
  // Các API xác thực (/auth/login, /auth/register, /auth/me, /auth/logout) KHÔNG nằm dưới /api
  AUTH_BASE_URL: BASE_ORIGIN,
  APP_NAME: "ClipShop AI",
  // Khóa lưu phiên đăng nhập trong localStorage (không bao giờ lưu mật khẩu)
  TOKEN_KEY: "access_token",
  USER_KEY: "current_user",
};
