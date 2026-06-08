// ============================================================
// Agoda Hotel Review Scraper - JavaScript Console Script
// ============================================================
// Cara pakai:
//   1. Buka halaman hotel di agoda.com
//      Contoh: https://www.agoda.com/hotel-santika-bandung/hotel/bandung-id.html?...
//   2. Scroll ke bawah sampai bagian review terlihat
//   3. Tekan F12 -> tab Console
//   4. Paste seluruh kode ini -> Enter
//   5. Tunggu sampai selesai -> CSV otomatis terdownload
//
// CATATAN PENTING:
//   - Script ini HANYA mengambil review ORIGINAL (bahasa asli reviewer).
//   - Review yang diterjemahkan AI ke bahasa Inggris secara otomatis diabaikan.
//   - Di Agoda, elemen tanpa class "--translation" justru berisi
//     terjemahan AI (bahasa Inggris), sedangkan elemen dengan
//     class "--translation" berisi teks ORIGINAL dari reviewer.
//     Script ini menangani logika terbalik tersebut.
// ============================================================

(async function () {
    'use strict';

    // ====== KONFIGURASI ======
    const CONFIG = {
        MAX_PAGES: 999,            // Maksimal halaman yang di-scrape (999 = semua)
        CLICK_DELAY: 1500,         // Delay setelah klik (ms)
        PAGE_LOAD_DELAY: 3000,     // Delay setelah pindah halaman (ms)
        SCROLL_DELAY: 300,         // Delay saat scroll (ms)
    };

    const allReviews = [];
    let currentPage = 1;

    // ====== UTILITY FUNCTIONS ======

    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    function log(msg) {
        console.log(`%c[Agoda Scraper] ${msg}`, 'color: #6A1B9A; font-weight: bold;');
    }

    function warn(msg) {
        console.warn(`[Agoda Scraper] ${msg}`);
    }

    function logSuccess(msg) {
        console.log(`%c[Agoda Scraper] ✓ ${msg}`, 'color: #2E7D32; font-weight: bold;');
    }

    function qsa(selector, parent = document) {
        return Array.from(parent.querySelectorAll(selector));
    }

    function qs(selector, parent = document) {
        return parent.querySelector(selector);
    }

    function cleanText(text) {
        return String(text || '')
            .replace(/\s+/g, ' ')
            .trim();
    }

    // ====== REVIEW DATA EXTRACTION ======

    /**
     * Menentukan teks review ORIGINAL (bukan terjemahan AI).
     *
     * Logika Agoda:
     * - `.Review-comment-body[data-selenium]` (tanpa --translation)
     *    → Ini adalah terjemahan AI ke bahasa Inggris (BUKAN yang kita mau).
     * - `.Review-comment-body--translation[data-selenium=translate-section]`
     *    → Ini adalah teks ORIGINAL dari reviewer (YANG KITA MAU).
     *
     * Jika ada elemen --translation, gunakan itu (original).
     * Jika tidak ada (artinya review memang ditulis dalam bahasa Inggris,
     * tidak ada terjemahan), gunakan elemen tanpa --translation.
     */
    function getOriginalReviewContent(reviewCard) {
        // Cek apakah ada section terjemahan (yang sebenarnya berisi teks original)
        const translationSection = qs('.Review-comment-body--translation', reviewCard) || qs('[data-selenium="translate-section"]', reviewCard);

        if (translationSection) {
            // Ada section "translation" = review BUKAN bahasa Inggris asli
            // Ambil dari section ini karena berisi teks ORIGINAL
            const title = qs('[data-testid="review-title"]', translationSection);
            const comment = qs('[data-testid="review-comment"]', translationSection);
            return {
                judul: cleanText(title?.textContent || ''),
                teks_ulasan: cleanText(comment?.textContent || ''),
                is_original: true,
            };
        }

        // Tidak ada section "translation" = review ditulis dalam bahasa Inggris asli
        // Tidak ada terjemahan, jadi ambil dari elemen utama
        const mainBody = qs('.Review-comment-body[data-selenium]', reviewCard);
        if (mainBody) {
            const title = qs('[data-testid="review-title"]', mainBody);
            const comment = qs('[data-testid="review-comment"]', mainBody);
            return {
                judul: cleanText(title?.textContent || ''),
                teks_ulasan: cleanText(comment?.textContent || ''),
                is_original: true,
            };
        }

        return { judul: '', teks_ulasan: '', is_original: false };
    }

    /**
     * Mengekstrak tanggal review dari sebuah review card.
     *
     * Agoda menampilkan tanggal dengan beberapa cara, jadi kita coba berurutan:
     *   1. Elemen khusus tanggal (data-selenium / data-testid / class).
     *   2. Teks dengan prefix "Reviewed" (EN) atau "Diulas" (ID).
     *   3. Teks apa pun di dalam status bar yang cocok pola tanggal.
     *
     * Hasil dibersihkan dari prefix sehingga hanya menyisakan tanggalnya.
     */
    function extractReviewDate(reviewCard) {
        const MONTHS_EN = '(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)';
        const MONTHS_ID = '(?:Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember|Jan|Feb|Mar|Apr|Mei|Jun|Jul|Agu|Agt|Sep|Okt|Nov|Des)';
        // Pola: "May 11, 2026", "11 May 2026", "11 Mei 2026", "11/05/2026", "2026-05-11"
        const DATE_PATTERN = new RegExp(
            `(${MONTHS_EN}\\s+\\d{1,2},?\\s*\\d{4}` +
            `|\\d{1,2}\\s+${MONTHS_EN}\\s+\\d{4}` +
            `|\\d{1,2}\\s+${MONTHS_ID}\\s+\\d{4}` +
            `|\\d{1,2}[\\/\\-.]\\d{1,2}[\\/\\-.]\\d{2,4}` +
            `|\\d{4}-\\d{2}-\\d{2})`,
            'i'
        );

        const stripPrefix = (text) => {
            return cleanText(text)
                .replace(/^(Reviewed|Reviewed on|Diulas|Diulas pada|Tanggal ulasan|Review date)\s*:?\s*/i, '')
                .trim();
        };

        // 1. Elemen khusus tanggal (paling andal jika ada)
        const dateSelectors = [
            '[data-selenium="review-date"]',
            '[data-testid="review-date"]',
            '[data-element-name="review-date"]',
            '.Review-statusBar-date',
            '.Review-comment-reviewDate',
            'time[datetime]',
        ];
        for (const sel of dateSelectors) {
            const el = qs(sel, reviewCard);
            if (el) {
                // Prioritaskan atribut datetime jika tersedia (format ISO)
                const dt = el.getAttribute && el.getAttribute('datetime');
                if (dt) {
                    const m = String(dt).match(/\d{4}-\d{2}-\d{2}/);
                    if (m) return m[0];
                }
                const txt = stripPrefix(el.textContent);
                if (txt) return txt;
            }
        }

        // 2 & 3. Telusuri semua elemen teks, cari prefix atau pola tanggal
        const candidates = qsa('span, div, p, time', reviewCard);
        let patternFallback = '';
        for (const el of candidates) {
            // Lewati elemen yang punya banyak child (kemungkinan kontainer besar)
            if (el.children && el.children.length > 2) continue;
            const raw = cleanText(el.textContent);
            if (!raw || raw.length > 60) continue;

            // Prefix eksplisit "Reviewed"/"Diulas"
            if (/^(Reviewed|Diulas)\b/i.test(raw)) {
                const stripped = stripPrefix(raw);
                if (stripped) return stripped;
            }

            // Simpan kandidat pertama yang cocok pola tanggal sebagai fallback
            if (!patternFallback) {
                const match = raw.match(DATE_PATTERN);
                if (match) patternFallback = match[0].trim();
            }
        }

        return patternFallback;
    }

    function extractReviewData(reviewCard, index) {
        const data = {
            review_index: index + 1,
            nama: '',
            negara: '',
            tipe_traveler: '',
            tipe_kamar: '',
            durasi_menginap: '',
            rating: '',
            rating_text: '',
            judul_ulasan: '',
            teks_ulasan: '',
            tanggal: '',
        };

        // ---- LEFT SECTION: Metadata ----

        // Rating score (e.g., "9.2")
        const scoreEl = qs('.Review-comment-leftScore', reviewCard);
        if (scoreEl) data.rating = cleanText(scoreEl.textContent);

        // Rating text (e.g., "Exceptional")
        const scoreTextEl = qs('.Review-comment-leftScoreText', reviewCard);
        if (scoreTextEl) data.rating_text = cleanText(scoreTextEl.textContent);

        // Reviewer name
        const nameSection = qs('.Review-comment-reviewer[data-info-type="reviewer-name"]', reviewCard);
        if (nameSection) {
            const strong = qs('strong', nameSection);
            if (strong) data.nama = cleanText(strong.textContent);

            // Country (from "from [Country]")
            const spans = qsa('span', nameSection);
            if (spans.length >= 2) {
                data.negara = cleanText(spans[spans.length - 1].textContent);
            }
        }

        // Traveler type (e.g., "Solo traveler", "Family with teens")
        const groupSection = qs('.Review-comment-reviewer[data-info-type="group-name"]', reviewCard);
        if (groupSection) {
            const span = qs('span', groupSection);
            if (span) data.tipe_traveler = cleanText(span.textContent);
        }

        // Room type (e.g., "Executive Room King")
        const roomSection = qs('.Review-comment-reviewer[data-info-type="room-type"]', reviewCard);
        if (roomSection) {
            const span = qs('span', roomSection);
            if (span) data.tipe_kamar = cleanText(span.textContent);
        }

        // Stay duration (e.g., "Stayed 1 night in October 2025")
        const staySection = qs('.Review-comment-reviewer[data-info-type="stay-detail"]', reviewCard);
        if (staySection) {
            const span = qs('span', staySection);
            if (span) data.durasi_menginap = cleanText(span.textContent);
        }

        // ---- RIGHT SECTION: Review Content ----

        // Get ORIGINAL review text (skip AI translation)
        const originalContent = getOriginalReviewContent(reviewCard);
        data.judul_ulasan = originalContent.judul;
        data.teks_ulasan = originalContent.teks_ulasan;

        // Remove curly quotes from title
        data.judul_ulasan = data.judul_ulasan
            .replace(/[\u201C\u201D\u201E\u201F\u2033\u2036]/g, '')
            .trim();

        // ---- DATE EXTRACTION ----
        // Tanggal review di Agoda bisa muncul dalam beberapa format/lokasi:
        //   - "Reviewed May 11, 2026"  (prefix bahasa Inggris)
        //   - "Diulas 11 Mei 2026"     (prefix bahasa Indonesia)
        //   - elemen khusus tanpa prefix, hanya tanggal "May 11, 2026" / "11 May 2026"
        //   - di dalam .Review-statusBar atau elemen dengan data-* date
        data.tanggal = extractReviewDate(reviewCard);

        return data;
    }

    // ====== PAGINATION ======

    function getReviewCards() {
        // Each review has class "Review-comment" and an id like "review-0"
        // Filter hanya yang visible (menghindari duplikat dari popup/side panel layout)
        const allCards = qsa('.Review-comment[id^="review-"]');
        const visibleCards = allCards.filter(card => card.offsetParent !== null);
        return visibleCards.length > 0 ? visibleCards : allCards;
    }

    function getNextPageButton() {
        // Agoda paginator uses:
        //   <button data-element-name="review-paginator-next" aria-label="Next reviews page">
        // There are 2+ paginators (top & bottom, plus possibly duplicates from popup layout)
        // Harus pilih yang VISIBLE agar tidak salah klik

        // Strategy 1: Direct selector for the "Next" button - pilih yang visible
        const nextBtns = qsa('button[data-element-name="review-paginator-next"], button[aria-label="Next reviews page"]');
        const visibleNextBtn = nextBtns.find(btn => btn.offsetParent !== null && !btn.hasAttribute('disabled'));
        if (visibleNextBtn) return visibleNextBtn;
        // Fallback jika offsetParent gagal (kadang terjadi di popup)
        const enabledNextBtn = nextBtns.find(btn => !btn.hasAttribute('disabled'));
        if (enabledNextBtn) return enabledNextBtn;

        // Strategy 2: Find the page button after the currently active one
        const paginators = qsa('.Review-paginator');
        for (const paginator of paginators) {
            if (paginator.offsetParent === null) continue; // skip hidden
            const allBtns = qsa('button[aria-label*="reviews page"]', paginator);
            let foundActive = false;
            for (const btn of allBtns) {
                if (foundActive && !btn.hasAttribute('disabled')) {
                    return btn;
                }
                if (btn.getAttribute('aria-current') === 'true') {
                    foundActive = true;
                }
            }
        }

        return null;
    }

    function getCurrentPageNumber() {
        // Cari paginator yang visible (hindari duplikat dari popup layout)
        const paginators = qsa('[data-element-name="review-paginator-step"]');
        const visiblePaginator = paginators.find(p => p.offsetParent !== null) || paginators[0];
        if (visiblePaginator) {
            const num = parseInt(visiblePaginator.getAttribute('data-element-page-number'));
            if (!isNaN(num)) return num;
        }

        // Fallback: find the active/current page button (visible one)
        const activeBtns = qsa('button[aria-current="true"][aria-label*="Reviews page"]');
        const activeBtn = activeBtns.find(btn => btn.offsetParent !== null) || activeBtns[0];
        if (activeBtn) {
            const match = activeBtn.getAttribute('aria-label')?.match(/page\s+(\d+)/i);
            if (match) return parseInt(match[1]);
            const num = parseInt(activeBtn.textContent.trim());
            if (!isNaN(num)) return num;
        }

        return currentPage;
    }

    function getTotalPages() {
        // Find the highest page number from VISIBLE pagination buttons
        const allBtns = qsa('button[aria-label*="reviews page"]');
        // Prioritaskan yang visible
        const visibleBtns = allBtns.filter(btn => btn.offsetParent !== null);
        const btnsToCheck = visibleBtns.length > 0 ? visibleBtns : allBtns;
        let max = 1;
        for (const btn of btnsToCheck) {
            const match = btn.getAttribute('aria-label')?.match(/page\s+(\d+)/i);
            if (match) {
                const num = parseInt(match[1]);
                if (num > max) max = num;
            }
        }
        return max;
    }

    async function goToNextPage() {
        const nextBtn = getNextPageButton();
        if (!nextBtn) {
            log('Tombol next page tidak ditemukan.');
            return false;
        }

        // Check if disabled
        if (nextBtn.hasAttribute('disabled')) {
            log('Tombol next page disabled (halaman terakhir).');
            return false;
        }

        // Save the current first review text for change detection
        const currentCards = getReviewCards();
        let oldFirstReviewId = '';
        let oldFirstText = '';
        if (currentCards.length > 0) {
            oldFirstReviewId = currentCards[0].getAttribute('id') || '';
            const firstComment = qs('[data-testid="review-comment"]', currentCards[0]);
            oldFirstText = (firstComment?.textContent || '').substring(0, 80);
        }

        // Click the next button
        nextBtn.scrollIntoView({ block: 'center' });
        await sleep(300);
        nextBtn.click();
        await sleep(CONFIG.PAGE_LOAD_DELAY);

        // Wait for reviews to actually change (AJAX content replacement)
        const startTime = Date.now();
        const maxWait = CONFIG.PAGE_LOAD_DELAY * 3;
        while (Date.now() - startTime < maxWait) {
            const newCards = getReviewCards();
            if (newCards.length > 0) {
                const newFirstId = newCards[0].getAttribute('id') || '';
                const newComment = qs('[data-testid="review-comment"]', newCards[0]);
                const newFirstText = (newComment?.textContent || '').substring(0, 80);

                // Check if content has actually changed
                if (newFirstText && newFirstText !== oldFirstText) {
                    currentPage = getCurrentPageNumber();
                    return true;
                }
                // Also check if review ID changed (e.g., review-0 stays but content differs)
                if (newFirstId && newFirstId !== oldFirstReviewId) {
                    currentPage = getCurrentPageNumber();
                    return true;
                }
            }
            await sleep(500);
        }

        // Even if we couldn't detect change, check if page number updated
        const newPage = getCurrentPageNumber();
        if (newPage > currentPage) {
            currentPage = newPage;
            return true;
        }

        warn('Timeout menunggu halaman baru dimuat.');
        return false;
    }

    // ====== SCROLL TO LOAD CONTENT ======

    async function scrollToLoadContent() {
        // Scroll through the review section to trigger lazy loading
        const reviewContainer = qs('.Review-paginator')?.closest('[class*="review"]')
            || qs('#reviewSection')
            || qs('[data-element-name="review-comment"]')?.parentElement;

        const scrollTarget = reviewContainer || document.body;
        const scrollHeight = scrollTarget.scrollHeight || document.body.scrollHeight;

        for (let y = 0; y < scrollHeight; y += 400) {
            window.scrollTo(0, y);
            await sleep(100);
        }
        // Scroll back to top of reviews
        const firstReview = qs('.Review-comment');
        if (firstReview) {
            firstReview.scrollIntoView({ block: 'start' });
        } else {
            window.scrollTo(0, 0);
        }
        await sleep(500);
    }

    // ====== MAIN SCRAPING ======

    async function scrapePage() {
        await scrollToLoadContent();

        const reviewCards = getReviewCards();
        if (reviewCards.length === 0) {
            warn('Tidak ada review card ditemukan di halaman ini.');
            return 0;
        }

        log(`Ditemukan ${reviewCards.length} review di halaman ${currentPage}`);

        // Klik tombol "Show original" terlebih dahulu di SEMUA review jika ada
        // Ini memastikan teks original dirender di DOM (menghindari error jika text masih hidden/belum diload)
        let clickedOriginal = 0;
        for (const card of reviewCards) {
            const showOrigBtn = qs('button[data-testid="show-original-btn"]', card);
            if (showOrigBtn) {
                try {
                    showOrigBtn.click();
                    clickedOriginal++;
                } catch (e) { }
            }
        }
        if (clickedOriginal > 0) {
            log(`Klik 'Show original' pada ${clickedOriginal} review...`);
            await sleep(1000); // Tunggu render / fetch Teks Original
        }

        let count = 0;

        for (let i = 0; i < reviewCards.length; i++) {
            const card = reviewCards[i];
            try {
                card.scrollIntoView({ block: 'center' });
                await sleep(CONFIG.SCROLL_DELAY);

                const reviewData = extractReviewData(card, allReviews.length);
                reviewData.page = currentPage;

                // Skip reviews with empty text
                if (!reviewData.teks_ulasan && !reviewData.judul_ulasan) {
                    warn(`  [${i + 1}/${reviewCards.length}] Review kosong, dilewati.`);
                    continue;
                }

                allReviews.push(reviewData);
                count++;

                const textPreview = reviewData.teks_ulasan.substring(0, 50);
                const ellipsis = reviewData.teks_ulasan.length > 50 ? '...' : '';
                log(`  [${i + 1}/${reviewCards.length}] ${reviewData.nama} - "${textPreview}${ellipsis}"`);

            } catch (e) {
                warn(`  Error review ${i + 1}: ${e.message}`);
            }
        }

        return count;
    }

    // ====== CSV GENERATION ======

    function escapeCSV(value) {
        if (value === null || value === undefined) return '';
        const str = String(value);
        if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
            return '"' + str.replace(/"/g, '""') + '"';
        }
        return str;
    }

    function generateCSV() {
        const headers = [
            'page',
            'review_index',
            'nama',
            'negara',
            'tipe_traveler',
            'tipe_kamar',
            'durasi_menginap',
            'rating',
            'rating_text',
            'judul_ulasan',
            'teks_ulasan',
            'tanggal',
        ];

        const rows = [headers.join(',')];

        for (const review of allReviews) {
            const row = [
                escapeCSV(review.page),
                escapeCSV(review.review_index),
                escapeCSV(review.nama),
                escapeCSV(review.negara),
                escapeCSV(review.tipe_traveler),
                escapeCSV(review.tipe_kamar),
                escapeCSV(review.durasi_menginap),
                escapeCSV(review.rating),
                escapeCSV(review.rating_text),
                escapeCSV(review.judul_ulasan),
                escapeCSV(review.teks_ulasan),
                escapeCSV(review.tanggal),
            ];
            rows.push(row.join(','));
        }

        return rows.join('\n');
    }

    function downloadCSV(csvContent) {
        const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');

        const now = new Date();
        const timestamp = now.toISOString().replace(/[:.]/g, '-').substring(0, 19);
        const hotelName = document.title.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 50);

        link.href = url;
        link.download = `agoda_reviews_${hotelName}_${timestamp}.csv`;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    // ====== MAIN ======

    log('========================================');
    log('Agoda Hotel Review Scraper');
    log('Review ORIGINAL saja (skip terjemahan AI)');
    log('========================================');
    log('');

    const detectedPages = getTotalPages();
    log(`Halaman terdeteksi di paginator: ${detectedPages}`);
    log(`Batas maksimal halaman: ${CONFIG.MAX_PAGES}`);
    log('(Script akan terus scrape sampai tidak ada halaman berikutnya)');
    log('');

    let totalScraped = 0;

    for (let page = 1; page <= CONFIG.MAX_PAGES; page++) {
        log(`--- Halaman ${currentPage} ---`);

        const count = await scrapePage();
        totalScraped += count;

        logSuccess(`Halaman ${currentPage} selesai: ${count} review (kumulatif: ${allReviews.length})`);

        // Cek apakah ada tombol next yang bisa diklik
        const nextBtn = getNextPageButton();
        if (!nextBtn) {
            log('Tombol next page tidak ditemukan. Scraping selesai.');
            break;
        }
        if (nextBtn.hasAttribute('disabled')) {
            log('Tombol next page disabled (halaman terakhir). Scraping selesai.');
            break;
        }

        log('Navigasi ke halaman berikutnya...');
        const success = await goToNextPage();
        if (!success) {
            log('Gagal pindah halaman. Scraping selesai.');
            break;
        }
        await sleep(1000);
    }

    // Generate and download CSV
    log('');
    log('========================================');
    logSuccess('SELESAI!');
    logSuccess(`Total review: ${allReviews.length}`);
    logSuccess(`Total halaman: ${currentPage}`);
    log('========================================');
    log('');

    if (allReviews.length > 0) {
        const csv = generateCSV();
        downloadCSV(csv);
        logSuccess('CSV berhasil didownload!');
    } else {
        warn('Tidak ada review yang berhasil di-scrape.');
    }

    // Return data for console access
    window.__agodaReviews = allReviews;
    log('Data juga tersedia di: window.__agodaReviews');

})();
