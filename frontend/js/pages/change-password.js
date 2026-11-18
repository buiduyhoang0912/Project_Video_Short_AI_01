// Trang Đổi mật khẩu (Task T3D1FE9).

const pwForm = document.getElementById("password-form");
const pwFields = ["current_password", "new_password", "confirm_password"];
const pwButton = document.getElementById("btn-save");

function setPwText(id, text) {
  document.getElementById(id).textContent = text || "";
}

function clearPwErrors() {
  pwFields.forEach((f) => setPwText(`err-${f}`, ""));
  setPwText("form-error", "");
  document.getElementById("form-success").style.display = "none";
}

// Kiểm tra nhanh ở trình duyệt; server vẫn kiểm tra lại tất cả.
function validateLocally(values) {
  const errors = {};
  if (!values.current_password) errors.current_password = "Vui lòng nhập mật khẩu hiện tại";
  if (!values.new_password) errors.new_password = "Vui lòng nhập mật khẩu mới";
  else if (values.new_password.length < 8) errors.new_password = "Mật khẩu mới cần ít nhất 8 ký tự";
  if (!values.confirm_password) errors.confirm_password = "Vui lòng nhập lại mật khẩu mới";
  else if (values.new_password && values.confirm_password !== values.new_password) {
    errors.confirm_password = "Xác nhận mật khẩu không khớp";
  }
  return errors;
}

pwForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearPwErrors();

  const values = {};
  pwFields.forEach((f) => (values[f] = document.getElementById(f).value));

  const local = validateLocally(values);
  if (Object.keys(local).length) {
    Object.entries(local).forEach(([f, msg]) => setPwText(`err-${f}`, msg));
    return;
  }

  pwButton.disabled = true;
  pwButton.textContent = "Đang xử lý...";
  try {
    await api.put("/me/password", values);
    pwFields.forEach((f) => (document.getElementById(f).value = ""));
    const ok = document.getElementById("form-success");
    ok.textContent = "✅ Đổi mật khẩu thành công. Lần đăng nhập sau hãy dùng mật khẩu mới.";
    ok.style.display = "block";
    showToast("Đổi mật khẩu thành công", "success");
  } catch (err) {
    const fields = getFieldErrors(err);
    let shown = false;
    pwFields.forEach((f) => {
      if (fields[f]) {
        setPwText(`err-${f}`, fields[f]);
        shown = true;
      }
    });
    if (!shown) {
      // 400 = mật khẩu hiện tại sai -> báo ngay dưới ô mật khẩu hiện tại
      if (err.status === 400) setPwText("err-current_password", err.message);
      else setPwText("form-error", err.message || "Không đổi được mật khẩu.");
    }
  } finally {
    pwButton.disabled = false;
    pwButton.textContent = "Đổi mật khẩu";
  }
});
