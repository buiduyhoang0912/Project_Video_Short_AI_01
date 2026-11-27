// Logic xử lý Feed video, Like, Comment (bảng trượt lên), Share, và Follow

let currentFeedType = "for-you";
let currentVideoIdForComments = null;
let currentReplyingCommentId = null;
let currentReplyingUsername = null;
let observer = null;
// Trạng thái phục vụ Task T3D2282: Âm thanh, Phân trang cuộn và Đếm view
let isMuted = true; // Mặc định tắt tiếng để trình duyệt cho phép tự phát (Autoplay Policy)
let currentSkip = 0;
let isLoadingMore = false;
let hasMoreVideos = true;
const PAGE_SIZE = 5;

document.addEventListener("DOMContentLoaded", () => {
  initFeedTabs();
  initCommentsSheet();
  initProductsSheet();
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
// ---------- 2. TẢI DANH SÁCH VIDEO FEED ----------
async function loadFeed(type) {
  const container = document.getElementById("feed-container");
  container.innerHTML = `
    <div style="color:#aaa;text-align:center;padding:60px 20px;">
      <div style="font-size:24px;margin-bottom:8px;">⏳</div>
      <div>Đang tải video...</div>
    </div>`;

  // Reset trạng thái phân trang khi chuyển tab hoặc tải lại
  currentSkip = 0;
  hasMoreVideos = true;
  isLoadingMore = false;

  try {
    let videos = [];
    if (type === "following") {
      videos = await api.get("/videos/feed/following", { skip: 0, limit: PAGE_SIZE });
    } else {
      videos = await api.get("/videos/feed/for-you", { skip: 0, limit: PAGE_SIZE });
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

    if (videos.length < PAGE_SIZE) {
      hasMoreVideos = false;
    }
    currentSkip = videos.length;

    container.innerHTML = "";
    videos.forEach((video) => {
      const card = createVideoCard(video);
      container.appendChild(card);
    });

    initIntersectionObserver();
    initFeedScrollListener(); // Lắng nghe cuộn gần cuối để tải thêm

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
      <video class="feed-video-element" loop playsinline preload="metadata" ${isMuted ? "muted" : ""} src="${videoSrc}">
        Trình duyệt của bạn không hỗ trợ thẻ video HTML5.
      </video>
      <div class="feed-video-overlay-play">▶</div>

      <!-- Nút Bật/Tắt âm thanh (Task T3D2282) -->
      <button class="feed-btn-volume" type="button" title="Bật/Tắt âm thanh">
        <span class="volume-icon">${isMuted ? "🔇" : "🔊"}</span>
      </button>

    <!-- Thông tin video (góc trái dưới) -->
    <div class="video-info-bottom">
      ${(video.products && video.products.length > 0) ? `
        <div class="feed-product-tag-pill" data-video-id="${video.id}" title="Xem ${video.products.length} sản phẩm gắn trong video">
          <span class="product-tag-icon">🛒</span>
          <span class="product-tag-title">${escapeHtml(video.products[0].name)}</span>
          <span class="product-tag-badge">${video.products.length > 1 ? `+${video.products.length - 1}` : "Xem"}</span>
        </div>
      ` : ""}
      <a href="profile.html?user_id=${video.user_id}">
        @${video.author_username}
        <span style="font-size:12px;font-weight:normal;opacity:0.8;">(${video.author_name})</span>
      </a>
      <p class="video-desc">${escapeHtml(video.title || "")} ${video.description ? "- " + escapeHtml(video.description) : ""}</p>
      <a href="video.html?id=${video.id}" style="font-size:12px;font-weight:600;color:#93c5fd;margin-top:6px;display:inline-block;">
        ↗ Xem trang riêng (/video/${video.id})
      </a>
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
      <div class="action-item share" data-video-id="${video.id}" title="Chia sẻ & sao chép link video">
        <div class="action-icon-wrap">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="18" cy="5" r="3"></circle>
            <circle cx="6" cy="12" r="3"></circle>
            <circle cx="18" cy="19" r="3"></circle>
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
          </svg>
        </div>
        <span class="action-label" id="share-count-${video.id}">${video.share_count || 0}</span>
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

  // Sự kiện Nút Âm thanh (Bật/Tắt tiếng - Task T3D2282)
  const volumeBtn = card.querySelector(".feed-btn-volume");
  if (volumeBtn) {
    volumeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleMute();
    });
  }

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

  // Sự kiện Nút Giỏ hàng / Thẻ sản phẩm trên video (Task T3D2296)
  const productPill = card.querySelector(".feed-product-tag-pill");
  if (productPill) {
    productPill.addEventListener("click", (e) => {
      e.stopPropagation();
      openProductsSheet(video);
    });
  }

  const cartActionBtn = card.querySelector(".feed-cart-action-btn");
  if (cartActionBtn) {
    cartActionBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      openProductsSheet(video);
    });
  }

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
  const basePath = window.location.pathname.includes("/pages/")
    ? window.location.pathname.split("/pages/")[0]
    : "";
  const shareUrl = `${window.location.origin}${basePath}/pages/video.html?id=${videoId}`;

  const countEl = document.getElementById(`share-count-${videoId}`);
  const oldCount = countEl ? parseInt(countEl.innerText, 10) || 0 : 0;

  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(shareUrl);
      showToast("Đã sao chép liên kết video vào bộ nhớ tạm!", "success");
    } else {
      prompt("Sao chép liên kết video bên dưới:", shareUrl);
    }

    if (countEl) countEl.innerText = oldCount + 1;

    // Ghi nhận lượt share lên backend và đồng bộ số đếm
    const res = await api.post(`/videos/${videoId}/share`);
    if (countEl && res && typeof res.share_count === "number") {
      countEl.innerText = res.share_count;
    }
  } catch (err) {
    if (countEl) countEl.innerText = oldCount;
    showToast(err.message || "Không thể chia sẻ liên kết", "error");
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

// ---------- BẢNG THẺ SẢN PHẨM GẮN TRONG VIDEO (TASK T3D2296) ----------
function initProductsSheet() {
  const overlay = document.getElementById("products-overlay");
  const btnClose = document.getElementById("btn-close-products");

  if (overlay) overlay.addEventListener("click", closeProductsSheet);
  if (btnClose) btnClose.addEventListener("click", closeProductsSheet);
}

async function openProductsSheet(video) {
  const overlay = document.getElementById("products-overlay");
  const sheet = document.getElementById("products-bottom-sheet");
  const countEl = document.getElementById("sheet-product-count");
  const listEl = document.getElementById("sheet-products-list");

  if (!sheet || !overlay) return;

  overlay.classList.add("active");
  sheet.classList.add("open");

  let products = video.products || [];
  if (products.length === 0) {
    listEl.innerHTML = `<div class="muted" style="text-align:center;padding:24px;">Đang tải sản phẩm...</div>`;
    try {
      products = await api.get(`/videos/${video.id}/products`);
      video.products = products;
    } catch (_) {
      products = [];
    }
  }

  if (countEl) countEl.textContent = products.length;

  if (products.length === 0) {
    listEl.innerHTML = `<div class="muted" style="text-align:center;padding:32px 16px;">Video này hiện không có sản phẩm gắn kèm.</div>`;
    return;
  }

  listEl.innerHTML = products.map((p) => {
    let thumb = p.thumbnail_url || "";
    if (thumb && thumb.startsWith("/uploads/")) {
      thumb = `${CONFIG.API_BASE_URL.replace("/api", "")}${thumb}`;
    } else if (!thumb) {
      thumb = "../assets/images/logo.svg";
    }

    const priceText = Number(p.price || 0).toLocaleString("vi-VN") + " ₫";
    const shopName = p.shop_name ? `🏪 ${escapeHtml(p.shop_name)}` : "";

    return `
      <div class="tagged-sheet-item">
        <a href="product.html?id=${p.id}" class="tagged-sheet-thumb-link">
          <img src="${escapeHtml(thumb)}" alt="${escapeHtml(p.name)}" class="tagged-sheet-thumb" onerror="this.src='../assets/images/logo.svg'">
        </a>
        <div class="tagged-sheet-info">
          <a href="product.html?id=${p.id}" class="tagged-sheet-name">${escapeHtml(p.name)}</a>
          <div class="tagged-sheet-price">${priceText}</div>
          ${shopName ? `<div class="tagged-sheet-shop">${shopName}</div>` : ""}
        </div>
        <a href="product.html?id=${p.id}" class="btn btn-small btn-primary btn-sheet-view">
          Xem chi tiết
        </a>
      </div>
    `;
  }).join("");
}

function closeProductsSheet() {
  const overlay = document.getElementById("products-overlay");
  const sheet = document.getElementById("products-bottom-sheet");

  if (sheet) sheet.classList.remove("open");
  if (overlay) overlay.classList.remove("active");
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
    const byId = new Map();
    comments.forEach((c) => byId.set(c.id, c));

    const roots = comments.filter((c) => !c.parent_id || !byId.has(c.parent_id));
    const repliesByParent = new Map();
    comments.forEach((c) => {
      if (c.parent_id && byId.has(c.parent_id)) {
        if (!repliesByParent.has(c.parent_id)) repliesByParent.set(c.parent_id, []);
        repliesByParent.get(c.parent_id).push(c);
      }
    });

    roots.forEach((c) => {
      const thread = document.createElement("div");
      thread.className = "comment-thread";
      thread.id = `comment-thread-${c.id}`;
      thread.appendChild(createCommentRow(c));

      const repliesBox = document.createElement("div");
      repliesBox.className = "comment-replies";
      repliesBox.id = `comment-replies-${c.id}`;
      const childList = repliesByParent.get(c.id) || [];
      const parentName = c.display_name || c.username || `User #${c.user_id}`;
      childList.forEach((r) => {
        repliesBox.appendChild(createCommentRow(r, parentName));
      });
      thread.appendChild(repliesBox);
      listEl.appendChild(thread);
    });
  } catch (err) {
    listEl.innerHTML = `<div style="color:var(--color-danger);text-align:center;padding:20px;">Lỗi tải bình luận: ${err.message}</div>`;
  }
}

function createCommentRow(comment, parentAuthorName = null) {
  const row = document.createElement("div");
  row.className = comment.parent_id ? "comment-row is-reply" : "comment-row";
  row.id = `comment-row-${comment.id}`;

  const currentU = getCurrentUser();
  const canDelete = currentU && (currentU.id === comment.user_id || currentU.role === "ADMIN");

  const formattedTime = formatTimeAgo(comment.created_at);
  const authorName = comment.display_name || comment.username || `User #${comment.user_id}`;
  const avatarSrc = comment.avatar_url || "../assets/images/logo.svg";

  row.innerHTML = `
    <img src="${escapeHtml(avatarSrc)}" alt="${escapeHtml(authorName)}" class="comment-avatar" onerror="this.src='../assets/images/logo.svg'">
    <div class="comment-content-box">
      <div class="comment-author-name">
        <a href="profile.html?user_id=${comment.user_id}" style="color:inherit;text-decoration:none;">${escapeHtml(authorName)}</a>
        <span class="comment-time">${formattedTime}</span>
      </div>
      <div class="comment-text">
        ${comment.parent_id ? `<span class="reply-badge-target">@${escapeHtml(parentAuthorName || `#${comment.parent_id}`)}</span>` : ""}
        ${escapeHtml(comment.content)}
      </div>
      <div class="comment-actions">
        <button class="comment-act-btn reply-btn" data-id="${comment.id}" data-author="${escapeHtml(authorName)}">Trả lời</button>
        ${canDelete ? `<button class="comment-act-btn delete" data-id="${comment.id}">Xóa</button>` : ""}
      </div>
    </div>
  `;

  // Bấm trả lời (nếu đang bấm vào reply thì gắn vào bình luận gốc cùng thread)
  const replyBtn = row.querySelector(".reply-btn");
  if (replyBtn) {
    replyBtn.addEventListener("click", () => {
      currentReplyingCommentId = comment.parent_id || comment.id;
      currentReplyingUsername = authorName;
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
    // Xóa thông báo "Chưa có bình luận nào" nếu có
    if (listEl.querySelectorAll(".comment-row").length === 0) {
      listEl.innerHTML = "";
    }

    if (newComment.parent_id) {
      const repliesBox = document.getElementById(`comment-replies-${newComment.parent_id}`);
      const parentRow = document.getElementById(`comment-row-${newComment.parent_id}`);
      const parentAuthor = parentRow?.querySelector(".comment-author-name a")?.textContent || null;
      const newRow = createCommentRow(newComment, parentAuthor);
      if (repliesBox) {
        repliesBox.appendChild(newRow);
      } else {
        listEl.prepend(newRow);
      }
    } else {
      const thread = document.createElement("div");
      thread.className = "comment-thread";
      thread.id = `comment-thread-${newComment.id}`;
      thread.appendChild(createCommentRow(newComment));
      const repliesBox = document.createElement("div");
      repliesBox.className = "comment-replies";
      repliesBox.id = `comment-replies-${newComment.id}`;
      thread.appendChild(repliesBox);
      listEl.prepend(thread);
    }

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
// ---------- 8. TỰ ĐỘNG PHÁT KHI CUỘN ĐẾN & ĐẾM LƯỢT XEM (INTERSECTION OBSERVER) ----------
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
      const card = entry.target;
      const videoId = card.dataset.videoId;
      if (!videoEl) return;

      if (entry.isIntersecting) {
        videoEl.muted = isMuted;
        videoEl.play().catch(() => {
          // Trình duyệt chặn autoplay có tiếng -> tự động fallback sang muted
          if (!videoEl.muted) {
            videoEl.muted = true;
            isMuted = true;
            document.querySelectorAll(".feed-btn-volume .volume-icon").forEach((ic) => (ic.innerText = "🔇"));
            videoEl.play().catch(() => {});
          }
        });
        if (playOverlay) playOverlay.classList.remove("visible");

        // Ghi nhận lượt xem khi xem quá 3 giây (Task T3D207C & T3D2282)
        if (videoId && !card.dataset.viewRecorded) {
          card.viewTimer = setTimeout(async () => {
            try {
              await api.post(`/videos/${videoId}/views`);
              card.dataset.viewRecorded = "true";
            } catch (e) {
              // Bỏ qua lỗi tăng view nếu mạng gián đoạn
            }
          }, 3000);
        }
      } else {
        videoEl.pause();
        if (playOverlay) playOverlay.classList.remove("visible");

        // Hủy đếm 3 giây nếu người dùng cuộn đi trước 3s
        if (card.viewTimer) {
          clearTimeout(card.viewTimer);
          card.viewTimer = null;
        }
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
  let normalized = String(dateString).trim().replace(" ", "T");
  if (!/[zZ]|[+-]\d{2}:?\d{2}$/.test(normalized)) normalized += "Z";
  const date = new Date(normalized);
  const now = new Date();
  const diffSec = Math.max(0, Math.floor((now - date) / 1000));

  if (diffSec < 60) return "vừa xong";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} phút trước`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} giờ trước`;
  return `${Math.floor(diffSec / 86400)} ngày trước`;
}

// Dùng showToast chung từ utils.js (góc trên phải, z-index: 9999)

// ---------- 10. HÀM HỖ TRỢ TASK T3D2282 (BẬT/TẮT TIẾNG & TẢI THÊM KHI GẦN CUỐI) ----------

// Hàm bật / tắt tiếng cho tất cả video trên Feed
function toggleMute() {
  isMuted = !isMuted;
  const allVideos = document.querySelectorAll(".feed-video-element");
  allVideos.forEach((vid) => {
    vid.muted = isMuted;
  });
  const allIcons = document.querySelectorAll(".feed-btn-volume .volume-icon");
  allIcons.forEach((ic) => {
    ic.innerText = isMuted ? "🔇" : "🔊";
  });
  showToast(isMuted ? "Đã tắt tiếng" : "Đã bật tiếng");
}

// Lắng nghe sự kiện cuộn của feed-container: cuộn gần chạm đáy thì tự tải thêm
let scrollListenerAttached = false;
function initFeedScrollListener() {
  if (scrollListenerAttached) return;
  const container = document.getElementById("feed-container");
  if (!container) return;

  container.addEventListener("scroll", () => {
    // Khi cuộn xuống cách đáy dưới 500px -> tự động tải thêm
    if (container.scrollTop + container.clientHeight >= container.scrollHeight - 500) {
      loadMoreVideos();
    }
  });
  scrollListenerAttached = true;
}

// Hàm tải thêm video cho trang tiếp theo
async function loadMoreVideos() {
  if (isLoadingMore || !hasMoreVideos) return;
  isLoadingMore = true;

  const container = document.getElementById("feed-container");
  showLoadingMoreIndicator(container);

  try {
    const endpoint = currentFeedType === "following" ? "/videos/feed/following" : "/videos/feed/for-you";
    const newVideos = await api.get(endpoint, { skip: currentSkip, limit: PAGE_SIZE });

    removeLoadingMoreIndicator();

    if (!newVideos || newVideos.length === 0) {
      hasMoreVideos = false;
      showEndOfFeedNotice(container);
      return;
    }

    if (newVideos.length < PAGE_SIZE) {
      hasMoreVideos = false;
    }

    currentSkip += newVideos.length;

    newVideos.forEach((video) => {
      const card = createVideoCard(video);
      container.appendChild(card);
      if (observer) observer.observe(card);
    });

    if (!hasMoreVideos) {
      showEndOfFeedNotice(container);
    }
  } catch (err) {
    console.error("Lỗi khi tải thêm video:", err);
    removeLoadingMoreIndicator();
  } finally {
    isLoadingMore = false;
  }
}

function showLoadingMoreIndicator(container) {
  if (document.getElementById("feed-loading-more-bar")) return;
  const el = document.createElement("div");
  el.id = "feed-loading-more-bar";
  el.className = "feed-loading-more";
  el.innerHTML = `
    <div class="feed-loading-spinner"></div>
    <span>Đang tải thêm video...</span>
  `;
  container.appendChild(el);
}

function removeLoadingMoreIndicator() {
  const el = document.getElementById("feed-loading-more-bar");
  if (el) el.remove();
}

function showEndOfFeedNotice(container) {
  if (document.getElementById("feed-end-notice-bar")) return;
  const el = document.createElement("div");
  el.id = "feed-end-notice-bar";
  el.className = "feed-end-notice";
  el.innerText = "✨ Bạn đã xem hết tất cả video hiện có.";
  container.appendChild(el);
}