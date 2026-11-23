// Trang Quản lý Đơn hàng & Huỷ đơn (Task T3D2B93).
// Hỗ trợ: Danh sách đơn hàng theo trạng thái, chi tiết đơn có dòng thời gian trạng thái (Timeline),
// huỷ đơn hàng khi còn Chờ xác nhận (PENDING) và hoàn tồn kho đúng một lần.

const ordersListContainer = document.getElementById("orders-list-container");
const statusTabsContainer = document.getElementById("status-tabs");
const orderDetailModal = document.getElementById("order-detail-modal");
const btnCloseModal = document.getElementById("btn-close-modal");

let currentStatusFilter = "";

function getBadgeClass(status) {
  const s = (status || "").toLowerCase();
  switch (s) {
    case "pending":
      return "badge-pending";
    case "confirmed":
      return "badge-confirmed";
    case "shipped":
      return "badge-shipped";
    case "delivered":
      return "badge-delivered";
    case "cancelled":
      return "badge-cancelled";
    default:
      return "badge-pending";
  }
}

function getStatusLabel(status) {
  const s = (status || "").toUpperCase();
  switch (s) {
    case "PENDING":
      return "Chờ xác nhận";
    case "CONFIRMED":
      return "Đã xác nhận";
    case "SHIPPED":
      return "Đang vận chuyển";
    case "DELIVERED":
      return "Hoàn thành";
    case "CANCELLED":
      return "Đã huỷ";
    default:
      return s;
  }
}

async function loadOrders() {
  if (!session.getToken()) {
    ordersListContainer.innerHTML = `
      <div class="card" style="text-align: center; padding: 40px;">
        <p>Vui lòng <a href="login.html">đăng nhập</a> để xem đơn hàng của bạn.</p>
      </div>`;
    return;
  }

  ordersListContainer.innerHTML = `
    <div class="card muted" style="text-align: center; padding: 40px;">
      Đang tải danh sách đơn hàng...
    </div>`;

  try {
    const url = currentStatusFilter
      ? `/orders?status=${encodeURIComponent(currentStatusFilter)}`
      : "/orders";
    const orders = await api.get(url);

    if (!Array.isArray(orders) || orders.length === 0) {
      ordersListContainer.innerHTML = `
        <div class="card" style="text-align: center; padding: 50px 20px;">
          <h3>📦 Chưa có đơn hàng nào</h3>
          <p class="muted">Không tìm thấy đơn hàng nào ${
            currentStatusFilter ? `ở trạng thái "${getStatusLabel(currentStatusFilter)}"` : ""
          }.</p>
          <a href="shop-public.html" class="btn btn-primary" style="margin-top: 12px; display: inline-block;">Khám phá sản phẩm ngay</a>
        </div>`;
      return;
    }

    renderOrders(orders);
  } catch (error) {
    ordersListContainer.innerHTML = `<div class="card text-error">${escapeHtml(error.message)}</div>`;
  }
}

function renderOrders(orders) {
  ordersListContainer.innerHTML = orders
    .map((o) => {
      const isPending = (o.status || "").toUpperCase() === "PENDING";
      const items = o.items || [];

      return `
        <article class="order-card" data-order-id="${o.id}">
          <div class="order-card-header">
            <div>
              <strong>Đơn #${o.id}</strong> · 🏪 <strong>${escapeHtml(o.shop_name || `Shop #${o.shop_id}`)}</strong>
              <div class="muted" style="font-size: 12px; margin-top: 2px;">
                Ngày đặt: ${new Date(o.created_at).toLocaleString("vi-VN")} · PTTT: <strong>${escapeHtml(o.payment_method)}</strong>
              </div>
            </div>
            <div>
              <span class="order-badge-status ${getBadgeClass(o.status)}">
                ${getStatusLabel(o.status)}
              </span>
            </div>
          </div>

          <div style="padding: 6px 0;">
            ${items
              .map(
                (it) => `
                <div class="order-product-row">
                  <div>
                    <strong>${escapeHtml(it.product_name || `Sản phẩm #${it.product_id}`)}</strong>
                    <div class="muted" style="font-size: 12px;">Số lượng: x${it.quantity} · Đơn vị: ${formatMoney(it.unit_price)}</div>
                  </div>
                  <div style="font-weight: 600;">${formatMoney(it.line_total || it.unit_price * it.quantity)}</div>
                </div>`
              )
              .join("")}
          </div>

          <div class="order-footer">
            <div style="font-size: 13px;">
              ${
                o.voucher_code && Number(o.discount_amount) > 0
                  ? `<span class="voucher-tag-inline" style="background:#fee2e2; color:#be123c; padding:2px 8px; border-radius:4px; font-size:11px; margin-right:6px;">🎟️ Giảm: -${formatMoney(o.discount_amount)}</span>`
                  : ""
              }
              Tổng thanh toán: <strong style="color: #dc2626; font-size: 16px;">${formatMoney(o.total_amount)}</strong>
            </div>

            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <button type="button" class="btn btn-small" data-view-detail="${o.id}">
                ⏱️ Chi tiết & Timeline
              </button>
              ${
                isPending
                  ? `<button type="button" class="btn btn-small btn-danger" data-cancel-order="${o.id}">
                       🚫 Huỷ đơn hàng
                     </button>`
                  : ""
              }
            </div>
          </div>
        </article>`;
    })
    .join("");
}

// Huỷ đơn hàng
async function handleCancelOrder(orderId) {
  const confirmed = confirm(
    `Bạn có chắc chắn muốn huỷ đơn hàng #${orderId} không?\n\nSố lượng sản phẩm sẽ được tự động hoàn lại vào kho ngay lập tức.`
  );
  if (!confirmed) return;

  try {
    const res = await api.post(`/orders/${orderId}/cancel`);
    showToast(res.message || "Huỷ đơn hàng thành công!");
    await loadOrders();
  } catch (error) {
    showToast(error.message, "error");
  }
}

// Xem chi tiết & Timeline
async function handleViewDetail(orderId) {
  try {
    const o = await api.get(`/orders/${orderId}`);
    document.getElementById("modal-order-title").textContent = `Chi tiết Đơn hàng #${o.id} · ${o.shop_name || `Shop #${o.shop_id}`}`;
    document.getElementById("modal-total-amount").textContent = formatMoney(o.total_amount);

    // Shipping info
    document.getElementById("modal-shipping-info").innerHTML = `
      <div><strong>Người nhận:</strong> ${escapeHtml(o.recipient_name)} (${escapeHtml(o.recipient_phone)})</div>
      <div style="margin-top: 4px;"><strong>Địa chỉ:</strong> ${escapeHtml(o.recipient_address)}</div>
      <div style="margin-top: 4px;"><strong>Phương thức thanh toán:</strong> ${escapeHtml(o.payment_method)}</div>
      <div style="margin-top: 4px;"><strong>Trạng thái hiện tại:</strong> <span class="order-badge-status ${getBadgeClass(o.status)}">${getStatusLabel(o.status)}</span></div>
    `;

    // Items
    document.getElementById("modal-items-list").innerHTML = (o.items || [])
      .map(
        (it) => `
        <div class="order-product-row">
          <div>
            <strong>${escapeHtml(it.product_name || `SP #${it.product_id}`)}</strong>
            <div class="muted" style="font-size: 12px;">Đơn giá: ${formatMoney(it.unit_price)} × ${it.quantity}</div>
          </div>
          <div><strong>${formatMoney(it.line_total || it.unit_price * it.quantity)}</strong></div>
        </div>`
      )
      .join("");

    // Timeline
    const timeline = o.timeline || [];
    const timelineBox = document.getElementById("modal-timeline-box");
    if (timeline.length === 0) {
      timelineBox.innerHTML = `<div class="muted">Chưa có thông tin dòng thời gian.</div>`;
    } else {
      timelineBox.innerHTML = timeline
        .map((step, idx) => {
          let stepClass = "";
          let nodeIcon = idx + 1;
          if (step.status_code === "CANCELLED") {
            stepClass = "cancelled";
            nodeIcon = "✕";
          } else if (step.is_current) {
            stepClass = "current";
            nodeIcon = "●";
          } else if (step.is_completed) {
            stepClass = "completed";
            nodeIcon = "✓";
          }

          const timeText = step.timestamp ? new Date(step.timestamp).toLocaleString("vi-VN") : "";

          return `
            <div class="timeline-step ${stepClass}">
              <div class="timeline-node">${nodeIcon}</div>
              <div class="timeline-content">
                <strong>${escapeHtml(step.title)}</strong>
                <p>${escapeHtml(step.description)}</p>
                ${timeText ? `<div class="time">🕒 ${escapeHtml(timeText)}</div>` : ""}
              </div>
            </div>`;
        })
        .join("");
    }

    orderDetailModal.style.display = "flex";
  } catch (error) {
    showToast(error.message, "error");
  }
}

// Bắt sự kiện
if (statusTabsContainer) {
  statusTabsContainer.addEventListener("click", (e) => {
    const btn = e.target.closest(".status-tab-btn");
    if (!btn) return;
    document.querySelectorAll(".status-tab-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    currentStatusFilter = btn.dataset.status || "";
    loadOrders();
  });
}

if (ordersListContainer) {
  ordersListContainer.addEventListener("click", async (e) => {
    const cancelBtn = e.target.closest("button[data-cancel-order]");
    if (cancelBtn) {
      const orderId = Number(cancelBtn.dataset.cancelOrder);
      await handleCancelOrder(orderId);
      return;
    }

    const detailBtn = e.target.closest("button[data-view-detail]");
    if (detailBtn) {
      const orderId = Number(detailBtn.dataset.viewDetail);
      await handleViewDetail(orderId);
      return;
    }
  });
}

if (btnCloseModal) {
  btnCloseModal.addEventListener("click", () => {
    orderDetailModal.style.display = "none";
  });
}

if (orderDetailModal) {
  orderDetailModal.addEventListener("click", (e) => {
    if (e.target === orderDetailModal) {
      orderDetailModal.style.display = "none";
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  loadOrders();
});
