// Trang Tìm kiếm Video, Người dùng, Hashtag (Task T3D2442)

(function () {
  const state = {
    query: "",
    tag: "",
    activeTab: "videos", // "videos" | "users" | "hashtags"
    skip: 0,
    limit: 12,
    loading: false,
    hasMore: true,
    videos: [],
    users: [],
    hashtags: [],
    counts: {
      videos: 0,
      users: 0,
      hashtags: 0,
    },
  };

  function init() {
    renderLayout();
    bindEvents();
    parseUrlParams();
    loadTrendingHashtags();
    doSearch(true);
  }

  function parseUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const q = params.get("q") || "";
    const tag = params.get("tag") || "";
    const type = params.get("type") || "videos";

    state.query = q;
    state.tag = tag;
    if (["videos", "users", "hashtags"].includes(type)) {
      state.activeTab = type;
    } else {
      state.activeTab = "videos";
    }

    const inputEl = document.getElementById("search-input");
    if (inputEl) {
      inputEl.value = q;
      toggleClearButton(q.length > 0);
    }

    updateTagBadgeUI();
    updateTabButtonsUI();
  }

  function updateUrl() {
    const params = new URLSearchParams();
    if (state.query) params.set("q", state.query);
    if (state.tag) params.set("tag", state.tag);
    if (state.activeTab) params.set("type", state.activeTab);

    const newUrl = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState({}, "", newUrl);
  }

  function bindEvents() {
    const form = document.getElementById("search-form");
    const input = document.getElementById("search-input");
    const btnClear = document.getElementById("btn-clear-search");
    const btnRemoveTag = document.getElementById("btn-remove-tag");
    const btnLoadMore = document.getElementById("btn-load-more");

    if (form) {
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        state.query = input.value.trim();
        state.skip = 0;
        updateUrl();
        doSearch(true);
      });
    }

    if (input) {
      input.addEventListener("input", () => {
        toggleClearButton(input.value.length > 0);
      });
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          form.dispatchEvent(new Event("submit"));
        }
      });
    }

    if (btnClear) {
      btnClear.addEventListener("click", () => {
        input.value = "";
        toggleClearButton(false);
        state.query = "";
        state.skip = 0;
        updateUrl();
        doSearch(true);
      });
    }

    if (btnRemoveTag) {
      btnRemoveTag.addEventListener("click", () => {
        state.tag = "";
        updateTagBadgeUI();
        state.skip = 0;
        updateUrl();
        doSearch(true);
      });
    }

    // Tabs
    const tabBtns = document.querySelectorAll(".search-tab-btn");
    tabBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetTab = btn.dataset.tab;
        if (targetTab === state.activeTab) return;
        state.activeTab = targetTab;
        state.skip = 0;
        updateTabButtonsUI();
        updateUrl();
        doSearch(true);
      });
    });

    // Nút Xem thêm
    if (btnLoadMore) {
      btnLoadMore.addEventListener("click", () => {
        if (state.loading || !state.hasMore) return;
        state.skip += state.limit;
        doSearch(false);
      });
    }
  }

  function toggleClearButton(visible) {
    const btn = document.getElementById("btn-clear-search");
    if (btn) btn.style.display = visible ? "block" : "none";
  }

  function updateTagBadgeUI() {
    const badge = document.getElementById("active-tag-badge");
    const label = document.getElementById("current-tag-label");
    if (!badge || !label) return;

    if (state.tag) {
      label.textContent = `#${state.tag.replace(/^#/, "")}`;
      badge.style.display = "inline-flex";
    } else {
      badge.style.display = "none";
    }
  }

  function updateTabButtonsUI() {
    const tabBtns = document.querySelectorAll(".search-tab-btn");
    tabBtns.forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === state.activeTab);
    });

    const tabPanels = document.querySelectorAll(".search-tab-content");
    tabPanels.forEach((panel) => {
      panel.classList.toggle("active", panel.id === `results-${state.activeTab}`);
    });
  }

  async function doSearch(isReset = true) {
    if (state.loading) return;
    state.loading = true;

    const loadingEl = document.getElementById("search-loading");
    const emptyEl = document.getElementById("search-empty");
    const paginationEl = document.getElementById("pagination-wrapper");
    const btnLoadMore = document.getElementById("btn-load-more");
    const noMoreEl = document.getElementById("no-more-results");

    if (isReset) {
      state.skip = 0;
      if (loadingEl) loadingEl.style.display = "block";
      if (emptyEl) emptyEl.style.display = "none";
      if (paginationEl) paginationEl.style.display = "none";
    } else {
      if (btnLoadMore) {
        btnLoadMore.disabled = true;
        btnLoadMore.textContent = "Đang tải thêm...";
      }
    }

    try {
      const params = {
        q: state.query || undefined,
        type: state.activeTab,
        skip: state.skip,
        limit: state.limit,
      };
      if (state.tag) {
        params.tag = state.tag.replace(/^#/, "");
      }

      const res = await api.get("/search", params);

      if (state.activeTab === "videos") {
        if (isReset) {
          state.videos = res.videos || [];
        } else {
          state.videos = state.videos.concat(res.videos || []);
        }
        state.hasMore = (res.videos || []).length === state.limit;
        renderVideos(state.videos);
      } else if (state.activeTab === "users") {
        if (isReset) {
          state.users = res.users || [];
        } else {
          state.users = state.users.concat(res.users || []);
        }
        state.hasMore = (res.users || []).length === state.limit;
        renderUsers(state.users);
      } else if (state.activeTab === "hashtags") {
        state.hashtags = res.hashtags || [];
        state.hasMore = false;
        renderHashtags(state.hashtags);
      }

      // Cập nhật tab badge counts nếu tìm tổng hợp ban đầu
      updateCountsBadge();

      // Kiểm tra rỗng
      const currentList =
        state.activeTab === "videos"
          ? state.videos
          : state.activeTab === "users"
          ? state.users
          : state.hashtags;

      if (currentList.length === 0) {
        if (emptyEl) emptyEl.style.display = "block";
        if (paginationEl) paginationEl.style.display = "none";
      } else {
        if (emptyEl) emptyEl.style.display = "none";
        if (state.activeTab !== "hashtags") {
          if (paginationEl) paginationEl.style.display = "block";
          if (btnLoadMore) {
            btnLoadMore.style.display = state.hasMore ? "inline-block" : "none";
            btnLoadMore.disabled = false;
            btnLoadMore.textContent = "Xem thêm kết quả";
          }
          if (noMoreEl) noMoreEl.style.display = state.hasMore ? "none" : "block";
        } else {
          if (paginationEl) paginationEl.style.display = "none";
        }
      }
    } catch (err) {
      console.error("Lỗi khi tìm kiếm:", err);
      showToast(err.message || "Không thể thực hiện tìm kiếm", "error");
    } finally {
      state.loading = false;
      if (loadingEl) loadingEl.style.display = "none";
    }
  }

  function updateCountsBadge() {
    const cv = document.getElementById("count-videos");
    const cu = document.getElementById("count-users");
    const ch = document.getElementById("count-hashtags");

    if (cv) cv.textContent = state.videos.length || 0;
    if (cu) cu.textContent = state.users.length || 0;
    if (ch) ch.textContent = state.hashtags.length || 0;
  }

  // 1. RENDER VIDEOS
  function renderVideos(videos) {
    const grid = document.getElementById("videos-grid");
    if (!grid) return;

    if (!videos || videos.length === 0) {
      grid.innerHTML = "";
      return;
    }

    const html = videos
      .map((v) => {
        const hashtags = Array.isArray(v.hashtags) ? v.hashtags : [];
        const tagsHtml = hashtags
          .map(
            (t) =>
              `<button type="button" class="video-hashtag-pill" data-tag="${escapeHtml(
                t
              )}">#${escapeHtml(t)}</button>`
          )
          .join(" ");

        const thumb = v.thumbnail_url || "../assets/images/logo.svg";
        const authorAvatar = v.author_avatar_url || "../assets/images/logo.svg";
        const durationFormatted = formatDuration(v.duration_seconds || 0);

        return `
          <div class="search-video-card" data-video-id="${v.id}">
            <div class="search-video-thumb-wrap" onclick="window.location.href='video.html?id=${v.id}'">
              <img src="${thumb}" alt="${escapeHtml(v.title)}" class="search-video-thumb" loading="lazy" onerror="this.src='../assets/images/logo.svg'">
              <span class="search-video-duration">${durationFormatted}</span>
              <div class="search-video-play-icon">▶</div>
            </div>
            <div class="search-video-info">
              <h4 class="search-video-title" onclick="window.location.href='video.html?id=${v.id}'" title="${escapeHtml(
          v.title
        )}">
                ${escapeHtml(v.title)}
              </h4>
              
              <div class="search-video-author" onclick="window.location.href='profile.html?id=${v.user_id}'">
                <img src="${authorAvatar}" alt="avatar" class="search-author-avatar" onerror="this.src='../assets/images/logo.svg'">
                <div class="search-author-names">
                  <span class="search-author-name">${escapeHtml(v.author_name || v.author_username)}</span>
                  <span class="search-author-user">@${escapeHtml(v.author_username)}</span>
                </div>
              </div>

              ${tagsHtml ? `<div class="search-video-tags">${tagsHtml}</div>` : ""}

              <div class="search-video-stats">
                <span>❤️ ${formatNumber(v.like_count || 0)}</span>
                <span>💬 ${formatNumber(v.comment_count || 0)}</span>
                <span>👁️ ${formatNumber(v.view_count || 0)}</span>
              </div>
            </div>
          </div>
        `;
      })
      .join("");

    grid.innerHTML = html;

    // Gắn sự kiện khi bấm hashtag trên card video
    grid.querySelectorAll(".video-hashtag-pill").forEach((pill) => {
      pill.addEventListener("click", (e) => {
        e.stopPropagation();
        const tag = pill.dataset.tag;
        filterByHashtag(tag);
      });
    });
  }

  // 2. RENDER USERS
  function renderUsers(users) {
    const list = document.getElementById("users-list");
    if (!list) return;

    if (!users || users.length === 0) {
      list.innerHTML = "";
      return;
    }

    const currentLoggedInUser = getCurrentUser();

    const html = users
      .map((u) => {
        const avatar = u.avatar_url || "../assets/images/logo.svg";
        const isSelf = currentLoggedInUser && currentLoggedInUser.id === u.id;
        const isFollowing = u.is_following;

        let followBtnHtml = "";
        if (isSelf) {
          followBtnHtml = `<span class="badge-self">Bạn</span>`;
        } else {
          followBtnHtml = `
            <button
              type="button"
              class="btn btn-small btn-search-follow ${isFollowing ? "is-following" : "not-following"}"
              data-user-id="${u.id}"
              data-following="${isFollowing ? "true" : "false"}"
            >
              ${isFollowing ? "Đang theo dõi" : "+ Theo dõi"}
            </button>
          `;
        }

        return `
          <div class="search-user-card">
            <div class="search-user-left" onclick="window.location.href='profile.html?id=${u.id}'">
              <img src="${avatar}" alt="avatar" class="search-user-avatar" onerror="this.src='../assets/images/logo.svg'">
              <div class="search-user-details">
                <div class="search-user-display-name">${escapeHtml(u.display_name || u.username)}</div>
                <div class="search-user-handle">@${escapeHtml(u.username)}</div>
                <div class="search-user-meta">
                  <span id="user-follower-count-${u.id}"><strong>${formatNumber(
          u.followers_count || 0
        )}</strong> người theo dõi</span>
                  <span>·</span>
                  <span><strong>${formatNumber(u.video_count || 0)}</strong> video</span>
                </div>
                ${u.bio ? `<div class="search-user-bio">${escapeHtml(u.bio)}</div>` : ""}
              </div>
            </div>
            <div class="search-user-action">
              ${followBtnHtml}
            </div>
          </div>
        `;
      })
      .join("");

    list.innerHTML = html;

    // Gắn sự kiện nút theo dõi
    list.querySelectorAll(".btn-search-follow").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const userId = parseInt(btn.dataset.userId, 10);
        const isFollowing = btn.dataset.following === "true";
        await handleToggleFollow(userId, isFollowing, btn);
      });
    });
  }

  // 3. RENDER HASHTAGS
  function renderHashtags(hashtags) {
    const grid = document.getElementById("hashtags-grid");
    if (!grid) return;

    if (!hashtags || hashtags.length === 0) {
      grid.innerHTML = "";
      return;
    }

    const html = hashtags
      .map((h) => {
        return `
          <div class="search-hashtag-card" data-tag="${escapeHtml(h.tag)}">
            <div class="search-hashtag-icon">#</div>
            <div class="search-hashtag-info">
              <h3 class="search-hashtag-name">#${escapeHtml(h.tag)}</h3>
              <p class="search-hashtag-count">${formatNumber(h.video_count || 0)} video</p>
            </div>
            <button type="button" class="btn btn-small btn-primary btn-view-tag" data-tag="${escapeHtml(
              h.tag
            )}">
              Xem video &rarr;
            </button>
          </div>
        `;
      })
      .join("");

    grid.innerHTML = html;

    // Gắn sự kiện: Bấm hashtag mở danh sách video có hashtag đó (Yêu cầu đề bài Task T3D2442)
    grid.querySelectorAll(".search-hashtag-card, .btn-view-tag").forEach((el) => {
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        const tag = el.dataset.tag;
        filterByHashtag(tag);
      });
    });
  }

  // 4. BẢNG XẾP HẠNG HASHTAG THỊNH HÀNH TRONG 7 NGÀY (TASK T3D2BE1)
  async function loadTrendingHashtags() {
    const listEl = document.getElementById("trending-hashtags-list");
    if (!listEl) return;

    try {
      const items = await api.get("/search/trending-hashtags", {
        days: 7,
        limit: 10,
      });

      if (!Array.isArray(items) || items.length === 0) {
        listEl.innerHTML = `<div class="muted" style="padding:8px 0;">Chưa có hashtag thịnh hành trong 7 ngày qua.</div>`;
        return;
      }

      const rankMedal = (r) => {
        if (r === 1) return "🥇 #1";
        if (r === 2) return "🥈 #2";
        if (r === 3) return "🥉 #3";
        return `#${r}`;
      };

      listEl.innerHTML = items
        .map((item) => {
          const rankClass = item.rank <= 3 ? `rank-top-${item.rank}` : "rank-normal";
          const isSelected =
            state.tag &&
            state.tag.replace(/^#/, "").toLowerCase() === item.tag.toLowerCase();
          return `
            <div class="trending-tag-card ${rankClass}${isSelected ? " active-trend" : ""}" data-tag="${escapeHtml(
              item.tag
            )}" title="Bấm để xem video có hashtag #${escapeHtml(item.tag)}">
              <div class="trending-tag-top">
                <span class="trending-rank-badge ${rankClass}">${rankMedal(item.rank)}</span>
                <span class="trending-tag-name">#${escapeHtml(item.tag)}</span>
              </div>
              <div class="trending-tag-metrics">
                <span>🎬 <strong>${formatNumber(item.video_count || 0)}</strong> video</span>
                <span>⚡ <strong>${formatNumber(item.interaction_count || 0)}</strong> tương tác</span>
              </div>
              <div class="trending-tag-breakdown">
                ❤️ ${formatNumber(item.like_count || 0)} · 💬 ${formatNumber(
            item.comment_count || 0
          )} · 🔗 ${formatNumber(item.share_count || 0)}
              </div>
            </div>
          `;
        })
        .join("");

      listEl.querySelectorAll(".trending-tag-card").forEach((card) => {
        card.addEventListener("click", () => {
          const tag = card.dataset.tag;
          filterByHashtag(tag);
          listEl.querySelectorAll(".trending-tag-card").forEach((c) => {
            c.classList.toggle("active-trend", c.dataset.tag === tag);
          });
        });
      });
    } catch (_) {
      listEl.innerHTML = `<div class="muted" style="padding:8px 0;">Không tải được bảng xếp hạng hashtag.</div>`;
    }
  }

  // Chức năng: "Bấm hashtag mở danh sách video có hashtag đó"
  function filterByHashtag(tag) {
    if (!tag) return;
    const cleanTag = tag.replace(/^#/, "");
    state.tag = cleanTag;
    state.activeTab = "videos";
    state.skip = 0;

    updateTagBadgeUI();
    updateTabButtonsUI();
    updateUrl();
    doSearch(true);

    // Cuộn mượt lên danh sách video
    window.scrollTo({ top: 180, behavior: "smooth" });
  }

  // Xử lý Follow / Unfollow người dùng trực tiếp trên Search
  async function handleToggleFollow(userId, isFollowing, btn) {
    const token = localStorage.getItem("token") || localStorage.getItem("access_token");
    if (!token) {
      if (typeof showLoginModal === "function") {
        showLoginModal();
      } else {
        alert("Vui lòng đăng nhập để thực hiện theo dõi!");
      }
      return;
    }

    btn.disabled = true;
    try {
      let countEl = document.getElementById(`user-follower-count-${userId}`);
      if (isFollowing) {
        // Huỷ theo dõi
        await api.delete(`/users/${userId}/follow`);
        btn.dataset.following = "false";
        btn.className = "btn btn-small btn-search-follow not-following";
        btn.textContent = "+ Theo dõi";
        showToast("Đã huỷ theo dõi", "success");
        if (countEl) {
          const current = parseInt(countEl.querySelector("strong")?.textContent || "0", 10);
          countEl.innerHTML = `<strong>${Math.max(0, current - 1)}</strong> người theo dõi`;
        }
      } else {
        // Theo dõi
        await api.post(`/users/${userId}/follow`);
        btn.dataset.following = "true";
        btn.className = "btn btn-small btn-search-follow is-following";
        btn.textContent = "Đang theo dõi";
        showToast("Đã theo dõi người dùng", "success");
        if (countEl) {
          const current = parseInt(countEl.querySelector("strong")?.textContent || "0", 10);
          countEl.innerHTML = `<strong>${current + 1}</strong> người theo dõi`;
        }
      }
    } catch (err) {
      console.error("Lỗi khi theo dõi:", err);
      showToast(err.message || "Không thể cập nhật theo dõi", "error");
    } finally {
      btn.disabled = false;
    }
  }

  function formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
  }

  function formatNumber(num) {
    if (!num) return "0";
    if (num >= 1000000) return (num / 1000000).toFixed(1).replace(/\.0$/, "") + "M";
    if (num >= 1000) return (num / 1000).toFixed(1).replace(/\.0$/, "") + "K";
    return num.toString();
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Khởi động khi tải xong DOM
  document.addEventListener("DOMContentLoaded", init);
})();
