# Expert Annotation Web — ABSA Hotel Santika

Website anotasi domain expert untuk validasi label **Aspect-Based Sentiment
Analysis (ABSA)** review Hotel Santika, menggunakan **Cohen's Kappa** sebagai
ukuran kesepakatan antar-anotator.

Tiga user (`researcher`, `expert_1`, `expert_2`) menganotasi **50 review yang
sama** secara independen. Tidak ada label awal yang ditampilkan, sehingga
penilaian setiap expert tidak bias.

## Aspek & Label

- Aspek: **Lokasi, Kenyamanan, Pelayanan, Kebersihan, Harga, Makanan, Fasilitas**
- Label tiap aspek: **None, positif, negatif, netral**
- Default semua aspek = `None`

## Teknologi

- Next.js 14 (App Router) + TypeScript
- **Supabase** (Postgres) untuk sinkronisasi lintas-perangkat — opsional
- localStorage sebagai cache instan + fallback offline
- Export CSV & backup JSON (implementasi manual, aman terhadap koma/kutip)
- Vercel-ready

> **Sinkronisasi:** Jika Supabase dikonfigurasi, jawaban tiap annotator tersimpan
> di server sehingga bisa dibuka dari HP maupun laptop dan progress-nya tergabung.
> Researcher dapat memantau progress semua expert secara real-time lewat Dashboard.
> Jika Supabase TIDAK dikonfigurasi, aplikasi otomatis jalan "mode lokal"
> (localStorage saja) tanpa error.

---

## Setup Supabase (untuk sinkronisasi lintas-perangkat)

1. Buat akun gratis di [supabase.com](https://supabase.com) → **New Project**.
2. Buka **SQL Editor** → New query → tempel isi file `supabase_setup.sql` → **Run**.
   Ini membuat tabel `annotations`.
3. Buka **Project Settings → API**, salin:
   - **Project URL** → jadi `SUPABASE_URL`
   - **service_role** key (bagian *Project API keys*) → jadi `SUPABASE_SERVICE_ROLE_KEY`
4. **Lokal:** buat file `.env.local` (contoh ada di `.env.example`):

   ```
   SUPABASE_URL=https://xxxx.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...
   ```

5. **Vercel:** Project Settings → **Environment Variables** → tambahkan kedua
   variabel di atas (untuk Production & Preview) → **Redeploy**.

> `service_role` key hanya dipakai di API routes (server). Tidak pernah dikirim
> ke browser, jadi expert tidak bisa mengakses data expert lain dari klien.

---

## 1. Cara Install

```bash
cd expert-annotation-web
npm install
```

## 2. Cara Run Lokal

```bash
npm run dev
```

Buka http://localhost:3000

## 3. Build Produksi

```bash
npm run build
npm run start
```

## 4. Deploy ke Vercel

1. Push folder `expert-annotation-web` ke repository GitHub.
2. Buka [vercel.com](https://vercel.com) → **New Project** → import repo.
3. Framework otomatis terdeteksi sebagai **Next.js**. Biarkan default:
   - Build command: `next build`
   - Output: `.next`
4. Klik **Deploy**.

Tidak perlu environment variable atau database. Data 50 review sudah
ter-bundle di `src/data/annotation_reviews.json`.

---

## 5. Cara Expert Mengisi Anotasi

1. Buka website, pilih identitas: **Researcher / Expert 1 / Expert 2**.
2. Untuk setiap review:
   - Baca teks review.
   - Pilih sentimen tiap aspek (`None / positif / negatif / netral`).
   - Pilih `None` jika aspek **tidak dibahas** dalam review.
   - Klik **Simpan** untuk menandai review selesai.
3. Setiap perubahan **tersimpan otomatis** (indikator "Autosaved").
4. Gunakan **Previous / Next** atau grid nomor untuk berpindah review.
5. Progress bar menampilkan jumlah review yang sudah selesai.

> Jawaban disimpan di browser (localStorage) dengan key terpisah per user:
> `absa_annotation_researcher`, `absa_annotation_expert_1`,
> `absa_annotation_expert_2`.

## 6. Cara Export Hasil

- **Export CSV** → menghasilkan `annotations_<user>.csv`
  (kolom: `annotator_id, ID_Review, Platform, Nama_Hotel, Review_Date,
  Text_Review, Lokasi, Kenyamanan, Pelayanan, Kebersihan, Harga, Makanan,
  Fasilitas, annotated_at`).
- **Backup JSON** → backup penuh localStorage (untuk jaga-jaga).
- **Import JSON** → memulihkan backup (hanya menerima backup milik user aktif).

---

## 7. Regenerasi 50 Review (opsional)

Sampel 50 review sudah dibuat di `src/data/annotation_reviews.json`
menggunakan **random seed tetap (42)** sehingga reproducible.

Untuk membuat ulang:

```bash
python scripts/prepare-annotation-sample.py
```

Script ini:
1. Membaca `../Data Labeling/dataset_absa_labeled.csv`.
2. Memfilter review yang punya **minimal 1 aspek terlabel**.
3. Mengambil **50 review** dengan seed tetap.
4. Join ke `../Data Preprocessing/dataset_absa_santika_clean.csv` untuk teks.
5. Menulis JSON **tanpa label** (hanya ID, Platform, Nama_Hotel, Review_Date,
   Text_Review).

## 8. Hitung Cohen's Kappa

Letakkan file hasil export (`annotations_researcher.csv`, dst.) di root project
`expert-annotation-web`, lalu jalankan:

```bash
python scripts/compute-cohens-kappa.py
```

Output:
- Cetak Kappa per aspek + macro average untuk setiap pasangan:
  - researcher vs expert_1
  - researcher vs expert_2
  - expert_1 vs expert_2
  - (dan vs `ai` = label awal, jika `dataset_absa_labeled.csv` tersedia)
- File `kappa_results.csv`.

Tidak butuh dependensi eksternal (implementasi Cohen's Kappa murni Python).

---

## Struktur Project

```
expert-annotation-web/
├─ package.json
├─ tsconfig.json
├─ next.config.mjs
├─ README.md
├─ scripts/
│  ├─ prepare-annotation-sample.py   # generate 50 review (seed tetap)
│  └─ compute-cohens-kappa.py        # hitung Cohen's Kappa
└─ src/
   ├─ app/
   │  ├─ layout.tsx
   │  ├─ globals.css
   │  ├─ page.tsx                     # halaman pilih user
   │  └─ annotate/page.tsx            # halaman anotasi
   ├─ components/
   │  ├─ AspectForm.tsx
   │  └─ ProgressPanel.tsx
   ├─ data/
   │  └─ annotation_reviews.json      # 50 review (TANPA label)
   └─ lib/
      ├─ types.ts
      ├─ constants.ts
      ├─ storage.ts
      └─ exporters.ts
```

## Catatan Metodologis

Website ini **tidak** melatih expert mengikuti label awal. Setiap expert memberi
anotasi independen terhadap 50 review yang sama. Hasil expert kemudian
dibandingkan dengan label awal (AI) dan antar-expert menggunakan Cohen's Kappa
untuk mengukur tingkat kesepakatan anotasi.

> File dataset asli (`dataset_absa_labeled.csv`,
> `dataset_absa_santika_clean.csv`) **tidak diubah** oleh project ini.
