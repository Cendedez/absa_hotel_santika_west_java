# Tutorial Mengaktifkan Sinkronisasi (Supabase)

Setelah langkah ini selesai, jawaban setiap annotator tersimpan di server.
Expert bisa isi sebagian di HP lalu lanjut di laptop (data tergabung), dan
researcher bisa memantau progress semua expert secara real-time.

**Estimasi waktu: 10 menit. Gratis.**

> 📌 **Catatan UI (penting):** Tampilan dashboard Supabase sudah berubah
> (akhir 2025). Sekarang Supabase memakai **API key model baru**
> (`sb_publishable_...` dan `sb_secret_...`) dan lokasi menunya berbeda dari
> tutorial lama. Panduan di bawah sudah disesuaikan dengan UI terbaru.
> Nama key lama (`anon` / `service_role`) masih ada di tab **Legacy** dan tetap
> berfungsi sampai akhir 2026, tapi kita pakai yang baru.

---

## Bagian 1 — Buat Project Supabase

### 1.1 Daftar / Login
1. Buka **https://supabase.com**
2. Klik **Start your project** → login dengan GitHub (paling cepat).

### 1.2 Buat Project Baru
1. Di dashboard, klik **New project** (pilih organization-mu dulu jika diminta).
2. Isi:
   - **Project name**: `absa-annotation` (bebas)
   - **Database Password**: klik **Generate a password** → **simpan** (jaga-jaga,
     tidak dipakai di app).
   - **Region**: pilih **Southeast Asia (Singapore)** agar dekat dengan Indonesia.
3. Klik **Create new project**.
4. Tunggu ±1–2 menit sampai project selesai disiapkan (indikator setup hilang /
   muncul tampilan project utama).

---

## Bagian 2 — Buat Tabel Database

1. Di sidebar kiri, klik **SQL Editor** (ikon `>_`).
2. Klik **+ New query** (atau langsung ketik di editor kosong yang muncul).
3. Salin-tempel SQL berikut (sama dengan isi file `supabase_setup.sql`):

   ```sql
   create table if not exists public.annotations (
     annotator_id text primary key,
     store        jsonb not null,
     updated_at   timestamptz not null default now()
   );

   alter table public.annotations enable row level security;
   ```

4. Klik **Run** (tombol hijau kanan bawah, atau tekan `Ctrl+Enter`).
5. Pastikan muncul **Success. No rows returned**. Tabel `annotations` sudah dibuat.

> Cek opsional: sidebar **Table Editor** → pilih schema `public` → harus ada
> tabel `annotations`.

---

## Bagian 3 — Ambil Kredensial API (UI BARU)

Kamu butuh **2 nilai**: **Project URL** dan **Secret key**.

### 3.1 Ambil Project URL
1. Di sidebar kiri paling bawah, klik **Project Settings** (ikon gerigi).
2. Klik menu **Data API**.
3. Di bagian **Project URL**, salin nilainya
   (contoh: `https://abcd1234.supabase.co`). Ini dipakai sebagai `SUPABASE_URL`.

> Alternatif cepat: klik tombol hijau **Connect** di bar atas dashboard →
> tab **App Frameworks** → Project URL dan key tampil di sana.

### 3.2 Ambil Secret key
1. Masih di **Project Settings**, klik menu **API Keys**.
2. Pastikan kamu berada di tab **API Keys** (bukan "Legacy API Keys").
3. Di bagian **Secret keys**:
   - Jika belum ada, klik **Create new secret key** → beri nama bebas
     (mis. `vercel`) → **Create**.
   - Klik ikon **Reveal / Copy** untuk menyalin nilainya
     (diawali `sb_secret_...`). Ini dipakai sebagai `SUPABASE_SERVICE_ROLE_KEY`.
4. Salin Project URL dan Secret key ke notepad sementara.

> ⚠️ **Penting:**
> - Gunakan **Secret key** (`sb_secret_...`), **BUKAN** Publishable key
>   (`sb_publishable_...`). Publishable key tidak punya izin tulis penuh.
> - Secret key bersifat **rahasia** — jangan dibagikan atau di-commit ke GitHub.
>   Key ini hanya dipakai di server (API routes), tidak pernah dikirim ke browser.
>
> 💡 **Kalau tidak menemukan tab "API Keys" / masih UI lama:** buka tab
> **Legacy API Keys**, lalu salin key **service_role** (klik **Reveal**).
> Itu juga bisa dipakai sebagai `SUPABASE_SERVICE_ROLE_KEY` — aplikasi menerima
> keduanya tanpa perlu mengubah kode.

> ℹ️ **Kenapa nama variabelnya tetap `SUPABASE_SERVICE_ROLE_KEY`?**
> Itu nama yang dibaca oleh kode aplikasi (`src/lib/supabaseServer.ts`).
> Isinya boleh Secret key baru (`sb_secret_...`) maupun service_role lama —
> dua-duanya valid sebagai key sisi server.

---

## Bagian 4 — Pasang Kredensial di Vercel

1. Buka **https://vercel.com/dashboard** → klik project **expert-annotation-web**.
2. Klik tab **Settings** → menu **Environment Variables**.
3. Tambahkan variabel pertama:
   - **Key**: `SUPABASE_URL`
   - **Value**: tempel Project URL (contoh: `https://abcd1234.supabase.co`)
   - **Environments**: pastikan **Production**, **Preview**, **Development**
     semua tercentang (di UI Vercel baru, defaultnya "All Environments").
   - Klik **Save**.
4. Tambahkan variabel kedua:
   - **Key**: `SUPABASE_SERVICE_ROLE_KEY`
   - **Value**: tempel Secret key (`sb_secret_...`) atau service_role lama
     (`eyJ...`)
   - **Environments**: centang semua.
   - Klik **Save**.

> Cek: di daftar Environment Variables sekarang ada 2 baris
> (`SUPABASE_URL` dan `SUPABASE_SERVICE_ROLE_KEY`). Ejaan harus persis.

---

## Bagian 5 — Redeploy

Environment variable baru hanya aktif setelah redeploy.

1. Di project Vercel, klik tab **Deployments**.
2. Cari deployment teratas (paling baru) → klik ikon **⋯** (titik tiga) di kanannya.
3. Klik **Redeploy** → pada dialog, biarkan opsi default → konfirmasi **Redeploy**.
4. Tunggu sampai status **Ready** (±1–2 menit).

---

## Bagian 6 — Uji Sinkronisasi

1. Buka website (URL Vercel) di **laptop**, masuk sebagai **Expert 2** (`/expert2`).
   - Perhatikan tulisan di bawah nama: harusnya berubah jadi **"Tersinkron ke server ✓"**.
   - Jika tertulis **"Mode lokal (tanpa server)"** → env var belum benar / belum redeploy.
2. Isi 2–3 review, klik **Simpan**.
3. Buka website yang sama di **HP**, masuk **Expert 2** lagi.
   - Jawaban dari laptop harus muncul. Tambah 1–2 review di HP.
4. Kembali ke laptop, **refresh** halaman → jawaban dari HP ikut muncul.
5. Buka **/researcher** → klik **📊 Dashboard** → progress semua user tampil
   dengan sumber **"server (real-time)"**.

Selesai. Sinkronisasi aktif. 🎉

---

## Pemecahan Masalah

**Status tetap "Mode lokal (tanpa server)"**
- Pastikan kedua env var sudah ditambahkan di Vercel (ejaan persis:
  `SUPABASE_URL` dan `SUPABASE_SERVICE_ROLE_KEY`).
- Pastikan sudah **Redeploy** setelah menambahkan env var.
- Pastikan memakai **Secret key** (`sb_secret_...`) atau **service_role** lama —
  bukan Publishable / anon key.

**Status "Offline — tersimpan lokal" muncul sesekali**
- Itu normal saat koneksi internet sempat putus. Data tetap aman di localStorage
  dan akan otomatis dikirim ulang saat koneksi kembali / save berikutnya.

**Dashboard kosong / 0 semua**
- Belum ada yang menyimpan jawaban di server, atau env var belum aktif.
  Coba isi 1 review sebagai salah satu user dulu, lalu refresh dashboard.

**Tidak ketemu menu "API Keys" atau "Data API" di Settings**
- UI Supabase masih dalam transisi; sebagian project menampilkan menu lama
  **Settings → API**. Di sana: Project URL ada di bagian *Project URL*, dan
  key ada di *Project API keys* (pakai **service_role**). Fungsinya sama.

**Ingin reset data seorang annotator**
- Supabase → **Table Editor** → tabel `annotations` → hapus baris dengan
  `annotator_id` yang dimaksud. (Hati-hati, tidak bisa dibatalkan.)

---

## Untuk Pengembangan Lokal (opsional)

Jika ingin menguji sync saat `npm run dev` di komputer:

1. Buat file `.env.local` di folder `expert-annotation-web` (lihat `.env.example`):

   ```
   SUPABASE_URL=https://abcd1234.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=sb_secret_xxxxxxxx
   ```

   > Boleh juga diisi service_role lama (`eyJ...`) jika kamu memakai key legacy.

2. Jalankan `npm run dev`. File `.env.local` sudah otomatis diabaikan Git
   (aman, tidak akan ter-commit).
