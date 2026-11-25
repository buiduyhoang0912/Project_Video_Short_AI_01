/**
 * shop.js – T3D2B47: Trang Shop lưới sản phẩm
 * Tìm kiếm, lọc danh mục/giá/shop, sắp xếp, phân trang
 */
(function () {
  'use strict';

  const BASE_URL = ((typeof CONFIG !== 'undefined' && (CONFIG.AUTH_BASE_URL || CONFIG.API_BASE_URL)) || '').replace(/\/api\/?$/, '');
  const PAGE_SIZE = 12;

  let currentPage = 1;
  let debounceTimer = null;

  // ── DOM refs ──────────────────────────────────────────────────────────────
  const qInput      = document.getElementById('q');
  const categorySel = document.getElementById('category');
  const minPrice    = document.getElementById('min-price');
  const maxPrice    = document.getElementById('max-price');
  const sortBySel   = document.getElementById('sort-by');
  const btnFilter   = document.getElementById('btn-filter');
  const gridEl      = document.getElementById('product-grid');
  const paginationEl= document.getElementById('pagination');

  // ── Init ──────────────────────────────────────────────────────────────────
  async function init() {
    // Read URL params (support ?q=&category_id=&shop_id=)
    const params = new URLSearchParams(window.location.search);
    if (params.get('q'))           qInput.value        = params.get('q');
    if (params.get('category_id')) categorySel.value   = params.get('category_id');
    if (params.get('min_price'))   minPrice.value       = params.get('min_price');
    if (params.get('max_price'))   maxPrice.value       = params.get('max_price');
    if (params.get('sort_by'))     sortBySel.value      = params.get('sort_by');
    if (params.get('page'))        currentPage          = parseInt(params.get('page')) || 1;

    await loadCategories();
    await loadProducts();

    // Events
    btnFilter.addEventListener('click', () => { currentPage = 1; loadProducts(); });
    qInput.addEventListener('input', debounceLoad);
    sortBySel.addEventListener('change', () => { currentPage = 1; loadProducts(); });
  }

  function debounceLoad() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => { currentPage = 1; loadProducts(); }, 350);
  }

  // ── Load categories ───────────────────────────────────────────────────────
  async function loadCategories() {
    try {
      const res = await fetch(BASE_URL + '/api/categories');
      if (!res.ok) return;
      const data = await res.json();
      const list = Array.isArray(data) ? data : (data.items || []);
      list.forEach(cat => {
        const opt = document.createElement('option');
        opt.value = cat.id;
        opt.textContent = cat.name;
        categorySel.appendChild(opt);
      });
    } catch (_) { /* categories optional */ }
  }

  // ── Build query string ────────────────────────────────────────────────────
  function buildQuery(page) {
    const p = new URLSearchParams();
    if (qInput.value.trim())       p.set('q',           qInput.value.trim());
    if (categorySel.value)         p.set('category_id', categorySel.value);
    if (minPrice.value)            p.set('min_price',   minPrice.value);
    if (maxPrice.value)            p.set('max_price',   maxPrice.value);
    if (sortBySel.value)           p.set('sort_by',     sortBySel.value);
    p.set('page',      page);
    p.set('page_size', PAGE_SIZE);
    return p.toString();
  }

  // ── Load products ─────────────────────────────────────────────────────────
  async function loadProducts() {
    renderSkeletons();
    const qs = buildQuery(currentPage);
    try {
      const res = await fetch(`${BASE_URL}/api/products?${qs}`);
      if (!res.ok) throw new Error('API error ' + res.status);
      const data = await res.json();

      // Support both {items, total, page, page_size} and plain array
      const items = Array.isArray(data) ? data : (data.items || []);
      const total = data.total || items.length;
      const totalPages = Math.ceil(total / PAGE_SIZE) || 1;

      renderGrid(items);
      renderPagination(totalPages);
    } catch (err) {
      gridEl.innerHTML = `<div class="empty-state">⚠️ Không thể tải sản phẩm. Vui lòng thử lại.<br><small>${err.message}</small></div>`;
      paginationEl.innerHTML = '';
    }
  }

  // ── Render skeleton placeholders ──────────────────────────────────────────
  function renderSkeletons() {
    gridEl.innerHTML = Array.from({ length: 8 }).map(() => `
      <div class="skeleton-card">
        <div class="skeleton-img"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-line short"></div>
      </div>
    `).join('');
  }

  // ── Render product grid ───────────────────────────────────────────────────
  function renderGrid(items) {
    if (!items.length) {
      gridEl.innerHTML = '<div class="empty-state" style="grid-column:1/-1">🔍 Không tìm thấy sản phẩm nào.</div>';
      return;
    }
    gridEl.innerHTML = items.map(p => {
      const imgUrl = getProductThumb(p);
      const price  = formatPrice(p.price);
      const sold   = p.sold_count || 0;
      const shopName = p.shop_name || (p.shop && p.shop.name) || '';
      return `
        <a class="product-card" href="product.html?id=${p.id}">
          <img src="${imgUrl}" alt="${escHtml(p.name)}"
               onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22%3E%3Crect fill=%22%23f0f0f0%22 width=%22200%22 height=%22200%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 fill=%22%23ccc%22 font-size=%2228%22%3E🖼️%3C/text%3E%3C/svg%3E'" />
          <div class="product-card-body">
            <div class="product-card-name">${escHtml(p.name)}</div>
            <div class="product-card-price">${price}</div>
            <div class="product-card-meta">Đã bán: ${sold}</div>
            ${shopName ? `<div class="product-card-shop">🏪 ${escHtml(shopName)}</div>` : ''}
          </div>
        </a>
      `;
    }).join('');
  }

  // ── Render pagination ─────────────────────────────────────────────────────
  function renderPagination(totalPages) {
    if (totalPages <= 1) { paginationEl.innerHTML = ''; return; }
    let html = '';
    // Prev
    html += `<button ${currentPage === 1 ? 'disabled' : ''} data-page="${currentPage - 1}">‹ Trước</button>`;
    // Pages: show up to 5 around current
    const start = Math.max(1, currentPage - 2);
    const end   = Math.min(totalPages, currentPage + 2);
    if (start > 1) html += `<button data-page="1">1</button>${start > 2 ? '<button disabled>…</button>' : ''}`;
    for (let i = start; i <= end; i++) {
      html += `<button class="${i === currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
    }
    if (end < totalPages) html += `${end < totalPages - 1 ? '<button disabled>…</button>' : ''}<button data-page="${totalPages}">${totalPages}</button>`;
    // Next
    html += `<button ${currentPage === totalPages ? 'disabled' : ''} data-page="${currentPage + 1}">Sau ›</button>`;

    paginationEl.innerHTML = html;
    paginationEl.querySelectorAll('button[data-page]').forEach(btn => {
      btn.addEventListener('click', () => {
        currentPage = parseInt(btn.dataset.page);
        window.scrollTo({ top: 0, behavior: 'smooth' });
        loadProducts();
      });
    });
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  function getProductThumb(p) {
    if (p.images && p.images.length) {
      const primary = p.images.find(img => img.is_primary) || p.images[0];
      return primary.image_url || primary.url || '';
    }
    if (p.thumbnail_url) return p.thumbnail_url;
    if (p.image_url) return p.image_url;
    return 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22%3E%3Crect fill=%22%23f0f0f0%22 width=%22200%22 height=%22200%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 fill=%22%23ccc%22 font-size=%2228%22%3E🖼️%3C/text%3E%3C/svg%3E';
  }

  function formatPrice(price) {
    if (price == null) return '—';
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
  }

  function escHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ── Start ─────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', init);
})();
