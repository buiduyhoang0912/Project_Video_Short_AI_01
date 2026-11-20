// Dashboard Admin (T3D201D): số liệu tổng quan + biểu đồ theo ngày bằng Chart.js.

const dashCharts = {};
let selectedDays = 30;

function drawChart(canvasId, config) {
  if (dashCharts[canvasId]) dashCharts[canvasId].destroy();
  const canvas = $(canvasId);
  if (!canvas) return;
  dashCharts[canvasId] = new Chart(canvas, config);
}

function renderStats(s) {
  const items = [
    { label: "👥 Người dùng", val: s.total_users },
    { label: "🏪 Người bán (SELLER)", val: s.total_sellers },
    { label: "🎬 Tổng Video", val: s.total_videos },
    { label: "🛍️ Tổng Sản phẩm", val: s.total_products },
    { label: "📦 Tổng Đơn hàng", val: s.total_orders },
    { label: "💰 Doanh thu toàn sàn", val: formatMoney(s.total_revenue), highlight: true },
  ];
  $("dash-stats").innerHTML = items
    .map(
      (item) => `<div class="stat-card ${item.highlight ? 'stat-card-highlight' : ''}">
        <div class="stat-label">${escapeHtml(item.label)}</div>
        <div class="stat-value">${escapeHtml(String(item.val))}</div>
      </div>`
    )
    .join("");
}

async function loadDashboard() {
  if (typeof Chart === "undefined") {
    showToast("Không tải được thư viện Chart.js. Vui lòng kiểm tra kết nối mạng.", "error");
    return;
  }
  try {
    const fromDate = $("dash-from-date").value;
    const toDate = $("dash-to-date").value;
    const params = {};

    if (fromDate && toDate) {
      if (fromDate > toDate) {
        showToast("Ngày bắt đầu không được lớn hơn ngày kết thúc", "error");
        return;
      }
      params.from_date = fromDate;
      params.to_date = toDate;
    } else {
      params.days = selectedDays;
    }

    const res = await api.get("/admin/dashboard", params);
    renderStats(res.summary);

    if (res.from_date && res.to_date) {
      $("dash-from-date").value = res.from_date;
      $("dash-to-date").value = res.to_date;
    }

    const labels = res.daily.map((p) => {
      // Format YYYY-MM-DD to DD/MM
      const parts = p.date.split("-");
      return `${parts[2]}/${parts[1]}`;
    });

    // 1. Biểu đồ doanh thu toàn sàn theo ngày (₫)
    drawChart("chart-revenue", {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Doanh thu (₫)",
          data: res.daily.map((p) => Number(p.revenue)),
          borderColor: "#fe2c55",
          backgroundColor: "rgba(254, 44, 85, 0.15)",
          fill: true,
          tension: 0.25,
          pointRadius: res.daily.length > 40 ? 0 : 3,
        }],
      },
      options: {
        responsive: true,
        plugins: {
          tooltip: {
            callbacks: {
              label: (ctx) => ` Doanh thu: ${Number(ctx.raw).toLocaleString("vi-VN")} ₫`,
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (v) => `${(v / 1000).toLocaleString("vi-VN")}k ₫`,
            },
          },
        },
      },
    });

    // 2. Biểu đồ số lượng đơn hàng theo ngày
    drawChart("chart-orders", {
      type: "bar",
      data: {
        labels,
        datasets: [{
          label: "Số đơn hàng",
          data: res.daily.map((p) => p.orders),
          backgroundColor: "#4a6cf7",
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        scales: {
          y: {
            beginAtZero: true,
            ticks: { precision: 0 },
          },
        },
      },
    });

    // 3. Biểu đồ người dùng & video mới theo ngày
    drawChart("chart-growth", {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Người dùng mới",
            data: res.daily.map((p) => p.new_users),
            borderColor: "#1c9b5a",
            backgroundColor: "transparent",
            tension: 0.25,
          },
          {
            label: "Video mới",
            data: res.daily.map((p) => p.new_videos),
            borderColor: "#e08a00",
            backgroundColor: "transparent",
            tension: 0.25,
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          y: {
            beginAtZero: true,
            ticks: { precision: 0 },
          },
        },
      },
    });
  } catch (err) {
    showToast(err.message || "Không thể tải dữ liệu dashboard", "error");
  }
}

adminTabLoaders.dashboard = loadDashboard;

document.addEventListener("DOMContentLoaded", () => {
  // Bộ chọn khoảng ngày
  $("dash-apply-range").addEventListener("click", () => {
    document.querySelectorAll(".quick-preset-picker button").forEach((b) => b.classList.remove("btn-primary"));
    loadDashboard();
  });

  // Nút chọn nhanh (7, 14, 30, 90 ngày)
  document.querySelectorAll(".quick-preset-picker button").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".quick-preset-picker button").forEach((b) => b.classList.remove("btn-primary"));
      btn.classList.add("btn-primary");
      selectedDays = Number(btn.dataset.days);
      $("dash-from-date").value = "";
      $("dash-to-date").value = "";
      loadDashboard();
    });
  });

  $("dash-refresh").addEventListener("click", loadDashboard);
});
