// Cấu hình chung của frontend.
// Đổi các địa chỉ này nếu backend chạy ở địa chỉ/cổng khác (hoặc khi deploy).
const CONFIG = {
  // Các API nghiệp vụ nằm dưới /api
  API_BASE_URL: "http://127.0.0.1:8000/api",
  // Các API xác thực (/auth/login, /auth/register, /auth/me, /auth/logout) KHÔNG nằm dưới /api
  AUTH_BASE_URL: "http://127.0.0.1:8000",
  APP_NAME: "KS25 Base",
  // Khóa lưu phiên đăng nhập trong localStorage (không bao giờ lưu mật khẩu)
  TOKEN_KEY: "access_token",
  USER_KEY: "current_user",
};