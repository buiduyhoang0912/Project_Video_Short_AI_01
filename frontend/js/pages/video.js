// Trang xem riêng một video (/video/{id}) và chia sẻ (Task T3D245C)

let currentVideoId = null;
let currentVideoData = null;
let replyingCommentId = null;
let replyingUsername = null;

document.addEventListener("DOMContentLoaded", () => {
  currentVideoId = getVideoIdFromUrl();
  initVideoPageEvents();

  if (!currentVideoId) {
    showUnavailableState(
      null,
      "Không tìm thấy mã video hợp lệ trong đường dẫn chia sẻ."
    );
    return;
  }

  const routeBadge = document.getElementById("video-route-badge");
  if (routeBadge) routeBadge.textContent = `/video/${currentVideoId}`;

  loadSingleVideo(currentVideoId);
});

// Lấy ID video từ ?id=, ?v=, ?video_id=, #id hoặc đường dẫn /video/{id}
function getVideoIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const queryId =
    params.get("id") || params.get("v") || params.get("video_id");
  if (queryId && /^\d+$/.test(queryId.trim())) {
    return parseInt(queryId.trim(), 10);
  }

  const pathMatch = window.location.pathname.match(/\/video\/(\d+)/i);
  if (pathMatch) {
    return parseInt(pathMatch[1], 10);
  }

  const hashMatch = window.location.hash.match(/^#\/?(\d+)$/);
  if (hashMatch) {
    return parseInt(hashMatch[1], 10);
  }

  return null;
}

// Tạo đường dẫn chia sẻ chuẩn cho trang xem riêng video
function buildShareUrl(videoId) {
  const origin = window.location.origin;
  const pathname = window.location.pathname;
  if (pathname.includes("/pages/")) {
    const basePages = pathname.split("/pages/")[0];
    return `${origin}${basePages}/pages/video.html?id=${videoId}`;
  }
  return `${origin}/pages/video.html?id=${videoId}`;
}

function initVideoPageEvents() {
  const btnCopyLink = document.getElementById("btn-copy-link");
  const btnSharePill = document.getElementById("btn-share-video");
  const btnLike = document.getElementById("btn-like-video");
  const btnFocusComment = document.getElementById("btn-focus-comment");
  const btnFollow = document.getElementById("btn-video-follow");
  const btnToggleVis = document.getElementById("btn-toggle-visibility");
  const btnUnhide = document.getElementById("btn-unhide-video");
  const commentForm = document.getElementById("single-comment-form");
  const btnCancelReply = document.getElementById("btn-single-cancel-reply");
  const shareInput = document.getElementById("share-link-input");

  if (btnCopyLink) {
    btnCopyLink.addEventListener("click", () => handleCopyAndCountShare());
  }
  if (btnSharePill) {
    btnSharePill.addEventListener("click", () => handleCopyAndCountShare());
  }
  if (shareInput) {
    shareInput.addEventListener("click", () => shareInput.select());
  }
  if (btnLike) {
    btnLike.addEventListener("click", () => handleSingleLike());
  }
  if (btnFocusComment) {
    btnFocusComment.addEventListener("click", () => {
      const input = document.getElementById("single-comment-input");
      if (input) {
        input.focus();
        input.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    });
  }
  if (btnFollow) {
    btnFollow.addEventListener("click", () => handleSingleFollow());
  }
  if (btnToggleVis) {
    btnToggleVis.addEventListener("click", () => handleToggleVisibility("HIDDEN"));
  }
  if (btnUnhide) {
    btnUnhide.addEventListener("click", () => handleToggleVisibility("VISIBLE"));
  }
  if (btnCancelReply) {
    btnCancelReply.addEventListener("click", () => clearReplyBanner());
  }
  if (commentForm) {
    commentForm.addEventListener("submit", (e) => {
      e.preventDefault();
      handleSubmitSingleComment();
    });
  }
}

// ---------- 1. TẢI CHI TIẾT VIDEO ----------
async function loadSingleVideo(videoId) {
  const loadingEl = document.getElementById("video-loading");
  const unavailableEl = document.getElementById("video-unavailable");
  const contentEl = document.getElementById("video-detail-content");
  const btnToggleVis = document.getElementById("btn-toggle-visibility");

  if (loadingEl) loadingEl.style.display = "block";
  if (unavailableEl) unavailableEl.style.display = "none";
  if (contentEl) contentEl.style.display = "none";
  if (btnToggleVis) btnToggleVis.style.display = "none";

  try {
    const video = await api.get(`/videos/${videoId}`);
    currentVideoData = video;

    if (loadingEl) loadingEl.style.display = "none";

    // Kiểm tra nếu video bị ẩn (status === "HIDDEN" hoặc is_available === false)
    if (video.status === "HIDDEN" || video.is_available === false) {
      showUnavailableState(
        video,
        video.unavailable_message ||
          "Video này đã bị ẩn bởi người đăng hoặc quản trị viên và hiện không còn khả dụng."
      );
      return;
    }

    renderVideoDetail(video);
    loadSingleComments(videoId);
  } catch (err) {
    if (loadingEl) loadingEl.style.display = "none";
    if (err && (err.status === 404 || err.status === 410)) {
      showUnavailableState(
        null,
        "Video không còn khả dụng. Liên kết chia sẻ có thể không tồn tại hoặc video đã bị xóa."
      );
    } else {
      showUnavailableState(
        null,
        err.message || "Không thể tải video vào lúc này. Vui lòng thử lại sau."
      );
    }
  }
}

// ---------- 2. HIỂN THỊ THÔNG BÁO VIDEO BỊ ẨN / KHÔNG CÒN KHẢ DỤNG ----------
function showUnavailableState(video, message) {
  const loadingEl = document.getElementById("video-loading");
  const unavailableEl = document.getElementById("video-unavailable");
  const contentEl = document.getElementById("video-detail-content");
  const descEl = document.getElementById("unavailable-desc");
  const titleEl = document.getElementById("unavailable-title");
  const unhideWrap = document.getElementById("owner-unhide-wrap");
  const player = document.getElementById("single-video-player");

  if (player) {
    player.pause();
    player.removeAttribute("src");
  }

  if (loadingEl) loadingEl.style.display = "none";
  if (contentEl) contentEl.style.display = "none";
  if (unavailableEl) unavailableEl.style.display = "block";

  if (titleEl) {
    titleEl.textContent = "Video không còn khả dụng";
  }
  if (descEl) {
    descEl.textContent =
      message || "Video này đã bị ẩn hoặc không còn khả dụng.";
  }

  // Nếu người dùng hiện tại là chủ video hoặc ADMIN -> cho phép hiện lại video
  const currentUser = typeof getCurrentUser === "function" ? getCurrentUser() : null;
  const canManage =
    video &&
    currentUser &&
    (currentUser.id === video.user_id || currentUser.role === "ADMIN");

  if (unhideWrap) {
    unhideWrap.style.display = canManage ? "block" : "none";
  }
}

// ---------- 3. RENDER NỘI DUNG VIDEO ----------
function renderVideoDetail(video) {
  const contentEl = document.getElementById("video-detail-content");
  if (contentEl) contentEl.style.display = "grid";

  document.title = `${video.title || "Xem Video"} | ClipShop AI`;

  // Chuẩn hóa đường dẫn video
  const player = document.getElementById("single-video-player");
  let videoSrc = video.video_url || "";
  if (videoSrc.startsWith("/uploads/")) {
    videoSrc = `${CONFIG.API_BASE_URL.replace("/api", "")}${videoSrc}`;
  }
  if (player) {
    player.src = videoSrc;
    if (video.thumbnail_url) {
      let thumbSrc = video.thumbnail_url;
      if (thumbSrc.startsWith("/uploads/")) {
        thumbSrc = `${CONFIG.API_BASE_URL.replace("/api", "")}${thumbSrc}`;
      }
      player.poster = thumbSrc;
    }
  }

  const durationEl = document.getElementById("single-video-duration");
  if (durationEl) {
    durationEl.textContent = formatDuration(video.duration_seconds || 0);
  }

  // Thông tin tác giả
  const avatarUrl =
    video.author_avatar_url ||
    video.author_avatar_key ||
    "../assets/images/logo.svg";
  const authorAvatarEl = document.getElementById("author-avatar");
  if (authorAvatarEl) {
    authorAvatarEl.src = avatarUrl;
    authorAvatarEl.onerror = () => {
      authorAvatarEl.src = "../assets/images/logo.svg";
    };
  }

  const authorNameEl = document.getElementById("author-display-name");
  if (authorNameEl) {
    authorNameEl.textContent = video.author_name || video.author_username;
  }

  const authorUserEl = document.getElementById("author-username");
  if (authorUserEl) {
    authorUserEl.textContent = `@${video.author_username}`;
  }

  const authorLinkEl = document.getElementById("author-profile-link");
  if (authorLinkEl) {
    authorLinkEl.href = `profile.html?id=${video.user_id}`;
  }

  // Nút Theo dõi & Nút Ẩn video (cho chủ video / Admin)
  const currentUser = typeof getCurrentUser === "function" ? getCurrentUser() : null;
  const isSelf = currentUser && currentUser.id === video.user_id;
  const canManage =
    currentUser && (isSelf || currentUser.role === "ADMIN");

  const btnFollow = document.getElementById("btn-video-follow");
  const selfBadge = document.getElementById("video-self-badge");
  const btnToggleVis = document.getElementById("btn-toggle-visibility");

  if (isSelf) {
    if (btnFollow) btnFollow.style.display = "none";
    if (selfBadge) selfBadge.style.display = "inline-block";
  } else {
    if (selfBadge) selfBadge.style.display = "none";
    if (btnFollow) {
      btnFollow.style.display = "inline-block";
      updateFollowBtnUI(video.is_following);
    }
  }

  if (btnToggleVis) {
    btnToggleVis.style.display = canManage ? "inline-block" : "none";
  }

  // Tiêu đề, lượt xem, thời gian, mô tả
  const titleEl = document.getElementById("video-title");
  if (titleEl) titleEl.textContent = video.title || "";

  const viewsEl = document.getElementById("video-views");
  if (viewsEl) viewsEl.textContent = Number(video.view_count || 0).toLocaleString("vi-VN");

  const createdEl = document.getElementById("video-created-at");
  if (createdEl) createdEl.textContent = formatTimeAgo(video.created_at);

  const descEl = document.getElementById("video-description");
  if (descEl) {
    if (video.description) {
      descEl.textContent = video.description;
      descEl.style.display = "block";
    } else {
      descEl.textContent = "";
      descEl.style.display = "none";
    }
  }

  // Hashtags
  const hashtagsWrap = document.getElementById("video-hashtags");
  if (hashtagsWrap) {
    const tags = Array.isArray(video.hashtags) ? video.hashtags : [];
    if (tags.length > 0) {
      hashtagsWrap.innerHTML = tags
        .map(
          (t) =>
            `<a href="search.html?tag=${encodeURIComponent(
              t.replace(/^#/, "")
            )}" class="video-hashtag-pill">#${escapeHtml(
              t.replace(/^#/, "")
            )}</a>`
        )
        .join(" ");
      hashtagsWrap.style.display = "flex";
    } else {
      hashtagsWrap.innerHTML = "";
      hashtagsWrap.style.display = "none";
    }
  }

  // Số lượt Thích, Bình luận, Chia sẻ
  updateLikeBtnUI(video.is_liked, video.like_count || 0);
  updateCommentCountUI(video.comment_count || 0);
  updateShareCountUI(video.share_count || 0);

  // Liên kết chia sẻ
  const shareUrl = buildShareUrl(video.id);
  const shareInput = document.getElementById("share-link-input");
  if (shareInput) shareInput.value = shareUrl;

  const shortPath = document.getElementById("share-short-path");
  if (shortPath) shortPath.textContent = `/video/${video.id}`;

  // Gắn danh sách sản phẩm (Task T3D2296)
  renderSingleVideoProducts(video);
}

function updateLikeBtnUI(isLiked, count) {
  const btnLike = document.getElementById("btn-like-video");
  const iconEl = document.getElementById("like-heart-icon");
  const countEl = document.getElementById("single-like-count");

  if (btnLike) btnLike.classList.toggle("liked", !!isLiked);
  if (iconEl) iconEl.textContent = isLiked ? "❤️" : "🤍";
  if (countEl) countEl.textContent = count;
}

function updateCommentCountUI(count) {
  const pillCount = document.getElementById("single-comment-count");
  const headerCount = document.getElementById("comments-header-count");
  if (pillCount) pillCount.textContent = count;
  if (headerCount) headerCount.textContent = count;
}

function updateShareCountUI(count) {
  const pillShare = document.getElementById("single-share-count");
  const boxShare = document.getElementById("share-box-count");
  if (pillShare) pillShare.textContent = count;
  if (boxShare) boxShare.textContent = count;
}

function updateFollowBtnUI(isFollowing) {
  const btnFollow = document.getElementById("btn-video-follow");
  if (!btnFollow) return;
  if (isFollowing) {
    btnFollow.className = "btn-profile-follow is-following";
    btnFollow.textContent = "✓ Đang theo dõi";
  } else {
    btnFollow.className = "btn-profile-follow not-following";
    btnFollow.textContent = "+ Theo dõi";
  }
}

// ---------- 3.5. HIỂN THỊ SẢN PHẨM TRONG VIDEO (TASK T3D2296) ----------
async function renderSingleVideoProducts(video) {
  const wrap = document.getElementById("video-tagged-products-wrap");
  const countEl = document.getElementById("video-prods-count");
  const listEl = document.getElementById("video-tagged-products-list");
  if (!wrap || !listEl) return;

  let products = Array.isArray(video.products) ? video.products : [];

  // Nếu trong object video chưa có products hoặc rỗng, gọi API /videos/{id}/products
  if (products.length === 0) {
    try {
      const res = await api.get(`/videos/${video.id}/products`);
      if (Array.isArray(res)) {
        products = res;
      }
    } catch {
      // Bỏ qua nếu có lỗi
    }
  }

  if (products.length === 0) {
    wrap.style.display = "none";
    listEl.innerHTML = "";
    return;
  }

  wrap.style.display = "block";
  if (countEl) countEl.textContent = products.length;

  listEl.innerHTML = products
    .map((p) => {
      let thumbUrl = p.thumbnail_url || "../assets/images/logo.svg";
      if (thumbUrl && thumbUrl.startsWith("/uploads/")) {
        thumbUrl = `${CONFIG.API_BASE_URL.replace("/api", "")}${thumbUrl}`;
      }
      const priceText = Number(p.price || 0).toLocaleString("vi-VN") + " đ";
      const shopName = p.shop_name ? escapeHtml(p.shop_name) : "Shop";

      return `
        <a href="product.html?id=${p.id}" class="tagged-prod-mini-card" title="Xem chi tiết: ${escapeHtml(p.name)}">
          <img src="${thumbUrl}" alt="${escapeHtml(p.name)}" class="tagged-prod-mini-thumb" onerror="this.src='../assets/images/logo.svg'">
          <div class="tagged-prod-mini-info">
            <span class="tagged-prod-mini-badge">🛍️ ${shopName}</span>
            <div class="tagged-prod-mini-name">${escapeHtml(p.name)}</div>
            <div class="tagged-prod-mini-price">${priceText}</div>
          </div>
          <span class="tagged-prod-mini-arrow">👉</span>
        </a>
      `;
    })
    .join("");
}

// ---------- 4. SAO CHÉP LINK & ĐẾM LƯỢT CHIA SẺ (YÊU CẦU CHÍNH TASK T3D245C) ----------
async function handleCopyAndCountShare() {
  if (!currentVideoData || !currentVideoId) return;

  const shareUrl = buildShareUrl(currentVideoId);
  const shareInput = document.getElementById("share-link-input");
  const btnCopy = document.getElementById("btn-copy-link");

  // 1. Sao chép link vào bộ nhớ tạm
  let copied = false;
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(shareUrl);
      copied = true;
    }
  } catch (_) {
    copied = false;
  }

  if (!copied && shareInput) {
    try {
      shareInput.focus();
      shareInput.select();
      copied = document.execCommand("copy");
    } catch (_) {
      copied = false;
    }
  }

  if (btnCopy) {
    const originalText = "📋 Sao chép link";
    btnCopy.textContent = "✓ Đã sao chép!";
    btnCopy.classList.add("copied");
    setTimeout(() => {
      btnCopy.textContent = originalText;
      btnCopy.classList.remove("copied");
    }, 2000);
  }

  showToast("Đã sao chép liên kết chia sẻ vào bộ nhớ tạm!", "success");

  // 2. Gọi API ghi nhận lượt chia sẻ và cập nhật số đếm lượt chia sẻ
  const currentCount = parseInt(
    document.getElementById("single-share-count")?.textContent || "0",
    10
  );
  updateShareCountUI(currentCount + 1);

  try {
    const res = await api.post(`/videos/${currentVideoId}/share`);
    if (res && typeof res.share_count === "number") {
      updateShareCountUI(res.share_count);
      currentVideoData.share_count = res.share_count;
    }
  } catch (err) {
    // Nếu video vừa bị ẩn ở phía server thì báo lỗi
    if (err && err.status === 400) {
      showUnavailableState(currentVideoData, err.message);
    }
  }
}

// ---------- 5. XỬ LÝ THÍCH (LIKE / UNLIKE) ----------
async function handleSingleLike() {
  if (!currentVideoData || !currentVideoId) return;

  const token = session.getToken();
  if (!token) {
    if (typeof showLoginModal === "function") showLoginModal();
    return;
  }

  const wasLiked = !!currentVideoData.is_liked;
  const oldCount = currentVideoData.like_count || 0;
  const newLiked = !wasLiked;
  const newCount = newLiked ? oldCount + 1 : Math.max(0, oldCount - 1);

  currentVideoData.is_liked = newLiked;
  currentVideoData.like_count = newCount;
  updateLikeBtnUI(newLiked, newCount);

  try {
    if (newLiked) {
      await api.post(`/videos/${currentVideoId}/likes`);
    } else {
      await api.delete(`/videos/${currentVideoId}/likes`);
    }
  } catch (err) {
    currentVideoData.is_liked = wasLiked;
    currentVideoData.like_count = oldCount;
    updateLikeBtnUI(wasLiked, oldCount);
    showToast(err.message || "Không thể cập nhật lượt thích", "error");
  }
}

// ---------- 6. XỬ LÝ THEO DÕI (FOLLOW / UNFOLLOW) ----------
async function handleSingleFollow() {
  if (!currentVideoData) return;

  const token = session.getToken();
  if (!token) {
    if (typeof showLoginModal === "function") showLoginModal();
    return;
  }

  const wasFollowing = !!currentVideoData.is_following;
  currentVideoData.is_following = !wasFollowing;
  updateFollowBtnUI(currentVideoData.is_following);

  try {
    if (!wasFollowing) {
      await api.post(`/users/${currentVideoData.user_id}/follow`);
      showToast("Đã theo dõi tác giả!", "success");
    } else {
      await api.delete(`/users/${currentVideoData.user_id}/follow`);
      showToast("Đã bỏ theo dõi", "success");
    }
  } catch (err) {
    currentVideoData.is_following = wasFollowing;
    updateFollowBtnUI(wasFollowing);
    showToast(err.message || "Không thể cập nhật theo dõi", "error");
  }
}

// ---------- 7. ẨN / HIỆN VIDEO (CHO CHỦ VIDEO HOẶC ADMIN) ----------
async function handleToggleVisibility(targetStatus) {
  if (!currentVideoId) return;

  try {
    const res = await api.patch
      ? await http.patch(`/videos/${currentVideoId}/status`, { status: targetStatus }).then((r) => r.data)
      : await axios.patch(
          `${CONFIG.API_BASE_URL}/videos/${currentVideoId}/status`,
          { status: targetStatus },
          { headers: { Authorization: `Bearer ${session.getToken()}` } }
        ).then((r) => r.data);

    showToast(res.message || "Đã cập nhật trạng thái video", "success");
    await loadSingleVideo(currentVideoId);
  } catch (err) {
    showToast(err.message || "Không thể thay đổi trạng thái video", "error");
  }
}

// ---------- 8. BÌNH LUẬN TRÊN TRANG XEM RIÊNG VIDEO ----------
async function loadSingleComments(videoId) {
  const listEl = document.getElementById("single-comments-list");
  if (!listEl) return;

  listEl.innerHTML = `<div class="muted" style="text-align:center;padding:24px;">Đang tải bình luận...</div>`;

  try {
    const comments = await api.get(`/videos/${videoId}/comments`);
    updateCommentCountUI(comments.length);

    if (!comments || comments.length === 0) {
      listEl.innerHTML = `
        <div class="muted" style="text-align:center;padding:32px 12px;">
          Chưa có bình luận nào. Hãy là người đầu tiên bình luận!
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
      thread.id = `single-thread-${c.id}`;
      thread.appendChild(renderSingleCommentRow(c));

      const repliesBox = document.createElement("div");
      repliesBox.className = "comment-replies";
      repliesBox.id = `single-replies-${c.id}`;
      const childList = repliesByParent.get(c.id) || [];
      const parentName = c.display_name || c.username || `User #${c.user_id}`;
      childList.forEach((r) => {
        repliesBox.appendChild(renderSingleCommentRow(r, parentName));
      });
      thread.appendChild(repliesBox);
      listEl.appendChild(thread);
    });
  } catch (err) {
    listEl.innerHTML = `<div class="text-error" style="text-align:center;padding:20px;">Không thể tải bình luận: ${escapeHtml(
      err.message
    )}</div>`;
  }
}

function renderSingleCommentRow(comment, parentAuthorName = null) {
  const row = document.createElement("div");
  row.className = comment.parent_id ? "comment-row is-reply" : "comment-row";
  row.id = `single-comment-${comment.id}`;

  const currentU = typeof getCurrentUser === "function" ? getCurrentUser() : null;
  const isCommentOwner = currentU && currentU.id === comment.user_id;
  const isVideoOwner =
    currentU && currentVideoData && currentU.id === currentVideoData.user_id;
  const isAdmin = currentU && currentU.role === "ADMIN";
  const canDelete = isCommentOwner || isVideoOwner || isAdmin;

  const authorName = comment.display_name || comment.username || `User #${comment.user_id}`;
  const avatarSrc = comment.avatar_url || "../assets/images/logo.svg";

  row.innerHTML = `
    <img src="${escapeHtml(avatarSrc)}" alt="${escapeHtml(authorName)}" class="comment-avatar" onerror="this.src='../assets/images/logo.svg'">
    <div class="comment-content-box">
      <div class="comment-author-name">
        <a href="profile.html?id=${comment.user_id}" style="color:inherit;text-decoration:none;">${escapeHtml(authorName)}</a>
        <span class="comment-time">${formatTimeAgo(comment.created_at)}</span>
      </div>
      <div class="comment-text">
        ${
          comment.parent_id
            ? `<span class="reply-badge-target">@${escapeHtml(parentAuthorName || `#${comment.parent_id}`)}</span>`
            : ""
        }
        ${escapeHtml(comment.content)}
      </div>
      <div class="comment-actions">
        ${
          !comment.parent_id
            ? `<button type="button" class="comment-act-btn reply-btn">Trả lời</button>`
            : ""
        }
        ${
          canDelete
            ? `<button type="button" class="comment-act-btn delete">Xóa</button>`
            : ""
        }
      </div>
    </div>
  `;

  const replyBtn = row.querySelector(".reply-btn");
  if (replyBtn) {
    replyBtn.addEventListener("click", () => {
      replyingCommentId = comment.id;
      replyingUsername = authorName;
      const replyUserEl = document.getElementById("single-reply-user");
      const bannerEl = document.getElementById("single-reply-banner");
      const inputEl = document.getElementById("single-comment-input");
      if (replyUserEl) replyUserEl.textContent = `@${replyingUsername}`;
      if (bannerEl) bannerEl.classList.add("active");
      if (inputEl) {
        inputEl.placeholder = `Trả lời ${replyingUsername}...`;
        inputEl.focus();
      }
    });
  }

  const deleteBtn = row.querySelector(".comment-act-btn.delete");
  if (deleteBtn) {
    deleteBtn.addEventListener("click", async () => {
      if (!confirm("Bạn có chắc chắn muốn xóa bình luận này?")) return;
      try {
        await api.delete(`/comments/${comment.id}`);
        showToast("Đã xóa bình luận", "success");
        await loadSingleComments(currentVideoId);
      } catch (err) {
        showToast(err.message || "Không thể xóa bình luận", "error");
      }
    });
  }

  return row;
}

function clearReplyBanner() {
  replyingCommentId = null;
  replyingUsername = null;
  const bannerEl = document.getElementById("single-reply-banner");
  const inputEl = document.getElementById("single-comment-input");
  if (bannerEl) bannerEl.classList.remove("active");
  if (inputEl) inputEl.placeholder = "Viết bình luận của bạn...";
}

async function handleSubmitSingleComment() {
  const token = session.getToken();
  if (!token) {
    if (typeof showLoginModal === "function") showLoginModal();
    return;
  }

  const inputEl = document.getElementById("single-comment-input");
  const btnSend = document.getElementById("btn-send-single-comment");
  if (!inputEl || !currentVideoId) return;

  const content = inputEl.value.trim();
  if (!content) return;

  if (btnSend) btnSend.disabled = true;
  try {
    await api.post(`/videos/${currentVideoId}/comments`, {
      content,
      parent_id: replyingCommentId || null,
    });
    inputEl.value = "";
    clearReplyBanner();
    showToast("Đã đăng bình luận!", "success");
    await loadSingleComments(currentVideoId);
  } catch (err) {
    showToast(err.message || "Không thể gửi bình luận", "error");
  } finally {
    if (btnSend) btnSend.disabled = false;
  }
}

// ---------- 9. TIỆN ÍCH ĐỊNH DẠNG ----------
function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
}

function formatTimeAgo(dateString) {
  if (!dateString) return "";
  let normalized = String(dateString).trim().replace(" ", "T");
  if (!/[zZ]|[+-]\d{2}:?\d{2}$/.test(normalized)) normalized += "Z";
  const date = new Date(normalized);
  const now = new Date();
  const diffSec = Math.max(0, Math.floor((now - date) / 1000));

  if (diffSec < 60) return "Vừa xong";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} phút trước`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} giờ trước`;
  return `${Math.floor(diffSec / 86400)} ngày trước`;
}
