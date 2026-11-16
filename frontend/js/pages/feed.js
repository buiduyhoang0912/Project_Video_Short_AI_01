// Logic xử lý Feed video, Like, Comment (bảng trượt lên), Share, và Follow

let currentFeedType = "for-you";
let currentVideoIdForComments = null;
let currentReplyingCommentId = null;
let currentReplyingUsername = null;
let observer = null;

document.addEventListener("DOMContentLoaded", () => {
  initFeedTabs();
  initCommentsSheet();
  if (new URLSearchParams(window.location.search).get("tab") === "following") {
    document.getElementById("tab-following").click(); // menu "Đang theo dõi"
  } else {
    loadFeed("for-you");
  }
});

// ---------- 1. TABS CHUYỂN FEED ----------
function initFeedTabs() {
  const tabForYou = document.getElementById("tab-for-you");
  const tabFollowing = document.getElementById("tab-following");

  tabForYou.addEventListener("click", () => {
    if (currentFeedType === "for-you") return;
    currentFeedType = "for-you";
    tabForYou.classList.add("active");
    tabFollowing.classList.remove("active");
    loadFeed("for-you");
  });

  tabFollowing.addEventListener("click", () => {
    if (currentFeedType === "following") return;
    const token = localStorage.getItem("token") || localStorage.getItem("access_token");
    if (!token) {
      if (typeof showLoginModal === "function") {
        showLoginModal();
      } else {
        alert("Vui lòng đăng nhập để xem video của người bạn theo dõi.");
      }
      return;
    }
    currentFeedType = "following";
    tabFollowing.classList.add("active");
    tabForYou.classList.remove("active");
    loadFeed("following");
  });
}

// ---------- 2. TẢI DANH SÁCH VIDEO FEED ----------
async function loadFeed(type) {
  const container = document.getElementById("feed-container");
  container.innerHTML = `
    <div style="color:#aaa;text-align:center;padding:60px 20px;">
      <div style="font-size:24px;margin-bottom:8px;">⏳</div>
      <div>Đang tải video...</div>
    </div>`;

  try {
    let videos = [];
    if (type === "following") {
      videos = await api.get("/videos/feed/following");
    } else {
      videos = await api.get("/videos/feed/for-you");
    }

    if (!videos || videos.length === 0) {
      container.innerHTML = `
        <div style="color:#aaa;text-align:center;padding:80px 20px;">
          <div style="font-size:36px;margin-bottom:12px;">📭</div>
          <div style="font-size:16px;font-weight:600;margin-bottom:6px;">Chưa có video nào</div>
          <div style="font-size:13px;color:#777;">
            ${type === "following" ? "Bạn chưa theo dõi ai hoặc những người bạn theo dõi chưa đăng video." : "Hệ thống đang chuẩn bị thêm các video thú vị."}
          </div>
        </div>`;
      return;
    }

    container.innerHTML = "";
    videos.forEach((video) => {
      const card = createVideoCard(video);
      container.appendChild(card);
    });

    initIntersectionObserver();

    // Tự động cuộn đến video được chọn từ trang Tìm kiếm hoặc link chia sẻ (?v=id)
    const targetVideoId = new URLSearchParams(window.location.search).get("v");
    if (targetVideoId) {
      const targetCard = container.querySelector(`.feed-video-card[data-video-id="${targetVideoId}"]`);
      if (targetCard) {
        setTimeout(() => targetCard.scrollIntoView({ behavior: "smooth" }), 150);
      }
    }
  } catch (err) {
    container.innerHTML = `
      <div style="color:#ef4444;text-align:center;padding:60px 20px;">
        <div>⚠️ ${err.message || "Không thể tải danh sách video"}</div>
        <button class="btn btn-small" style="margin-top:12px;" onclick="loadFeed('${type}')">Thử lại</button>
      </div>`;
  }
}

// ---------- 3. TẠO THẺ VIDEO & CỘT NÚT BÊN PHẢI ----------
function createVideoCard(video) {
  const card = document.createElement("div");
  card.className = "feed-video-card";
  card.dataset.videoId = video.id;

  const defaultAvatar = "../assets/images/logo.svg";
  const avatarUrl = video.author_avatar_url || video.author_avatar_key || defaultAvatar;

  // Chuẩn hóa đường dẫn video
  let videoSrc = video.video_url;
  if (videoSrc && videoSrc.startsWith("/uploads/")) {
    videoSrc = `${CONFIG.API_BASE_URL.replace("/api", "")}${videoSrc}`;
  }

  card.innerHTML = `
    <!-- Thẻ Video -->
    <video class="feed-video-element" loop playsinline preload="metadata" src="${videoSrc}">
      Trình duyệt của bạn không hỗ trợ thẻ video HTML5.
    </video>
    <div class="feed-video-overlay-play">▶</div>

    <!-- Thông tin video (góc trái dưới) -->
    <div class="video-info-bottom">
      <a href="profile.html?user_id=${video.user_id}">
        @${video.author_username}
        <span style="font-size:12px;font-weight:normal;opacity:0.8;">(${video.author_name})</span>
      </a>
      <p class="video-desc">${escapeHtml(video.title || "")} ${video.description ? "- " + escapeHtml(video.description) : ""}</p>
    </div>

    <!-- Cột nút hành động bên phải video (Action Column) -->
    <div class="video-actions-right">
      <!-- 1. Avatar + Nút theo dõi -->
      <div class="avatar-action-wrap">
        <a href="profile.html?user_id=${video.user_id}">
          <img src="${avatarUrl}" alt="${video.author_username}" class="author-avatar" onerror="this.src='../assets/images/logo.svg'">
        </a>
        <button class="btn-follow-badge ${video.is_following ? "following" : ""}" 
                data-user-id="${video.user_id}" 
                title="${video.is_following ? "Đang theo dõi" : "Theo dõi"}">
          ${video.is_following ? "✓" : "+"}
        </button>
      </div>

      <!-- 2. Nút Tim (Like) -->
      <div class="action-item like ${video.is_liked ? "liked" : ""}" data-video-id="${video.id}" title="Thích video">
        <div class="action-icon-wrap">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="${video.is_liked ? "#ef4444" : "none"}" stroke="${video.is_liked ? "#ef4444" : "#ffffff"}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
          </svg>
        </div>
        <span class="action-label" id="like-count-${video.id}">${video.like_count || 0}</span>
      </div>

      <!-- 3. Nút Bình luận -->
      <div class="action-item comment" data-video-id="${video.id}" title="Bình luận">
        <div class="action-icon-wrap">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
          </svg>
        </div>
        <span class="action-label" id="comment-count-${video.id}">${video.comment_count || 0}</span>
      </div>

      <!-- 4. Nút Chia sẻ -->
      <div class="action-item share" data-video-id="${video.id}" title="Chia sẻ video">
        <div class="action-icon-wrap">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="18" cy="5" r="3"></circle>
            <circle cx="6" cy="12" r="3"></circle>
            <circle cx="18" cy="19" r="3"></circle>
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
          </svg>
        </div>
        <span class="action-label">Chia sẻ</span>
      </div>
    </div>
  `;

  // Sự kiện phát / tạm dừng video
  const videoEl = card.querySelector(".feed-video-element");
  const playOverlay = card.querySelector(".feed-video-overlay-play");
  videoEl.addEventListener("click", () => {
    if (videoEl.paused) {
      videoEl.play();
      playOverlay.classList.remove("visible");
    } else {
      videoEl.pause();
      playOverlay.classList.add("visible");
    }
  });

  // Sự kiện Nút Theo dõi trên Avatar
  const followBtn = card.querySelector(".btn-follow-badge");
  followBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    handleFollowAction(video.user_id, followBtn);
  });

  // Sự kiện Nút Tim (Like)
  const likeBtn = card.querySelector(".action-item.like");
  likeBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    handleLikeAction(video.id, likeBtn);
  });

  // Sự kiện Nút Bình luận (mở bảng trượt lên)
  const commentBtn = card.querySelector(".action-item.comment");
  commentBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    openCommentsSheet(video.id);
  });

  // Sự kiện Nút Chia sẻ
  const shareBtn = card.querySelector(".action-item.share");
  shareBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    handleShareAction(video.id);
  });

  return card;
}

// ---------- 4. XỬ LÝ THEO DÕI (FOLLOW / UNFOLLOW) ----------
async function handleFollowAction(targetUserId, buttonEl) {
  const token = localStorage.getItem("token") || localStorage.getItem("access_token");
  if (!token) {
    if (typeof showLoginModal === "function") showLoginModal();
    return;
  }

  const isFollowing = buttonEl.classList.contains("following");
  try {
    if (!isFollowing) {
      // Optimistic update
      buttonEl.classList.add("following");
      buttonEl.innerText = "✓";
      buttonEl.title = "Đang theo dõi";
      showToast("Đã theo dõi người dùng!", "success");

      await api.post(`/users/${targetUserId}/follow`);
    } else {
      // Bỏ theo dõi
      buttonEl.classList.remove("following");
      buttonEl.innerText = "+";
      buttonEl.title = "Theo dõi";
      showToast("Đã hủy theo dõi", "success");

      await api.delete(`/users/${targetUserId}/follow`);
    }
  } catch (err) {
    // Rollback nếu lỗi
    if (!isFollowing) {
      buttonEl.classList.remove("following");
      buttonEl.innerText = "+";
    } else {
      buttonEl.classList.add("following");
      buttonEl.innerText = "✓";
    }
    showToast(err.message || "Lỗi cập nhật theo dõi", "error");
  }
}

// ---------- 5. XỬ LÝ TIM (LIKE / UNLIKE) CẬP NHẬT NGAY ----------
async function handleLikeAction(videoId, buttonEl) {
  const token = localStorage.getItem("token") || localStorage.getItem("access_token");
  if (!token) {
    if (typeof showLoginModal === "function") showLoginModal();
    return;
  }

  const countEl = document.getElementById(`like-count-${videoId}`);
  const isLiked = buttonEl.classList.contains("liked");
  const currentCount = parseInt(countEl.innerText, 10) || 0;
  const svg = buttonEl.querySelector("svg");

  // Optimistic UI Update ngay lập tức
  if (!isLiked) {
    buttonEl.classList.add("liked");
    countEl.innerText = currentCount + 1;
    svg.setAttribute("fill", "#ef4444");
    svg.setAttribute("stroke", "#ef4444");

    try {
      await api.post(`/videos/${videoId}/likes`);
    } catch (err) {
      // Rollback nếu API lỗi
      buttonEl.classList.remove("liked");
      countEl.innerText = currentCount;
      svg.setAttribute("fill", "none");
      svg.setAttribute("stroke", "#ffffff");
      showToast(err.message || "Không thể thích video", "error");
    }
  } else {
    buttonEl.classList.remove("liked");
    countEl.innerText = Math.max(0, currentCount - 1);
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "#ffffff");

    try {
      await api.delete(`/videos/${videoId}/likes`);
    } catch (err) {
      // Rollback nếu API lỗi
      buttonEl.classList.add("liked");
      countEl.innerText = currentCount;
      svg.setAttribute("fill", "#ef4444");
      svg.setAttribute("stroke", "#ef4444");
      showToast(err.message || "Không thể bỏ thích", "error");
    }
  }
}

// ---------- 6. XỬ LÝ CHIA SẺ VIDEO ----------
async function handleShareAction(videoId) {
  const shareUrl = `${window.location.origin}${window.location.pathname}?v=${videoId}`;

  try {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(shareUrl);
      showToast("Đã sao chép liên kết video vào bộ nhớ tạm!", "success");
    } else {
      prompt("Sao chép liên kết video bên dưới:", shareUrl);
    }

    // Ghi nhận lượt share lên backend
    const token = localStorage.getItem("token") || localStorage.getItem("access_token");
    if (token) {
      await api.post(`/videos/${videoId}/share`);
    }
  } catch (err) {
    showToast("Không thể sao chép liên kết", "error");
  }
}

// ---------- 7. BẢNG BÌNH LUẬN TRƯỢT LÊN (SLIDE-UP SHEET) ----------
function initCommentsSheet() {
  const overlay = document.getElementById("comments-overlay");
  const sheet = document.getElementById("comments-bottom-sheet");
  const btnClose = document.getElementById("btn-close-comments");
  const btnSubmit = document.getElementById("btn-submit-comment");
  const inputComment = document.getElementById("input-comment-text");
  const btnCancelReply = document.getElementById("btn-cancel-reply");

  overlay.addEventListener("click", closeCommentsSheet);
  btnClose.addEventListener("click", closeCommentsSheet);

  btnCancelReply.addEventListener("click", () => {
    cancelReplyState();
  });

  inputComment.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitComment();
    }
  });

  btnSubmit.addEventListener("click", submitComment);
}

function openCommentsSheet(videoId) {
  currentVideoIdForComments = videoId;
  cancelReplyState();

  const overlay = document.getElementById("comments-overlay");
  const sheet = document.getElementById("comments-bottom-sheet");

  overlay.classList.add("active");
  sheet.classList.add("open");

  loadCommentsForSheet(videoId);
}

function closeCommentsSheet() {
  const overlay = document.getElementById("comments-overlay");
  const sheet = document.getElementById("comments-bottom-sheet");

  sheet.classList.remove("open");
  overlay.classList.remove("active");
  currentVideoIdForComments = null;
  cancelReplyState();
}

function cancelReplyState() {
  currentReplyingCommentId = null;
  currentReplyingUsername = null;
  const banner = document.getElementById("reply-banner");
  if (banner) banner.classList.remove("active");
  const input = document.getElementById("input-comment-text");
  if (input) input.placeholder = "Thêm bình luận...";
}

async function loadCommentsForSheet(videoId) {
  const listEl = document.getElementById("sheet-comments-list");
  const titleEl = document.getElementById("sheet-comment-title");
  listEl.innerHTML = `<div style="text-align:center;padding:30px;color:var(--color-muted);">Đang tải bình luận...</div>`;

  try {
    const comments = await api.get(`/videos/${videoId}/comments`);
    titleEl.innerText = `Bình luận (${comments.length})`;

    // Cập nhật số trên icon feed
    const countEl = document.getElementById(`comment-count-${videoId}`);
    if (countEl) countEl.innerText = comments.length;

    if (!comments || comments.length === 0) {
      listEl.innerHTML = `
        <div style="text-align:center;padding:40px 10px;color:var(--color-muted);">
          <div style="font-size:24px;margin-bottom:8px;">💬</div>
          <div>Chưa có bình luận nào. Hãy là người đầu tiên bình luận!</div>
        </div>`;
      return;
    }

    listEl.innerHTML = "";
    comments.forEach((c) => {
      listEl.appendChild(createCommentRow(c));
    });
  } catch (err) {
    listEl.innerHTML = `<div style="color:var(--color-danger);text-align:center;padding:20px;">Lỗi tải bình luận: ${err.message}</div>`;
  }
}

function createCommentRow(comment) {
  const row = document.createElement("div");
  row.className = "comment-row";
  row.id = `comment-row-${comment.id}`;

  const currentU = getCurrentUser();
  const canDelete = currentU && (currentU.id === comment.user_id || currentU.role === "ADMIN");

  const formattedTime = formatTimeAgo(comment.created_at);

  row.innerHTML = `
    <img src="../assets/images/logo.svg" alt="avatar" class="comment-avatar">
    <div class="comment-content-box">
      <div class="comment-author-name">
        <a href="profile.html?user_id=${comment.user_id}" style="color:inherit;text-decoration:none;">User #${comment.user_id}</a>
        <span class="comment-time">${formattedTime}</span>
      </div>
      <div class="comment-text">
        ${comment.parent_id ? `<span class="reply-badge-target">Trả lời #${comment.parent_id}</span>` : ""}
        ${escapeHtml(comment.content)}
      </div>
      <div class="comment-actions">
        <button class="comment-act-btn reply-btn" data-id="${comment.id}" data-author="User #${comment.user_id}">Trả lời</button>
        ${canDelete ? `<button class="comment-act-btn delete" data-id="${comment.id}">Xóa</button>` : ""}
      </div>
    </div>
  `;

  // Bấm trả lời
  const replyBtn = row.querySelector(".reply-btn");
  if (replyBtn) {
    replyBtn.addEventListener("click", () => {
      currentReplyingCommentId = comment.id;
      currentReplyingUsername = `User #${comment.user_id}`;
      document.getElementById("reply-to-user").innerText = `@${currentReplyingUsername}`;
      document.getElementById("reply-banner").classList.add("active");
      const input = document.getElementById("input-comment-text");
      input.placeholder = `Trả lời ${currentReplyingUsername}...`;
      input.focus();
    });
  }

  // Bấm xóa
  const deleteBtn = row.querySelector(".comment-act-btn.delete");
  if (deleteBtn) {
    deleteBtn.addEventListener("click", async () => {
      if (!confirm("Bạn có chắc chắn muốn xóa bình luận này?")) return;
      try {
        await api.delete(`/comments/${comment.id}`);
        row.remove();
        showToast("Đã xóa bình luận", "success");
        // Giảm số đếm
        if (currentVideoIdForComments) {
          const countEl = document.getElementById(`comment-count-${currentVideoIdForComments}`);
          if (countEl) {
            const current = parseInt(countEl.innerText, 10) || 1;
            countEl.innerText = Math.max(0, current - 1);
          }
        }
      } catch (err) {
        showToast(err.message || "Lỗi xóa bình luận", "error");
      }
    });
  }

  return row;
}

async function submitComment() {
  const token = localStorage.getItem("token") || localStorage.getItem("access_token");
  if (!token) {
    if (typeof showLoginModal === "function") showLoginModal();
    return;
  }

  const input = document.getElementById("input-comment-text");
  const content = input.value.trim();
  if (!content) return;

  if (!currentVideoIdForComments) return;

  const btnSubmit = document.getElementById("btn-submit-comment");
  btnSubmit.disabled = true;

  try {
    const payload = {
      content: content,
      parent_id: currentReplyingCommentId || null,
    };

    const newComment = await api.post(`/videos/${currentVideoIdForComments}/comments`, payload);

    input.value = "";
    cancelReplyState();

    const listEl = document.getElementById("sheet-comments-list");
    // Thêm comment mới vào danh sách
    const newRow = createCommentRow(newComment);
    listEl.prepend(newRow);

    // Cập nhật số bình luận ngay lập tức
    const countEl = document.getElementById(`comment-count-${currentVideoIdForComments}`);
    if (countEl) {
      const current = parseInt(countEl.innerText, 10) || 0;
      countEl.innerText = current + 1;
    }

    const titleEl = document.getElementById("sheet-comment-title");
    if (titleEl) {
      const allRows = listEl.querySelectorAll(".comment-row");
      titleEl.innerText = `Bình luận (${allRows.length})`;
    }

    showToast("Đã đăng bình luận!", "success");
  } catch (err) {
    showToast(err.message || "Không thể đăng bình luận", "error");
  } finally {
    btnSubmit.disabled = false;
  }
}

// ---------- 8. TỰ ĐỘNG PHÁT KHI CUỘN ĐẾN (INTERSECTION OBSERVER) ----------
function initIntersectionObserver() {
  if (observer) observer.disconnect();

  const options = {
    root: document.getElementById("feed-container"),
    threshold: 0.65, // video hiển thị trên 65% màn hình thì phát
  };

  observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      const videoEl = entry.target.querySelector(".feed-video-element");
      const playOverlay = entry.target.querySelector(".feed-video-overlay-play");
      if (!videoEl) return;

      if (entry.isIntersecting) {
        videoEl.play().catch(() => {});
        if (playOverlay) playOverlay.classList.remove("visible");
      } else {
        videoEl.pause();
        if (playOverlay) playOverlay.classList.remove("visible");
      }
    });
  }, options);

  const cards = document.querySelectorAll(".feed-video-card");
  cards.forEach((c) => observer.observe(c));
}

// ---------- 9. TIỆN ÍCH ----------
function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/[&<>'"]/g, (tag) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  }[tag] || tag));
}

function formatTimeAgo(dateString) {
  if (!dateString) return "";
  const date = new Date(dateString);
  const now = new Date();
  const diffSec = Math.floor((now - date) / 1000);

  if (diffSec < 60) return "vừa xong";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} phút trước`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} giờ trước`;
  return `${Math.floor(diffSec / 86400)} ngày trước`;
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
