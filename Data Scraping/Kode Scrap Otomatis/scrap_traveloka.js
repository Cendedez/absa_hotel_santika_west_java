/**
 * ============================================================
 * Traveloka Review Photo Scraper v2 - Console Script
 * ============================================================
 * 
 * Script ini dijalankan di Chrome DevTools Console pada halaman
 * review hotel Traveloka untuk mengambil SEMUA foto review,
 * termasuk foto ke-7 dan seterusnya yang tersembunyi.
 * 
 * OTOMATIS melakukan pagination (klik next page) sampai semua
 * halaman review selesai di-scrape.
 * 
 * CARA PAKAI:
 * 1. Buka halaman review hotel di Traveloka
 *    (contoh: https://www.traveloka.com/id-id/user/review/consumption/HOTEL/GENERAL/3000010000113)
 * 2. Buka Chrome DevTools (F12 atau Ctrl+Shift+I)
 * 3. Klik tab "Console"
 * 4. Copy-paste seluruh script ini ke console
 * 5. Tekan Enter
 * 6. Tunggu proses selesai (ada progress di console)
 * 7. File CSV akan otomatis terdownload
 */

(async function() {
    'use strict';

    // ====== KONFIGURASI ======
    const CONFIG = {
        SCROLL_DELAY: 300,
        PAGE_LOAD_DELAY: 4000,
        MAX_PAGES: 999,
        DOWNLOAD_CSV: true,
    };

    // ====== HELPER FUNCTIONS ======
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    function log(msg) {
        console.log(`%c[Scraper] ${msg}`, 'color: #0064D2; font-weight: bold;');
    }

    function logWarn(msg) {
        console.warn(`[Scraper] ${msg}`);
    }

    function logSuccess(msg) {
        console.log(`%c[Scraper] ✓ ${msg}`, 'color: #00AA00; font-weight: bold;');
    }

    function scrollToElement(el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    // ====== REVIEW EXTRACTION ======

    function findReviewCards() {
        let cards = document.querySelectorAll('div.r-14lw9ot.r-h1746q.r-kdyh1x.r-d045u9');
        if (cards.length === 0) {
            const container = document.querySelector("div[data-testid='review-list-container']");
            if (container) {
                cards = container.querySelectorAll(':scope > div > div');
            }
        }
        return Array.from(cards);
    }

    async function extractReviewData(reviewCard, index) {
        const data = {
            review_index: index + 1,
            teks_ulasan: '',
            tanggal: '',
        };

        // Extract teks ulasan
        const textEl = reviewCard.querySelector('div.css-cens5h');
        if (textEl) {
            data.teks_ulasan = textEl.textContent.trim();
        } else {
            const autoDirDivs = reviewCard.querySelectorAll('div[dir="auto"]');
            for (const div of autoDirDivs) {
                const text = div.textContent.trim();
                if (text.length > 30) {
                    data.teks_ulasan = text;
                    break;
                }
            }
        }

        // Extract tanggal
        const dateEl = reviewCard.querySelector('div.r-1pz39u2 > div.r-1ud240a.r-b88u0q');
        if (dateEl) {
            data.tanggal = dateEl.textContent.trim();
        } else {
            const allDivs = reviewCard.querySelectorAll('div');
            for (const div of allDivs) {
                if (div.textContent.includes('Diulas') && div.children.length === 0) {
                    data.tanggal = div.textContent.trim();
                    break;
                }
            }
        }

        return data;
    }

    // ====== PAGINATION ======

    function findNextPageButton() {
        // Cari tombol next page di area pagination (bawah halaman)
        // Harus dibedakan dari chevron-right di dalam lightbox/modal
        
        // Pastikan tidak ada modal terbuka
        if (document.querySelector('div[role="dialog"]')) return null;

        // Cari di area pagination: biasanya ada container dengan "Jumlah review per halaman"
        // atau area dengan tombol < >
        const allChevrons = document.querySelectorAll("svg[data-id='IcSystemChevronRight']");
        
        for (const chevron of allChevrons) {
            const btn = chevron.closest("div[role='button']") || chevron.parentElement;
            if (!btn) continue;

            // Pastikan tombol ini bukan bagian dari modal/dialog
            if (btn.closest('div[role="dialog"]')) continue;
            if (btn.closest('div[aria-modal="true"]')) continue;

            // Pastikan tombol tidak disabled
            if (btn.getAttribute('aria-disabled') === 'true') continue;

            // Pastikan tombol ini terlihat
            const rect = btn.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) continue;

            // Cek apakah tombol ini ada di area bawah halaman (pagination area)
            // Biasanya di dekat teks "Jumlah review per halaman"
            const parent = btn.parentElement;
            if (parent) {
                const parentText = parent.textContent || '';
                // Jika parent mengandung teks navigasi halaman, ini tombol yang benar
                if (parentText.includes('Jumlah review') || parentText.includes('per halaman')) {
                    return btn;
                }
            }

            // Fallback: cari chevron yang ada di area bawah viewport
            // (pagination biasanya di bawah daftar review)
            const siblingChevronLeft = btn.parentElement?.querySelector("svg[data-id='IcSystemChevronLeft']");
            if (siblingChevronLeft) {
                // Ada chevron left di sebelahnya = ini pagination controls
                return btn;
            }
        }

        return null;
    }

    async function waitForNewReviews(oldFirstReviewText, maxWait) {
        // Tunggu sampai review berubah (halaman baru dimuat)
        const startTime = Date.now();
        while (Date.now() - startTime < maxWait) {
            await sleep(500);
            const cards = findReviewCards();
            if (cards.length > 0) {
                const firstText = cards[0].querySelector('div.css-cens5h');
                if (firstText) {
                    const newText = firstText.textContent.trim().substring(0, 50);
                    if (newText !== oldFirstReviewText) {
                        return true; // Halaman baru berhasil dimuat
                    }
                }
            }
        }
        return false; // Timeout
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

    function generateCSV(allReviews) {
        const headers = ['url', 'page', 'review_index', 'teks_ulasan', 'tanggal'];

        let csv = '\uFEFF';
        csv += headers.map(escapeCSV).join(',') + '\n';

        for (const review of allReviews) {
            const row = [
                review.url,
                review.page,
                review.review_index,
                review.teks_ulasan,
                review.tanggal,
            ];
            csv += row.map(escapeCSV).join(',') + '\n';
        }

        return csv;
    }

    function downloadCSV(csv, filename) {
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    // ====== MAIN EXECUTION ======

    log('========================================');
    log('  Traveloka Review Scraper v2');
    log('  (Auto-pagination enabled)');
    log('========================================');
    log('');

    const currentUrl = window.location.href;
    const allReviews = [];
    let currentPage = 1;

    async function scrollToLoadContent() {
        const scrollHeight = document.body.scrollHeight;
        for (let y = 0; y < scrollHeight; y += 400) {
            window.scrollTo(0, y);
            await sleep(CONFIG.SCROLL_DELAY);
        }
        window.scrollTo(0, 0);
        await sleep(500);
    }

    async function processCurrentPage() {
        log(`\n--- Halaman ${currentPage} ---`);

        // Scroll untuk load semua lazy content
        await scrollToLoadContent();

        const reviewCards = findReviewCards();
        log(`Ditemukan ${reviewCards.length} review di halaman ${currentPage}`);

        if (reviewCards.length === 0) {
            logWarn('Tidak ada review ditemukan di halaman ini.');
            return 0;
        }

        for (let i = 0; i < reviewCards.length; i++) {
            const card = reviewCards[i];
            scrollToElement(card);
            await sleep(300);

            const reviewData = await extractReviewData(card, i);
            reviewData.url = currentUrl;
            reviewData.page = currentPage;

            allReviews.push(reviewData);

            const textPreview = reviewData.teks_ulasan.substring(0, 50) + (reviewData.teks_ulasan.length > 50 ? '...' : '');
            log(`  [${i + 1}/${reviewCards.length}] "${textPreview}"`);
        }

        logSuccess(`Halaman ${currentPage} selesai: ${reviewCards.length} review`);
        return reviewCards.length;
    }

    // Proses halaman pertama
    await processCurrentPage();

    // Auto-pagination: terus klik next sampai tidak bisa lagi
    while (currentPage < CONFIG.MAX_PAGES) {
        // Scroll ke bawah dulu untuk memastikan tombol pagination terlihat
        window.scrollTo(0, document.body.scrollHeight);
        await sleep(1000);

        // Cari tombol next page
        const nextBtn = findNextPageButton();
        if (!nextBtn) {
            log('\nTidak ada tombol next page atau sudah di halaman terakhir.');
            break;
        }

        // Simpan teks review pertama untuk deteksi perubahan halaman
        const currentCards = findReviewCards();
        let oldFirstText = '';
        if (currentCards.length > 0) {
            const firstTextEl = currentCards[0].querySelector('div.css-cens5h');
            if (firstTextEl) {
                oldFirstText = firstTextEl.textContent.trim().substring(0, 50);
            }
        }

        // Klik tombol next
        currentPage++;
        log(`\nNavigasi ke halaman ${currentPage}...`);
        scrollToElement(nextBtn);
        await sleep(300);
        nextBtn.click();

        // Tunggu halaman baru dimuat
        const loaded = await waitForNewReviews(oldFirstText, CONFIG.PAGE_LOAD_DELAY * 2);
        if (!loaded) {
            logWarn(`Halaman ${currentPage} tidak berhasil dimuat atau konten sama. Menghentikan pagination.`);
            currentPage--; // Revert karena tidak berhasil
            break;
        }

        // Tunggu sedikit lebih lama untuk stabilitas
        await sleep(1000);

        // Proses halaman baru
        const count = await processCurrentPage();
        if (count === 0) {
            log('Tidak ada review baru, menghentikan pagination.');
            break;
        }
    }

    // Generate dan download CSV
    log('');
    log('========================================');
    logSuccess(`SELESAI!`);
    logSuccess(`Total halaman: ${currentPage}`);
    logSuccess(`Total review: ${allReviews.length}`);

    if (CONFIG.DOWNLOAD_CSV) {
        const csv = generateCSV(allReviews);
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
        
        // Ambil nama hotel dari H1 (lebih bersih dari document.title yang banyak tulisan promonya)
        const h1 = document.querySelector('h1');
        let rawHotelName = h1 ? h1.textContent.trim() : document.title;
        // Bersihkan karakter aneh agar aman dijadikan nama file
        const hotelName = rawHotelName.replace(/[^a-zA-Z0-9]/g, '_').replace(/_+/g, '_').substring(0, 50);
        
        const filename = `traveloka_reviews_${hotelName}_${timestamp}.csv`;
        downloadCSV(csv, filename);
        logSuccess(`CSV terdownload: ${filename}`);
    }

    // Simpan ke variable global
    window.__travelokaReviews = allReviews;
    log('Data juga tersimpan di: window.__travelokaReviews');
    log('========================================');

    return allReviews;
})();
