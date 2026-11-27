// ==========================================================
// T3D2235: Xử lý Trang đăng video (Upload Video UI)
// ==========================================================

const MAX_VIDEO_BYTES = 50 * 1024 * 1024; // 50 MB
const MAX_IMAGE_BYTES = 50 * 1024 * 1024; // 50 MB
const MAX_VIDEO_DURATION_SECONDS = 60; // Tối đa 60 giây
const ALLOWED_VIDEO_EXTS = [".mp4", ".webm"];
const ALLOWED_VIDEO_TYPES = ["video/mp4", "video/webm"];
const ALLOWED_IMAGE_EXTS = [".jpg", ".jpeg", ".png", ".webp"];
const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];

// State
let selectedVideoFile = null;
let selectedThumbnailFile = null;
let selectedHashtags = new Set();
let isUploading = false;
let videoObjectUrl = null;

// State gắn sản phẩm (Task T3D2296)
let myShopProducts = [];
let selectedProductIds = new Set();
let tempSelectedProductIds = new Set();

// DOM Elements
const dropzone = document.getElementById("video-dropzone");
const videoFileInput = document.getElementById("video-file-input");
const videoPreviewWrapper = document.getElementById("video-preview-wrapper");
const videoPlayer = document.getElementById("video-preview-player");
const metaFileName = document.getElementById("meta-file-name");
const metaFileSize = document.getElementById("meta-file-size");
const metaFileDuration = document.getElementById("meta-file-duration");
const btnReselectVideo = document.getElementById("btn-reselect-video");
const videoErrorBox = document.getElementById("video-error-box");

const formUpload = document.getElementById("form-upload-video");
const inputTitle = document.getElementById("input-video-title");
const titleCharCounter = document.getElementById("title-char-counter");
const inputDesc = document.getElementById("input-video-desc");
const descCharCounter = document.getElementById("desc-char-counter");

const inputHashtag = document.getElementById("input-video-hashtag");
const btnAddHashtag = document.getElementById("btn-add-hashtag");
const hashtagsContainer = document.getElementById(
  "selected-hashtags-container",
);
const tagPills = document.querySelectorAll(".btn-tag-pill");

const thumbPreviewImage = document.getElementById("thumb-preview-image");
const thumbSourceBadge = document.getElementById("thumb-source-badge");
const btnCaptureFrame = document.getElementById("btn-capture-frame");
const thumbFileInput = document.getElementById("thumb-file-input");
const thumbFileName = document.getElementById("thumb-file-name");
const thumbErrorBox = document.getElementById("thumb-error-box");

const progressContainer = document.getElementById("upload-progress-container");
const progressFill = document.getElementById("upload-progress-fill");
const progressPercent = document.getElementById("upload-percent-text");
const progressStatus = document.getElementById("upload-status-text");
const serverErrorBox = document.getElementById("upload-server-error");
const btnSubmit = document.getElementById("btn-submit-upload");

// ---------- XỬ LÝ LỖI & THÔNG BÁO ----------
function showVideoError(msg) {
  videoErrorBox.textContent = msg;
  videoErrorBox.style.display = "block";
}

function hideVideoError() {
  videoErrorBox.textContent = "";
  videoErrorBox.style.display = "none";
}

function showThumbError(msg) {
  thumbErrorBox.textContent = msg;
  thumbErrorBox.style.display = "block";
}

function hideThumbError() {
  thumbErrorBox.textContent = "";
  thumbErrorBox.style.display = "none";
}

function showServerError(msg) {
  serverErrorBox.textContent = msg;
  serverErrorBox.style.display = "block";
}

function hideServerError() {
  serverErrorBox.textContent = "";
  serverErrorBox.style.display = "none";
}

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(2)} MB`;
}

// ---------- VALIDATE & XỬ LÝ TỆP VIDEO ----------
function isVideoFileValid(file) {
  if (!file) return { valid: false, error: "Vui lòng chọn tệp video." };

  const name = file.name.toLowerCase();
  const hasValidExt = ALLOWED_VIDEO_EXTS.some((ext) => name.endsWith(ext));
  const hasValidType = file.type
    ? ALLOWED_VIDEO_TYPES.includes(file.type)
    : hasValidExt;

  if (!hasValidExt && !hasValidType) {
    return {
      valid: false,
      error: `Định dạng tệp không hợp lệ (${file.name}). Chỉ chấp nhận video định dạng MP4 hoặc WebM.`,
    };
  }

  if (file.size > MAX_VIDEO_BYTES) {
    return {
      valid: false,
      error: `Dung lượng video vượt quá 50MB (Tệp hiện tại: ${formatBytes(file.size)}). Vui lòng nén video hoặc chọn tệp khác.`,
    };
  }

  return { valid: true };
}

function handleVideoSelection(file) {
  hideVideoError();
  hideServerError();

  const check = isVideoFileValid(file);
  if (!check.valid) {
    showVideoError(check.error);
    resetVideoSelection();
    return;
  }

  selectedVideoFile = file;

  if (videoObjectUrl) {
    URL.revokeObjectURL(videoObjectUrl);
  }
  videoObjectUrl = URL.createObjectURL(file);

  metaFileName.textContent = file.name;
  metaFileSize.textContent = formatBytes(file.size);
  metaFileDuration.textContent = "Đang kiểm tra...";

  videoPlayer.src = videoObjectUrl;
  videoPlayer.load();

  videoPlayer.onloadedmetadata = () => {
    const duration = videoPlayer.duration;
    if (isNaN(duration) || duration <= 0) {
      showVideoError("Không đọc được thời lượng của video. Tệp có thể bị lỗi.");
      resetVideoSelection();
      return;
    }

    if (duration > MAX_VIDEO_DURATION_SECONDS) {
      showVideoError(
        `Thời lượng video tối đa là 60 giây (Video của bạn dài ${Math.ceil(duration)} giây). Vui lòng cắt ngắn trước khi tải lên.`,
      );
      resetVideoSelection();
      return;
    }

    metaFileDuration.textContent = `${Math.ceil(duration)} giây`;
    dropzone.style.display = "none";
    videoPreviewWrapper.style.display = "flex";

    // Tự động seek tới giây thứ 0.5 để chụp frame làm ảnh bìa mặc định
    videoPlayer.currentTime = Math.min(0.5, duration / 2);
  };

  videoPlayer.onseeked = () => {
    // Nếu người dùng chưa chọn ảnh bìa riêng từ máy, tự động tạo ảnh bìa từ video
    if (!thumbFileInput.files || thumbFileInput.files.length === 0) {
      captureFrameToThumbnail(true);
    }
  };

  videoPlayer.onerror = () => {
    showVideoError(
      "Không thể phát video này. Tệp bị hỏng hoặc mã hóa không được hỗ trợ.",
    );
    resetVideoSelection();
  };
}

function resetVideoSelection() {
  selectedVideoFile = null;
  videoFileInput.value = "";
  if (videoObjectUrl) {
    URL.revokeObjectURL(videoObjectUrl);
    videoObjectUrl = null;
  }
  videoPlayer.removeAttribute("src");
  dropzone.style.display = "block";
  videoPreviewWrapper.style.display = "none";
}

// ---------- TRÍCH XUẤT ẢNH BÌA TỪ VIDEO ----------
function captureFrameToThumbnail(isAuto = false) {
  if (!videoPlayer || videoPlayer.readyState < 2) {
    if (!isAuto) showToast("Video chưa tải xong khung hình để chụp.", "error");
    return;
  }

  try {
    const canvas = document.createElement("canvas");
    canvas.width = videoPlayer.videoWidth || 720;
    canvas.height = videoPlayer.videoHeight || 1280;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(videoPlayer, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        selectedThumbnailFile = new File([blob], "thumbnail.jpg", {
          type: "image/jpeg",
        });
        thumbPreviewImage.src = URL.createObjectURL(blob);
        thumbSourceBadge.textContent = isAuto
          ? "Tự động từ video"
          : `Khung hình (${Math.round(videoPlayer.currentTime)}s)`;
        thumbFileName.textContent = "Đã trích xuất từ khung hình video";
        hideThumbError();
        if (!isAuto) showToast("Đã chụp khung hình làm ảnh bìa!", "success");
      },
      "image/jpeg",
      0.9,
    );
  } catch (e) {
    console.error("Lỗi trích xuất khung hình:", e);
  }
}

// ---------- CHỌN ẢNH BÌA TỪ MÁY TÍNH ----------
function handleThumbnailSelection(file) {
  hideThumbError();
  if (!file) return;

  const name = file.name.toLowerCase();
  const hasValidExt = ALLOWED_IMAGE_EXTS.some((ext) => name.endsWith(ext));
  const hasValidType = file.type
    ? ALLOWED_IMAGE_TYPES.includes(file.type)
    : hasValidExt;

  if (!hasValidExt && !hasValidType) {
    showThumbError("Ảnh bìa phải có định dạng JPG, PNG hoặc WebP.");
    thumbFileInput.value = "";
    return;
  }

  if (file.size > MAX_IMAGE_BYTES) {
    showThumbError(
      `Dung lượng ảnh bìa vượt quá 50MB (${formatBytes(file.size)}).`,
    );
    thumbFileInput.value = "";
    return;
  }

  selectedThumbnailFile = file;
  thumbPreviewImage.src = URL.createObjectURL(file);
  thumbSourceBadge.textContent = "Ảnh tùy chỉnh";
  thumbFileName.textContent = file.name;
}

// ---------- QUẢN LÝ HASHTAGS ----------
function addHashtag(tag) {
  if (!tag) return;
  // Bỏ khoảng trắng, dấu # nếu có
  let clean = tag.trim().replace(/^#+/, "").toLowerCase();
  // Chỉ lấy chữ cái tiếng Việt/Anh, số và gạch dưới
  clean = clean.replace(/[^a-zA-Z0-9_\u00C0-\u1EF9]/g, "");

  if (!clean) return;
  if (selectedHashtags.size >= 10) {
    showToast("Tối đa 10 hashtag cho mỗi video.", "error");
    return;
  }

  selectedHashtags.add(clean);
  renderHashtags();
  inputHashtag.value = "";
}

function removeHashtag(tag) {
  selectedHashtags.delete(tag);
  renderHashtags();
}

function renderHashtags() {
  hashtagsContainer.innerHTML = "";
  selectedHashtags.forEach((tag) => {
    const item = document.createElement("span");
    item.className = "selected-tag-item";
    item.innerHTML = `
      #${escapeHtml(tag)}
      <button type="button" class="btn-remove-tag" data-tag="${escapeHtml(tag)}" title="Xóa">&times;</button>
    `;
    hashtagsContainer.appendChild(item);
  });
}

// ---------- TIẾN TRÌNH UPLOAD ----------
function setUploadProgress(percent, label) {
  progressContainer.style.display = "block";
  progressFill.style.width = `${percent}%`;
  progressPercent.textContent = `${percent}%`;
  progressStatus.textContent = label || `Đang tải lên... ${percent}%`;
}

function hideUploadProgress() {
  progressContainer.style.display = "none";
  progressFill.style.width = "0%";
  progressPercent.textContent = "0%";
}

// ---------- SUBMIT ĐĂNG VIDEO ----------
async function handleSubmitUpload(e) {
  e.preventDefault();
  hideServerError();
  hideVideoError();
  hideThumbError();

  if (isUploading) return;

  // Kiểm tra đăng nhập
  if (!session.getToken()) {
    showServerError("Bạn chưa đăng nhập! Vui lòng đăng nhập tài khoản trước khi đăng tải video.");
    showToast("Vui lòng đăng nhập để đăng video", "error");
    setTimeout(() => {
      window.location.href = typeof loginUrl === "function" ? loginUrl() : "login.html?next=pages/upload.html";
    }, 1500);
    return;
  }

  // 1. Kiểm tra video
  if (!selectedVideoFile) {
    showVideoError("Vui lòng chọn hoặc kéo thả tệp video trước khi đăng.");
    dropzone.scrollIntoView({ behavior: "smooth" });
    return;
  }

  // 2. Kiểm tra ảnh bìa
  if (!selectedThumbnailFile) {
    // Nếu chưa có, cố gắng capture frame lần nữa
    captureFrameToThumbnail(true);
    if (!selectedThumbnailFile) {
      showThumbError("Vui lòng chọn hoặc chụp ảnh bìa cho video.");
      return;
    }
  }

  // 3. Kiểm tra tiêu đề
  const title = inputTitle.value.trim();
  if (!title) {
    showServerError("Tiêu đề video không được để trống.");
    inputTitle.focus();
    return;
  }

  // 4. Ghép mô tả và hashtags
  let finalDescription = inputDesc.value.trim();
  if (selectedHashtags.size > 0) {
    const tagsString = Array.from(selectedHashtags)
      .map((t) => `#${t}`)
      .join(" ");
    finalDescription = finalDescription
      ? `${finalDescription}\n\n${tagsString}`
      : tagsString;
  }

  // 5. Chuẩn bị FormData
  const formData = new FormData();
  formData.append("title", title);
  formData.append("video", selectedVideoFile);
  formData.append("thumbnail", selectedThumbnailFile);
  if (finalDescription) {
    formData.append("description", finalDescription);
  }
  // Gắn sản phẩm của Shop (Task T3D2296: Tối đa 3 sản phẩm)
  if (selectedProductIds.size > 0) {
    formData.append("product_ids", JSON.stringify(Array.from(selectedProductIds)));
  }

  // 6. Bắt đầu tải lên (ưu tiên đẩy thẳng lên R2 để hỗ trợ tới 50MB qua Vercel)
  try {
    isUploading = true;
    btnSubmit.disabled = true;
    btnSubmit.textContent = "⏳ Đang đăng video...";
    setUploadProgress(0, "Đang chuẩn bị tải video lên máy chủ...");

    let res = null;
    const videoCt = (selectedVideoFile.type || "video/mp4").split(";")[0].trim();
    const thumbCt = (selectedThumbnailFile.type || "image/jpeg").split(";")[0].trim();

    let directPrep = null;
    try {
      directPrep = await api.post("/videos/upload-urls", {
        video_filename: selectedVideoFile.name || "video.mp4",
        video_content_type: videoCt,
        video_size_bytes: selectedVideoFile.size,
        thumbnail_filename: selectedThumbnailFile.name || "thumb.jpg",
        thumbnail_content_type: thumbCt,
        thumbnail_size_bytes: selectedThumbnailFile.size,
      });
    } catch (prepErr) {
      if (prepErr.status === 413 || prepErr.status === 401 || prepErr.status === 422) {
        throw prepErr;
      }
      directPrep = null;
    }

    if (directPrep && directPrep.direct_upload) {
      setUploadProgress(5, "Đang tải ảnh bìa lên Cloudflare R2...");
      await axios.put(directPrep.thumbnail_upload_url, selectedThumbnailFile, {
        headers: { "Content-Type": thumbCt },
        timeout: 60000,
      });

      setUploadProgress(10, "Đang tải video trực tiếp lên Cloudflare R2...");
      await axios.put(directPrep.video_upload_url, selectedVideoFile, {
        headers: { "Content-Type": videoCt },
        timeout: 300000,
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percent = Math.min(
              95,
              10 + Math.round((progressEvent.loaded * 85) / progressEvent.total),
            );
            setUploadProgress(percent, `Đang tải video lên R2... ${percent}%`);
          }
        },
      });

      setUploadProgress(96, "Đang lưu thông tin video...");
      res = await api.post("/videos/direct", {
        title,
        description: finalDescription || null,
        video_key: directPrep.video_key,
        thumbnail_key: directPrep.thumbnail_key,
        duration_seconds: Math.round(Number.isFinite(videoPlayer.duration) ? videoPlayer.duration : 0),
        product_ids: Array.from(selectedProductIds),
      });
    } else {
      res = await api.upload("/videos", formData, {
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percent = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total,
            );
            if (percent < 100) {
              setUploadProgress(percent, `Đang tải lên dữ liệu... ${percent}%`);
            } else {
              setUploadProgress(
                100,
                "Đang xử lý định dạng video trên máy chủ...",
              );
            }
          }
        },
      });
    }

    setUploadProgress(100, "✅ Đăng tải thành công!");
    showToast("Đăng video thành công!", "success");

    // Chuyển hướng sau 1.2s đến trang video vừa đăng hoặc về Feed
    setTimeout(() => {
      if (res && res.id) {
        window.location.href = `video.html?id=${res.id}`;
      } else {
        window.location.href = "feed.html";
      }
    }, 1200);
  } catch (err) {
    console.error("Lỗi upload video:", err);
    hideUploadProgress();
    isUploading = false;
    btnSubmit.disabled = false;
    btnSubmit.textContent = "🚀 Đăng video ngay";

    // Phân tích lỗi cụ thể
    if (err.status === 413) {
      showServerError(
        "Dung lượng tệp quá lớn vượt giới hạn cho phép của máy chủ (tối đa 50MB).",
      );
    } else if (err.status === 422) {
      showServerError(`Dữ liệu không hợp lệ: ${err.message}`);
    } else if (err.status === 401) {
      showServerError(
        "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại để đăng video.",
      );
    } else {
      showServerError(
        err.message || "Có lỗi xảy ra khi tải video lên. Vui lòng thử lại.",
      );
    }
  }
}

// ---------- QUẢN LÝ GẮN SẢN PHẨM CỦA SHOP (TASK T3D2296) ----------
async function checkSellerAndLoadProducts() {
  try {
    const user = session.getUser();
    if (!user || user.role !== "SELLER") return;

    // Dùng API sản phẩm của module Người bán (Task T3D2296)
    const prods = await api.get("/shops/me/products");
    if (Array.isArray(prods) && prods.length > 0) {
      myShopProducts = prods.filter((p) => p.status === "ACTIVE");
      const section = document.getElementById("video-products-section");
      if (section && myShopProducts.length > 0) {
        section.style.display = "block";
      }
    }
  } catch (_) {
    // Không phải seller hoặc chưa có shop thì ẩn mục gắn sản phẩm
  }
}

function openProductPicker() {
  const modal = document.getElementById("modal-product-picker");
  if (!modal) return;
  tempSelectedProductIds = new Set(selectedProductIds);
  renderPickerList("");
  updatePickerCounter();
  modal.style.display = "flex";
}

function closeProductPicker() {
  const modal = document.getElementById("modal-product-picker");
  if (modal) modal.style.display = "none";
}

function updatePickerCounter() {
  const counter = document.getElementById("modal-picker-counter");
  if (counter) counter.textContent = `Đã chọn: ${tempSelectedProductIds.size}/3 sản phẩm`;
}

function renderPickerList(filterText) {
  const listEl = document.getElementById("picker-products-list");
  const errorBox = document.getElementById("picker-error-msg");
  if (errorBox) errorBox.style.display = "none";
  if (!listEl) return;

  const q = (filterText || "").toLowerCase().trim();
  const filtered = myShopProducts.filter((p) => !q || p.name.toLowerCase().includes(q));

  if (filtered.length === 0) {
    listEl.innerHTML = `<div class="muted" style="text-align:center;padding:24px;">Không tìm thấy sản phẩm phù hợp.</div>`;
    return;
  }

  listEl.innerHTML = "";
  filtered.forEach((p) => {
    const isChecked = tempSelectedProductIds.has(p.id);
    const item = document.createElement("div");
    item.className = `picker-product-item ${isChecked ? "selected" : ""}`;

    let thumb = p.thumbnail_url || "";
    if (p.images && p.images.length > 0) {
      const primary = p.images.find((img) => img.is_primary) || p.images[0];
      thumb = primary.image_url || primary.object_key || thumb;
    }
    if (thumb && thumb.startsWith("/uploads/")) {
      thumb = `${CONFIG.API_BASE_URL.replace("/api", "")}${thumb}`;
    } else if (!thumb) {
      thumb = "../assets/images/logo.svg";
    }

    const priceText = Number(p.price || 0).toLocaleString("vi-VN") + " ₫";

    item.innerHTML = `
      <input type="checkbox" class="picker-checkbox" data-id="${p.id}" ${isChecked ? "checked" : ""}>
      <img src="${escapeHtml(thumb)}" alt="${escapeHtml(p.name)}" class="picker-item-thumb" onerror="this.src='../assets/images/logo.svg'">
      <div class="picker-item-info">
        <div class="picker-item-name">${escapeHtml(p.name)}</div>
        <div class="picker-item-price">${priceText}</div>
      </div>
    `;

    item.addEventListener("click", (e) => {
      if (e.target.tagName !== "INPUT") {
        const cb = item.querySelector(".picker-checkbox");
        cb.checked = !cb.checked;
        cb.dispatchEvent(new Event("change"));
      }
    });

    const checkbox = item.querySelector(".picker-checkbox");
    checkbox.addEventListener("change", (e) => {
      const pid = parseInt(e.target.dataset.id, 10);
      if (e.target.checked) {
        if (tempSelectedProductIds.size >= 3) {
          e.target.checked = false;
          if (errorBox) {
            errorBox.textContent = "Một video chỉ được gắn tối đa 3 sản phẩm!";
            errorBox.style.display = "block";
          }
          return;
        }
        tempSelectedProductIds.add(pid);
        item.classList.add("selected");
      } else {
        tempSelectedProductIds.delete(pid);
        item.classList.remove("selected");
        if (errorBox) errorBox.style.display = "none";
      }
      updatePickerCounter();
    });

    listEl.appendChild(item);
  });
}

function confirmProductPicker() {
  selectedProductIds = new Set(tempSelectedProductIds);
  renderSelectedProductsPreview();
  closeProductPicker();
}

function renderSelectedProductsPreview() {
  const container = document.getElementById("selected-products-preview");
  const counter = document.getElementById("tagged-product-counter");
  if (counter) counter.textContent = `${selectedProductIds.size} / 3 sản phẩm`;
  if (!container) return;

  container.innerHTML = "";
  if (selectedProductIds.size === 0) return;

  selectedProductIds.forEach((pid) => {
    const p = myShopProducts.find((item) => item.id === pid);
    if (!p) return;

    let thumb = p.thumbnail_url || "";
    if (p.images && p.images.length > 0) {
      const primary = p.images.find((img) => img.is_primary) || p.images[0];
      thumb = primary.image_url || primary.object_key || thumb;
    }
    if (thumb && thumb.startsWith("/uploads/")) {
      thumb = `${CONFIG.API_BASE_URL.replace("/api", "")}${thumb}`;
    } else if (!thumb) {
      thumb = "../assets/images/logo.svg";
    }

    const priceText = Number(p.price || 0).toLocaleString("vi-VN") + " ₫";
    const badge = document.createElement("div");
    badge.className = "tagged-preview-card";
    badge.innerHTML = `
      <img src="${escapeHtml(thumb)}" alt="${escapeHtml(p.name)}" class="tagged-preview-img" onerror="this.src='../assets/images/logo.svg'">
      <div class="tagged-preview-details">
        <div class="tagged-preview-name">${escapeHtml(p.name)}</div>
        <div class="tagged-preview-price">${priceText}</div>
      </div>
      <button type="button" class="btn-remove-tagged-prod" data-id="${p.id}" title="Gỡ sản phẩm">&times;</button>
    `;

    badge.querySelector(".btn-remove-tagged-prod").addEventListener("click", () => {
      selectedProductIds.delete(pid);
      renderSelectedProductsPreview();
    });

    container.appendChild(badge);
  });
}

// ---------- GẮN SỰ KIỆN KHỞI TẠO ----------
function initEvents() {
  // Dropzone drag & drop
  dropzone.addEventListener("click", () => videoFileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("drag-over");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("drag-over");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("drag-over");
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleVideoSelection(files[0]);
    }
  });

  videoFileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleVideoSelection(e.target.files[0]);
    }
  });

  btnReselectVideo.addEventListener("click", () => {
    resetVideoSelection();
    videoFileInput.click();
  });

  // Chụp frame làm ảnh bìa
  btnCaptureFrame.addEventListener("click", () =>
    captureFrameToThumbnail(false),
  );

  // Tải ảnh bìa tùy chỉnh
  thumbFileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleThumbnailSelection(e.target.files[0]);
    }
  });

  // Đếm ký tự tiêu đề & mô tả
  inputTitle.addEventListener("input", () => {
    titleCharCounter.textContent = `${inputTitle.value.length} / 255`;
  });

  inputDesc.addEventListener("input", () => {
    descCharCounter.textContent = `${inputDesc.value.length} / 1000`;
  });

  // Thêm hashtag
  btnAddHashtag.addEventListener("click", () => addHashtag(inputHashtag.value));

  inputHashtag.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addHashtag(inputHashtag.value);
    }
  });

  tagPills.forEach((pill) => {
    pill.addEventListener("click", () => {
      addHashtag(pill.dataset.tag);
    });
  });

  hashtagsContainer.addEventListener("click", (e) => {
    if (e.target.classList.contains("btn-remove-tag")) {
      removeHashtag(e.target.dataset.tag);
    }
  });

  // Submit form
  formUpload.addEventListener("submit", handleSubmitUpload);

  // Gắn sản phẩm (Task T3D2296)
  const btnOpenPicker = document.getElementById("btn-open-product-picker");
  if (btnOpenPicker) btnOpenPicker.addEventListener("click", openProductPicker);

  const btnConfirmPicker = document.getElementById("btn-confirm-picker");
  if (btnConfirmPicker) btnConfirmPicker.addEventListener("click", confirmProductPicker);

  const btnCancelPicker = document.getElementById("btn-cancel-picker");
  if (btnCancelPicker) btnCancelPicker.addEventListener("click", closeProductPicker);

  const btnClosePickerModal = document.getElementById("btn-close-picker-modal");
  if (btnClosePickerModal) btnClosePickerModal.addEventListener("click", closeProductPicker);

  const pickerSearch = document.getElementById("input-search-picker");
  if (pickerSearch) {
    pickerSearch.addEventListener("input", (e) => renderPickerList(e.target.value));
  }
}

// Chạy khởi tạo khi trang đã sẵn sàng
document.addEventListener("DOMContentLoaded", () => {
  initEvents();
  checkSellerAndLoadProducts();
});
