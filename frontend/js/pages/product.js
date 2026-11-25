/**
 * product.js – T3D2B47: Trang chi tiết sản phẩm
 * Gallery ảnh, chọn số lượng, thêm giỏ, mua ngay, thông tin shop
 */
(function () {
  'use strict';

  const BASE_URL = ((typeof CONFIG !== 'undefined' && (CONFIG.AUTH_BASE_URL || CONFIG.API_BASE_URL)) || '').replace(/\/api\/?$/, '');

  let product = null;
  let currentQty = 1;

  // ── DOM refs ──────────────────────────────────────────────────────────────
  const mainImg      = document.getElementById('gallery-main-img');
  const thumbsEl     = document.getElementById('gallery-thumbs');
  const nameEl       = document.getElementById('detail-name');
  const priceEl      = document.getElementById('detail-price');
  const soldEl       = document.getElementById('detail-sold');
  const stockNumEl   = document.getElementById('detail-stock-num');
  const stockStatEl  = document.getElementById('detail-stock-status');
  const descEl       = document.getElementById('detail-desc');
  const qtyInput     = document.getElementById('qty-input');
  const qtyMinus     = document.getElementById('qty-minus');
  const qtyPlus      = document.getElementById('qty-plus');
  const btnAddCart   = document.getElementById('btn-add-cart');
  const btnBuyNow    = document.getElementById('btn-buy-now');
  const shopCard     = document.getElementById('shop-info-card');
  const shopLogo     = document.getElementById('shop-logo');
  const shopNameEl   = document.getElementById('shop-name');
  const shopLinkEl   = document.getElementById('shop-link');
  const breadcrumb   = document.getElementById('breadcrumb-name');

  // ── Init ──────────────────────────────────────────────────────────────────
  async function init() {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('id');
    if (!id) {
      showError('Không tìm thấy sản phẩm. Vui lòng quay lại trang shop.');
      return;
    }
    await loadProduct(id);
  }

  // ── Load product ──────────────────────────────────────────────────────────
  async function loadProduct(id) {
    try {
      const res = await fetch(`${BASE_URL}/api/products/${id}`);
      if (res.status === 404) throw new Error('Sản phẩm không tồn tại');
      if (!res.ok) throw new Error('Lỗi API: ' + res.status);
      product = await res.json();
      renderProduct();
    } catch (err) {
      showError(err.message);
    }
  }

  // ── Render product ────────────────────────────────────────────────────────
  function renderProduct() {
    document.title = `${product.name} – ShortAI`;
    breadcrumb.textContent = product.name;
    nameEl.textContent = product.name;
    priceEl.textContent = formatPrice(product.price);
    soldEl.textContent  = product.sold_count || 0;

    const stock = product.stock || 0;
    stockNumEl.textContent = stock;
    if (stock <= 0) {
      stockStatEl.className = 'detail-stock out';
      stockStatEl.innerHTML = 'Trạng thái: <span>Hết hàng</span>';
      btnAddCart.disabled = true;
      btnBuyNow.disabled  = true;
      qtyMinus.disabled   = true;
      qtyPlus.disabled    = true;
      qtyInput.disabled   = true;
    } else {
      stockStatEl.innerHTML = `Còn hàng: <span>${stock}</span>`;
      qtyInput.max = stock;
      qtyInput.value = 1;
      currentQty = 1;
      updateQtyButtons();
    }

    descEl.textContent = product.description || 'Chưa có mô tả.';

    // Gallery
    renderGallery();

    // Shop card
    if (product.shop) {
      const shop = product.shop;
      shopNameEl.textContent = shop.name || 'Cửa hàng';
      shopLinkEl.href = `shop.html?shop_id=${shop.id}`;
      shopLinkEl.textContent = `Xem tất cả sản phẩm của ${shop.name || 'shop'} →`;
      const logoUrl = shop.logo_url || shop.avatar_url || '';
      if (logoUrl) {
        shopLogo.src = logoUrl;
      } else {
        shopLogo.src = 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2260%22 height=%2260%22%3E%3Crect fill=%22%23e0e0e0%22 width=%2260%22 height=%2260%22 rx=%2230%22/%3E%3Ctext x=%2250%25%22 y=%2254%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 font-size=%2226%22%3E🏪%3C/text%3E%3C/svg%3E';
      }
      shopCard.style.display = 'flex';
    }

    // Qty events
    qtyMinus.addEventListener('click', () => {
      if (currentQty > 1) { currentQty--; qtyInput.value = currentQty; updateQtyButtons(); }
    });
    qtyPlus.addEventListener('click', () => {
      if (currentQty < (product.stock || 1)) { currentQty++; qtyInput.value = currentQty; updateQtyButtons(); }
    });
    qtyInput.addEventListener('change', () => {
      let v = parseInt(qtyInput.value) || 1;
      v = Math.max(1, Math.min(v, product.stock || 1));
      currentQty = v;
      qtyInput.value = v;
      updateQtyButtons();
    });

    // Action buttons
    btnAddCart.addEventListener('click', () => handleAddToCart(false));
    btnBuyNow.addEventListener('click',  () => handleAddToCart(true));
  }

  // ── Gallery ───────────────────────────────────────────────────────────────
  function renderGallery() {
    const images = product.images || [];
    const PLACEHOLDER = 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22400%22 height=%22400%22%3E%3Crect fill=%22%23f0f0f0%22 width=%22400%22 height=%22400%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 fill=%22%23ccc%22 font-size=%2248%22%3E🖼️%3C/text%3E%3C/svg%3E';

    if (!images.length) {
      mainImg.src = PLACEHOLDER;
      thumbsEl.innerHTML = '';
      return;
    }

    // Sort by sort_order / display_order
    const sorted = [...images].sort((a, b) => (a.sort_order || a.display_order || 0) - (b.sort_order || b.display_order || 0));
    const primary = sorted.find(i => i.is_primary) || sorted[0];
    setMainImage(primary.image_url || primary.url || PLACEHOLDER);

    thumbsEl.innerHTML = sorted.map((img, idx) => {
      const url = img.image_url || img.url || PLACEHOLDER;
      return `<img src="${url}" data-idx="${idx}" alt="Ảnh ${idx + 1}" class="${img === primary ? 'active' : ''}" onerror="this.src='${PLACEHOLDER}'" />`;
    }).join('');

    thumbsEl.querySelectorAll('img').forEach(thumb => {
      thumb.addEventListener('click', () => {
        const imgObj = sorted[parseInt(thumb.dataset.idx)];
        setMainImage(imgObj.image_url || imgObj.url || PLACEHOLDER);
        thumbsEl.querySelectorAll('img').forEach(t => t.classList.remove('active'));
        thumb.classList.add('active');
      });
    });
  }

  function setMainImage(url) {
    mainImg.style.opacity = '0.5';
    mainImg.onload = () => { mainImg.style.opacity = '1'; };
    mainImg.src = url;
  }

  // ── Add to cart ───────────────────────────────────────────────────────────
  async function handleAddToCart(buyNow) {
    // Check login
    const token = getToken();
    if (!token) {
      showToast('Vui lòng đăng nhập để thêm vào giỏ hàng', 'error');
      setTimeout(() => { window.location.href = typeof loginUrl === 'function' ? loginUrl() : 'login.html?next=' + encodeURIComponent('pages/product.html' + window.location.search); }, 1200);
      return;
    }

    btnAddCart.disabled = true;
    btnBuyNow.disabled  = true;
    try {
      const res = await fetch(`${BASE_URL}/api/cart/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
        body: JSON.stringify({ product_id: product.id, quantity: currentQty })
      });

      if (res.status === 401) {
        showToast('Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.', 'error');
        setTimeout(() => { window.location.href = 'login.html'; }, 1200);
        return;
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Thêm vào giỏ thất bại');
      }

      showToast('✅ Đã thêm vào giỏ hàng!', 'success');
      if (buyNow) setTimeout(() => { window.location.href = 'cart.html'; }, 800);
    } catch (err) {
      showToast('❌ ' + err.message, 'error');
    } finally {
      btnAddCart.disabled = false;
      btnBuyNow.disabled  = false;
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  function updateQtyButtons() {
    qtyMinus.disabled = currentQty <= 1;
    qtyPlus.disabled  = currentQty >= (product ? (product.stock || 1) : 1);
  }

  function getToken() {
    try {
      if (typeof session !== 'undefined') return session.getToken();
      return localStorage.getItem('access_token') || localStorage.getItem('token') || null;
    } catch (_) { return null; }
  }

  function formatPrice(price) {
    if (price == null) return '—';
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
  }

  function showError(msg) {
    document.getElementById('detail-layout').innerHTML =
      `<div style="grid-column:1/-1;text-align:center;padding:60px 20px;color:#ef4444">⚠️ ${msg}</div>`;
  }

  // ── Start ─────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', init);
})();
