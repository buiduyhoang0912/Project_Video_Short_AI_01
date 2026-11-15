// Logic xử lý trang Hồ sơ người dùng & Nút Theo dõi (Task T3D2428)

let targetUserId = null;
let profileData = null;

document.addEventListener("DOMContentLoaded", () => {
  const urlParams = new URLSearchParams(window.location.search);
  const paramId = urlParams.get("user_id");

  const currentUser = getCurrentUser();

  if (paramId) {
    targetUserId = parseInt(paramId, 10);
  } else if (currentUser && currentUser.id) {
    targetUserId = currentUser.id;
  } else {
    // Mặc định xem hồ sơ của tài khoản số 1 nếu chưa đăng nhập và không truyền tham số
    targetUserId = 1;
  }

  loadProfile(targetUserId);
});

async function loadProfile(userId) {
  const loadingEl = document.getElementById("profile-loading");
  const containerEl = document.getElementById("profile-container");

  try {
    profileData = await api.get(`/users/${userId}/profile`);

    // Render thông tin
    document.getElementById("profile-display-name").innerText = profileData.display_name;
    document.getElementById("profile-username").innerText = `@${profileData.username}`;
    document.getElementById("profile-role").innerText = profileData.role || "USER";
    document.getElementById("profile-bio").innerText = profileData.bio || "Chưa có tiểu sử giới thiệu.";

    const avatarUrl = profileData.avatar_url || profileData.avatar_key || "../assets/images/logo.svg";
    document.getElementById("profile-avatar").src = avatarUrl;

    document.getElementById("stat-following").innerText = profileData.following_count || 0;
    document.getElementById("stat-followers").innerText = profileData.followers_count || 0;
    document.getElementById("stat-videos").innerText = profileData.video_count || (profileData.videos ? profileData.videos.length : 0);

    // Cấu hình Nút Theo dõi trên trang hồ sơ
    setupProfileFollowButton();

    // Render danh sách video
    renderUserVideos(profileData.videos || []);

    loadingEl.style.display = "none";
    containerEl.style.display = "block";
  } catch (err) {
    loadingEl.innerHTML = `
      <div style="color:var(--color-danger);margin-bottom:12px;">⚠️ ${err.message || "Không thể tải thông tin hồ sơ."}</div>
      <a href="feed.html" class="btn btn-small">Quay lại Feed Video</a>
    `;
  }
}

// ---------- CẤU HÌNH NÚT THEO DÕI TRÊN TRANG HỒ SƠ ----------
function setupProfileFollowButton() {
  const btnFollow = document.getElementById("btn-profile-follow");
  const selfBadge = document.getElementById("profile-self-badge");
  const currentUser = getCurrentUser();

  // Kiểm tra nếu đang xem hồ sơ của chính mình
  if (currentUser && currentUser.id === targetUserId) {
    btnFollow.style.display = "none";
    selfBadge.style.display = "block";
    return;
  }

  selfBadge.style.display = "none";
  btnFollow.style.display = "inline-block";

  updateFollowButtonUI(profileData.is_following);

  btnFollow.onclick = async () => {
    const token = localStorage.getItem("token") || localStorage.getItem("access_token");
    if (!token) {
      if (typeof showLoginModal === "function") showLoginModal();
      return;
    }

    const wasFollowing = profileData.is_following;
    const statFollowersEl = document.getElementById("stat-followers");
    let currentFollowers = parseInt(statFollowersEl.innerText, 10) || 0;

    // Optimistic UI update
    profileData.is_following = !wasFollowing;
    updateFollowButtonUI(profileData.is_following);

    if (!wasFollowing) {
      // Đã bấm Theo dõi
      statFollowersEl.innerText = currentFollowers + 1;
      showToast("Đã theo dõi người dùng này!", "success");
      try {
        await api.post(`/users/${targetUserId}/follow`);
      } catch (err) {
        // Rollback nếu API lỗi
        profileData.is_following = wasFollowing;
        updateFollowButtonUI(wasFollowing);
        statFollowersEl.innerText = currentFollowers;
        showToast(err.message || "Lỗi khi theo dõi", "error");
      }
    } else {
      // Đã bấm Bỏ theo dõi
      statFollowersEl.innerText = Math.max(0, currentFollowers - 1);
      showToast("Đã hủy theo dõi", "success");
      try {
        await api.delete(`/users/${targetUserId}/follow`);
      } catch (err) {
        // Rollback nếu API lỗi
        profileData.is_following = wasFollowing;
        updateFollowButtonUI(wasFollowing);
        statFollowersEl.innerText = currentFollowers;
        showToast(err.message || "Lỗi khi hủy theo dõi", "error");
      }
    }
  };
}

function updateFollowButtonUI(isFollowing) {
  const btnFollow = document.getElementById("btn-profile-follow");
  if (isFollowing) {
    btnFollow.className = "btn-profile-follow is-following";
    btnFollow.innerText = "✓ Đang theo dõi";
  } else {
    btnFollow.className = "btn-profile-follow not-following";
    btnFollow.innerText = "+ Theo dõi";
  }
}

// ---------- RENDER DANH SÁCH VIDEO CỦA USER ----------
function renderUserVideos(videos) {
  const gridEl = document.getElementById("profile-videos-grid");
  const emptyEl = document.getElementById("profile-videos-empty");

  gridEl.innerHTML = "";

  if (!videos || videos.length === 0) {
    emptyEl.style.display = "block";
    return;
  }

  emptyEl.style.display = "none";

  videos.forEach((v) => {
    const item = document.createElement("div");
    item.className = "profile-video-thumb-card";

    let thumbSrc = v.thumbnail_url;
    if (thumbSrc && thumbSrc.startsWith("/uploads/")) {
      thumbSrc = `${CONFIG.API_BASE_URL.replace("/api", "")}${thumbSrc}`;
    }

    item.innerHTML = `
      ${thumbSrc ? `<img src="${thumbSrc}" alt="${v.title}" onerror="this.style.display='none'">` : ""}
      <div class="profile-video-thumb-overlay">
        <span>▶</span>
        <span>${v.view_count || 0}</span>
      </div>
    `;

    item.addEventListener("click", () => {
      window.location.href = `feed.html?v=${v.id}`;
    });

    gridEl.appendChild(item);
  });
}

function showToast(message, type = "success") {
  const existing = document.querySelector(".toast");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerText = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 3000);
}
