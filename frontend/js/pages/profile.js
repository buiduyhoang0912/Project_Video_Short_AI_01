// Logic xử lý trang Hồ sơ người dùng & Nút Theo dõi (Task T3D2428)

let targetUserId = null;
let profileData = null;

document.addEventListener("DOMContentLoaded", async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const paramId = urlParams.get("user_id") || urlParams.get("id");
  const paramUsername = (urlParams.get("username") || "").trim();

  let currentUser = getCurrentUser();

  if (paramUsername) {
    // Hồ sơ công khai theo username: không cần đăng nhập (T3D1FE9).
    try {
      const pub = await api.get(`/profiles/${encodeURIComponent(paramUsername)}`);
      targetUserId = pub.id;
    } catch (err) {
      showProfileError(
        err.status === 404
          ? `Không tìm thấy người dùng "${paramUsername}". Hãy kiểm tra lại username.`
          : err.message,
      );
      return;
    }
  } else if (paramId) {
    targetUserId = parseInt(paramId, 10);
  } else {
    // Hồ sơ cá nhân: phải xác nhận phiên bằng /auth/me rồi mới tải hồ sơ chính chủ.
    if (!session.getToken()) return; // chưa đăng nhập: layout.js đã chuyển về trang đăng nhập
    try {
      const me = await api.get("/auth/me");
      session.setUser(me);
      currentUser = me;
      targetUserId = me.id;
    } catch (err) {
      // 401/khóa: interceptor đã chuyển trang; lỗi khác: layout.js hiện thông báo + nút thử lại
      return;
    }
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

    // Hồ sơ của chính mình: nút sửa hồ sơ / đổi mật khẩu; luôn có link hồ sơ công khai
    const me = getCurrentUser();
    const isSelf = !!(me && me.id === profileData.id && session.getToken());
    document.getElementById("profile-self-actions").style.display = isSelf ? "flex" : "none";
    const publicHref = `profile.html?username=${encodeURIComponent(profileData.username)}`;
    const publicLink = document.getElementById("profile-public-link");
    publicLink.href = publicHref;
    publicLink.innerText = new URL(publicHref, window.location.href).href;
    document.getElementById("profile-public-row").style.display = "block";
    document.title = `${profileData.display_name} (@${profileData.username}) | ClipShop AI`;

    // Vị trí cho module Video gắn lưới video + sự kiện báo hồ sơ đã tải xong
    const slot = document.getElementById("profile-video-slot");
    slot.dataset.userId = profileData.id;
    slot.dataset.username = profileData.username;
    document.dispatchEvent(
      new CustomEvent("profile:loaded", {
        detail: { id: profileData.id, username: profileData.username, isSelf },
      }),
    );

    // Cấu hình Nút Theo dõi trên trang hồ sơ
    setupProfileFollowButton();

    // Render danh sách video
    renderUserVideos(profileData.videos || []);

    loadingEl.style.display = "none";
    containerEl.style.display = "block";
  } catch (err) {
    showProfileError(err.message || "Không thể tải thông tin hồ sơ.");
  }
}

function showProfileError(message) {
  const loadingEl = document.getElementById("profile-loading");
  loadingEl.style.display = "block";
  loadingEl.innerHTML = `
    <div style="color:var(--color-danger);margin-bottom:12px;">⚠️ ${escapeHtml(message)}</div>
    <a href="feed.html" class="btn btn-small">Quay lại Feed Video</a>
  `;
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
// ---------- RENDER DANH SÁCH LƯỚI VIDEO (TASK T3D226A) ----------
function renderUserVideos(videos) {
  const gridEl = document.getElementById("profile-videos-grid");
  const emptyEl = document.getElementById("profile-videos-empty");

  if (!gridEl) return;
  gridEl.innerHTML = "";

  if (!videos || videos.length === 0) {
    if (emptyEl) emptyEl.style.display = "block";
    return;
  }

  if (emptyEl) emptyEl.style.display = "none";

  videos.forEach((v) => {
    const item = document.createElement("div");
    item.className = "profile-video-thumb-card";
    item.setAttribute("title", v.title || "Video ngắn");

    let thumbSrc = v.thumbnail_url || "";
    if (thumbSrc && thumbSrc.startsWith("/uploads/")) {
      thumbSrc = `${CONFIG.API_BASE_URL.replace("/api", "")}${thumbSrc}`;
    } else if (!thumbSrc) {
      thumbSrc = "../assets/images/logo.svg";
    }

    const viewsFormatted = Number(v.view_count || 0).toLocaleString("vi-VN");

    item.innerHTML = `
      <img src="${escapeHtml(thumbSrc)}" alt="${escapeHtml(v.title || "")}" loading="lazy" onerror="this.src='../assets/images/logo.svg'">
      <div class="profile-video-thumb-overlay">
        <span class="video-views-badge">▶ ${viewsFormatted}</span>
      </div>
      <div class="profile-video-title-hover">${escapeHtml(v.title || "")}</div>
    `;

    // Bấm mở trang xem video (Yêu cầu đề bài)
    item.addEventListener("click", () => {
      window.location.href = `video.html?id=${v.id}`;
    });

    gridEl.appendChild(item);
  });
}

// Dùng showToast chung từ utils.js (góc trên phải, z-index: 9999)
