// Cấu hình chung của frontend: tự nhận diện môi trường Local hay Production (Vercel / Domain riêng).
const isLocalHost =
  window.location.hostname === "127.0.0.1" ||
  window.location.hostname === "localhost" ||
  window.location.protocol === "file:";

const BASE_ORIGIN = isLocalHost
  ? "http://127.0.0.1:8000"
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
