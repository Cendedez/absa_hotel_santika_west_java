/**
 * Mockup Dashboard ABSA — Grayscale Prototype JavaScript
 * ======================================================
 * Navigation, dummy chart rendering (Chart.js with gray palette),
 * and placeholder data for all 8 pages.
 */

// ========================================
// CHART.JS CONFIG (Grayscale)
// ========================================
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.color = '#6b7280';
Chart.defaults.borderColor = '#e5e7eb';
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.pointStyleWidth = 10;
Chart.defaults.plugins.legend.labels.padding = 14;

const GRAY = {
  g900: '#111827', g800: '#1f2937', g700: '#374151', g600: '#4b5563',
  g500: '#6b7280', g400: '#9ca3af', g300: '#d1d5db', g200: '#e5e7eb',
  g100: '#f3f4f6', g50: '#f9fafb',
};

const ASPECTS = ['Lokasi', 'Kenyamanan', 'Pelayanan', 'Kebersihan', 'Harga', 'Makanan', 'Fasilitas'];
const ASPECT_GRAYS = [GRAY.g800, GRAY.g700, GRAY.g600, GRAY.g500, GRAY.g400, GRAY.g300, '#b0b0b0'];
const SENTIMENT_GRAYS = { positif: GRAY.g700, negatif: GRAY.g400, netral: GRAY.g200 };

const charts = {};

function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

// ========================================
// NAVIGATION
// ========================================
const PAGE_TITLES = {
  'overview': ['Overview', 'Ringkasan analisis sentimen ulasan Hotel Santika Jawa Barat'],
  'aspect': ['Analisis Aspek', 'Distribusi sentimen untuk setiap aspek layanan'],
  'hotel-platform': ['Hotel & Platform', 'Perbandingan sentimen antar hotel dan platform OTA'],
  'trend': ['Tren Waktu', 'Perubahan sentimen dari waktu ke waktu'],
  'reviews': ['Review Explorer', 'Jelajahi dan cari review secara detail'],
  'predict': ['Prediksi Sentimen', 'Analisis sentimen review baru menggunakan IndoBERT'],
  'performance': ['Performa Model', 'Metrik evaluasi model IndoBERT fine-tune'],
  'about': ['Tentang Sistem', 'Informasi tentang sistem dashboard ABSA'],
};

document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => navigateTo(item.dataset.page));
});

function navigateTo(page) {
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const navEl = document.querySelector(`[data-page="${page}"]`);
  if (navEl) navEl.classList.add('active');

  document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
  const pageEl = document.getElementById(`page-${page}`);
  if (pageEl) pageEl.classList.add('active');

  const [title, subtitle] = PAGE_TITLES[page] || ['', ''];
  document.getElementById('page-title').textContent = title;
  document.getElementById('page-subtitle').textContent = subtitle;

  switch (page) {
    case 'overview': renderOverview(); break;
    case 'aspect': renderAspect(); break;
    case 'hotel-platform': renderHotelPlatform(); break;
    case 'trend': renderTrend(); break;
    case 'performance': renderPerformance(); break;
  }

  document.getElementById('sidebar')?.classList.remove('open');
}

// ========================================
// OVERVIEW
// ========================================
function renderOverview() {
  // Gauge chart
  destroyChart('gauge');
  const gaugeCtx = document.getElementById('chart-gauge');
  if (gaugeCtx) {
    charts['gauge'] = new Chart(gaugeCtx, {
      type: 'doughnut',
      data: {
        datasets: [{
          data: [0.76, 0.24],
          backgroundColor: [GRAY.g600, GRAY.g200],
          borderWidth: 0,
          circumference: 180,
          rotation: 270,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '72%',
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
      }
    });
  }

  // Composition donut
  destroyChart('comp');
  const compCtx = document.getElementById('chart-comp');
  if (compCtx) {
    charts['comp'] = new Chart(compCtx, {
      type: 'doughnut',
      data: {
        labels: ['Positif', 'Negatif', 'Netral'],
        datasets: [{
          data: [62.4, 18.3, 19.3],
          backgroundColor: [GRAY.g700, GRAY.g400, GRAY.g200],
          borderWidth: 0,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '64%',
        plugins: { legend: { display: false } },
      }
    });
  }

  // Sentiment distribution bar
  destroyChart('sentDist');
  const sentCtx = document.getElementById('chart-sent-dist');
  if (sentCtx) {
    charts['sentDist'] = new Chart(sentCtx, {
      type: 'bar',
      data: {
        labels: ASPECTS,
        datasets: [
          { label: 'Positif', data: [2100, 3400, 4200, 3800, 1900, 2600, 2800], backgroundColor: GRAY.g700 },
          { label: 'Negatif', data: [420, 1100, 680, 780, 540, 920, 1050], backgroundColor: GRAY.g400 },
          { label: 'Netral', data: [580, 900, 720, 650, 460, 680, 740], backgroundColor: GRAY.g200 },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top' } },
        scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } }
      }
    });
  }

  // Negative aspects bar
  destroyChart('negAspects');
  const negCtx = document.getElementById('chart-neg-aspects');
  if (negCtx) {
    charts['negAspects'] = new Chart(negCtx, {
      type: 'bar',
      data: {
        labels: ['Kenyamanan', 'Fasilitas', 'Makanan', 'Kebersihan', 'Pelayanan', 'Harga', 'Lokasi'],
        datasets: [{
          label: 'Jumlah Negatif',
          data: [1100, 1050, 920, 780, 680, 540, 420],
          backgroundColor: GRAY.g500,
          borderRadius: 4,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true } }
      }
    });
  }

  // Price vs Quality
  destroyChart('priceQuality');
  const pqCtx = document.getElementById('chart-price-quality');
  if (pqCtx) {
    const hotels = ['Bandung', 'Bogor', 'Cirebon', 'Depok', 'Bekasi', 'Tasikmalaya'];
    charts['priceQuality'] = new Chart(pqCtx, {
      type: 'bar',
      data: {
        labels: hotels,
        datasets: [
          { label: 'Harga (% Negatif)', data: [12, 18, 8, 22, 15, 10], backgroundColor: GRAY.g600, borderRadius: 3 },
          { label: 'Pelayanan (% Negatif)', data: [8, 14, 6, 16, 12, 7], backgroundColor: GRAY.g400, borderRadius: 3 },
          { label: 'Fasilitas (% Negatif)', data: [14, 20, 10, 24, 18, 12], backgroundColor: GRAY.g200, borderRadius: 3 },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top' } },
        scales: { y: { beginAtZero: true, title: { display: true, text: '% Sentimen Negatif' } } }
      }
    });
  }
}

// ========================================
// ANALISIS ASPEK
// ========================================
function renderAspect() {
  destroyChart('aspectDetail');
  const ctx1 = document.getElementById('chart-aspect-detail');
  if (ctx1) {
    charts['aspectDetail'] = new Chart(ctx1, {
      type: 'bar',
      data: {
        labels: ASPECTS,
        datasets: [
          { label: 'Positif', data: [2100, 3400, 4200, 3800, 1900, 2600, 2800], backgroundColor: GRAY.g700 },
          { label: 'Negatif', data: [420, 1100, 680, 780, 540, 920, 1050], backgroundColor: GRAY.g400 },
          { label: 'Netral', data: [580, 900, 720, 650, 460, 680, 740], backgroundColor: GRAY.g200 },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top' } },
        scales: { y: { beginAtZero: true } }
      }
    });
  }

  destroyChart('aspectRatio');
  const ctx2 = document.getElementById('chart-aspect-ratio');
  if (ctx2) {
    charts['aspectRatio'] = new Chart(ctx2, {
      type: 'bar',
      data: {
        labels: ASPECTS,
        datasets: [
          { label: 'Positif %', data: [67.7, 63.0, 75.0, 72.7, 65.5, 61.9, 61.0], backgroundColor: GRAY.g700 },
          { label: 'Negatif %', data: [13.5, 20.4, 12.1, 14.9, 18.6, 21.9, 22.9], backgroundColor: GRAY.g400 },
          { label: 'Netral %', data: [18.7, 16.7, 12.9, 12.4, 15.9, 16.2, 16.1], backgroundColor: GRAY.g200 },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top' } },
        scales: { x: { stacked: true }, y: { stacked: true, max: 100, title: { display: true, text: '%' } } }
      }
    });
  }
}

// ========================================
// HOTEL & PLATFORM
// ========================================
function renderHotelPlatform() {
  const hotels = ['Bandung', 'Bogor', 'Cirebon', 'Depok', 'Bekasi', 'Tasikmalaya'];

  destroyChart('hotelCompare');
  const ctx1 = document.getElementById('chart-hotel-compare');
  if (ctx1) {
    charts['hotelCompare'] = new Chart(ctx1, {
      type: 'bar',
      data: {
        labels: hotels,
        datasets: [
          { label: 'Positif', data: [4800, 3200, 3600, 2800, 2400, 2200], backgroundColor: GRAY.g700, borderRadius: 3 },
          { label: 'Negatif', data: [980, 860, 640, 720, 580, 440], backgroundColor: GRAY.g400, borderRadius: 3 },
          { label: 'Netral', data: [720, 640, 560, 480, 420, 380], backgroundColor: GRAY.g200, borderRadius: 3 },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top' } },
        scales: { y: { beginAtZero: true } }
      }
    });
  }

  destroyChart('platformCompare');
  const ctx2 = document.getElementById('chart-platform-compare');
  if (ctx2) {
    charts['platformCompare'] = new Chart(ctx2, {
      type: 'bar',
      data: {
        labels: ['Traveloka', 'Agoda', 'Tiket.com'],
        datasets: [
          { label: 'Positif', data: [8400, 5200, 2100], backgroundColor: GRAY.g700, borderRadius: 3 },
          { label: 'Negatif', data: [1800, 1600, 820], backgroundColor: GRAY.g400, borderRadius: 3 },
          { label: 'Netral', data: [1400, 1100, 700], backgroundColor: GRAY.g200, borderRadius: 3 },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top' } },
        scales: { y: { beginAtZero: true } }
      }
    });
  }
}

// ========================================
// TREN WAKTU
// ========================================
function renderTrend() {
  destroyChart('trend');
  const ctx = document.getElementById('chart-trend');
  if (ctx) {
    const years = ['2020', '2021', '2022', '2023', '2024', '2025', '2026'];
    charts['trend'] = new Chart(ctx, {
      type: 'line',
      data: {
        labels: years,
        datasets: [
          {
            label: 'Positif',
            data: [1200, 800, 1400, 2800, 3600, 4200, 2100],
            borderColor: GRAY.g700, backgroundColor: GRAY.g700 + '20',
            fill: true, tension: .3, pointRadius: 4, borderWidth: 2,
          },
          {
            label: 'Negatif',
            data: [320, 200, 380, 720, 940, 1100, 560],
            borderColor: GRAY.g400, backgroundColor: GRAY.g400 + '20',
            fill: true, tension: .3, pointRadius: 4, borderWidth: 2,
          },
          {
            label: 'Netral',
            data: [240, 160, 300, 560, 680, 820, 440],
            borderColor: GRAY.g300, backgroundColor: GRAY.g300 + '20',
            fill: true, tension: .3, pointRadius: 4, borderWidth: 2,
          },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top' } },
        scales: { y: { beginAtZero: true } }
      }
    });
  }
}

// ========================================
// PERFORMA MODEL
// ========================================
function renderPerformance() {
  destroyChart('perfAspect');
  const ctx = document.getElementById('chart-perf-aspect');
  if (ctx) {
    charts['perfAspect'] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ASPECTS,
        datasets: [
          { label: 'F1 Score', data: [0.82, 0.78, 0.85, 0.81, 0.76, 0.74, 0.77], backgroundColor: GRAY.g600, borderRadius: 3 },
          { label: 'Accuracy', data: [0.88, 0.84, 0.90, 0.87, 0.83, 0.80, 0.82], backgroundColor: GRAY.g300, borderRadius: 3 },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top' } },
        scales: { y: { beginAtZero: true, max: 1.0, ticks: { callback: v => (v*100).toFixed(0)+'%' } } }
      }
    });
  }
}

// ========================================
// PREDICT DEMO
// ========================================
function demoPredict() {
  const input = document.getElementById('predict-input');
  const results = document.getElementById('predict-results');
  const text = input?.value?.trim();

  if (!text) {
    results.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠</div>Masukkan teks review terlebih dahulu.</div>';
    return;
  }

  const demoResults = ASPECTS.map(a => {
    const labels = ['positif', 'negatif', 'netral', 'none'];
    const pick = labels[Math.floor(Math.random() * 3)]; // bias toward non-none
    const conf = (0.5 + Math.random() * 0.45).toFixed(4);
    return { aspect: a, prediction: pick, confidence: conf };
  });

  results.innerHTML = demoResults.map(r => `
    <div class="predict-result">
      <div>
        <span class="predict-aspect">${r.aspect}</span>
        <span class="predict-conf">${(r.confidence * 100).toFixed(1)}%</span>
      </div>
      <span class="predict-label">${r.prediction.charAt(0).toUpperCase() + r.prediction.slice(1)}</span>
    </div>
  `).join('');
}

// ========================================
// LOGIN DEMO
// ========================================
function demoLogin(e) {
  e.preventDefault();
  document.getElementById('login-page').style.display = 'none';
  document.getElementById('dashboard-page').style.display = 'flex';
  navigateTo('overview');
}

function demoLogout() {
  document.getElementById('dashboard-page').style.display = 'none';
  document.getElementById('login-page').style.display = 'flex';
}

// ========================================
// INIT
// ========================================
document.addEventListener('DOMContentLoaded', () => {
  // Start on login
  document.getElementById('login-page').style.display = 'flex';
  document.getElementById('dashboard-page').style.display = 'none';
});
