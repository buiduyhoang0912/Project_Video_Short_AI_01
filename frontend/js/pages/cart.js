// Trang Giỏ hàng & Thanh toán (Task T3D2B79).
// Hỗ trợ: Giỏ hàng nhóm theo shop, tăng/giảm/xoá, sổ địa chỉ nhận hàng, COD / thanh toán mô phỏng,
// tóm tắt đơn, báo lỗi hết hàng & tích hợp mã giảm giá của Shop.

const cartShopsContainer = document.getElementById("cart-shops-container");
const myOrdersContainer = document.getElementById("my-orders-container");
const refreshMyOrdersBtn = document.getElementById("btn-refresh-my-orders");
const checkoutForm = document.getElementById("checkout-form");
const recNameInput = document.getElementById("rec-name");
const recPhoneInput = document.getElementById("rec-phone");
const recAddressInput = document.getElementById("rec-address");
const chkSaveAddress = document.getElementById("chk-save-address");
const savedAddressListEl = document.getElementById("saved-address-list");
const payMethodSelect = document.getElementById("pay-method");
const summarySubtotalEl = document.getElementById("summary-subtotal");
const summaryDiscountEl = document.getElementById("summary-discount");
const summaryFinalTotalEl = document.getElementById("summary-final-total");
const appliedVouchersSummaryEl = document.getElementById("applied-vouchers-summary");
const submitCheckoutBtn = document.getElementById("btn-submit-checkout");
const outOfStockAlertEl = document.getElementById("cart-out-of-stock-alert");

let currentCart = null;
// Map shop_id -> { code, discount_amount, subtotal, total_after_discount, message }
let appliedVouchersByShop = {};
// Map shop_id -> danh sách mã công khai của shop
let availableVouchersByShop = {};

// Key sổ địa chỉ theo người dùng
function getAddressBookKey() {
  const user = session.getUser();
  const uid = user ? user.id : "guest";
  return `clipshop_address_book_${uid}`;
}

function getSavedAddresses() {
  try {
    const raw = localStorage.getItem(getAddressBookKey());
    return raw ? JSON.parse(raw) : [];
  } catch (_) {
    return [];
  }
}

function saveAddressToBook(addr) {
  if (!addr.name || !addr.phone || !addr.address) return;
  const list = getSavedAddresses();
  // Tránh trùng lặp
  const exists = list.some(
    (a) => a.phone === addr.phone && a.address.toLowerCase() === addr.address.toLowerCase()
  );
  if (!exists) {
    list.unshift(addr);
    if (list.length > 5) list.pop(); // Giữ tối đa 5 địa chỉ
    localStorage.setItem(getAddressBookKey(), JSON.stringify(list));
  }
}

function removeAddressFromBook(index) {
  const list = getSavedAddresses();
  if (index >= 0 && index < list.length) {
    list.splice(index, 1);
    localStorage.setItem(getAddressBookKey(), JSON.stringify(list));
    renderSavedAddresses();
  }
}

function renderSavedAddresses() {
  if (!savedAddressListEl) return;
  const list = getSavedAddresses();
  if (list.length === 0) {
    savedAddressListEl.innerHTML = `<span class="muted" style="font-size: 12px;">Chưa có địa chỉ nào được lưu. Hãy nhập thông tin bên dưới và bấm đặt hàng để lưu.</span>`;
    return;
  }

  savedAddressListEl.innerHTML = list
    .map(
      (a, idx) => `
        <div class="saved-addr-chip" data-addr-idx="${idx}" title="${escapeAttr(a.address)}">
          <span>📍 <strong>${escapeHtml(a.name)}</strong> (${escapeHtml(a.phone)}) - ${escapeHtml(a.address)}</span>
          <button type="button" data-del-addr="${idx}" style="border:none; background:none; color:#ef4444; cursor:pointer; font-size:13px; font-weight:700;">×</button>
        </div>`
    )
    .join("");
}

async function loadCart() {
  if (!session.getToken()) {
    cartShopsContainer.innerHTML = `
      <div class="card" style="text-align: center; padding: 32px;">
        <p>Vui lòng <a href="login.html">đăng nhập</a> để xem giỏ hàng và thanh toán.</p>
      </div>`;
    return;
  }

  try {
    currentCart = await api.get("/cart");
    const shops = currentCart.shops || [];

    // Tải danh sách voucher nếu có
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

    // Kiểm tra lại voucher
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
        <p class="muted">Hãy ghé <a href="shop-public.html">Trang Cửa hàng công khai</a> để mua sắm ngay nhé!</p>
      </div>`;
    if (outOfStockAlertEl) outOfStockAlertEl.style.display = "none";
    updateCheckoutSummary();
    return;
  }

  let hasInvalidItems = false;

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
                const prod = it.product || {};
                const pName = prod.name || it.product_name || `SP #${it.product_id}`;
                const uPrice = prod.price ?? it.unit_price ?? 0;
                const stock = typeof prod.stock === "number" ? prod.stock : 999;
                const isValid = it.is_valid !== false && stock > 0 && it.quantity <= stock;
                if (!isValid) hasInvalidItems = true;

                let statusBadge = "";
                if (stock <= 0) {
                  statusBadge = `<span style="display:inline-block; background:#fee2e2; color:#b91c1c; font-size:11px; font-weight:700; padding:2px 8px; border-radius:999px; margin-left:6px;">⚠️ Hết hàng</span>`;
                } else if (it.quantity > stock) {
                  statusBadge = `<span style="display:inline-block; background:#fef3c7; color:#b45309; font-size:11px; font-weight:700; padding:2px 8px; border-radius:999px; margin-left:6px;">⚠️ Vượt tồn kho (Còn ${stock})</span>`;
                }

                return `
                  <div class="cart-item-row ${!isValid ? "item-invalid" : ""}">
                    <div style="flex: 1; min-width: 180px;">
                      <strong>${escapeHtml(pName)}</strong> ${statusBadge}
                      <div class="muted" style="font-size: 13px;">
                        Đơn giá: ${formatMoney(uPrice)} ${stock > 0 ? `· Tồn kho: ${stock}` : ""}
                      </div>
                      ${it.error_message ? `<div style="color:#dc2626; font-size:12px; margin-top:2px;">⚠️ ${escapeHtml(it.error_message)}</div>` : ""}
                    </div>
                    <div class="cart-qty-box">
                      <button type="button" data-qty-change="-1" data-item-id="${it.id}" data-cur-qty="${it.quantity}">−</button>
                      <span style="min-width: 26px; text-align: center; font-weight: 700;">${it.quantity}</span>
                      <button type="button" data-qty-change="1" data-item-id="${it.id}" data-cur-qty="${it.quantity}" ${it.quantity >= stock ? "disabled title='Đã đạt giới hạn tồn kho'" : ""}>+</button>
                    </div>
                    <div style="min-width: 110px; text-align: right;">
                      <strong>${formatMoney(it.line_total ?? uPrice * it.quantity)}</strong>
                    </div>
                    <button type="button" class="btn btn-small btn-danger" data-remove-item="${it.id}" title="Xoá khỏi giỏ">✕</button>
                  </div>`;
              })
              .join("")}
          </div>

          <!-- Khung voucher shop nếu có -->
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
                     <span class="muted" style="font-size: 12px; align-self: center;">Mã đang có:</span>
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

  // Hiển thị cảnh báo hết hàng nếu có
  if (outOfStockAlertEl) {
    outOfStockAlertEl.style.display = hasInvalidItems ? "block" : "none";
  }

  // Khoá nút đặt hàng nếu giỏ hàng có hàng hết hàng
  if (submitCheckoutBtn) {
    if (hasInvalidItems) {
      submitCheckoutBtn.disabled = true;
      submitCheckoutBtn.title = "Vui lòng xoá hoặc giảm số lượng các sản phẩm hết hàng";
    } else {
      submitCheckoutBtn.disabled = false;
      submitCheckoutBtn.title = "";
    }
  }

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
    showToast(res.message || "Đã áp dụng mã giảm giá!");
    renderCart();
  } catch (error) {
    showToast(error.message, "error");
  }
}

// Bắt sự kiện giỏ hàng
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

  // Tăng/giảm số lượng
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

  // Xoá sản phẩm
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

// Bắt sự kiện Sổ địa chỉ
if (savedAddressListEl) {
  savedAddressListEl.addEventListener("click", (e) => {
    // Xoá địa chỉ
    const delBtn = e.target.closest("button[data-del-addr]");
    if (delBtn) {
      e.stopPropagation();
      const idx = Number(delBtn.dataset.delAddr);
      removeAddressFromBook(idx);
      return;
    }

    // Chọn địa chỉ
    const chip = e.target.closest(".saved-addr-chip");
    if (chip) {
      const idx = Number(chip.dataset.addrIdx);
      const list = getSavedAddresses();
      const item = list[idx];
      if (item) {
        recNameInput.value = item.name || "";
        recPhoneInput.value = item.phone || "";
        recAddressInput.value = item.address || "";
        // Highlight active chip
        document.querySelectorAll(".saved-addr-chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        showToast(`Đã chọn địa chỉ của ${item.name}`);
      }
    }
  });
}

// Xử lý submit thanh toán
if (checkoutForm) {
  checkoutForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const shops = (currentCart && currentCart.shops) || [];
    if (shops.length === 0) {
      showToast("Giỏ hàng của bạn đang trống!", "error");
      return;
    }

    // Kiểm tra tên, số điện thoại, địa chỉ
    const name = recNameInput.value.trim();
    const phone = recPhoneInput.value.trim();
    const address = recAddressInput.value.trim();

    if (!name || !phone || !address) {
      showToast("Vui lòng điền đầy đủ thông tin giao hàng!", "error");
      return;
    }

    // Lưu vào sổ địa chỉ nếu người dùng tick
    if (chkSaveAddress && chkSaveAddress.checked) {
      saveAddressToBook({ name, phone, address });
      renderSavedAddresses();
    }

    const voucherCodes = Object.values(appliedVouchersByShop).map((v) => v.code);
    submitCheckoutBtn.disabled = true;
    submitCheckoutBtn.textContent = "⏳ Đang xử lý đặt hàng...";

    try {
      const res = await api.post("/orders", {
        recipient_name: name,
        recipient_phone: phone,
        recipient_address: address,
        payment_method: payMethodSelect.value,
        voucher_codes: voucherCodes.length > 0 ? voucherCodes : null,
      });

      const isBankTransfer = payMethodSelect.value === "BANK_TRANSFER";
      const discountMsg =
        res.total_discount > 0
          ? ` (Đã giảm ${formatMoney(res.total_discount)}, còn ${formatMoney(res.total_amount)})`
          : "";
      showToast(`🎉 Đặt hàng thành công!${discountMsg}`);
      appliedVouchersByShop = {};

      // Hiển thị VietQR Modal nếu phương thức là chuyển khoản
      if (isBankTransfer && res.orders && res.orders.length > 0) {
        showVietQrModal(res.orders[0]);
      }

      await Promise.all([loadCart(), loadMyOrders()]);
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      submitCheckoutBtn.disabled = false;
      submitCheckoutBtn.textContent = "✅ Đặt hàng ngay";
    }
  });
}

function showVietQrModal(order) {
  const modal = document.getElementById("vietqr-modal");
  if (!modal) return;

  const qrImg = document.getElementById("vietqr-image");
  const bankEl = document.getElementById("vietqr-bank-name");
  const accNumEl = document.getElementById("vietqr-account-number");
  const accHolderEl = document.getElementById("vietqr-account-holder");
  const amountEl = document.getElementById("vietqr-amount");
  const memoEl = document.getElementById("vietqr-memo");

  const bankName = order.bank_name || "MB";
  const accNumber = order.bank_account_number || "0987654321";
  const accHolder = order.bank_account_holder || (order.shop_name ? order.shop_name.toUpperCase() : "SHOP");
  const amount = Number(order.total_amount || 0);
  const memo = `DH${order.id}`;

  const qrUrl = order.vietqr_url || 
    `https://img.vietqr.io/image/${bankName}-${accNumber}-compact2.png?amount=${Math.round(amount)}&addInfo=${encodeURIComponent(memo)}&accountName=${encodeURIComponent(accHolder)}`;

  if (qrImg) qrImg.src = qrUrl;
  if (bankEl) bankEl.textContent = bankName;
  if (accNumEl) accNumEl.textContent = accNumber;
  if (accHolderEl) accHolderEl.textContent = accHolder;
  if (amountEl) amountEl.textContent = formatMoney(amount);
  if (memoEl) memoEl.textContent = memo;

  modal.style.display = "flex";
}

const btnCloseVietQr = document.getElementById("btn-close-vietqr");
if (btnCloseVietQr) {
  btnCloseVietQr.addEventListener("click", () => {
    const modal = document.getElementById("vietqr-modal");
    if (modal) modal.style.display = "none";
    showToast("Cảm ơn bạn! Đơn hàng đang chờ người bán xác nhận thanh toán.");
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

    const targetOrderId =
      new URLSearchParams(window.location.search).get("order_id") ||
      (window.location.hash.startsWith("#order-")
        ? window.location.hash.replace("#order-", "")
        : null);

    myOrdersContainer.innerHTML = orders
      .slice(0, 15)
      .map((o) => {
        const isTarget = targetOrderId && String(o.id) === String(targetOrderId);
        const highlightStyle = isTarget
          ? "border: 2px solid #2563eb; background: #eff6ff; box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);"
          : "border: 1px solid #e2e8f0; background: #ffffff;";

        return `
          <div id="order-${o.id}" class="my-order-card" style="padding: 12px; ${highlightStyle} border-radius: 10px; margin-bottom: 10px; transition: all 0.3s ease;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
              <strong>Đơn #${o.id} · 🏪 ${escapeHtml(o.shop_name || `Shop #${o.shop_id}`)}</strong>
              <div>
                ${isTarget ? '<span style="display: inline-block; background: #2563eb; color: #fff; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 999px; margin-right: 6px;">Vừa cập nhật</span>' : ""}
                <span class="order-badge ${escapeHtml(o.status)}">${escapeHtml(o.status)}</span>
              </div>
            </div>
            <div class="muted" style="font-size: 13px; margin-top: 4px;">
              ${
                o.voucher_code && Number(o.discount_amount) > 0
                  ? `Tạm tính: ${formatMoney(o.subtotal_amount ?? o.total_amount + o.discount_amount)} ·
                     <span class="voucher-tag-inline">🎟️ Mã ${escapeHtml(o.voucher_code)}: -${formatMoney(o.discount_amount)}</span> · `
                  : ""
              }
              Tổng thanh toán: <strong style="color: #dc2626;">${formatMoney(o.total_amount)}</strong> ·
              PTTT: <strong>${escapeHtml(o.payment_method || "COD")}</strong>
            </div>
            <div class="muted" style="font-size: 12px; margin-top: 4px;">
              📍 Giao tới: ${escapeHtml(o.delivery_address || o.recipient_address || "Địa chỉ mặc định")}
              ${o.phone || o.recipient_phone ? `(${escapeHtml(o.phone || o.recipient_phone)})` : ""}
            </div>
          </div>`;
      })
      .join("");
  } catch (error) {
    myOrdersContainer.innerHTML = `<div class="muted text-error">${escapeHtml(error.message)}</div>`;
  }
}

if (refreshMyOrdersBtn) {
  refreshMyOrdersBtn.addEventListener("click", loadMyOrders);
}

document.addEventListener("DOMContentLoaded", () => {
  renderSavedAddresses();
  // Điền thử thông tin user nếu có
  const u = session.getUser();
  if (u) {
    if (!recNameInput.value && (u.display_name || u.full_name)) {
      recNameInput.value = u.display_name || u.full_name;
    }
  }
  loadCart();
  loadMyOrders();
});
