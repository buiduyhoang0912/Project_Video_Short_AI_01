// Trang Giỏ hàng & Thanh toán áp Mã giảm giá của Shop (Task T3D2BFB).
// Người mua nhập hoặc chọn mã giảm giá khi thanh toán -> gọi POST /api/vouchers/apply để server kiểm tra
// và tính lại tiền; khi bấm Đặt hàng -> gửi voucher_codes lên POST /api/orders để server kiểm tra & trừ tiền.

const cartShopsContainer = document.getElementById("cart-shops-container");
const myOrdersContainer = document.getElementById("my-orders-container");
const refreshMyOrdersBtn = document.getElementById("btn-refresh-my-orders");
const checkoutForm = document.getElementById("checkout-form");
const recNameInput = document.getElementById("rec-name");
const recPhoneInput = document.getElementById("rec-phone");
const recAddressInput = document.getElementById("rec-address");
const payMethodSelect = document.getElementById("pay-method");
const summarySubtotalEl = document.getElementById("summary-subtotal");
const summaryDiscountEl = document.getElementById("summary-discount");
const summaryFinalTotalEl = document.getElementById("summary-final-total");
const appliedVouchersSummaryEl = document.getElementById("applied-vouchers-summary");
const submitCheckoutBtn = document.getElementById("btn-submit-checkout");

let currentCart = null;
// Map shop_id -> { code, discount_amount, subtotal, total_after_discount, message }
let appliedVouchersByShop = {};
// Map shop_id -> danh sách mã công khai của shop
let availableVouchersByShop = {};

async function loadCart() {
  if (!session.getToken()) {
    cartShopsContainer.innerHTML = `
      <div class="card" style="text-align: center; padding: 32px;">
        <p>Vui lòng <a href="login.html">đăng nhập</a> để xem giỏ hàng và áp dụng mã giảm giá.</p>
      </div>`;
    return;
  }

  try {
    currentCart = await api.get("/cart");
    const shops = currentCart.shops || [];

    // Tải danh sách mã giảm giá đang hoạt động của từng shop trong giỏ
    await Promise.all(
      shops.map(async (group) => {
        try {
          availableVouchersByShop[group.shop_id] = await api.get(
            `/shops/${group.shop_id}/vouchers`
          );
        } catch (_) {
          availableVouchersByShop[group.shop_id] = [];
        }
      })
    );

    // Kiểm tra lại các mã đã áp nếu giỏ hàng thay đổi số lượng
    for (const shopIdStr of Object.keys(appliedVouchersByShop)) {
      const shopId = Number(shopIdStr);
      const stillInCart = shops.some((g) => g.shop_id === shopId);
      if (!stillInCart) {
        delete appliedVouchersByShop[shopId];
      } else {
        try {
          const res = await api.post("/vouchers/apply", {
            code: appliedVouchersByShop[shopId].code,
          });
          appliedVouchersByShop[shopId] = res;
        } catch (_) {
          delete appliedVouchersByShop[shopId];
        }
      }
    }

    renderCart();
  } catch (error) {
    cartShopsContainer.innerHTML = `<div class="card text-error">${escapeHtml(error.message)}</div>`;
  }
}

function renderCart() {
  const shops = (currentCart && currentCart.shops) || [];
  if (shops.length === 0) {
    cartShopsContainer.innerHTML = `
      <div class="card" style="text-align: center; padding: 36px;">
        <h3>🛒 Giỏ hàng của bạn đang trống</h3>
        <p class="muted">Hãy ghé <a href="shop-public.html">Trang Cửa hàng công khai</a> để thêm sản phẩm và săn mã giảm giá nhé!</p>
      </div>`;
    updateCheckoutSummary();
    return;
  }

  cartShopsContainer.innerHTML = shops
    .map((group) => {
      const shopId = group.shop_id;
      const subtotal = Number(group.shop_subtotal ?? group.subtotal ?? 0);
      const applied = appliedVouchersByShop[shopId];
      const publicVouchers = availableVouchersByShop[shopId] || [];

      return `
        <article class="cart-shop-card" data-shop-id="${shopId}">
          <div class="cart-shop-header">
            <strong>🏪 ${escapeHtml(group.shop_name)}</strong>
            <span class="muted">Tạm tính Shop: <strong>${formatMoney(subtotal)}</strong></span>
          </div>

          <div>
            ${(group.items || [])
              .map((it) => {
                const pName = it.product ? it.product.name : it.product_name || `SP #${it.product_id}`;
                const uPrice = it.product ? it.product.price : it.unit_price || 0;
                return `
                  <div class="cart-item-row">
                    <div style="flex: 1; min-width: 180px;">
                      <strong>${escapeHtml(pName)}</strong>
                      <div class="muted" style="font-size: 13px;">Đơn giá: ${formatMoney(uPrice)}</div>
                    </div>
                    <div class="cart-qty-box">
                      <button type="button" data-qty-change="-1" data-item-id="${it.id}" data-cur-qty="${it.quantity}">−</button>
                      <span style="min-width: 26px; text-align: center; font-weight: 700;">${it.quantity}</span>
                      <button type="button" data-qty-change="1" data-item-id="${it.id}" data-cur-qty="${it.quantity}">+</button>
                    </div>
                    <div style="min-width: 110px; text-align: right;">
                      <strong>${formatMoney(it.line_total ?? uPrice * it.quantity)}</strong>
                    </div>
                    <button type="button" class="btn btn-small btn-danger" data-remove-item="${it.id}">✕</button>
                  </div>`;
              })
              .join("")}
          </div>

          <!-- Khung nhập Mã giảm giá của Shop -->
          <div class="shop-voucher-box">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
              <strong style="color: #be123c; font-size: 13px;">🎟️ Mã giảm giá của ${escapeHtml(group.shop_name)}</strong>
              ${
                applied
                  ? `<span class="voucher-tag-inline">
                       Đã áp mã ${escapeHtml(applied.code)}: -${formatMoney(applied.discount_amount)}
                       <button type="button" data-clear-voucher="${shopId}" style="border:none;background:none;color:#b91c1c;cursor:pointer;font-weight:800;">✕</button>
                     </span>`
                  : ""
              }
            </div>

            <div class="voucher-input-row">
              <input
                type="text"
                data-voucher-input="${shopId}"
                value="${applied ? escapeAttr(applied.code) : ""}"
                placeholder="Nhập mã giảm giá của shop (VD: GIAM10)..."
              >
              <button
                type="button"
                class="btn btn-small btn-primary"
                data-apply-voucher="${shopId}"
                style="white-space: nowrap;"
              >
                Áp dụng
              </button>
            </div>

            ${
              publicVouchers.length > 0
                ? `<div class="available-vouchers-chips">
                     <span class="muted" style="font-size: 12px; align-self: center;">Mã đang có của shop:</span>
                     ${publicVouchers
                       .map((v) => {
                         const label =
                           v.discount_type === "PERCENT"
                             ? `${v.code} (-${v.discount_value}% · đơn từ ${formatMoney(v.min_order_amount)})`
                             : `${v.code} (-${formatMoney(v.discount_value)} · đơn từ ${formatMoney(v.min_order_amount)})`;
                         return `
                           <button
                             type="button"
                             class="voucher-chip-btn"
                             data-pick-voucher="${escapeAttr(v.code)}"
                             data-target-shop="${shopId}"
                           >
                             🎟️ ${escapeHtml(label)}
                           </button>`;
                       })
                       .join("")}
                   </div>`
                : ""
            }
          </div>
        </article>`;
    })
    .join("");

  updateCheckoutSummary();
}

function updateCheckoutSummary() {
  const shops = (currentCart && currentCart.shops) || [];
  const subtotal = shops.reduce(
    (sum, g) => sum + Number(g.shop_subtotal ?? g.subtotal ?? 0),
    0
  );
  const appliedList = Object.values(appliedVouchersByShop);
  const totalDiscount = appliedList.reduce(
    (sum, v) => sum + Number(v.discount_amount || 0),
    0
  );
  const finalTotal = Math.max(0, subtotal - totalDiscount);

  summarySubtotalEl.textContent = formatMoney(subtotal);
  summaryDiscountEl.textContent = `-${formatMoney(totalDiscount)}`;
  summaryFinalTotalEl.textContent = formatMoney(finalTotal);

  if (appliedList.length > 0) {
    appliedVouchersSummaryEl.innerHTML = appliedList
      .map(
        (v) =>
          `<div>• <strong>${escapeHtml(v.code)}</strong> (${escapeHtml(v.shop_name)}): giảm <strong>${formatMoney(v.discount_amount)}</strong></div>`
      )
      .join("");
  } else {
    appliedVouchersSummaryEl.innerHTML = "";
  }
}

async function applyVoucherCode(shopId, rawCode) {
  const code = (rawCode || "").trim().toUpperCase();
  if (!code) {
    showToast("Vui lòng nhập mã giảm giá trước khi bấm Áp dụng.", "error");
    return;
  }
  try {
    const res = await api.post("/vouchers/apply", { code });
    appliedVouchersByShop[res.shop_id] = res;
    showToast(res.message);
    renderCart();
  } catch (error) {
    showToast(error.message, "error");
  }
}

cartShopsContainer.addEventListener("click", async (event) => {
  const pickBtn = event.target.closest("button[data-pick-voucher]");
  if (pickBtn) {
    const code = pickBtn.dataset.pickVoucher;
    const shopId = Number(pickBtn.dataset.targetShop);
    const input = cartShopsContainer.querySelector(`input[data-voucher-input="${shopId}"]`);
    if (input) input.value = code;
    await applyVoucherCode(shopId, code);
    return;
  }

  const applyBtn = event.target.closest("button[data-apply-voucher]");
  if (applyBtn) {
    const shopId = Number(applyBtn.dataset.applyVoucher);
    const input = cartShopsContainer.querySelector(`input[data-voucher-input="${shopId}"]`);
    await applyVoucherCode(shopId, input ? input.value : "");
    return;
  }

  const clearBtn = event.target.closest("button[data-clear-voucher]");
  if (clearBtn) {
    const shopId = Number(clearBtn.dataset.clearVoucher);
    delete appliedVouchersByShop[shopId];
    renderCart();
    return;
  }

  const qtyBtn = event.target.closest("button[data-qty-change]");
  if (qtyBtn) {
    const itemId = Number(qtyBtn.dataset.itemId);
    const curQty = Number(qtyBtn.dataset.curQty);
    const delta = Number(qtyBtn.dataset.qtyChange);
    const nextQty = curQty + delta;
    if (nextQty < 1) return;
    try {
      await api.put(`/cart/items/${itemId}`, { quantity: nextQty });
      await loadCart();
    } catch (error) {
      showToast(error.message, "error");
    }
    return;
  }

  const removeBtn = event.target.closest("button[data-remove-item]");
  if (removeBtn) {
    const itemId = Number(removeBtn.dataset.removeItem);
    try {
      await api.delete(`/cart/items/${itemId}`);
      showToast("Đã xoá sản phẩm khỏi giỏ hàng.");
      await loadCart();
    } catch (error) {
      showToast(error.message, "error");
    }
  }
});

if (checkoutForm) {
  checkoutForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const shops = (currentCart && currentCart.shops) || [];
    if (shops.length === 0) {
      showToast("Giỏ hàng của bạn đang trống!", "error");
      return;
    }

    const voucherCodes = Object.values(appliedVouchersByShop).map((v) => v.code);
    submitCheckoutBtn.disabled = true;
    try {
      const res = await api.post("/orders", {
        recipient_name: recNameInput.value.trim(),
        recipient_phone: recPhoneInput.value.trim(),
        recipient_address: recAddressInput.value.trim(),
        payment_method: payMethodSelect.value,
        voucher_codes: voucherCodes.length > 0 ? voucherCodes : null,
      });

      const discountMsg =
        res.total_discount > 0
          ? ` (Đã giảm ${formatMoney(res.total_discount)}, còn ${formatMoney(res.total_amount)})`
          : "";
      showToast(`🎉 Đặt hàng thành công!${discountMsg}`);
      appliedVouchersByShop = {};
      await Promise.all([loadCart(), loadMyOrders()]);
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      submitCheckoutBtn.disabled = false;
    }
  });
}

async function loadMyOrders() {
  if (!session.getToken() || !myOrdersContainer) return;
  try {
    const orders = await api.get("/orders");
    if (!Array.isArray(orders) || orders.length === 0) {
      myOrdersContainer.innerHTML = `<div class="muted">Bạn chưa có đơn hàng nào.</div>`;
      return;
    }
    myOrdersContainer.innerHTML = orders
      .slice(0, 8)
      .map((o) => {
        return `
          <div style="padding: 12px; border: 1px solid #e2e8f0; border-radius: 10px; margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
              <strong>Đơn #${o.id} · 🏪 ${escapeHtml(o.shop_name || `Shop #${o.shop_id}`)}</strong>
              <span class="order-badge ${escapeHtml(o.status)}">${escapeHtml(o.status)}</span>
            </div>
            <div class="muted" style="font-size: 13px; margin-top: 4px;">
              ${
                o.voucher_code && Number(o.discount_amount) > 0
                  ? `Tạm tính: ${formatMoney(o.subtotal_amount ?? o.total_amount + o.discount_amount)} ·
                     <span class="voucher-tag-inline">🎟️ Mã ${escapeHtml(o.voucher_code)}: -${formatMoney(o.discount_amount)}</span> · `
                  : ""
              }
              Thanh toán: <strong style="color: #dc2626;">${formatMoney(o.total_amount)}</strong>
            </div>
          </div>`;
      })
      .join("");
  } catch (error) {
    myOrdersContainer.innerHTML = `<div class="text-error">${escapeHtml(error.message)}</div>`;
  }
}

if (refreshMyOrdersBtn) {
  refreshMyOrdersBtn.addEventListener("click", loadMyOrders);
}

const currentUser = session.getUser();
if (currentUser && recNameInput && !recNameInput.value) {
  recNameInput.value = currentUser.display_name || currentUser.username || "";
}

loadCart();
loadMyOrders();
