/**
 * cart.js – T3D2B47: Trang giỏ hàng
 * Hiển thị theo shop, cập nhật số lượng, xóa sản phẩm, đặt hàng
 */
(function () {
  'use strict';

  const BASE_URL = (typeof CONFIG !== 'undefined' && CONFIG.API_BASE_URL) || '';

  const contentEl = document.getElementById('cart-content');
  const toastEl   = document.getElementById('toast');
  const modalEl   = document.getElementById('checkout-modal');

  let cartData = null; // {shops: [{shop_id, shop_name, items: [...], subtotal}], grand_total}

  // ── Init ──────────────────────────────────────────────────────────────────
  function init() {
    const token = getToken();
    if (!token) {
      renderEmpty('Vui lòng <a href="login.html">đăng nhập</a> để xem giỏ hàng.');
      return;
    }
    loadCart();

    document.getElementById('btn-cancel-checkout').addEventListener('click', closeModal);
    document.getElementById('btn-confirm-checkout').addEventListener('click', confirmOrder);
    modalEl.addEventListener('click', e => { if (e.target === modalEl) closeModal(); });
  }

  // ── Load cart ─────────────────────────────────────────────────────────────
  async function loadCart() {
    contentEl.innerHTML = '<div style="text-align:center;padding:40px;color:#aaa">Đang tải giỏ hàng...</div>';
    try {
      const res = await fetchWithAuth('/api/cart');
      if (res.status === 401) { renderEmpty('Phiên đăng nhập hết hạn. <a href="login.html">Đăng nhập lại</a>'); return; }
      if (!res.ok) throw new Error('API error ' + res.status);
      cartData = await res.json();
      renderCart();
    } catch (err) {
      contentEl.innerHTML = `<div class="empty-cart"><div class="icon">⚠️</div><p>${err.message}</p></div>`;
    }
  }

  // ── Render cart ───────────────────────────────────────────────────────────
  function renderCart() {
    // Normalize response format
    // Backend returns CartViewResponse: {shops: [ShopCartGroup], grand_total}
    const shops = cartData.shops || [];
    const grandTotal = cartData.grand_total || 0;

    if (!shops.length || shops.every(s => !s.items || !s.items.length)) {
      renderEmpty('Giỏ hàng của bạn đang trống. <a href="shop.html">Mua sắm ngay!</a>');
      return;
    }

    let html = '';
    shops.forEach(group => {
      const items = group.items || [];
      if (!items.length) return;

      html += `
        <div class="cart-shop-box">
          <div class="cart-shop-title">🏪 ${escHtml(group.shop_name || 'Cửa hàng')}</div>
          ${items.map(item => renderItem(item)).join('')}
          <div class="cart-shop-subtotal">
            Tạm tính: <strong>${formatPrice(group.subtotal || 0)}</strong>
          </div>
        </div>
      `;
    });

    // Summary / checkout
    html += `
      <div class="cart-summary">
        <div class="cart-total-row">
          <span>Tổng cộng (${countItems(shops)} sản phẩm):</span>
          <strong>${formatPrice(grandTotal)}</strong>
        </div>
        <button class="btn-checkout" id="btn-checkout">🛍️ Tiến hành đặt hàng</button>
      </div>
    `;

    contentEl.innerHTML = html;
    bindItemEvents();
    document.getElementById('btn-checkout').addEventListener('click', openModal);
  }

  function renderItem(item) {
    const invalid = item.is_invalid || (!item.is_active) || false;
    const imgUrl  = item.image_url || item.thumbnail_url ||
      'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2272%22 height=%2272%22%3E%3Crect fill=%22%23f0f0f0%22 width=%2272%22 height=%2272%22/%3E%3Ctext x=%2250%25%22 y=%2254%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 font-size=%2222%22%3E🖼️%3C/text%3E%3C/svg%3E';
    const stock   = item.stock != null ? item.stock : 999;
    const qty     = item.quantity || 1;

    return `
      <div class="cart-item-row" data-item-id="${item.id}">
        <img class="cart-item-img" src="${imgUrl}" alt="${escHtml(item.product_name || '')}"
             onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2272%22 height=%2272%22%3E%3Crect fill=%22%23f0f0f0%22 width=%2272%22 height=%2272%22/%3E%3Ctext x=%2250%25%22 y=%2254%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 font-size=%2222%22%3E%F0%9F%96%BC%EF%B8%8F%3C/text%3E%3C/svg%3E'" />
        <div class="cart-item-info">
          <div class="cart-item-name">${escHtml(item.product_name || 'Sản phẩm')}</div>
          <div class="cart-item-price">${formatPrice(item.unit_price || item.price || 0)}</div>
          ${invalid ? '<div class="cart-item-invalid">⚠️ Sản phẩm không còn khả dụng</div>' : ''}
        </div>
        <div class="cart-qty-control" ${invalid ? 'style="opacity:0.4;pointer-events:none"' : ''}>
          <button class="qty-dec" data-id="${item.id}" ${qty <= 1 ? 'disabled' : ''}>−</button>
          <input type="number" class="qty-val" data-id="${item.id}" value="${qty}" min="1" max="${stock}" readonly />
          <button class="qty-inc" data-id="${item.id}" ${qty >= stock ? 'disabled' : ''}>+</button>
        </div>
        <div class="cart-line-total">${formatPrice((item.unit_price || item.price || 0) * qty)}</div>
        <button class="cart-delete-btn" data-id="${item.id}" title="Xóa">🗑️</button>
      </div>
    `;
  }

  function bindItemEvents() {
    // Qty decrease
    contentEl.querySelectorAll('.qty-dec').forEach(btn => {
      btn.addEventListener('click', () => {
        const id  = btn.dataset.id;
        const inp = contentEl.querySelector(`.qty-val[data-id="${id}"]`);
        const newQty = Math.max(1, parseInt(inp.value) - 1);
        updateQty(id, newQty);
      });
    });
    // Qty increase
    contentEl.querySelectorAll('.qty-inc').forEach(btn => {
      btn.addEventListener('click', () => {
        const id  = btn.dataset.id;
        const inp = contentEl.querySelector(`.qty-val[data-id="${id}"]`);
        const newQty = Math.min(parseInt(inp.max) || 999, parseInt(inp.value) + 1);
        updateQty(id, newQty);
      });
    });
    // Delete
    contentEl.querySelectorAll('.cart-delete-btn').forEach(btn => {
      btn.addEventListener('click', () => deleteItem(btn.dataset.id));
    });
  }

  // ── Update quantity ───────────────────────────────────────────────────────
  async function updateQty(itemId, newQty) {
    try {
      const res = await fetchWithAuth(`/api/cart/items/${itemId}`, {
        method: 'PUT',
        body: JSON.stringify({ quantity: newQty })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Cập nhật thất bại');
      }
      await loadCart();
    } catch (err) {
      showToast('❌ ' + err.message, 'error');
    }
  }

  // ── Delete item ───────────────────────────────────────────────────────────
  async function deleteItem(itemId) {
    try {
      const res = await fetchWithAuth(`/api/cart/items/${itemId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Xóa thất bại');
      showToast('🗑️ Đã xóa sản phẩm khỏi giỏ hàng', 'success');
      await loadCart();
    } catch (err) {
      showToast('❌ ' + err.message, 'error');
    }
  }

  // ── Checkout modal ────────────────────────────────────────────────────────
  function openModal() { modalEl.classList.add('open'); }
  function closeModal() { modalEl.classList.remove('open'); }

  async function confirmOrder() {
    const address = document.getElementById('delivery-address').value.trim();
    const phone   = document.getElementById('delivery-phone').value.trim();
    const note    = document.getElementById('delivery-note').value.trim();

    if (!address) { showToast('⚠️ Vui lòng nhập địa chỉ giao hàng', 'error'); return; }
    if (!phone)   { showToast('⚠️ Vui lòng nhập số điện thoại', 'error'); return; }

    const btn = document.getElementById('btn-confirm-checkout');
    btn.disabled = true;
    btn.textContent = 'Đang xử lý...';

    try {
      const body = { delivery_address: address, phone, note };
      const res  = await fetchWithAuth('/api/orders', { method: 'POST', body: JSON.stringify(body) });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Đặt hàng thất bại');
      }

      closeModal();
      showToast('✅ Đặt hàng thành công! Cảm ơn bạn.', 'success');
      setTimeout(() => loadCart(), 1500); // reload empty cart
    } catch (err) {
      showToast('❌ ' + err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = '✅ Đặt hàng';
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  function countItems(shops) {
    return shops.reduce((acc, s) => acc + (s.items || []).length, 0);
  }

  function renderEmpty(msg) {
    contentEl.innerHTML = `<div class="empty-cart"><div class="icon">🛒</div><p>${msg}</p></div>`;
  }

  function getToken() {
    try {
      if (typeof session !== 'undefined') return session.getToken();
      return localStorage.getItem('access_token') || localStorage.getItem('token') || null;
    } catch (_) { return null; }
  }

  async function fetchWithAuth(path, options = {}) {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (token) headers['Authorization'] = 'Bearer ' + token;
    return fetch(BASE_URL + path, { ...options, headers });
  }

  function formatPrice(price) {
    if (price == null) return '—';
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
  }

  function escHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function showToast(msg, type) {
    toastEl.textContent = msg;
    toastEl.className = 'toast show' + (type ? ' ' + type : '');
    setTimeout(() => { toastEl.className = 'toast'; }, 2800);
  }

  // ── Start ─────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', init);
})();
