/**
 * Dashboard ABSA Hotel Santika — Frontend JavaScript
 * ===================================================
 * Single-page app: navigasi, API calls, chart rendering.
 */

// ========================================
// CHART.JS DEFAULT CONFIG
// ========================================
Chart.defaults.font.family = 'Segoe UI, sans-serif';
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.pointStyleWidth = 12;
Chart.defaults.plugins.legend.labels.padding = 16;

let COLORS = {};

const FALLBACK_COLORS = {
    positif: '#3fb950',
    negatif: '#f85149',
    netral: '#d29922',
    none: '#6e7681',
    grid: '#21262d',
    muted: '#6e7681',
    textPrimary: '#e6edf3',
    textSecondary: '#8b949e',
    blue: '#58a6ff',
    purple: '#a78bfa',
};

const SENTIMENT_META = {
    positif: { label: 'Positif' },
    negatif: { label: 'Negatif' },
    netral: { label: 'Netral' },
    none: { label: 'Tidak terdeteksi' },
};

const ASPECT_COLORS = [
    '#58a6ff', '#bc8cff', '#3fb950', '#f85149',
    '#d29922', '#39d2c0', '#f778ba'
];

const ASPECTS = ['Lokasi', 'Kenyamanan', 'Pelayanan', 'Kebersihan', 'Harga', 'Makanan', 'Fasilitas'];

// Track active charts for cleanup
const charts = {};
const appState = {
    dateRange: { min: '', max: '' },
    overviewRange: 'all',
    priorityRows: [],
    priorityPage: 1,
    priorityPerPage: 5,
    reviewPerPage: 10,
    reviewPage: 1,
    overviewDateRange: { min: '', max: '' },
};
const CURRENT_USER = window.ABSA_USER || {};
const IS_ADMIN = CURRENT_USER.role === 'admin';
const CAN_MANAGE_REVIEWS = ['admin', 'staff_ota'].includes(CURRENT_USER.role);
const CAN_VIEW_ACTIVITY_LOG = IS_ADMIN;
const STAFF_ALLOWED_PAGES = new Set(['reviews', 'predict', 'performance', 'about']);
document.title = 'Customer Sentiment Dashboard - Hotel Santika Jawa Barat';

function cssVar(name, fallback = '') {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
}

function refreshThemeColors() {
    COLORS = {
        positif: cssVar('--color-positif', FALLBACK_COLORS.positif),
        negatif: cssVar('--color-negatif', FALLBACK_COLORS.negatif),
        netral: cssVar('--color-netral', FALLBACK_COLORS.netral),
        none: cssVar('--color-none', FALLBACK_COLORS.none),
        grid: cssVar('--chart-grid', FALLBACK_COLORS.grid),
        muted: cssVar('--chart-muted', FALLBACK_COLORS.muted),
        textPrimary: cssVar('--text-primary', FALLBACK_COLORS.textPrimary),
        textSecondary: cssVar('--text-secondary', FALLBACK_COLORS.textSecondary),
        blue: cssVar('--accent-blue', FALLBACK_COLORS.blue),
        purple: cssVar('--accent-purple', FALLBACK_COLORS.purple),
    };

    Chart.defaults.color = COLORS.textSecondary;
    Chart.defaults.borderColor = COLORS.grid;
}

function applyTheme(theme, persist = true) {
    const nextTheme = theme === 'light' ? 'light' : 'dark';
    document.documentElement.dataset.theme = nextTheme;
    if (persist) {
        localStorage.setItem('absa-dashboard-theme', nextTheme);
    }
    refreshThemeColors();

    const icon = document.getElementById('theme-toggle-icon');
    const text = document.getElementById('theme-toggle-text');
    if (icon) icon.textContent = nextTheme === 'light' ? '☀️' : '🌙';
    if (text) text.textContent = nextTheme === 'light' ? 'Mode Terang' : 'Mode Gelap';
}

function reloadActivePage() {
    const activePage = document.querySelector('.nav-item.active')?.dataset.page || 'overview';
    switch (activePage) {
        case 'overview': loadOverview(); break;
        case 'aspect': loadAspectAnalysis(); break;
        case 'hotel-platform': loadHotelPlatform(); break;
        case 'trend': loadTrend(); break;
        case 'reviews': loadReviews(1); break;
        case 'performance': loadPerformance(); break;
        case 'staff': loadStaffManagement(); break;
    }
}

refreshThemeColors();

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
    'staff': ['Manajemen Staf OTA', 'Tambah, lihat, dan hapus akun Staf OTA'],
    'about': ['Tentang Sistem', 'Informasi tentang sistem dashboard ABSA'],
};

function checkAuth() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.hidden = !canAccessPage(item.dataset.page);
    });
}

function canAccessPage(page) {
    return IS_ADMIN || STAFF_ALLOWED_PAGES.has(page);
}

function getDefaultPage() {
    return IS_ADMIN ? 'overview' : 'reviews';
}

document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
        const page = item.dataset.page;
        navigateTo(page);
    });
});

function navigateTo(page) {
    if (!canAccessPage(page) || !document.getElementById(`page-${page}`)) {
        page = getDefaultPage();
    }

    // Update nav
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const navEl = document.querySelector(`[data-page="${page}"]`);
    if (navEl) navEl.classList.add('active');

    // Update pages
    document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
    const pageEl = document.getElementById(`page-${page}`);
    if (pageEl) pageEl.classList.add('active');

    // Update header
    const [title, subtitle] = PAGE_TITLES[page] || ['', ''];
    document.getElementById('page-title').textContent = title;
    document.getElementById('page-subtitle').textContent = subtitle;

    // Load data
    switch (page) {
        case 'overview': loadOverview(); break;
        case 'aspect': loadAspectAnalysis(); break;
        case 'hotel-platform': loadHotelPlatform(); break;
        case 'trend': loadTrend(); break;
        case 'reviews':
            loadReviews(1);
            if (CAN_VIEW_ACTIVITY_LOG) loadActivityLog();
            break;
        case 'performance': loadPerformance(); break;
        case 'staff': loadStaffManagement(); break;
    }

    // Close mobile sidebar
    document.getElementById('sidebar').classList.remove('open');
}

// ========================================
// UTILITY FUNCTIONS
// ========================================
async function fetchAPI(endpoint, params = {}) {
    const url = new URL(endpoint, window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
        if (v && v !== 'all') url.searchParams.set(k, v);
    });
    const res = await fetch(url);
    if (res.status === 401) {
        window.location.href = '/login';
        return { error: 'Autentikasi diperlukan' };
    }
    if (res.status === 403) {
        return { error: 'Akses tidak tersedia untuk role pengguna ini' };
    }
    return res.json();
}

function destroyChart(id) {
    if (charts[id]) {
        charts[id].destroy();
        delete charts[id];
    }
}

function createBadge(label) {
    const meta = SENTIMENT_META[label] || { label };
    return `<span class="badge badge-${label}">${meta.label}</span>`;
}

// Render satu kartu review (dipakai di Review Explorer & Contoh Review Analisis Aspek).
// Hanya menampilkan aspek yang punya sentimen (bukan 'none') agar ringkas.
function renderReviewCard(r, options = {}) {
    const sentClass = { positif: 'pos', negatif: 'neg', netral: 'net' };
    const sentText = { positif: 'Positif', negatif: 'Negatif', netral: 'Netral' };
    const hotel = (r.Nama_Hotel || '').replace('Hotel Santika ', '') || '-';
    const platform = platformLabel(r.Platform || '-');
    const date = r.Review_Date || '-';
    const id = r.ID_Review || '';
    const showActions = Boolean(id && CAN_MANAGE_REVIEWS && options.actions !== false && !options.onlyAspect);

    // Jika options.onlyAspect diberikan, tonjolkan aspek itu; selain itu tampilkan semua aspek bersentimen.
    const aspectsToShow = options.onlyAspect ? [options.onlyAspect] : ASPECTS;
    const chips = aspectsToShow.map(a => {
        const s = r[`pred_${a}`];
        if (!s || s === 'none') return '';
        return `<span class="review-aspect-chip ${sentClass[s] || ''}">
                    <span class="chip-aspect">${escapeHtml(a)}</span>
                    <span class="chip-sentiment">${sentText[s] || escapeHtml(s)}</span>
                </span>`;
    }).filter(Boolean).join('');

    const chipsBlock = chips
        ? `<div class="review-item-aspects">${chips}</div>`
        : `<div class="review-item-aspects"><span class="review-aspect-chip"><span class="chip-aspect">Tidak ada aspek terdeteksi</span></span></div>`;

    return `
        <div class="review-item">
            <div class="review-item-head">
                <span class="review-item-hotel">${escapeHtml(hotel)}</span>
                <span class="review-item-meta">${escapeHtml(platform)}</span>
                <span class="review-item-meta">${escapeHtml(date)}</span>
                ${id ? `<span class="review-item-meta">ID ${escapeHtml(id)}</span>` : ''}
                ${showActions ? `<button class="btn btn-danger btn-sm review-delete-btn" type="button" data-review-id="${escapeHtml(id)}" onclick="deleteReview(this.dataset.reviewId)">Hapus</button>` : ''}
            </div>
            <div class="review-item-text">${escapeHtml(r.Text_Review || '')}</div>
            ${chipsBlock}
        </div>`;
}

function sentimentLabel(key, withPercent = false) {
    const meta = SENTIMENT_META[key] || { label: key };
    return `${meta.label}${withPercent ? ' %' : ''}`;
}

function iconSvg(name) {
    return `<svg class="icon-svg" aria-hidden="true"><use href="#icon-${name}"></use></svg>`;
}

function pct(value) {
    return Number.isFinite(value) ? `${value.toFixed(1)}%` : '0.0%';
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function platformLabel(platform) {
    if (platform === 'Manual') return 'Lainnya';
    if (platform === 'Tiket') return 'Tiket.com';
    return platform || '-';
}

function formatMetric(value) {
    const num = Number(value || 0);
    return `${(num * 100).toFixed(1)}%`;
}

function toDateInputValue(date) {
    return date.toISOString().slice(0, 10);
}

function addDays(date, days) {
    const next = new Date(date);
    next.setDate(next.getDate() + days);
    return next;
}

function addMonths(date, months) {
    const next = new Date(date);
    next.setMonth(next.getMonth() + months);
    return next;
}

function getOverviewDateParams(rangeKey = appState.overviewRange, dateRange = appState.overviewDateRange) {
    const effectiveRange = dateRange?.max ? dateRange : appState.dateRange;
    const maxDateText = effectiveRange.max;
    if (!maxDateText || rangeKey === 'all') {
        return { params: {}, label: 'Seluruh rentang data', dateRange: effectiveRange };
    }

    const maxDate = new Date(`${maxDateText}T00:00:00`);
    let startDate = null;
    let endDate = maxDate;
    let label = 'Seluruh rentang data';

    if (rangeKey === '1d') {
        startDate = maxDate;
        label = '1 hari terakhir pada filter ini';
    } else if (rangeKey === '7d') {
        startDate = addDays(maxDate, -6);
        label = '7 hari terakhir pada filter ini';
    } else if (rangeKey === '30d') {
        startDate = addDays(maxDate, -29);
        label = '30 hari terakhir pada filter ini';
    } else if (rangeKey === '3m') {
        startDate = addMonths(maxDate, -3);
        label = '3 bulan terakhir pada filter ini';
    } else if (rangeKey === '6m') {
        startDate = addMonths(maxDate, -6);
        label = '6 bulan terakhir pada filter ini';
    } else if (rangeKey === '1y') {
        startDate = addMonths(maxDate, -12);
        label = '1 tahun terakhir pada filter ini';
    } else if (/^\d{4}$/.test(rangeKey)) {
        startDate = new Date(`${rangeKey}-01-01T00:00:00`);
        endDate = new Date(`${rangeKey}-12-31T00:00:00`);
        label = `Tahun ${rangeKey}`;
    }

    const params = {};
    if (startDate) params.date_from = toDateInputValue(startDate);
    if (endDate) params.date_to = toDateInputValue(endDate);
    return { params, label, dateRange: effectiveRange };
}

function getAspectRows(stats) {
    return ASPECTS.map(aspect => {
        const item = stats[aspect] || {};
        const positif = item.positif || 0;
        const negatif = item.negatif || 0;
        const netral = item.netral || 0;
        const total = item.total_with_sentiment || (positif + negatif + netral);
        return {
            aspect,
            positif,
            negatif,
            netral,
            total,
            positiveRate: total > 0 ? (positif / total) * 100 : 0,
            negativeRate: total > 0 ? (negatif / total) * 100 : 0,
        };
    }).filter(row => row.total > 0);
}

function renderOverviewInsight(data, posRate) {
    const insightEl = document.getElementById('overview-insight');
    if (!insightEl) return;

    if (data.total_reviews === 0) {
        insightEl.innerHTML = `
            <div class="insight-card" style="display: flex; flex-direction: column; justify-content: center;">
                <div class="insight-eyebrow">SEGERA DIPERBAIKI</div>
                <h2 style="color: var(--text-muted); margin-top: 8px;">Tidak cukup data.</h2>
                <p>Silakan ubah filter periode, hotel, atau platform untuk melihat wawasan keluhan terbesar pada data ulasan.</p>
            </div>
            <div class="insight-card" style="display: flex; flex-direction: column; justify-content: center;">
                <div class="insight-eyebrow">PRIORITAS PERBAIKAN</div>
                <div style="color: var(--text-muted); padding-top: 10px;">Belum ada data sentimen negatif.</div>
            </div>
            <div class="insight-card" style="display: flex; flex-direction: column; justify-content: center;">
                <div class="insight-eyebrow">RISIKO TERTINGGI</div>
                <div style="color: var(--text-muted); padding-top: 10px;">Belum ada risiko terdeteksi.</div>
            </div>
            <div class="insight-card" style="display: flex; flex-direction: column; justify-content: center;">
                <div class="insight-eyebrow">KEKUATAN UTAMA</div>
                <div style="color: var(--text-muted); padding-top: 10px;">Belum ada data sentimen positif.</div>
            </div>
        `;
        return;
    }

    const rows = getAspectRows(data.aspect_stats || {});
    const topNeg = [...rows].sort((a, b) => b.negatif - a.negatif);
    const topRisk = [...rows].sort((a, b) => b.negativeRate - a.negativeRate);
    const topPos = [...rows].sort((a, b) => b.positif - a.positif);

    // Guard: tidak ada keluhan sama sekali
    const totalNegatif = topNeg.reduce((s, r) => s + r.negatif, 0);
    if (totalNegatif === 0) {
        const strength = topPos[0] || null;
        insightEl.innerHTML = `
            <div class="insight-card" style="grid-column: 1 / span 2;">
                <div class="insight-eyebrow" style="color: var(--accent-green);">TIDAK ADA KELUHAN</div>
                <h2 style="color: var(--accent-green); margin-top: 8px;">Tidak ditemukan keluhan pada filter ini.</h2>
                <p>Dari ${data.total_reviews.toLocaleString()} review dalam periode dan filter yang dipilih, tidak ada sentimen negatif yang terdeteksi. Semua ulasan tamu yang menyebutkan aspek layanan bernada positif atau netral.</p>
            </div>
            <div class="insight-card">
                <div class="insight-eyebrow">PRIORITAS PERBAIKAN</div>
                <div style="color: var(--text-secondary); padding-top: 10px; font-size: 13px;">
                    Tidak ada aspek dengan keluhan pada filter ini.
                </div>
            </div>
            ${strength ? `
            <div class="insight-card insight-clickable" onclick="drillDownToReviews({aspect: '${strength.aspect}', sentiment: 'positif'})" title="Klik untuk lihat review positif ${strength.aspect}">
                <div class="insight-eyebrow">KEKUATAN UTAMA</div>
                <div class="insight-metric success">${strength.aspect}</div>
                <p>${strength.positif.toLocaleString()} ulasan positif pada aspek ini dalam periode yang dipilih.</p>
                <div class="insight-drill-hint">Klik untuk lihat review &rarr;</div>
            </div>` : `
            <div class="insight-card">
                <div class="insight-eyebrow">KEKUATAN UTAMA</div>
                <div style="color: var(--text-secondary); padding-top: 10px; font-size: 13px;">Belum ada data sentimen positif.</div>
            </div>`}
        `;
        return;
    }

    const priority = topNeg.slice(0, 3);
    const mainNeg = topNeg[0] || { aspect: '-', negatif: 0, negativeRate: 0 };
    const secondNeg = topNeg[1] || { aspect: '-', negatif: 0, negativeRate: 0 };
    const risk = topRisk[0] || mainNeg;
    const strength = topPos[0] || { aspect: '-', positif: 0, positiveRate: 0 };

    insightEl.innerHTML = `
        <div class="insight-card insight-primary insight-clickable" onclick="drillDownToReviews({aspect: '${mainNeg.aspect}', sentiment: 'negatif'})" title="Klik untuk melihat review negatif aspek ${mainNeg.aspect}">
            <div class="insight-eyebrow insight-alert-label">SEGERA DIPERBAIKI</div>
            <h2>${mainNeg.aspect} dan ${secondNeg.aspect} adalah sumber keluhan terbesar.</h2>
            <p>
                Dari ${data.total_reviews.toLocaleString()} review, sentimen positif masih dominan (${posRate}%).
                Namun keluhan paling banyak terkonsentrasi pada aspek ${mainNeg.aspect.toLowerCase()}
                (${mainNeg.negatif.toLocaleString()} sentimen negatif) dan ${secondNeg.aspect.toLowerCase()}
                (${secondNeg.negatif.toLocaleString()} sentimen negatif).
            </p>
            <div class="insight-drill-hint">Klik untuk lihat review &rarr;</div>
        </div>
        <div class="insight-card">
            <div class="insight-eyebrow">Prioritas perbaikan</div>
            <div class="priority-list">
                ${priority.map((row, index) => `
                    <div class="priority-row insight-clickable" onclick="drillDownToReviews({aspect: '${row.aspect}', sentiment: 'negatif'})" title="Klik untuk lihat review negatif ${row.aspect}">
                        <div class="priority-rank">${index + 1}</div>
                        <div class="priority-content">
                            <div class="priority-title">${row.aspect}</div>
                            <div class="priority-meta">${row.negatif.toLocaleString()} negatif &middot; ${pct(row.negativeRate)} dari sentimen aspek</div>
                            <div class="priority-track"><div style="width:${Math.min(row.negativeRate, 100)}%"></div></div>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
        <div class="insight-card insight-clickable" onclick="drillDownToReviews({aspect: '${risk.aspect}', sentiment: 'negatif'})" title="Klik untuk lihat review negatif ${risk.aspect}">
            <div class="insight-eyebrow">Risiko tertinggi</div>
            <div class="insight-metric danger">${risk.aspect}</div>
            <p>${pct(risk.negativeRate)} sentimen pada aspek ini bernada negatif, sehingga perlu dicek bukan hanya dari jumlah keluhan tetapi juga proporsinya.</p>
            <div class="insight-drill-hint">Klik untuk lihat review &rarr;</div>
        </div>
        <div class="insight-card insight-clickable" onclick="drillDownToReviews({aspect: '${strength.aspect}', sentiment: 'positif'})" title="Klik untuk lihat review positif ${strength.aspect}">
            <div class="insight-eyebrow">Kekuatan utama</div>
            <div class="insight-metric success">${strength.aspect}</div>
            <p>${strength.positif.toLocaleString()} sentimen positif muncul pada aspek ini. Insight ini bisa dipakai sebagai kekuatan komunikasi layanan.</p>
            <div class="insight-drill-hint">Klik untuk lihat review &rarr;</div>
        </div>
    `;
}

function renderSentimentSummary(data) {
    const sc = data.sentiment_counts || { positif: 0, negatif: 0, netral: 0 };
    const pos = sc.positif || 0, neg = sc.negatif || 0, net = sc.netral || 0;
    const total = pos + neg + net;

    const posPct = total > 0 ? (pos / total) * 100 : 0;
    const negPct = total > 0 ? (neg / total) * 100 : 0;
    const netPct = total > 0 ? (net / total) * 100 : 0;

    // Skor 1-5: positif=5, netral=3, negatif=1 (rata-rata berbobot)
    const score = total > 0 ? ((pos * 5 + net * 3 + neg * 1) / total) : 0;
    let levelText = 'Netral', levelColor = COLORS.netral;
    if (total === 0) { levelText = 'Tidak ada data'; levelColor = COLORS.muted; }
    else if (score >= 3.8) { levelText = 'Positif'; levelColor = COLORS.positif; }
    else if (score >= 2.6) { levelText = 'Netral'; levelColor = COLORS.netral; }
    else { levelText = 'Negatif'; levelColor = COLORS.negatif; }

    // ---- Gauge (setengah donut) ----
    destroyChart('sentiment-gauge');
    const gaugeCtx = document.getElementById('chart-sentiment-gauge');
    if (gaugeCtx) {
        const frac = Math.max(0, Math.min(1, score / 5));
        charts['sentiment-gauge'] = new Chart(gaugeCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [frac, 1 - frac],
                    backgroundColor: [levelColor, COLORS.grid],
                    borderWidth: 0,
                    circumference: 180,
                    rotation: 270,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '72%',
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
            }
        });
    }
    const metaEl = document.getElementById('sentiment-level-meta');
    if (metaEl) {
        metaEl.innerHTML = `
            <div class="sentiment-score" style="color:${levelColor};">${score.toFixed(2)}</div>
            <div class="sentiment-score-sub">dari 5</div>
            <div class="sentiment-level-badge" style="color:${levelColor};border-color:${levelColor};">${levelText}</div>
            <div class="sentiment-level-note">${total.toLocaleString()} sentimen aspek dianalisis</div>
        `;
    }

    const legendBox = document.getElementById('sentiment-scale-legend');
    if (legendBox) {
        legendBox.innerHTML = `
            <div class="scale-legend-item${score < 2.6 && total > 0 ? ' active' : ''}">
                <span class="scale-dot" style="background:${COLORS.negatif};"></span>
                <span class="scale-range">1.0 &ndash; 2.5</span>
                <span class="scale-name">Negatif</span>
            </div>
            <div class="scale-legend-item${score >= 2.6 && score < 3.8 && total > 0 ? ' active' : ''}">
                <span class="scale-dot" style="background:${COLORS.netral};"></span>
                <span class="scale-range">2.6 &ndash; 3.7</span>
                <span class="scale-name">Netral</span>
            </div>
            <div class="scale-legend-item${score >= 3.8 && total > 0 ? ' active' : ''}">
                <span class="scale-dot" style="background:${COLORS.positif};"></span>
                <span class="scale-range">3.8 &ndash; 5.0</span>
                <span class="scale-name">Positif</span>
            </div>
        `;
    }

    // ---- Donut komposisi ----
    destroyChart('sentiment-comp');
    const compCtx = document.getElementById('chart-sentiment-comp');
    if (compCtx) {
        charts['sentiment-comp'] = new Chart(compCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Positif', 'Negatif', 'Netral'],
                datasets: [{
                    data: [pos, neg, net],
                    backgroundColor: [COLORS.positif, COLORS.negatif, COLORS.netral],
                    borderWidth: 0,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '64%',
                plugins: { legend: { display: false }, tooltip: { enabled: true } },
            }
        });
    }
    const legendEl = document.getElementById('sentiment-comp-legend');
    if (legendEl) {
        legendEl.innerHTML = `
            <div class="comp-legend-item">
                <span class="comp-dot" style="background:${COLORS.positif};"></span>
                <span class="comp-pct" style="color:${COLORS.positif};">${posPct.toFixed(1)}%</span>
                <span class="comp-label">Positif</span>
            </div>
            <div class="comp-legend-item">
                <span class="comp-dot" style="background:${COLORS.negatif};"></span>
                <span class="comp-pct" style="color:${COLORS.negatif};">${negPct.toFixed(1)}%</span>
                <span class="comp-label">Negatif</span>
            </div>
            <div class="comp-legend-item">
                <span class="comp-dot" style="background:${COLORS.netral};"></span>
                <span class="comp-pct" style="color:${COLORS.netral};">${netPct.toFixed(1)}%</span>
                <span class="comp-label">Netral</span>
            </div>
        `;
    }
}

function renderPriorityImprovements(rows = null) {
    const wrapper = document.getElementById('priority-table-wrapper');
    if (!wrapper) return;
    if (Array.isArray(rows)) {
        appState.priorityRows = rows;
        appState.priorityPage = 1;
    }

    const allRows = appState.priorityRows || [];
    const totalRows = allRows.length;
    const totalPages = Math.max(1, Math.ceil(totalRows / appState.priorityPerPage));
    appState.priorityPage = Math.min(Math.max(appState.priorityPage, 1), totalPages);

    if (!totalRows) {
        wrapper.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-text">Tidak ada prioritas perbaikan pada filter periode ini.</div>
            </div>
        `;
        return;
    }

    const start = (appState.priorityPage - 1) * appState.priorityPerPage;
    const pageRows = allRows.slice(start, start + appState.priorityPerPage);
    const body = pageRows.map((row, index) => {
        const review = row.supporting_review || {};
        const negativeRate = Number(row.negative_rate || 0);
        const globalIndex = start + index + 1;
        const drillHotel = escapeHtml(row.hotel || '').replace(/'/g, "\\'");
        const drillAspect = escapeHtml(row.aspect || '').replace(/'/g, "\\'");
        return `
            <tr class="priority-row-clickable" onclick="drillDownToReviews({hotel: '${drillHotel}', aspect: '${drillAspect}', sentiment: 'negatif'})" title="Klik untuk lihat review negatif ${escapeHtml(row.aspect)} di ${escapeHtml(row.hotel_short)}">
                <td><span class="priority-rank-cell">${globalIndex}</span></td>
                <td>
                    <strong>${escapeHtml(row.hotel_short || row.hotel || '-')}</strong>
                    <div class="table-muted">${escapeHtml(row.hotel || '')}</div>
                </td>
                <td><span class="aspect-pill">${escapeHtml(row.aspect || '-')}</span></td>
                <td>
                    <strong>${Number(row.negative_count || 0).toLocaleString()}</strong>
                    <div class="table-muted">dari ${Number(row.total_aspect_sentiment || 0).toLocaleString()} sentimen aspek</div>
                </td>
                <td>
                    <div class="priority-rate">
                        <span>${negativeRate.toFixed(1)}%</span>
                        <div class="priority-rate-track">
                            <div style="width:${Math.min(Math.max(negativeRate, 0), 100)}%"></div>
                        </div>
                    </div>
                </td>
                <td>
                    <strong>${escapeHtml(row.dominant_platform || '-')}</strong>
                    <div class="table-muted">${Number(row.dominant_platform_count || 0).toLocaleString()} keluhan</div>
                </td>
                <td class="priority-review-cell">
                    <div class="table-muted">${escapeHtml(review.date || '-')} &middot; ${escapeHtml(review.platform || row.dominant_platform || '-')}</div>
                    <div class="priority-review-text">${escapeHtml(review.text || 'Tidak ada contoh review.')}</div>
                </td>
            </tr>
        `;
    }).join('');

    wrapper.innerHTML = `
        <div class="priority-table-toolbar">
            <div class="priority-table-info">
                Menampilkan ${start + 1}-${Math.min(start + appState.priorityPerPage, totalRows)} dari ${totalRows} prioritas
            </div>
            <div class="priority-table-controls">
                <span>Jumlah prioritas per halaman</span>
                <button class="priority-size-btn ${appState.priorityPerPage === 5 ? 'active' : ''}" onclick="setPriorityPerPage(5)">5</button>
                <button class="priority-size-btn ${appState.priorityPerPage === 10 ? 'active' : ''}" onclick="setPriorityPerPage(10)">10</button>
                <button class="priority-size-btn ${appState.priorityPerPage === 20 ? 'active' : ''}" onclick="setPriorityPerPage(20)">20</button>
                <button class="priority-page-btn" ${appState.priorityPage <= 1 ? 'disabled' : ''} onclick="changePriorityPage(-1)" aria-label="Halaman sebelumnya">&lsaquo;</button>
                <button class="priority-page-btn" ${appState.priorityPage >= totalPages ? 'disabled' : ''} onclick="changePriorityPage(1)" aria-label="Halaman berikutnya">&rsaquo;</button>
            </div>
        </div>
        <table class="data-table priority-table">
            <thead>
                <tr>
                    <th>No.</th>
                    <th>Hotel</th>
                    <th>Aspek</th>
                    <th>Jumlah Negatif</th>
                    <th>Rasio Negatif</th>
                    <th>Platform Dominan</th>
                    <th>Review Pendukung Terbaru</th>
                </tr>
            </thead>
            <tbody>${body}</tbody>
        </table>
    `;
}

function setPriorityPerPage(value) {
    appState.priorityPerPage = value;
    appState.priorityPage = 1;
    renderPriorityImprovements();
}

function changePriorityPage(delta) {
    appState.priorityPage += delta;
    renderPriorityImprovements();
}

function getFilterValues(prefix) {
    const hotel = document.getElementById(`${prefix}-filter-hotel`)?.value || 'all';
    const platform = document.getElementById(`${prefix}-filter-platform`)?.value || 'all';
    return { hotel, platform };
}

function drillDownToReviews(filters = {}) {
    document.getElementById('review-filter-hotel').value = filters.hotel || 'all';
    document.getElementById('review-filter-platform').value = filters.platform || 'all';
    document.getElementById('review-filter-aspect').value = filters.aspect || 'all';
    document.getElementById('review-filter-sentiment').value = filters.sentiment || 'all';
    document.getElementById('review-filter-keyword').value = filters.keyword || '';
    document.getElementById('review-date-from').value = filters.date_from || '';
    document.getElementById('review-date-to').value = filters.date_to || '';
    navigateTo('reviews');
}

// ========================================
// INIT: LOAD FILTERS
// ========================================
async function initFilters() {
    const data = await fetchAPI('/api/filters');
    if (data.error) return;

    // Populate all hotel dropdowns
    document.querySelectorAll('.filter-hotel').forEach(select => {
        data.hotels.forEach(h => {
            const short = h.replace('Hotel Santika ', '');
            select.innerHTML += `<option value="${h}">${short}</option>`;
        });
    });

    // Populate all platform dropdowns
    document.querySelectorAll('.filter-platform').forEach(select => {
        data.platforms.forEach(p => {
            select.innerHTML += `<option value="${escapeHtml(p)}">${escapeHtml(platformLabel(p))}</option>`;
        });
    });

    // Populate aspect dropdowns
    ['aspect-filter-aspect', 'trend-filter-aspect', 'review-filter-aspect'].forEach(id => {
        const select = document.getElementById(id);
        if (select) {
            data.aspects.forEach(a => {
                select.innerHTML += `<option value="${a}">${a}</option>`;
            });
        }
    });

    if (data.date_range) {
        appState.dateRange = data.date_range;
        appState.overviewDateRange = data.date_range;
        ['trend-date-from', 'trend-date-to', 'review-date-from', 'review-date-to'].forEach(id => {
            const input = document.getElementById(id);
            if (input) {
                // Menghapus batas min/max agar pengguna bebas memilih tanggal berapapun
                input.removeAttribute('min');
                input.removeAttribute('max');
            }
        });
    }
}

// ========================================
// PAGE: OVERVIEW
// ========================================
async function loadOverview() {
    const { hotel: ovHotel, platform: ovPlatform } = getFilterValues('overview');
    const rangeData = await fetchAPI('/api/date-range', { hotel: ovHotel, platform: ovPlatform });
    if (!rangeData.error && rangeData.date_range) {
        appState.overviewDateRange = rangeData.date_range;
    }
    const { params, label, dateRange } = getOverviewDateParams();
    const allParams = { ...params };
    if (ovHotel && ovHotel !== 'all') allParams.hotel = ovHotel;
    if (ovPlatform && ovPlatform !== 'all') allParams.platform = ovPlatform;
    const data = await fetchAPI('/api/overview', allParams);
    if (data.error) return;

    // Stat cards
    const statsEl = document.getElementById('overview-stats');
    const totalSentiment = data.sentiment_counts.positif + data.sentiment_counts.negatif + data.sentiment_counts.netral;
    const posRate = totalSentiment > 0 ? ((data.sentiment_counts.positif / totalSentiment) * 100).toFixed(1) : 0;

    const dateText = params.date_from || params.date_to
        ? `${params.date_from || dateRange.min || '-'} sampai ${params.date_to || dateRange.max || '-'}`
        : `${dateRange.min || '-'} sampai ${dateRange.max || '-'}`;
    const timeLabel = document.getElementById('overview-time-label');
    if (timeLabel) {
        timeLabel.textContent = `${label} - ${dateText}`;
    }

    statsEl.innerHTML = `
        <div class="stat-card filter-stat-card">
            <div class="stat-card-icon blue">${iconSvg('calendar')}</div>
            <div class="filter-stat-content">
                <div class="stat-card-label">Periode Analisis</div>
                <div class="stat-card-note" id="overview-time-label">${label} &middot; ${dateText}</div>
                <select class="quick-filter-select" id="overview-time-select" aria-label="Filter waktu overview">
                    <option value="all">Semua data</option>
                    <option value="1d">1 hari terakhir</option>
                    <option value="7d">7 hari terakhir</option>
                    <option value="30d">30 hari terakhir</option>
                    <option value="3m">3 bulan terakhir</option>
                    <option value="6m">6 bulan terakhir</option>
                    <option value="1y">1 tahun terakhir</option>
                    <option value="2026">Tahun 2026</option>
                    <option value="2025">Tahun 2025</option>
                </select>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-card-icon blue">${iconSvg('review')}</div>
            <div class="stat-card-value">${data.total_reviews.toLocaleString()}</div>
            <div class="stat-card-label">Total Review</div>
        </div>
        <div class="stat-card">
            <div class="stat-card-icon purple">${iconSvg('hotel')}</div>
            <div class="stat-card-value">${data.total_hotels}</div>
            <div class="stat-card-label">Cabang Hotel</div>
        </div>
        <div class="stat-card">
            <div class="stat-card-icon cyan">${iconSvg('platform')}</div>
            <div class="stat-card-value">${data.total_platforms}</div>
            <div class="stat-card-label">Platform OTA</div>
        </div>
        <div class="stat-card">
            <div class="stat-card-icon green">${iconSvg('positive')}</div>
            <div class="stat-card-value">${posRate}%</div>
            <div class="stat-card-label">Rasio Positif Aspek</div>
        </div>
    `;

    const overviewSelect = document.getElementById('overview-time-select');
    if (overviewSelect) {
        overviewSelect.value = appState.overviewRange;
        overviewSelect.addEventListener('change', () => {
            appState.overviewRange = overviewSelect.value;
            loadOverview();
        });
    }

    renderOverviewInsight(data, posRate);
    renderSentimentSummary(data);
    renderPriorityImprovements(data.priority_improvements || []);

    // Sentiment composition bar
    destroyChart('sentiment-dist');
    const ctx1 = document.getElementById('chart-sentiment-dist').getContext('2d');
    charts['sentiment-dist'] = new Chart(ctx1, {
        type: 'bar',
        data: {
            labels: [sentimentLabel('positif'), sentimentLabel('negatif'), sentimentLabel('netral')],
            datasets: [{
                label: 'Jumlah Sentimen',
                data: [data.sentiment_counts.positif, data.sentiment_counts.negatif, data.sentiment_counts.netral],
                backgroundColor: [COLORS.positif, COLORS.negatif, COLORS.netral],
                borderWidth: 0,
                borderRadius: 8,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: COLORS.grid }, beginAtZero: true },
                y: { grid: { display: false } },
            },
        }
    });

    // Top negative aspects bar
    destroyChart('negative-aspects');
    const ctx2 = document.getElementById('chart-negative-aspects').getContext('2d');
    const negAspects = data.top_negative_aspects || [];
    charts['negative-aspects'] = new Chart(ctx2, {
        type: 'bar',
        data: {
            labels: negAspects.map(a => a[0]),
            datasets: [{
                label: sentimentLabel('negatif'),
                data: negAspects.map(a => a[1]),
                backgroundColor: negAspects.map((_, index) => index < 2 ? COLORS.negatif + 'd9' : COLORS.muted + '66'),
                borderColor: negAspects.map((_, index) => index < 2 ? COLORS.negatif : COLORS.muted),
                borderWidth: 1,
                borderRadius: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: COLORS.grid } },
                y: { grid: { display: false } },
            }
        }
    });

    // Stacked bar per aspect
    destroyChart('overview-aspects');
    const ctx3 = document.getElementById('chart-overview-aspects').getContext('2d');
    const stats = data.aspect_stats;
    charts['overview-aspects'] = new Chart(ctx3, {
        type: 'bar',
        data: {
            labels: ASPECTS,
            datasets: [
                { label: sentimentLabel('positif'), data: ASPECTS.map(a => stats[a]?.positif || 0), backgroundColor: COLORS.positif + 'cc', borderRadius: 4 },
                { label: sentimentLabel('negatif'), data: ASPECTS.map(a => stats[a]?.negatif || 0), backgroundColor: COLORS.negatif + 'cc', borderRadius: 4 },
                { label: sentimentLabel('netral'), data: ASPECTS.map(a => stats[a]?.netral || 0), backgroundColor: COLORS.netral + 'cc', borderRadius: 4 },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'top' } },
            scales: {
                x: { stacked: true, grid: { display: false } },
                y: { stacked: true, grid: { color: COLORS.grid } },
            }
        }
    });

    // Load price vs quality analysis
    loadPriceQuality(allParams);
}

// ========================================
// PRICE vs QUALITY ANALYSIS
// ========================================
async function loadPriceQuality(overviewParams = {}) {
    const data = await fetchAPI('/api/price-quality', overviewParams);
    if (data.error) return;

    destroyChart('price-quality');
    const ctx = document.getElementById('chart-price-quality')?.getContext('2d');
    if (!ctx) return;

    const hotels = data.hotels || [];
    const labels = hotels.map(h => h.hotel_short);

    charts['price-quality'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Harga (% Negatif)',
                    data: hotels.map(h => h.aspects?.Harga?.negative_rate || 0),
                    backgroundColor: COLORS.negatif + 'cc',
                    borderRadius: 4,
                },
                {
                    label: 'Pelayanan (% Negatif)',
                    data: hotels.map(h => h.aspects?.Pelayanan?.negative_rate || 0),
                    backgroundColor: COLORS.blue + 'cc',
                    borderRadius: 4,
                },
                {
                    label: 'Fasilitas (% Negatif)',
                    data: hotels.map(h => h.aspects?.Fasilitas?.negative_rate || 0),
                    backgroundColor: COLORS.purple + 'cc',
                    borderRadius: 4,
                },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'top' } },
            scales: {
                x: { grid: { display: false } },
                y: { grid: { color: COLORS.grid }, beginAtZero: true, ticks: { callback: v => v + '%' } },
            }
        }
    });

    const tableWrapper = document.getElementById('price-quality-table-wrapper');
    if (tableWrapper && hotels.length) {
        let html = '<table class="data-table"><thead><tr>';
        html += '<th>Hotel</th><th>Harga (% Neg)</th><th>Pelayanan (% Neg)</th><th>Fasilitas (% Neg)</th><th>Gap Harga vs Layanan</th><th>Penilaian</th>';
        html += '</tr></thead><tbody>';
        hotels.forEach(h => {
            const gapColor = h.gap > 5 ? 'color:var(--color-negatif);font-weight:600;' : h.gap < -5 ? 'color:var(--color-positif);font-weight:600;' : '';
            const verdictBadge = h.gap > 5 ? 'badge-negatif' : h.gap < -5 ? 'badge-positif' : 'badge-netral';
            html += `<tr>
                <td><strong>${escapeHtml(h.hotel_short)}</strong></td>
                <td>${h.aspects?.Harga?.negative_rate || 0}%</td>
                <td>${h.aspects?.Pelayanan?.negative_rate || 0}%</td>
                <td>${h.aspects?.Fasilitas?.negative_rate || 0}%</td>
                <td style="${gapColor}">${h.gap > 0 ? '+' : ''}${h.gap}%</td>
                <td><span class="badge ${verdictBadge}">${escapeHtml(h.verdict)}</span></td>
            </tr>`;
        });
        html += '</tbody></table>';
        tableWrapper.innerHTML = html;
    }
}

// ========================================
// EXPORT SUMMARY FOR BRIEFING
// ========================================
async function exportSummary() {
    const { hotel: ovHotel, platform: ovPlatform } = getFilterValues('overview');
    const rangeData = await fetchAPI('/api/date-range', { hotel: ovHotel, platform: ovPlatform });
    if (!rangeData.error && rangeData.date_range) {
        appState.overviewDateRange = rangeData.date_range;
    }
    const { params } = getOverviewDateParams();
    const allParams = { ...params };
    if (ovHotel && ovHotel !== 'all') allParams.hotel = ovHotel;
    if (ovPlatform && ovPlatform !== 'all') allParams.platform = ovPlatform;

    const data = await fetchAPI('/api/export-summary', allParams);
    if (data.error) { alert('Gagal mengambil data ringkasan.'); return; }

    const win = window.open('', '_blank');
    if (!win) { alert('Pop-up diblokir browser. Izinkan pop-up untuk fitur ini.'); return; }
    win.document.write(generateSummaryHTML(data));
    win.document.close();
}

function generateSummaryHTML(data) {
    return `<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<title>Ringkasan Briefing Customer Sentiment Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;padding:40px;color:#1a1a1a;max-width:820px;margin:0 auto;line-height:1.5}
h1{font-size:22px;margin-bottom:4px}
h2{font-size:16px;margin-top:28px;margin-bottom:12px;border-bottom:2px solid #333;padding-bottom:4px}
h3{font-size:14px;margin-bottom:6px}
.subtitle{color:#666;font-size:13px;margin-bottom:20px}
.meta{font-size:12px;color:#888;margin-bottom:16px}
.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}
.stat-box{background:#f5f5f5;padding:12px;border-radius:6px;text-align:center}
.stat-value{font-size:24px;font-weight:700}
.stat-label{font-size:11px;color:#666;margin-top:2px}
table{width:100%;border-collapse:collapse;margin-bottom:16px;font-size:13px}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #ddd}
th{background:#f5f5f5;font-weight:600}
.neg{color:#d32f2f;font-weight:600}
.pos{color:#2e7d32;font-weight:600}
.review-box{background:#fafafa;border-left:3px solid #d32f2f;padding:10px 14px;margin-bottom:10px;border-radius:0 4px 4px 0;font-size:13px}
.review-meta{font-size:11px;color:#888;margin-bottom:4px}
.phrase-tag{display:inline-block;background:#fff3e0;color:#e65100;padding:2px 8px;border-radius:10px;font-size:12px;margin:2px}
.footer{margin-top:32px;padding-top:12px;border-top:1px solid #ddd;font-size:11px;color:#999}
.print-btn{padding:8px 20px;background:#1a73e8;color:white;border:none;border-radius:4px;cursor:pointer;font-size:13px}
@media print{.no-print{display:none}body{padding:20px}}
</style>
</head>
<body>
<div style="text-align:right;" class="no-print">
    <button onclick="window.print()" class="print-btn">🖨️ Cetak / Simpan PDF</button>
</div>
<h1>Ringkasan Briefing Analisis</h1>
<div class="subtitle">Customer Sentiment Dashboard - Hotel Santika Jawa Barat</div>
<div class="meta">
    Dibuat: ${escapeHtml(data.generated_at)} &bull;
    Periode data: ${escapeHtml(data.date_range?.min || '-')} s/d ${escapeHtml(data.date_range?.max || '-')} &bull;
    Hotel: ${data.hotels?.length || 0} cabang &bull;
    Platform: ${escapeHtml((data.platforms || []).map(platformLabel).join(', ') || '-')}
</div>

<div class="stats-grid">
    <div class="stat-box"><div class="stat-value">${data.total_reviews?.toLocaleString()}</div><div class="stat-label">Total Review</div></div>
    <div class="stat-box"><div class="stat-value pos">${data.positive_rate}%</div><div class="stat-label">Rasio Positif</div></div>
    <div class="stat-box"><div class="stat-value neg">${data.sentiment_counts?.negatif?.toLocaleString()}</div><div class="stat-label">Sentimen Negatif</div></div>
    <div class="stat-box"><div class="stat-value">${data.hotels?.length || 0}</div><div class="stat-label">Cabang Hotel</div></div>
</div>

<h2>Top Aspek Bermasalah</h2>
<table>
    <thead><tr><th>#</th><th>Aspek</th><th>Jumlah Negatif</th><th>Total Sentimen</th><th>Rasio Negatif</th></tr></thead>
    <tbody>
        ${(data.top_negative_aspects || []).map((a, i) => {
        const rate = a.total > 0 ? ((a.count / a.total) * 100).toFixed(1) : '0.0';
        return `<tr><td>${i + 1}</td><td><strong>${escapeHtml(a.aspect)}</strong></td><td class="neg">${a.count.toLocaleString()}</td><td>${a.total.toLocaleString()}</td><td>${rate}%</td></tr>`;
    }).join('')}
    </tbody>
</table>

<h2>Top Kekuatan Layanan</h2>
<table>
    <thead><tr><th>#</th><th>Aspek</th><th>Jumlah Positif</th><th>Total Sentimen</th><th>Rasio Positif</th></tr></thead>
    <tbody>
        ${(data.top_positive_aspects || []).map((a, i) => {
        const rate = a.total > 0 ? ((a.count / a.total) * 100).toFixed(1) : '0.0';
        return `<tr><td>${i + 1}</td><td><strong>${escapeHtml(a.aspect)}</strong></td><td class="pos">${a.count.toLocaleString()}</td><td>${a.total.toLocaleString()}</td><td>${rate}%</td></tr>`;
    }).join('')}
    </tbody>
</table>

<h2>Top Frasa Keluhan Per Aspek</h2>
${Object.entries(data.phrases_summary || {}).map(([aspect, phrases]) => {
        if (!phrases || !phrases.length) return '';
        return `<h3>${escapeHtml(aspect)}</h3><div style="margin-bottom:12px;">${phrases.map(p => `<span class="phrase-tag">${escapeHtml(p.phrase)} (${p.count}x)</span>`).join(' ')}</div>`;
    }).join('')}

<h2>Prioritas Perbaikan</h2>
<table>
    <thead><tr><th>#</th><th>Hotel</th><th>Aspek</th><th>Negatif</th><th>Rasio</th><th>Platform</th></tr></thead>
    <tbody>
        ${(data.priority_improvements || []).map((row, i) => `
            <tr>
                <td>${i + 1}</td>
                <td>${escapeHtml(row.hotel_short || row.hotel)}</td>
                <td>${escapeHtml(row.aspect)}</td>
                <td class="neg">${row.negative_count}</td>
                <td>${row.negative_rate}%</td>
                <td>${escapeHtml(row.dominant_platform)}</td>
            </tr>
        `).join('')}
    </tbody>
</table>

<h2>Contoh Review Negatif Terbaru</h2>
${(data.recent_negative_reviews || []).map(r => `
    <div class="review-box">
        <div class="review-meta">${escapeHtml(r.hotel || '')} &bull; ${escapeHtml(r.platform || '')} &bull; ${escapeHtml(r.date || '')} &bull; Aspek: ${escapeHtml(r.aspect || '')}</div>
        <div>${escapeHtml(r.text || '')}</div>
    </div>
`).join('')}

<div class="footer">
    <p>Laporan ini dihasilkan otomatis oleh Customer Sentiment Dashboard. Hasil analisis merupakan output model IndoBERT dan bersifat sebagai alat bantu keputusan, bukan keputusan final.</p>
</div>
</body>
</html>`;
}


async function loadComplaintPhrases(filterPayload) {
    const complaintPayload = { ...filterPayload, sentiment: 'all' };
    const data = await fetchAPI('/api/complaint-phrases', complaintPayload);
    if (data.error) return;
    renderComplaintPhrases(data.top_phrases || {});
}

function renderComplaintPhrases(topPhrases) {
    const wrapper = document.getElementById('complaint-phrases-wrapper');
    if (!wrapper) return;

    const aspectEntries = Object.entries(topPhrases).filter(([, payload]) => (payload.phrases || []).length > 0);
    if (!aspectEntries.length) {
        wrapper.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-text">Belum ada frasa keluhan pada filter ini. Coba pilih aspek atau filter lain.</div>
            </div>
        `;
        return;
    }

    wrapper.innerHTML = `
        <div class="complaint-phrase-grid">
            ${aspectEntries.map(([aspect, payload]) => {
        const phrases = payload.phrases || [];
        const maxCount = Math.max(...phrases.map(item => item.count || 0), 1);
        return `
                    <div class="complaint-phrase-card">
                        <div class="complaint-phrase-header">
                            <div>
                                <div class="complaint-aspect">${escapeHtml(aspect)}</div>
                                <div class="table-muted">${Number(payload.negative_reviews || 0).toLocaleString()} review negatif</div>
                            </div>
                        </div>
                        <div class="complaint-phrase-list">
                            ${phrases.map(item => {
            const width = Math.max(8, ((item.count || 0) / maxCount) * 100);
            const example = item.example || {};
            return `
                                    <div class="complaint-phrase-item">
                                        <div class="complaint-phrase-main">
                                            <span class="complaint-phrase-text">${escapeHtml(item.phrase)}</span>
                                            <span class="complaint-phrase-count">${Number(item.count || 0).toLocaleString()}x</span>
                                        </div>
                                        <div class="complaint-phrase-track"><div style="width:${width}%"></div></div>
                                        <div class="complaint-example">
                                            ${escapeHtml((example.hotel || '').replace('Hotel Santika ', '') || '-')} &middot;
                                            ${escapeHtml(example.platform || '-')} &middot;
                                            ${escapeHtml(example.date || '-')}
                                        </div>
                                    </div>
                                `;
        }).join('')}
                        </div>
                    </div>
                `;
    }).join('')}
        </div>
    `;
}

async function loadAspectAnalysis() {
    const { hotel, platform } = getFilterValues('aspect');
    const aspect = document.getElementById('aspect-filter-aspect')?.value || 'all';
    const sentiment = document.getElementById('aspect-filter-sentiment')?.value || 'all';

    const filterPayload = { hotel, platform, aspect, sentiment };
    const data = await fetchAPI('/api/aspect-analysis', filterPayload);
    if (data.error) return;
    loadComplaintPhrases(filterPayload);

    const stats = data.aspect_stats;

    // Stacked bar
    destroyChart('aspect-detail');
    const ctx1 = document.getElementById('chart-aspect-detail').getContext('2d');
    charts['aspect-detail'] = new Chart(ctx1, {
        type: 'bar',
        data: {
            labels: ASPECTS,
            datasets: [
                { label: sentimentLabel('positif'), data: ASPECTS.map(a => stats[a]?.positif || 0), backgroundColor: COLORS.positif + 'cc', borderRadius: 4 },
                { label: sentimentLabel('negatif'), data: ASPECTS.map(a => stats[a]?.negatif || 0), backgroundColor: COLORS.negatif + 'cc', borderRadius: 4 },
                { label: sentimentLabel('netral'), data: ASPECTS.map(a => stats[a]?.netral || 0), backgroundColor: COLORS.netral + 'cc', borderRadius: 4 },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'top' } },
            scales: {
                x: { stacked: true, grid: { display: false } },
                y: { stacked: true, grid: { color: COLORS.grid } },
            }
        }
    });

    // Ratio chart (percentage)
    destroyChart('aspect-ratio');
    const ctx2 = document.getElementById('chart-aspect-ratio').getContext('2d');
    const ratioData = ASPECTS.map(a => {
        const s = stats[a] || {};
        const total = (s.positif || 0) + (s.negatif || 0) + (s.netral || 0);
        return {
            positif: total > 0 ? ((s.positif || 0) / total * 100).toFixed(1) : 0,
            negatif: total > 0 ? ((s.negatif || 0) / total * 100).toFixed(1) : 0,
            netral: total > 0 ? ((s.netral || 0) / total * 100).toFixed(1) : 0,
        };
    });
    charts['aspect-ratio'] = new Chart(ctx2, {
        type: 'bar',
        data: {
            labels: ASPECTS,
            datasets: [
                { label: sentimentLabel('positif', true), data: ratioData.map(r => r.positif), backgroundColor: COLORS.positif + 'cc', borderRadius: 4 },
                { label: sentimentLabel('negatif', true), data: ratioData.map(r => r.negatif), backgroundColor: COLORS.negatif + 'cc', borderRadius: 4 },
                { label: sentimentLabel('netral', true), data: ratioData.map(r => r.netral), backgroundColor: COLORS.netral + 'cc', borderRadius: 4 },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'top' } },
            scales: {
                x: { stacked: true, grid: { display: false } },
                y: { stacked: true, max: 100, grid: { color: COLORS.grid }, ticks: { callback: v => v + '%' } },
            }
        }
    });

    // Examples table
    const exTable = document.getElementById('aspect-examples-table');
    const examples = data.aspect_examples;
    if (aspect !== 'all' && examples[aspect] && examples[aspect].length > 0) {
        const cards = examples[aspect]
            .map(r => renderReviewCard(r, { onlyAspect: aspect }))
            .join('');
        exTable.innerHTML = `<div class="review-list">${cards}</div>`;
    } else if (aspect === 'all') {
        exTable.innerHTML = '<div class="empty-state"><div class="empty-state-text">Pilih aspek spesifik untuk melihat contoh review.</div></div>';
    } else {
        exTable.innerHTML = '<div class="empty-state"><div class="empty-state-text">Tidak ada review ditemukan untuk filter ini.</div></div>';
    }
}

// ========================================
// PAGE: HOTEL & PLATFORM
// ========================================
async function loadHotelPlatform() {
    const { hotel, platform } = getFilterValues('hp');
    const data = await fetchAPI('/api/hotel-platform', { hotel, platform });
    if (data.error) return;

    // Hotel comparison
    destroyChart('hotel-compare');
    const ctx1 = document.getElementById('chart-hotel-compare').getContext('2d');
    const hotels = Object.keys(data.hotel_stats);
    const hotelLabels = hotels.map(h => h.replace('Hotel Santika ', ''));

    // Aggregate across all aspects
    const hotelPos = hotels.map(h => ASPECTS.reduce((s, a) => s + (data.hotel_stats[h][a]?.positif || 0), 0));
    const hotelNeg = hotels.map(h => ASPECTS.reduce((s, a) => s + (data.hotel_stats[h][a]?.negatif || 0), 0));
    const hotelNet = hotels.map(h => ASPECTS.reduce((s, a) => s + (data.hotel_stats[h][a]?.netral || 0), 0));

    charts['hotel-compare'] = new Chart(ctx1, {
        type: 'bar',
        data: {
            labels: hotelLabels,
            datasets: [
                { label: sentimentLabel('positif'), data: hotelPos, backgroundColor: COLORS.positif + 'cc', borderRadius: 4 },
                { label: sentimentLabel('negatif'), data: hotelNeg, backgroundColor: COLORS.negatif + 'cc', borderRadius: 4 },
                { label: sentimentLabel('netral'), data: hotelNet, backgroundColor: COLORS.netral + 'cc', borderRadius: 4 },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'top' } },
            scales: {
                x: { grid: { display: false } },
                y: { grid: { color: COLORS.grid } },
            }
        }
    });

    // Platform comparison
    destroyChart('platform-compare');
    const ctx2 = document.getElementById('chart-platform-compare').getContext('2d');
    const platforms = Object.keys(data.platform_stats);

    const platPos = platforms.map(p => ASPECTS.reduce((s, a) => s + (data.platform_stats[p][a]?.positif || 0), 0));
    const platNeg = platforms.map(p => ASPECTS.reduce((s, a) => s + (data.platform_stats[p][a]?.negatif || 0), 0));
    const platNet = platforms.map(p => ASPECTS.reduce((s, a) => s + (data.platform_stats[p][a]?.netral || 0), 0));

    charts['platform-compare'] = new Chart(ctx2, {
        type: 'bar',
        data: {
            labels: platforms.map(platformLabel),
            datasets: [
                { label: sentimentLabel('positif'), data: platPos, backgroundColor: COLORS.positif + 'cc', borderRadius: 4 },
                { label: sentimentLabel('negatif'), data: platNeg, backgroundColor: COLORS.negatif + 'cc', borderRadius: 4 },
                { label: sentimentLabel('netral'), data: platNet, backgroundColor: COLORS.netral + 'cc', borderRadius: 4 },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'top' } },
            scales: {
                x: { grid: { display: false } },
                y: { grid: { color: COLORS.grid } },
            }
        }
    });
}

// ========================================
// PAGE: TREND
// ========================================
function getTrendPeriodStats(periods, trendData) {
    return periods.map(period => {
        const item = trendData[period] || {};
        const positif = item.positif || 0;
        const negatif = item.negatif || 0;
        const netral = item.netral || 0;
        const total = positif + negatif + netral;
        return {
            period,
            positif,
            negatif,
            netral,
            total,
            positiveRate: total > 0 ? (positif / total) * 100 : 0,
            negativeRate: total > 0 ? (negatif / total) * 100 : 0,
            neutralRate: total > 0 ? (netral / total) * 100 : 0,
        };
    });
}

function renderTrendInsights(periodStats, mode) {
    const el = document.getElementById('trend-insights');
    if (!el) return;

    const nonEmpty = periodStats.filter(row => row.total > 0);
    if (!nonEmpty.length) {
        el.innerHTML = `
            <div class="trend-insight-card">
                <div class="trend-insight-label">Ringkasan tren</div>
                <div class="trend-insight-value">Belum ada data</div>
                <div class="trend-insight-note">Coba ubah filter hotel, platform, aspek, atau rentang tanggal.</div>
            </div>
        `;
        return;
    }

    const latest = nonEmpty[nonEmpty.length - 1];
    const previous = nonEmpty.length > 1 ? nonEmpty[nonEmpty.length - 2] : null;
    const deltaNegative = previous ? latest.negativeRate - previous.negativeRate : 0;
    const peakRisk = [...nonEmpty].sort((a, b) => b.negativeRate - a.negativeRate)[0];
    const displayUnit = mode === 'percent' ? 'proporsi' : 'jumlah';

    el.innerHTML = `
        <div class="trend-insight-card">
            <div class="trend-insight-label">Periode terbaru</div>
            <div class="trend-insight-value">${escapeHtml(latest.period)}</div>
            <div class="trend-insight-note">${latest.total.toLocaleString()} sentimen aspek terbaca pada periode ini.</div>
        </div>
        <div class="trend-insight-card danger">
            <div class="trend-insight-label">Negatif terbaru</div>
            <div class="trend-insight-value">${pct(latest.negativeRate)}</div>
            <div class="trend-insight-note">${latest.negatif.toLocaleString()} dari ${latest.total.toLocaleString()} sentimen aspek bernada negatif.</div>
        </div>
        <div class="trend-insight-card ${deltaNegative > 0 ? 'danger' : 'success'}">
            <div class="trend-insight-label">Perubahan negatif</div>
            <div class="trend-insight-value">${previous ? `${deltaNegative >= 0 ? '+' : ''}${deltaNegative.toFixed(1)}%` : '-'}</div>
            <div class="trend-insight-note">${previous ? `Dibanding periode ${escapeHtml(previous.period)} berdasarkan ${displayUnit} sentimen.` : 'Belum ada periode pembanding.'}</div>
        </div>
        <div class="trend-insight-card">
            <div class="trend-insight-label">Risiko historis tertinggi</div>
            <div class="trend-insight-value">${escapeHtml(peakRisk.period)}</div>
            <div class="trend-insight-note">${pct(peakRisk.negativeRate)} sentimen aspek bernada negatif pada periode ini.</div>
        </div>
    `;
}

async function loadTrend() {
    const { hotel, platform } = getFilterValues('trend');
    const aspect = document.getElementById('trend-filter-aspect')?.value || 'all';
    const granularity = document.getElementById('trend-granularity')?.value || 'year';
    const viewMode = document.getElementById('trend-view-mode')?.value || 'count';
    const dateFrom = document.getElementById('trend-date-from')?.value || '';
    const dateTo = document.getElementById('trend-date-to')?.value || '';

    const data = await fetchAPI('/api/trend', {
        hotel,
        platform,
        trend_aspect: aspect,
        aspect: aspect,
        granularity,
        date_from: dateFrom,
        date_to: dateTo,
    });
    if (data.error) return;

    destroyChart('trend');
    const ctx = document.getElementById('chart-trend').getContext('2d');
    const periods = data.periods;
    const periodStats = getTrendPeriodStats(periods, data.trend_data || {});
    const isPercentMode = viewMode === 'percent';
    const posData = isPercentMode ? periodStats.map(p => p.positiveRate.toFixed(1)) : periodStats.map(p => p.positif);
    const negData = isPercentMode ? periodStats.map(p => p.negativeRate.toFixed(1)) : periodStats.map(p => p.negatif);
    const netData = isPercentMode ? periodStats.map(p => p.neutralRate.toFixed(1)) : periodStats.map(p => p.netral);
    const granularityLabels = {
        day: 'harian',
        week: 'mingguan',
        month: 'bulanan',
        year: 'tahunan',
    };
    const rangeLabel = dateFrom || dateTo
        ? `${dateFrom || 'awal data'} sampai ${dateTo || 'akhir data'}`
        : 'seluruh rentang data';
    const aspectLabel = aspect === 'all' ? 'semua aspek' : `aspek ${aspect}`;
    const summary = document.getElementById('trend-summary');
    if (summary) {
        summary.textContent = `${periods.length} periode ${granularityLabels[data.granularity] || 'tahunan'} - ${data.total_reviews.toLocaleString()} review - ${data.total_sentiment_points.toLocaleString()} sentimen aspek - ${aspectLabel} - ${rangeLabel} - tampilan ${isPercentMode ? 'persentase' : 'jumlah'}`;
    }
    renderTrendInsights(periodStats, viewMode);

    charts['trend'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: periods,
            datasets: [
                {
                    label: sentimentLabel('positif'), data: posData,
                    borderColor: COLORS.positif, backgroundColor: COLORS.positif + '22',
                    fill: true, tension: 0.3, pointRadius: 3, pointHoverRadius: 6, borderWidth: 2,
                },
                {
                    label: sentimentLabel('negatif'), data: negData,
                    borderColor: COLORS.negatif, backgroundColor: COLORS.negatif + '22',
                    fill: true, tension: 0.3, pointRadius: 3, pointHoverRadius: 6, borderWidth: 2,
                },
                {
                    label: sentimentLabel('netral'), data: netData,
                    borderColor: COLORS.netral, backgroundColor: COLORS.netral + '22',
                    fill: true, tension: 0.3, pointRadius: 3, pointHoverRadius: 6, borderWidth: 2,
                },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: context => `${context.dataset.label}: ${context.parsed.y}${isPercentMode ? '%' : ''}`,
                    }
                }
            },
            scales: {
                x: { grid: { color: COLORS.grid } },
                y: {
                    grid: { color: COLORS.grid },
                    beginAtZero: true,
                    max: isPercentMode ? 100 : undefined,
                    ticks: {
                        callback: value => `${value}${isPercentMode ? '%' : ''}`,
                    },
                },
            }
        }
    });
}

function resetTrendFilters() {
    document.getElementById('trend-filter-hotel').value = 'all';
    document.getElementById('trend-filter-platform').value = 'all';
    document.getElementById('trend-filter-aspect').value = 'all';
    document.getElementById('trend-granularity').value = 'year';
    document.getElementById('trend-view-mode').value = 'count';
    document.getElementById('trend-date-from').value = '';
    document.getElementById('trend-date-to').value = '';
    loadTrend();
}

// ========================================
// PAGE: REVIEW EXPLORER
// ========================================
async function loadReviews(page = 1) {
    appState.reviewPage = page;
    const { hotel, platform } = getFilterValues('review');
    const aspect = document.getElementById('review-filter-aspect')?.value || 'all';
    const sentiment = document.getElementById('review-filter-sentiment')?.value || 'all';
    const keyword = document.getElementById('review-filter-keyword')?.value || '';
    const dateFrom = document.getElementById('review-date-from')?.value || '';
    const dateTo = document.getElementById('review-date-to')?.value || '';

    const data = await fetchAPI('/api/reviews', { hotel, platform, aspect, sentiment, keyword, date_from: dateFrom, date_to: dateTo, page, per_page: appState.reviewPerPage });
    if (data.error) return;

    if (data.total > 0 && page > (data.total_pages || 1)) {
        await loadReviews(data.total_pages || 1);
        return;
    }

    // Count
    document.getElementById('review-count').textContent = `${data.total.toLocaleString()} review ditemukan`;

    // List (kartu per-review)
    const tbody = document.getElementById('reviews-tbody');
    if (data.reviews.length === 0) {
        tbody.innerHTML = '<div class="empty-state"><div class="empty-state-text">Tidak ada review ditemukan.</div></div>';
    } else {
        tbody.innerHTML = data.reviews.map(r => renderReviewCard(r)).join('');
    }

    // Selector per-halaman di card header (kanan atas sebelah "review ditemukan")
    const perpageHeader = document.getElementById('review-perpage-header');
    if (perpageHeader) {
        const sizes = [5, 10, 20, 50];
        perpageHeader.innerHTML = sizes.map(s =>
            `<button class="priority-size-btn ${appState.reviewPerPage === s ? 'active' : ''}" onclick="setReviewPerPage(${s})">${s}</button>`
        ).join('');
    }

    // Navigasi halaman di bawah
    const pagEl = document.getElementById('reviews-pagination');
    const totalPages = data.total_pages || 1;
    if (totalPages <= 1) {
        pagEl.innerHTML = '';
        return;
    }
    const maxBtns = 7;
    let start = Math.max(1, page - Math.floor(maxBtns / 2));
    let end = Math.min(totalPages, start + maxBtns - 1);
    if (end - start < maxBtns - 1) start = Math.max(1, end - maxBtns + 1);
    let navHtml = `<button class="pagination-btn" ${page <= 1 ? 'disabled' : ''} onclick="loadReviews(${page - 1})">&laquo;</button>`;
    for (let i = start; i <= end; i++) {
        navHtml += `<button class="pagination-btn ${i === page ? 'active' : ''}" onclick="loadReviews(${i})">${i}</button>`;
    }
    navHtml += `<span class="pagination-info">Hal ${page}/${totalPages}</span>`;
    navHtml += `<button class="pagination-btn" ${page >= totalPages ? 'disabled' : ''} onclick="loadReviews(${page + 1})">&raquo;</button>`;
    pagEl.innerHTML = navHtml;
}

async function deleteReview(reviewId) {
    if (!CAN_MANAGE_REVIEWS || !reviewId) return;

    const ok = confirm(`Hapus review ${reviewId} dari dataset? Aksi ini akan tercatat di log aktivitas.`);
    if (!ok) return;

    try {
        const res = await fetch(`/api/reviews/${encodeURIComponent(reviewId)}`, {
            method: 'DELETE',
        });
        const data = await res.json();

        if (!res.ok || data.error) {
            alert('Gagal menghapus review: ' + (data.error || res.statusText));
            return;
        }

        alert('Review berhasil dihapus.');
        await loadReviews(appState.reviewPage);
        if (CAN_VIEW_ACTIVITY_LOG) {
            await loadActivityLog();
        }
    } catch (err) {
        alert('Terjadi kesalahan saat menghapus review: ' + err.message);
    }
}

async function loadActivityLog() {
    if (!CAN_VIEW_ACTIVITY_LOG) return;

    const wrapper = document.getElementById('review-log-body');
    if (!wrapper) return;

    wrapper.innerHTML = '<div class="empty-state"><div class="empty-state-text">Memuat log aktivitas...</div></div>';
    const data = await fetchAPI('/api/activity-log', { limit: 100 });
    if (data.error) {
        wrapper.innerHTML = `<div class="empty-state"><div class="empty-state-text">${escapeHtml(data.error)}</div></div>`;
        return;
    }

    const logs = data.logs || [];
    if (logs.length === 0) {
        wrapper.innerHTML = '<div class="empty-state"><div class="empty-state-text">Belum ada aktivitas input atau penghapusan review.</div></div>';
        return;
    }

    wrapper.innerHTML = `
        <table class="data-table activity-log-table">
            <thead>
                <tr>
                    <th>Waktu</th>
                    <th>Aksi</th>
                    <th>Pengguna</th>
                    <th>Review</th>
                    <th>Ringkasan</th>
                </tr>
            </thead>
            <tbody>
                ${logs.map(log => {
                    const review = log.review || {};
                    const actionClass = log.action === 'delete' ? 'negatif' : 'positif';
                    const reviewTitle = [
                        review.Nama_Hotel,
                        platformLabel(review.Platform),
                        review.Review_Date,
                    ].filter(Boolean).map(escapeHtml).join(' &middot; ');
                    return `
                        <tr>
                            <td>${escapeHtml(log.timestamp || '-')}</td>
                            <td><span class="badge badge-${actionClass}">${escapeHtml(log.action_label || log.action || '-')}</span></td>
                            <td>
                                <strong>${escapeHtml(log.actor_name || '-')}</strong>
                                <div class="table-muted">${escapeHtml(log.actor_role_label || log.actor_username || '-')}</div>
                            </td>
                            <td>
                                <strong>ID ${escapeHtml(review.ID_Review || '-')}</strong>
                                <div class="table-muted">${reviewTitle || '-'}</div>
                            </td>
                            <td class="activity-log-text">${escapeHtml(review.Text_Review_Short || review.Text_Review || '-')}</td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
}

function setReviewPerPage(value) {
    appState.reviewPerPage = value;
    loadReviews(1);
}
function exportReviews() {
    const { hotel, platform } = getFilterValues('review');
    const aspect = document.getElementById('review-filter-aspect')?.value || 'all';
    const sentiment = document.getElementById('review-filter-sentiment')?.value || 'all';
    const keyword = document.getElementById('review-filter-keyword')?.value || '';
    const dateFrom = document.getElementById('review-date-from')?.value || '';
    const dateTo = document.getElementById('review-date-to')?.value || '';

    const params = new URLSearchParams();
    if (hotel && hotel !== 'all') params.set('hotel', hotel);
    if (platform && platform !== 'all') params.set('platform', platform);
    if (aspect && aspect !== 'all') params.set('aspect', aspect);
    if (sentiment && sentiment !== 'all') params.set('sentiment', sentiment);
    if (keyword) params.set('keyword', keyword);
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);

    window.open(`/api/export?${params.toString()}`, '_blank');
}

function resetReviewFilters() {
    document.getElementById('review-filter-hotel').value = 'all';
    document.getElementById('review-filter-platform').value = 'all';
    document.getElementById('review-filter-aspect').value = 'all';
    document.getElementById('review-filter-sentiment').value = 'all';
    document.getElementById('review-filter-keyword').value = '';
    document.getElementById('review-date-from').value = '';
    document.getElementById('review-date-to').value = '';
    loadReviews(1);
}

// ========================================
// PAGE: PREDICTION
// ========================================
let lastPredictionData = null;

function getPredictionLabelText(label) {
    const labels = {
        positif: 'Positif',
        negatif: 'Negatif',
        netral: 'Netral',
        none: 'Tidak terdeteksi',
    };
    return labels[label] || label;
}

function renderManualLabelingPanel(lowConfidence = []) {
    if (!lowConfidence.length) return '';

    return `
        <div class="manual-label-panel">
            <div class="manual-label-header">
                <div>
                    <div class="manual-label-title">Validasi Manual Confidence Rendah</div>
                    <div class="manual-label-subtitle">
                        Beberapa aspek memiliki confidence di bawah 60%. Pilih label manual jika hasil otomatis dirasa belum tepat sebelum menyimpan ke database.
                    </div>
                </div>
                <span class="manual-label-count">${lowConfidence.length} aspek</span>
            </div>
            <div class="manual-label-list">
                ${lowConfidence.map(item => `
                    <div class="manual-label-row">
                        <div>
                            <div class="manual-label-aspect">${escapeHtml(item.aspect)}</div>
                            <div class="manual-label-current">
                                Otomatis: ${escapeHtml(getPredictionLabelText(item.prediction))} &middot; ${(item.confidence * 100).toFixed(1)}%
                            </div>
                        </div>
                        <select class="form-select manual-label-select" data-aspect="${escapeHtml(item.aspect)}" onchange="applyManualPredictionOverride(this)">
                            <option value="auto">Gunakan otomatis</option>
                            <option value="positif">Label manual: Positif</option>
                            <option value="negatif">Label manual: Negatif</option>
                            <option value="netral">Label manual: Netral</option>
                            <option value="none">Label manual: Tidak terdeteksi</option>
                        </select>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

function applyManualPredictionOverride(selectEl) {
    if (!lastPredictionData) return;

    const aspect = selectEl.dataset.aspect;
    const manualValue = selectEl.value;
    const item = lastPredictionData.find(row => row.aspect === aspect);
    if (!item) return;

    if (manualValue === 'auto') {
        item.prediction = item.autoPrediction || item.prediction;
        item.confidence = item.autoConfidence ?? item.confidence;
        item.manual_override = false;
    } else {
        item.prediction = manualValue;
        item.confidence = 1.0;
        item.manual_override = true;
    }

    const row = document.querySelector(`.prediction-row[data-aspect="${CSS.escape(aspect)}"]`);
    if (row) {
        row.className = `prediction-row is-${item.prediction}`;
        const badge = row.querySelector('.prediction-badge-slot');
        if (badge) badge.innerHTML = createBadge(item.prediction);
        const value = row.querySelector('.confidence-value');
        if (value) value.textContent = item.manual_override ? 'Manual' : `${(item.confidence * 100).toFixed(1)}%`;
        const fill = row.querySelector('.confidence-bar-fill');
        if (fill) {
            fill.className = `confidence-bar-fill ${item.manual_override ? 'manual' : item.confidence >= 0.7 ? 'high' : item.confidence >= 0.4 ? 'medium' : 'low'}`;
            fill.style.width = item.manual_override ? '100%' : `${(item.confidence * 100).toFixed(1)}%`;
        }
    }
}

async function runPrediction() {
    const text = document.getElementById('predict-input').value.trim();
    if (!text) {
        alert('Masukkan teks review terlebih dahulu.');
        return;
    }

    const btn = document.getElementById('btn-predict');
    const loading = document.getElementById('predict-loading');
    const resultsEl = document.getElementById('predict-results');

    btn.classList.add('btn-loading');
    btn.disabled = true;
    loading.style.display = 'flex';

    try {
        const res = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });
        const data = await res.json();

        if (data.error) {
            resultsEl.innerHTML = `<div class="empty-state"><div class="empty-state-text" style="color:var(--accent-red);">${data.error}</div></div>`;
            return;
        }

        const detected = data.results.filter(r => r.prediction !== 'none');
        const negatives = detected.filter(r => r.prediction === 'negatif');
        const positives = detected.filter(r => r.prediction === 'positif');
        const lowConfidence = data.results.filter(r => r.confidence < 0.6);
        lastPredictionData = data.results.map(item => ({
            ...item,
            autoPrediction: item.prediction,
            autoConfidence: item.confidence,
            manual_override: false,
        }));

        let html = `
            <div class="prediction-summary">
                <div class="prediction-summary-card">
                    <div class="summary-label">Aspek terdeteksi</div>
                    <div class="summary-value">${detected.length}</div>
                    <div class="summary-note">${detected.length ? escapeHtml(detected.map(r => r.aspect).join(', ')) : 'Tidak ada aspek spesifik yang kuat terdeteksi.'}</div>
                </div>
                <div class="prediction-summary-card ${negatives.length ? 'danger' : 'success'}">
                    <div class="summary-label">Perlu perhatian</div>
                    <div class="summary-value">${negatives.length}</div>
                    <div class="summary-note">${negatives.length ? escapeHtml(negatives.map(r => r.aspect).join(', ')) : 'Tidak ada sentimen negatif dominan pada aspek layanan.'}</div>
                </div>
                <div class="prediction-summary-card">
                    <div class="summary-label">Kekuatan terdeteksi</div>
                    <div class="summary-value">${positives.length}</div>
                    <div class="summary-note">${positives.length ? escapeHtml(positives.map(r => r.aspect).join(', ')) : 'Belum ada aspek positif yang menonjol.'}</div>
                </div>
            </div>
        `;

        if (lowConfidence.length > 0) {
            html += `
                <div class="prediction-warning">
                    Confidence beberapa aspek masih di bawah 60%. Gunakan hasil ini sebagai bantuan analisis, bukan keputusan tunggal.
                </div>
            `;
            html += renderManualLabelingPanel(lowConfidence);
        }

        html += '<div class="prediction-results">';
        data.results.forEach(r => {
            const confPct = (r.confidence * 100).toFixed(1);
            const confClass = r.confidence >= 0.7 ? 'high' : r.confidence >= 0.4 ? 'medium' : 'low';

            html += `<div class="prediction-row is-${r.prediction}" data-aspect="${escapeHtml(r.aspect)}">
                <span class="prediction-aspect">${escapeHtml(r.aspect)}</span>
                <span class="prediction-badge-slot">${createBadge(r.prediction)}</span>
                <div class="confidence-bar">
                    <div class="confidence-bar-track">
                        <div class="confidence-bar-fill ${confClass}" style="width: ${confPct}%"></div>
                    </div>
                </div>
                <span class="confidence-value">${confPct}%</span>
            </div>`;
        });
        html += '</div>';
        resultsEl.innerHTML = html;

        document.getElementById('predict-save-wrapper').style.display = 'block';
    } catch (err) {
        resultsEl.innerHTML = `<div class="empty-state"><div class="empty-state-text" style="color:var(--accent-red);">Error: ${err.message}</div></div>`;
        document.getElementById('predict-save-wrapper').style.display = 'none';
    } finally {
        btn.classList.remove('btn-loading');
        btn.disabled = false;
        loading.style.display = 'none';
    }
}

async function savePrediction() {
    const text = document.getElementById('predict-input').value.trim();
    const hotel = document.getElementById('predict-input-hotel').value;
    const platform = document.getElementById('predict-input-platform').value;
    const date = document.getElementById('predict-input-date').value;

    if (!text || !hotel || !platform || !date || !lastPredictionData) {
        alert('Mohon lengkapi semua form input (Hotel, Platform, Tanggal, dan Teks Review) sebelum menyimpan.');
        return;
    }

    const btn = document.getElementById('btn-save-predict');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<div class="spinner" style="width:14px;height:14px;border-width:2px;display:inline-block;vertical-align:middle;margin-right:5px;"></div> Menyimpan...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/save-prediction', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                hotel: hotel,
                platform: platform,
                date: date,
                predictions: lastPredictionData
            }),
        });
        const data = await res.json();

        if (data.error) {
            alert('Gagal menyimpan: ' + data.error);
        } else {
            alert(`Berhasil disimpan! Data telah ditambahkan ke database dengan ID ${data.review_id || 'baru'}.`);
            // Reset form
            document.getElementById('predict-input').value = '';
            document.getElementById('predict-input-hotel').value = '';
            document.getElementById('predict-input-platform').value = '';
            document.getElementById('predict-input-date').value = '';
            document.getElementById('predict-results').innerHTML = '<div class="empty-state"><div class="empty-state-icon">AI</div><div class="empty-state-text">Masukkan review dan klik "Prediksi Sentimen" untuk melihat hasilnya.</div></div>';
            document.getElementById('predict-save-wrapper').style.display = 'none';
            lastPredictionData = null;
            if (CAN_VIEW_ACTIVITY_LOG) {
                loadActivityLog();
            }
        }
    } catch (err) {
        alert('Terjadi kesalahan: ' + err.message);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// ========================================
// PAGE: PERFORMANCE
// ========================================
async function loadPerformance() {
    const data = await fetchAPI('/api/model-performance');

    // Metric cards
    const metricsEl = document.getElementById('perf-metrics');
    const o = data.overall;
    metricsEl.innerHTML = `
        <div class="metric-card" style="border-left-color: var(--accent-green);">
            <div class="metric-value">${(o.accuracy * 100).toFixed(1)}%</div>
            <div class="metric-label">Akurasi Keseluruhan</div>
        </div>
        <div class="metric-card" style="border-left-color: var(--accent-blue);">
            <div class="metric-value">${(data.total_reviews || 0).toLocaleString('id-ID')}</div>
            <div class="metric-label">Total Ulasan yang Dipelajari</div>
        </div>
        <div class="metric-card" style="border-left-color: var(--accent-purple);">
            <div class="metric-value">7</div>
            <div class="metric-label">Area Layanan Dianalisis</div>
        </div>
    `;

    // Per-aspect chart (simplified to just Accuracy)
    destroyChart('perf-aspect');
    const ctx = document.getElementById('chart-perf-aspect').getContext('2d');
    const perAspect = data.per_aspect;
    charts['perf-aspect'] = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ASPECTS,
            datasets: [
                {
                    label: 'Akurasi per Aspek (%)',
                    data: ASPECTS.map(a => {
                        // acc dari backend berupa fraksi 0..1. Konversi ke persen,
                        // lalu clamp 0..100 agar radar tidak meledak bila data anomali/kosong.
                        const pct = (perAspect[a]?.acc || 0) * 100;
                        return Math.max(0, Math.min(100, Number(pct.toFixed(1))));
                    }),
                    borderColor: COLORS.blue,
                    backgroundColor: COLORS.blue + '33',
                    pointBackgroundColor: COLORS.blue,
                    borderWidth: 2,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    min: 60,
                    max: 100,
                    grid: { color: COLORS.grid },
                    angleLines: { color: COLORS.grid },
                    pointLabels: { color: COLORS.textPrimary, font: { size: 13, weight: 600 } },
                    ticks: { color: COLORS.muted, backdropColor: 'transparent', stepSize: 10 },
                }
            },
            plugins: { legend: { position: 'top' } },
        }
    });

    // Notes
    const notesEl = document.getElementById('perf-notes');
    if (notesEl) {
        notesEl.innerHTML = `
            <div class="doc-callout">
                <h3>Cara membaca grafik ini</h3>
                <p>Grafik menunjukkan seberapa sering prediksi model sesuai dengan label yang sudah diperiksa manual, untuk masing-masing area layanan. Angka diukur dari data uji yang tidak ikut dipakai saat melatih model, sehingga mencerminkan performa pada ulasan yang benar-benar baru bagi model.</p>
            </div>
            <div class="about-block" style="border-left-color: var(--accent-green);">
                <h3>Yang perlu dipahami</h3>
                <ul>
                    <li>Akurasi di atas 85% menunjukkan prediksi model cukup dapat diandalkan untuk area tersebut.</li>
                    <li>Wajar bila angkanya berbeda antar area. Area yang lebih jarang disebut tamu, seperti Harga, biasanya punya contoh data lebih sedikit sehingga hasilnya bisa bervariasi.</li>
                    <li>Angka ini adalah rata-rata pada data historis. Performa pada ulasan baru bisa sedikit berbeda.</li>
                </ul>
            </div>
        `;
    }
}

// ========================================
// PAGE: STAFF MANAGEMENT
// ========================================
async function loadStaffManagement() {
    if (!IS_ADMIN) return;

    const wrapper = document.getElementById('staff-list');
    if (!wrapper) return;

    wrapper.innerHTML = '<div class="empty-state"><div class="empty-state-text">Memuat daftar staf OTA...</div></div>';
    const data = await fetchAPI('/api/staff-ota');
    if (data.error) {
        wrapper.innerHTML = `<div class="empty-state"><div class="empty-state-text">${escapeHtml(data.error)}</div></div>`;
        return;
    }

    const staff = data.staff || [];
    if (!staff.length) {
        wrapper.innerHTML = '<div class="empty-state"><div class="empty-state-text">Belum ada akun Staf OTA.</div></div>';
        return;
    }

    wrapper.innerHTML = `
        <table class="data-table staff-table">
            <thead>
                <tr>
                    <th>Nama</th>
                    <th>ID Pengguna</th>
                    <th>Role</th>
                    <th>Aksi</th>
                </tr>
            </thead>
            <tbody>
                ${staff.map(item => `
                    <tr>
                        <td><strong>${escapeHtml(item.name || '-')}</strong></td>
                        <td><code>${escapeHtml(item.username || '-')}</code></td>
                        <td><span class="badge badge-netral">${escapeHtml(item.role_label || 'Staf OTA')}</span></td>
                        <td>
                            <button class="btn btn-danger btn-sm" type="button" data-username="${escapeHtml(item.username)}" onclick="deleteStaffOta(this.dataset.username)">Hapus</button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

function setStaffMessage(message, type = 'info') {
    const box = document.getElementById('staff-message');
    if (!box) return;
    box.textContent = message || '';
    box.className = `staff-message ${type}`;
}

async function createStaffOta(event) {
    event.preventDefault();
    if (!IS_ADMIN) return;

    const name = document.getElementById('staff-name')?.value.trim() || '';
    const username = document.getElementById('staff-username')?.value.trim() || '';
    const password = document.getElementById('staff-password')?.value.trim() || '';
    const button = document.getElementById('btn-create-staff');

    if (!name || !username || !password) {
        setStaffMessage('Nama, ID pengguna, dan password wajib diisi.', 'error');
        return;
    }

    const originalText = button?.textContent || 'Tambah Staf OTA';
    if (button) {
        button.disabled = true;
        button.textContent = 'Menyimpan...';
    }
    setStaffMessage('', 'info');

    try {
        const res = await fetch('/api/staff-ota', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, username, password }),
        });
        const data = await res.json();

        if (!res.ok || data.error) {
            setStaffMessage(data.error || 'Gagal menambahkan staf OTA.', 'error');
            return;
        }

        document.getElementById('staff-form')?.reset();
        setStaffMessage(`Staf OTA ${data.staff?.username || username} berhasil ditambahkan.`, 'success');
        await loadStaffManagement();
    } catch (err) {
        setStaffMessage('Terjadi kesalahan: ' + err.message, 'error');
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = originalText;
        }
    }
}

async function deleteStaffOta(username) {
    if (!IS_ADMIN || !username) return;

    const ok = confirm(`Hapus akun Staf OTA "${username}"? Akun ini tidak bisa login lagi setelah dihapus.`);
    if (!ok) return;

    try {
        const res = await fetch(`/api/staff-ota/${encodeURIComponent(username)}`, {
            method: 'DELETE',
        });
        const data = await res.json();

        if (!res.ok || data.error) {
            setStaffMessage(data.error || 'Gagal menghapus staf OTA.', 'error');
            return;
        }

        setStaffMessage(`Staf OTA ${username} berhasil dihapus.`, 'success');
        await loadStaffManagement();
    } catch (err) {
        setStaffMessage('Terjadi kesalahan: ' + err.message, 'error');
    }
}

// ========================================
// INIT
// ========================================
const FS_DEFAULTS = {
    heading: 100, text: 100, weight: 0, line: 100, ui: 100,
    contrast: false, readwidth: false, tableroomy: false,
};
const FS_PRESETS = {
    kecil:  { heading: 95,  text: 90,  line: 100 },
    normal: { heading: 100, text: 100, line: 100 },
    besar:  { heading: 115, text: 120, line: 120 },
    ekstra: { heading: 130, text: 145, line: 140 },
};
const FS_WEIGHT_LABELS = ['Normal', 'Tebal', 'Sangat Tebal'];

function getFontState() {
    return {
        heading: parseInt(localStorage.getItem('absa-fs-heading') || FS_DEFAULTS.heading, 10),
        text: parseInt(localStorage.getItem('absa-fs-text') || FS_DEFAULTS.text, 10),
        weight: parseInt(localStorage.getItem('absa-fs-weight') || FS_DEFAULTS.weight, 10),
        line: parseInt(localStorage.getItem('absa-fs-line') || FS_DEFAULTS.line, 10),
        ui: parseInt(localStorage.getItem('absa-fs-ui') || FS_DEFAULTS.ui, 10),
        contrast: localStorage.getItem('absa-fs-contrast') === '1',
        readwidth: localStorage.getItem('absa-fs-readwidth') === '1',
        tableroomy: localStorage.getItem('absa-fs-tableroomy') === '1',
    };
}

function applyFontState(s) {
    const root = document.documentElement;
    root.style.setProperty('--fs-heading-scale', s.heading / 100);
    root.style.setProperty('--fs-text-scale', s.text / 100);
    root.style.setProperty('--fs-line-scale', s.line / 100);
    root.style.setProperty('--fs-ui-scale', s.ui / 100);

    const body = document.body;
    body.dataset.fsWeight = String(s.weight);
    body.dataset.fsContrast = s.contrast ? 'on' : 'off';
    body.dataset.fsReadwidth = s.readwidth ? 'on' : 'off';
    body.dataset.fsTableroomy = s.tableroomy ? 'on' : 'off';

    // Update label nilai
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('fs-heading-value', `${s.heading}%`);
    set('fs-text-value', `${s.text}%`);
    set('fs-weight-value', FS_WEIGHT_LABELS[s.weight] || 'Normal');
    set('fs-lineheight-value', `${s.line}%`);
    set('fs-ui-value', `${s.ui}%`);
}

function saveFontState(s) {
    localStorage.setItem('absa-fs-heading', s.heading);
    localStorage.setItem('absa-fs-text', s.text);
    localStorage.setItem('absa-fs-weight', s.weight);
    localStorage.setItem('absa-fs-line', s.line);
    localStorage.setItem('absa-fs-ui', s.ui);
    localStorage.setItem('absa-fs-contrast', s.contrast ? '1' : '0');
    localStorage.setItem('absa-fs-readwidth', s.readwidth ? '1' : '0');
    localStorage.setItem('absa-fs-tableroomy', s.tableroomy ? '1' : '0');
}

function syncFontControls(s) {
    const setVal = (id, v) => { const el = document.getElementById(id); if (el) el.value = v; };
    const setChk = (id, v) => { const el = document.getElementById(id); if (el) el.checked = v; };
    setVal('fs-heading', s.heading);
    setVal('fs-text', s.text);
    setVal('fs-weight', s.weight);
    setVal('fs-lineheight', s.line);
    setVal('fs-ui', s.ui);
    setChk('fs-contrast', s.contrast);
    setChk('fs-readwidth', s.readwidth);
    setChk('fs-tableroomy', s.tableroomy);
    // Tandai preset aktif jika cocok
    document.querySelectorAll('.fs-preset-btn').forEach(btn => {
        const p = FS_PRESETS[btn.dataset.preset];
        const match = p && p.heading === s.heading && p.text === s.text && p.line === s.line;
        btn.classList.toggle('active', !!match);
    });
    // Tandai tema aktif
    const theme = document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
    document.querySelectorAll('.fs-theme-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.themeChoice === theme);
    });
}

function initFontSettings() {
    const toggle = document.getElementById('font-settings-toggle');
    const panel = document.getElementById('font-settings-panel');
    if (!panel) return;

    let state = getFontState();
    applyFontState(state);
    syncFontControls(state);

    const update = (changes) => {
        state = { ...state, ...changes };
        applyFontState(state);
        saveFontState(state);
        syncFontControls(state);
    };

    document.getElementById('fs-heading')?.addEventListener('input', e => update({ heading: parseInt(e.target.value, 10) }));
    document.getElementById('fs-text')?.addEventListener('input', e => update({ text: parseInt(e.target.value, 10) }));
    document.getElementById('fs-weight')?.addEventListener('input', e => update({ weight: parseInt(e.target.value, 10) }));
    document.getElementById('fs-lineheight')?.addEventListener('input', e => update({ line: parseInt(e.target.value, 10) }));
    document.getElementById('fs-ui')?.addEventListener('input', e => update({ ui: parseInt(e.target.value, 10) }));
    document.getElementById('fs-contrast')?.addEventListener('change', e => update({ contrast: e.target.checked }));
    document.getElementById('fs-readwidth')?.addEventListener('change', e => update({ readwidth: e.target.checked }));
    document.getElementById('fs-tableroomy')?.addEventListener('change', e => update({ tableroomy: e.target.checked }));

    document.querySelectorAll('.fs-preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const p = FS_PRESETS[btn.dataset.preset];
            if (p) update({ heading: p.heading, text: p.text, line: p.line });
        });
    });

    document.querySelectorAll('.fs-theme-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            applyTheme(btn.dataset.themeChoice);
            syncFontControls(state);
            reloadActivePage();
        });
    });

    document.getElementById('fs-reset')?.addEventListener('click', () => {
        update({ ...FS_DEFAULTS });
    });

    toggle?.addEventListener('click', (e) => {
        e.stopPropagation();
        panel.hidden = !panel.hidden;
    });
    document.addEventListener('click', (e) => {
        if (panel && !panel.hidden && !panel.contains(e.target) && e.target !== toggle && !toggle.contains(e.target)) {
            panel.hidden = true;
        }
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    const themeFromUrl = new URLSearchParams(window.location.search).get('theme');
    applyTheme(themeFromUrl || localStorage.getItem('absa-dashboard-theme') || 'dark', !themeFromUrl);
    document.getElementById('theme-toggle')?.addEventListener('click', () => {
        const currentTheme = document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
        applyTheme(currentTheme === 'light' ? 'dark' : 'light');
        reloadActivePage();
    });

    checkAuth();
    await initFilters();
    const initialPage = document.querySelector('.nav-item.active')?.dataset.page || getDefaultPage();
    navigateTo(initialPage);

    initFontSettings();

    // Responsive menu button
    const mediaQuery = window.matchMedia('(max-width: 900px)');
    function handleMobile(e) {
        document.getElementById('btn-mobile-menu').style.display = e.matches ? 'inline-flex' : 'none';
    }
    mediaQuery.addEventListener('change', handleMobile);
    handleMobile(mediaQuery);
});
