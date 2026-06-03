-- ============================================================
-- Supabase setup untuk Expert Annotation Web
-- Jalankan di Supabase Dashboard -> SQL Editor -> New query -> Run
-- ============================================================

-- Tabel menyimpan satu baris JSON per annotator.
create table if not exists public.annotations (
  annotator_id text primary key,
  store        jsonb not null,
  updated_at   timestamptz not null default now()
);

-- Aktifkan Row Level Security.
alter table public.annotations enable row level security;

-- CATATAN KEAMANAN:
-- Aplikasi mengakses tabel ini HANYA dari server (API routes Next.js)
-- menggunakan SERVICE ROLE key, yang otomatis melewati RLS.
-- Karena tidak ada akses langsung dari browser (anon key tidak dipakai),
-- kita tidak membuat policy publik. Ini menjaga data tetap privat:
-- expert tidak bisa membaca/menulis data expert lain dari sisi klien.

-- (Opsional) Jika nanti ingin akses anon read-only untuk debugging,
-- baru tambahkan policy spesifik. Default: tidak ada policy = tertutup
-- untuk anon/auth, tapi service role tetap bisa.
