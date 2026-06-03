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
    positif: { label: 'Positif', emoji: '🙂' },
    negatif: { label: 'Negatif', emoji: '🙁' },
    netral: { label: 'Netral', emoji: '😐' },
    none: { label: 'Tidak terdeteksi', emoji: '—' },
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
};
const CURRENT_USER = window.ABSA_USER || {};
document.title = 'Dashboard ABSA - Hotel Santika';

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
    if (icon) icon.textContent = nextTheme === 'light' ? 'Light' : 'Dark';
    if (text) text.textContent = nextTheme === 'light' ? 'Terang' : 'Gelap';
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
    }
}

refreshThemeColors();

// ========================================
// NAVIGATION
// ========================================
const PAGE_TITLES = {
    'overview': ['Overview', 'Ringkasan analisis sentimen ulasan Hotel Santika'],
    'aspect': ['Analisis Aspek', 'Distribusi sentimen untuk setiap aspek layanan'],
    'hotel-platform': ['Hotel & Platform', 'Perbandingan sentimen antar hotel dan platform OTA'],
    'trend': ['Tren Waktu', 'Perubahan sentimen dari waktu ke waktu'],
    'reviews': ['Review Explorer', 'Jelajahi dan cari review secara detail'],
    'predict': ['Prediksi Manual', 'Analisis sentimen review baru menggunakan IndoBERT'],
    'performance': ['Performa Model', 'Metrik evaluasi model IndoBERT fine-tune'],
    'about': ['Tentang Sistem', 'Informasi tentang sistem dashboard ABSA'],
};

function applyAccessControls() {
    if (CURRENT_USER.role !== 'admin') {
        document.querySelectorAll('.admin-only').forEach(el => el.remove());
    }
}

applyAccessControls();

document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
        const page = item.dataset.page;
        navigateTo(page);
    });
});

function navigateTo(page) {
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
        case 'reviews': loadReviews(1); break;
        case 'performance': loadPerformance(); break;
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
    const meta = SENTIMENT_META[label] || { label, emoji: '' };
    return `<span class="badge badge-${label}">${meta.label}</span>`;
}

function sentimentLabel(key, withPercent = false) {
    const meta = SENTIMENT_META[key] || { label: key, emoji: '' };
    return `${meta.label}${withPercent ? ' %' : ''}`;
}

function iconSvg(name) {
    return `<svg class="icon-svg" aria-hidden="true"><use href="#icon-${name}"></use></svg>`;
}

function pct(value) {
    return Number.isFinite(value) ? `${value.toFixed(1)}%` : '0.0%';
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

function getOverviewDateParams(rangeKey = appState.overviewRange) {
    const maxDateText = appState.dateRange.max;
    if (!maxDateText || rangeKey === 'all') {
        return { params: {}, label: 'Seluruh rentang data' };
    }

    const maxDate = new Date(`${maxDateText}T00:00:00`);
    let startDate = null;
    let endDate = maxDate;
    let label = 'Seluruh rentang data';

    if (rangeKey === '7d') {
        startDate = addDays(maxDate, -6);
        label = '7 hari terakhir pada dataset';
    } else if (rangeKey === '30d') {
        startDate = addDays(maxDate, -29);
        label = '30 hari terakhir pada dataset';
    } else if (rangeKey === '3m') {
        startDate = addMonths(maxDate, -3);
        label = '3 bulan terakhir pada dataset';
    } else if (rangeKey === '6m') {
        startDate = addMonths(maxDate, -6);
        label = '6 bulan terakhir pada dataset';
    } else if (rangeKey === '1y') {
        startDate = addMonths(maxDate, -12);
        label = '1 tahun terakhir pada dataset';
    } else if (/^\d{4}$/.test(rangeKey)) {
        startDate = new Date(`${rangeKey}-01-01T00:00:00`);
        endDate = new Date(`${rangeKey}-12-31T00:00:00`);
        label = `Tahun ${rangeKey}`;
    }

    const params = {};
    if (startDate) params.date_from = toDateInputValue(startDate);
    if (endDate) params.date_to = toDateInputValue(endDate);
    return { params, label };
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

    const rows = getAspectRows(data.aspect_stats || {});
    const topNeg = [...rows].sort((a, b) => b.negatif - a.negatif);
    const topRisk = [...rows].sort((a, b) => b.negativeRate - a.negativeRate);
    const topPos = [...rows].sort((a, b) => b.positif - a.positif);
    const priority = topNeg.slice(0, 3);
    const mainNeg = topNeg[0] || { aspect: '-', negatif: 0, negativeRate: 0 };
    const secondNeg = topNeg[1] || { aspect: '-', negatif: 0, negativeRate: 0 };
    const risk = topRisk[0] || mainNeg;
    const strength = topPos[0] || { aspect: '-', positif: 0, positiveRate: 0 };

    insightEl.innerHTML = `
        <div class="insight-card insight-primary">
            <div class="insight-eyebrow">Cerita utama</div>
            <h2>${mainNeg.aspect} dan ${secondNeg.aspect} adalah sumber keluhan terbesar.</h2>
            <p>
                Dari ${data.total_reviews.toLocaleString()} review, sentimen positif masih dominan (${posRate}%).
                Namun keluhan paling banyak terkonsentrasi pada aspek ${mainNeg.aspect.toLowerCase()}
                (${mainNeg.negatif.toLocaleString()} sentimen negatif) dan ${secondNeg.aspect.toLowerCase()}
                (${secondNeg.negatif.toLocaleString()} sentimen negatif).
            </p>
        </div>
        <div class="insight-card">
            <div class="insight-eyebrow">Prioritas perbaikan</div>
            <div class="priority-list">
                ${priority.map((row, index) => `
                    <div class="priority-row">
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
        <div class="insight-card">
            <div class="insight-eyebrow">Risiko tertinggi</div>
            <div class="insight-metric danger">${risk.aspect}</div>
            <p>${pct(risk.negativeRate)} sentimen pada aspek ini bernada negatif, sehingga perlu dicek bukan hanya dari jumlah keluhan tetapi juga proporsinya.</p>
        </div>
        <div class="insight-card">
            <div class="insight-eyebrow">Kekuatan utama</div>
            <div class="insight-metric success">${strength.aspect}</div>
            <p>${strength.positif.toLocaleString()} sentimen positif muncul pada aspek ini. Insight ini bisa dipakai sebagai kekuatan komunikasi layanan.</p>
        </div>
    `;
}

function getFilterValues(prefix) {
    const hotel = document.getElementById(`${prefix}-filter-hotel`)?.value || 'all';
    const platform = document.getElementById(`${prefix}-filter-platform`)?.value || 'all';
    return { hotel, platform };
}

// ========================================
// INIT: LOAD FILTERS
// ========================================
async function initFilters() {
    const data = await fetchAPI('/api/filters');

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
            select.innerHTML += `<option value="${p}">${p}</option>`;
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
        ['trend-date-from', 'trend-date-to'].forEach(id => {
            const input = document.getElementById(id);
            if (input) {
                input.min = data.date_range.min || '';
                input.max = data.date_range.max || '';
            }
        });
    }
}

// ========================================
// PAGE: OVERVIEW
// ========================================
async function loadOverview() {
    const { params, label } = getOverviewDateParams();
    const data = await fetchAPI('/api/overview', params);
    if (data.error) return;

    // Stat cards
    const statsEl = document.getElementById('overview-stats');
    const totalSentiment = data.sentiment_counts.positif + data.sentiment_counts.negatif + data.sentiment_counts.netral;
    const posRate = totalSentiment > 0 ? ((data.sentiment_counts.positif / totalSentiment) * 100).toFixed(1) : 0;

    const dateText = params.date_from || params.date_to
            ? `${params.date_from || appState.dateRange.min} sampai ${params.date_to || appState.dateRange.max}`
            : `${appState.dateRange.min || '-'} sampai ${appState.dateRange.max || '-'}`;
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
}

// ========================================
// PAGE: ASPECT ANALYSIS
// ========================================
async function loadAspectAnalysis() {
    const { hotel, platform } = getFilterValues('aspect');
    const aspect = document.getElementById('aspect-filter-aspect')?.value || 'all';
    const sentiment = document.getElementById('aspect-filter-sentiment')?.value || 'all';

    const data = await fetchAPI('/api/aspect-analysis', { hotel, platform, aspect, sentiment });
    if (data.error) return;

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
        let html = '<table class="data-table"><thead><tr><th>ID</th><th>Hotel</th><th>Platform</th><th>Tanggal</th><th>Review</th><th>Sentimen</th></tr></thead><tbody>';
        examples[aspect].forEach(r => {
            const predCol = `pred_${aspect}`;
            const sent = r[predCol] || 'none';
            html += `<tr>
                <td>${r.ID_Review || ''}</td>
                <td>${(r.Nama_Hotel || '').replace('Hotel Santika ', '')}</td>
                <td>${r.Platform || ''}</td>
                <td>${r.Review_Date || ''}</td>
                <td class="text-review">${r.Text_Review || ''}</td>
                <td>${createBadge(sent)}</td>
            </tr>`;
        });
        html += '</tbody></table>';
        exTable.innerHTML = html;
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
            labels: platforms,
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
async function loadTrend() {
    const { hotel, platform } = getFilterValues('trend');
    const aspect = document.getElementById('trend-filter-aspect')?.value || 'all';
    const granularity = document.getElementById('trend-granularity')?.value || 'year';
    const dateFrom = document.getElementById('trend-date-from')?.value || '';
    const dateTo = document.getElementById('trend-date-to')?.value || '';

    const data = await fetchAPI('/api/trend', {
        hotel,
        platform,
        trend_aspect: aspect,
        granularity,
        date_from: dateFrom,
        date_to: dateTo,
    });
    if (data.error) return;

    destroyChart('trend');
    const ctx = document.getElementById('chart-trend').getContext('2d');
    const periods = data.periods;
    const posData = periods.map(p => data.trend_data[p]?.positif || 0);
    const negData = periods.map(p => data.trend_data[p]?.negatif || 0);
    const netData = periods.map(p => data.trend_data[p]?.netral || 0);
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
        summary.textContent = `${periods.length} periode ${granularityLabels[data.granularity] || 'tahunan'} - ${data.total_reviews.toLocaleString()} review - ${data.total_sentiment_points.toLocaleString()} sentimen aspek - ${aspectLabel} - ${rangeLabel}`;
    }

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
            plugins: { legend: { position: 'top' } },
            scales: {
                x: { grid: { color: COLORS.grid } },
                y: { grid: { color: COLORS.grid }, beginAtZero: true },
            }
        }
    });
}

function resetTrendFilters() {
    document.getElementById('trend-filter-hotel').value = 'all';
    document.getElementById('trend-filter-platform').value = 'all';
    document.getElementById('trend-filter-aspect').value = 'all';
    document.getElementById('trend-granularity').value = 'year';
    document.getElementById('trend-date-from').value = '';
    document.getElementById('trend-date-to').value = '';
    loadTrend();
}

// ========================================
// PAGE: REVIEW EXPLORER
// ========================================
async function loadReviews(page = 1) {
    const { hotel, platform } = getFilterValues('review');
    const aspect = document.getElementById('review-filter-aspect')?.value || 'all';
    const sentiment = document.getElementById('review-filter-sentiment')?.value || 'all';
    const keyword = document.getElementById('review-filter-keyword')?.value || '';

    const data = await fetchAPI('/api/reviews', { hotel, platform, aspect, sentiment, keyword, page, per_page: 25 });
    if (data.error) return;

    // Count
    document.getElementById('review-count').textContent = `${data.total.toLocaleString()} review ditemukan`;

    // Table body
    const tbody = document.getElementById('reviews-tbody');
    if (data.reviews.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12" class="empty-state"><div class="empty-state-text">Tidak ada review ditemukan.</div></td></tr>';
    } else {
        tbody.innerHTML = data.reviews.map(r => {
            const aspectCells = ASPECTS.map(a => {
                const pred = r[`pred_${a}`] || 'none';
                return `<td>${createBadge(pred)}</td>`;
            }).join('');
            return `<tr>
                <td>${r.ID_Review || ''}</td>
                <td style="white-space:nowrap;">${(r.Nama_Hotel || '').replace('Hotel Santika ', '')}</td>
                <td>${r.Platform || ''}</td>
                <td style="white-space:nowrap;">${r.Review_Date || ''}</td>
                <td class="text-review">${r.Text_Review || ''}</td>
                ${aspectCells}
            </tr>`;
        }).join('');
    }

    // Pagination
    const pagEl = document.getElementById('reviews-pagination');
    if (data.total_pages <= 1) {
        pagEl.innerHTML = '';
        return;
    }

    let pagHtml = '';
    pagHtml += `<button class="pagination-btn" ${page <= 1 ? 'disabled' : ''} onclick="loadReviews(${page - 1})">&laquo;</button>`;

    const maxBtns = 7;
    let start = Math.max(1, page - Math.floor(maxBtns / 2));
    let end = Math.min(data.total_pages, start + maxBtns - 1);
    if (end - start < maxBtns - 1) start = Math.max(1, end - maxBtns + 1);

    for (let i = start; i <= end; i++) {
        pagHtml += `<button class="pagination-btn ${i === page ? 'active' : ''}" onclick="loadReviews(${i})">${i}</button>`;
    }

    pagHtml += `<span class="pagination-info">Hal ${page}/${data.total_pages}</span>`;
    pagHtml += `<button class="pagination-btn" ${page >= data.total_pages ? 'disabled' : ''} onclick="loadReviews(${page + 1})">&raquo;</button>`;
    pagEl.innerHTML = pagHtml;
}

function exportReviews() {
    const { hotel, platform } = getFilterValues('review');
    const aspect = document.getElementById('review-filter-aspect')?.value || 'all';
    const sentiment = document.getElementById('review-filter-sentiment')?.value || 'all';
    const keyword = document.getElementById('review-filter-keyword')?.value || '';

    const params = new URLSearchParams();
    if (hotel && hotel !== 'all') params.set('hotel', hotel);
    if (platform && platform !== 'all') params.set('platform', platform);
    if (aspect && aspect !== 'all') params.set('aspect', aspect);
    if (sentiment && sentiment !== 'all') params.set('sentiment', sentiment);
    if (keyword) params.set('keyword', keyword);

    window.open(`/api/export?${params.toString()}`, '_blank');
}

// ========================================
// PAGE: PREDICTION
// ========================================
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

        let html = '<div class="prediction-results">';
        data.results.forEach(r => {
            const confPct = (r.confidence * 100).toFixed(1);
            const confClass = r.confidence >= 0.7 ? 'high' : r.confidence >= 0.4 ? 'medium' : 'low';
            const isActive = r.prediction !== 'none';

            html += `<div class="prediction-row" style="${isActive ? 'border-color: var(--border-default);' : ''}">
                <span class="prediction-aspect">${r.aspect}</span>
                ${createBadge(r.prediction)}
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
    } catch (err) {
        resultsEl.innerHTML = `<div class="empty-state"><div class="empty-state-text" style="color:var(--accent-red);">Error: ${err.message}</div></div>`;
    } finally {
        btn.classList.remove('btn-loading');
        btn.disabled = false;
        loading.style.display = 'none';
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
        <div class="metric-card">
            <div class="metric-value">${(o.macro_f1 * 100).toFixed(1)}%</div>
            <div class="metric-label">Macro F1</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">${(o.accuracy * 100).toFixed(1)}%</div>
            <div class="metric-label">Accuracy</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">${(o.weighted_f1 * 100).toFixed(1)}%</div>
            <div class="metric-label">Weighted F1</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">${(o.non_none_f1 * 100).toFixed(1)}%</div>
            <div class="metric-label">Non-none F1</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">${(o.aspect_detection_f1 * 100).toFixed(1)}%</div>
            <div class="metric-label">Aspect Detection F1</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">${(o.false_aspect_rate * 100).toFixed(1)}%</div>
            <div class="metric-label">False Aspect Rate</div>
        </div>
    `;

    // Per-aspect chart
    destroyChart('perf-aspect');
    const ctx = document.getElementById('chart-perf-aspect').getContext('2d');
    const perAspect = data.per_aspect;
    charts['perf-aspect'] = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ASPECTS,
            datasets: [
                {
                    label: 'Macro F1',
                    data: ASPECTS.map(a => ((perAspect[a]?.macro_f1 || 0) * 100).toFixed(1)),
                    borderColor: COLORS.blue,
                    backgroundColor: COLORS.blue + '22',
                    pointBackgroundColor: COLORS.blue,
                    borderWidth: 2,
                },
                {
                    label: 'Non-none F1',
                    data: ASPECTS.map(a => ((perAspect[a]?.non_none_macro_f1 || 0) * 100).toFixed(1)),
                    borderColor: COLORS.purple,
                    backgroundColor: COLORS.purple + '22',
                    pointBackgroundColor: COLORS.purple,
                    borderWidth: 2,
                },
                {
                    label: 'Aspect Detection F1',
                    data: ASPECTS.map(a => ((perAspect[a]?.aspect_detection_f1 || 0) * 100).toFixed(1)),
                    borderColor: COLORS.positif,
                    backgroundColor: COLORS.positif + '22',
                    pointBackgroundColor: COLORS.positif,
                    borderWidth: 2,
                },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: COLORS.grid },
                    angleLines: { color: COLORS.grid },
                    pointLabels: { color: COLORS.textPrimary, font: { size: 12, weight: 600 } },
                    ticks: { color: COLORS.muted, backdropColor: 'transparent' },
                }
            },
            plugins: { legend: { position: 'top' } },
        }
    });

    // Per-aspect table
    const tableEl = document.getElementById('perf-table-wrapper');
    let html = '<table class="data-table"><thead><tr><th>Aspek</th><th>Macro F1</th><th>Weighted F1</th><th>Accuracy</th><th>Non-none F1</th><th>Aspect Det. F1</th><th>False Aspect</th></tr></thead><tbody>';
    ASPECTS.forEach(a => {
        const p = perAspect[a] || {};
        html += `<tr>
            <td><strong>${a}</strong></td>
            <td>${((p.macro_f1 || 0) * 100).toFixed(1)}%</td>
            <td>${((p.weighted_f1 || 0) * 100).toFixed(1)}%</td>
            <td>${((p.acc || 0) * 100).toFixed(1)}%</td>
            <td>${((p.non_none_macro_f1 || 0) * 100).toFixed(1)}%</td>
            <td>${((p.aspect_detection_f1 || 0) * 100).toFixed(1)}%</td>
            <td>${((p.false_aspect_rate || 0) * 100).toFixed(1)}%</td>
        </tr>`;
    });
    html += '</tbody></table>';
    tableEl.innerHTML = html;

    // Model config
    const cfgEl = document.getElementById('perf-config');
    const cfg = data.model_config;
    cfgEl.innerHTML = `
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;">
            <div class="about-block" style="margin-bottom:0;"><h3>Base Model</h3><p>${cfg.model_name}</p></div>
            <div class="about-block" style="margin-bottom:0;"><h3>Max Length</h3><p>${cfg.max_len} tokens</p></div>
            <div class="about-block" style="margin-bottom:0;"><h3>Learning Rate</h3><p>${cfg.learning_rate}</p></div>
            <div class="about-block" style="margin-bottom:0;"><h3>Batch Size</h3><p>${cfg.batch_size}</p></div>
            <div class="about-block" style="margin-bottom:0;"><h3>Epochs</h3><p>${cfg.epochs}</p></div>
            <div class="about-block" style="margin-bottom:0;"><h3>Dropout</h3><p>${cfg.dropout}</p></div>
            <div class="about-block" style="margin-bottom:0;"><h3>Class Weight</h3><p>${cfg.class_weight ? 'Ya (sqrt_capped)' : 'Tidak'}</p></div>
            <div class="about-block" style="margin-bottom:0;"><h3>Label Smoothing</h3><p>${cfg.label_smoothing}</p></div>
        </div>
    `;
}

// ========================================
// INIT
// ========================================
document.addEventListener('DOMContentLoaded', async () => {
    const themeFromUrl = new URLSearchParams(window.location.search).get('theme');
    applyTheme(themeFromUrl || localStorage.getItem('absa-dashboard-theme') || 'dark', !themeFromUrl);
    document.getElementById('theme-toggle')?.addEventListener('click', () => {
        const currentTheme = document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
        applyTheme(currentTheme === 'light' ? 'dark' : 'light');
        reloadActivePage();
    });

    await initFilters();
    loadOverview();

    // Responsive menu button
    const mediaQuery = window.matchMedia('(max-width: 900px)');
    function handleMobile(e) {
        document.getElementById('btn-mobile-menu').style.display = e.matches ? 'inline-flex' : 'none';
    }
    mediaQuery.addEventListener('change', handleMobile);
    handleMobile(mediaQuery);
});
