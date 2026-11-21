// Trang Chỉnh sửa hồ sơ (Task T3D1FE9): sửa tên hiển thị, tiểu sử, chọn avatar + xem trước.

const MAX_AVATAR_BYTES = 2 * 1024 * 1024; // khớp giới hạn 2 MB ở server (server vẫn kiểm tra lại)
const ALLOWED_AVATAR_TYPES = ["image/jpeg", "image/png"];
const DEFAULT_AVATAR = "../assets/images/logo.svg";

const form = document.getElementById("profile-form");
const avatarInput = document.getElementById("avatar-input");
const avatarPreview = document.getElementById("avatar-preview");
const displayNameInput = document.getElementById("display_name");
const bioInput = document.getElementById("bio");
const bioCount = document.getElementById("bio-count");
const btnSave = document.getElementById("btn-save");

let currentAvatarUrl = null; // avatar đang lưu trên server
let selectedFile = null; // ảnh vừa chọn, chưa lưu
let previewObjectUrl = null;

function clearErrors() {
  ["avatar", "display_name", "bio"].forEach((f) => setText(`err-${f}`, ""));
  setText("form-error", "");
  document.getElementById("form-success").style.display = "none";
}

function setText(id, text) {
  document.getElementById(id).textContent = text || "";
}

function updateBioCount() {
  const n = bioInput.value.length;
  bioCount.textContent = `${n}/500`;
  bioCount.style.color = n > 500 ? "var(--color-danger)" : "";
}

function showAvatar(url) {
  avatarPreview.onerror = () => {
    avatarPreview.onerror = null;
    avatarPreview.src = DEFAULT_AVATAR;
  };
  avatarPreview.src = url || DEFAULT_AVATAR;
}

function fillForm(profile) {
  document.getElementById("username").value = profile.username;
  displayNameInput.value = profile.display_name || "";
  bioInput.value = profile.bio || "";
  currentAvatarUrl = profile.avatar_url;
  showAvatar(currentAvatarUrl);
  updateBioCount();
}

async function loadMyProfile() {
  const loading = document.getElementById("edit-loading");
  try {
    const profile = await api.get("/me/profile");
    fillForm(profile);
    loading.style.display = "none";
    form.style.display = "block";
  } catch (err) {
    // 401: interceptor đã chuyển về trang đăng nhập; lỗi khác hiện tại chỗ này
    loading.innerHTML = `<span class="text-error">⚠️ ${escapeHtml(err.message || "Không tải được hồ sơ.")}</span>`;
  }
}

// ---------- Chọn ảnh + xem trước ----------
avatarInput.addEventListener("change", () => {
  setText("err-avatar", "");
  if (previewObjectUrl) {
    URL.revokeObjectURL(previewObjectUrl);
    previewObjectUrl = null;
  }
  const file = avatarInput.files[0];
  selectedFile = null;

  if (!file) {
    showAvatar(currentAvatarUrl);
    return;
  }
  // Kiểm tra sớm cho tiện người dùng; server vẫn kiểm tra lại nội dung thật của tệp.
  if (!ALLOWED_AVATAR_TYPES.includes(file.type)) {
    setText("err-avatar", "Chỉ chấp nhận ảnh JPG hoặc PNG.");
    avatarInput.value = "";
    showAvatar(currentAvatarUrl);
    return;
  }
  if (file.size > MAX_AVATAR_BYTES) {
    setText("err-avatar", "Ảnh vượt quá dung lượng cho phép (2 MB).");
    avatarInput.value = "";
    showAvatar(currentAvatarUrl);
    return;
  }
  selectedFile = file;
  previewObjectUrl = URL.createObjectURL(file);
  avatarPreview.src = previewObjectUrl;
});

bioInput.addEventListener("input", updateBioCount);

// ---------- Lưu ----------
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearErrors();
  btnSave.disabled = true;
  btnSave.textContent = "Đang lưu...";

  let profile;
  try {
    profile = await api.patch("/me/profile", {
      display_name: displayNameInput.value,
      bio: bioInput.value,
    });
  } catch (err) {
    showSaveErrors(err);
    resetButton();
    return;
  }

  if (selectedFile) {
    try {
      const data = new FormData();
      data.append("file", selectedFile);
      profile = await api.upload("/me/avatar", data);
    } catch (err) {
      fillTextOnly(profile);
      syncHeaderName(profile);
      setText("err-avatar", err.message || "Không tải được ảnh đại diện.");
      setText("form-error", "Đã lưu tên và tiểu sử, nhưng ảnh đại diện bị từ chối.");
      resetButton();
      return;
    }
  }

  // Thành công: đồng bộ lại form + tên trên header, báo cho người dùng.
  fillForm(profile);
  selectedFile = null;
  avatarInput.value = "";
  syncHeaderName(profile);
  const ok = document.getElementById("form-success");
  ok.textContent = "✅ Đã lưu hồ sơ thành công.";
  ok.style.display = "block";
  showToast("Đã lưu hồ sơ thành công", "success");
  resetButton();
});

// Cập nhật tên hiển thị đã lưu vào phiên + thanh header
function syncHeaderName(profile) {
  const user = session.getUser();
  if (user) {
    session.setUser({ ...user, display_name: profile.display_name });
    renderLayout();
  }
}

function fillTextOnly(profile) {
  displayNameInput.value = profile.display_name || "";
  bioInput.value = profile.bio || "";
  updateBioCount();
}

function showSaveErrors(err) {
  const fields = getFieldErrors(err);
  let shown = false;
  ["display_name", "bio"].forEach((f) => {
    if (fields[f]) {
      setText(`err-${f}`, fields[f]);
      shown = true;
    }
  });
  if (!shown) setText("form-error", err.message || "Không lưu được hồ sơ.");
}

function resetButton() {
  btnSave.disabled = false;
  btnSave.textContent = "Lưu thay đổi";
}

if (session.getToken()) loadMyProfile();
