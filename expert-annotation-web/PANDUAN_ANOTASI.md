# Panduan Anotasi ABSA Hotel Santika

**Untuk:** Researcher, Expert 1, Expert 2  
**Tugas:** Anotasi sentimen aspek pada 50 review hotel  
**Estimasi waktu:** 60–90 menit  

---

## Apa yang Anda Kerjakan?

Anda diminta membaca 50 ulasan (review) pelanggan Hotel Santika dan memberikan label sentimen untuk **7 aspek** yang mungkin dibahas dalam setiap review.

Tugas ini bertujuan mengukur seberapa konsisten penilaian manusia terhadap sentimen dalam teks, menggunakan metode **Cohen's Kappa**.

> **Penting:** Kerjakan secara **mandiri dan independen**. Jangan mendiskusikan jawaban dengan anotator lain sebelum semua selesai.

---

## Langkah 1 — Buka Website

Buka link berikut di browser:

```
https://expert-annotation-web.vercel.app
```

> Bisa dikerjakan di laptop maupun HP.

---

## Langkah 2 — Pilih Identitas

Di halaman awal, pilih identitas Anda:

| Identitas | Untuk siapa |
|---|---|
| **Researcher** | Peneliti utama |
| **Expert 1** | Domain expert pertama |
| **Expert 2** | Domain expert kedua |

Klik nama Anda → Anda akan masuk ke halaman anotasi.

> Jawaban disimpan otomatis di browser Anda. Jika halaman di-refresh, jawaban tetap ada.

---

## Langkah 3 — Pahami Tampilan

Setiap review menampilkan:

```
┌─────────────────────────────────────────┐
│  Review 12 dari 50                      │
│  ID: 1234 | Platform: Agoda             │
│  Hotel: Hotel Santika Bandung           │
│  Tanggal: 2024-01-15                    │
│                                         │
│  [Teks review pelanggan di sini...]     │
│                                         │
│  Lokasi:      ○ None ○ positif ○ negatif ○ netral  │
│  Kenyamanan:  ○ None ○ positif ○ negatif ○ netral  │
│  Pelayanan:   ○ None ○ positif ○ negatif ○ netral  │
│  Kebersihan:  ○ None ○ positif ○ negatif ○ netral  │
│  Harga:       ○ None ○ positif ○ negatif ○ netral  │
│  Makanan:     ○ None ○ positif ○ negatif ○ netral  │
│  Fasilitas:   ○ None ○ positif ○ negatif ○ netral  │
│                                         │
│  [← Prev]  [Simpan ✓]  [Next →]        │
└─────────────────────────────────────────┘
```

---

## Langkah 4 — Cara Memberi Label

### 7 Aspek yang Dinilai

| Aspek | Artinya |
|---|---|
| **Lokasi** | Posisi hotel, akses, kedekatan dengan tempat tertentu |
| **Kenyamanan** | Kondisi kamar, suasana, ketenangan, kualitas tidur |
| **Pelayanan** | Sikap staf, kecepatan layanan, check-in/out |
| **Kebersihan** | Kebersihan kamar, kamar mandi, area hotel |
| **Harga** | Nilai uang, harga sesuai/tidak dengan fasilitas |
| **Makanan** | Kualitas, variasi, rasa makanan/sarapan |
| **Fasilitas** | Kolam renang, gym, WiFi, parkir, lift, dll |

### 4 Pilihan Label

| Label | Kapan digunakan |
|---|---|
| **None** | Aspek **tidak dibahas** sama sekali dalam review |
| **positif** | Reviewer mengungkapkan hal **baik/puas** tentang aspek ini |
| **negatif** | Reviewer mengungkapkan hal **buruk/kecewa** tentang aspek ini |
| **netral** | Aspek dibahas tapi **tidak jelas positif atau negatif**, atau ada dua sisi seimbang |

> **Default semua aspek = None.** Ubah hanya jika aspek tersebut benar-benar dibahas.

---

## Langkah 5 — Contoh Penilaian

### Contoh Review 1
> *"Kamarnya bersih dan luas. Staf sangat ramah. Lokasinya dekat mall."*

| Aspek | Label | Alasan |
|---|---|---|
| Lokasi | **positif** | "dekat mall" → positif |
| Kenyamanan | **positif** | "kamarnya luas" → positif |
| Pelayanan | **positif** | "staf sangat ramah" → positif |
| Kebersihan | **positif** | "kamarnya bersih" → positif |
| Harga | None | tidak dibahas |
| Makanan | None | tidak dibahas |
| Fasilitas | None | tidak dibahas |

---

### Contoh Review 2
> *"Sarapannya enak dan bervariasi, tapi kamar mandinya bau dan WiFi sangat lambat."*

| Aspek | Label | Alasan |
|---|---|---|
| Lokasi | None | tidak dibahas |
| Kenyamanan | None | tidak dibahas secara langsung |
| Pelayanan | None | tidak dibahas |
| Kebersihan | **negatif** | "kamar mandinya bau" → negatif |
| Harga | None | tidak dibahas |
| Makanan | **positif** | "sarapannya enak dan bervariasi" → positif |
| Fasilitas | **negatif** | "WiFi sangat lambat" → negatif |

---

### Contoh Review 3
> *"Harganya memang mahal, tapi sebanding dengan fasilitas yang diberikan."*

| Aspek | Label | Alasan |
|---|---|---|
| Harga | **netral** | Ada dua sisi: mahal (negatif) tapi sebanding (positif) → netral |
| Fasilitas | **positif** | "fasilitas yang diberikan" → implikasinya positif |

---

### Contoh Review 4
> *"Bagus, akan kembali lagi."*

| Aspek | Label | Alasan |
|---|---|---|
| Semua | **None** | Terlalu umum, tidak menyebut aspek spesifik apapun |

---

## Langkah 6 — Simpan Setiap Review

Setelah memberi label untuk satu review:

1. Klik tombol **Simpan ✓**
2. Review akan ditandai **hijau** di grid progress
3. Klik **Next →** untuk lanjut ke review berikutnya

> Anda bisa kembali ke review sebelumnya kapan saja menggunakan tombol **← Prev** atau klik nomor di grid progress.

---

## Langkah 7 — Pantau Progress

Di bagian atas halaman terdapat:
- **Progress bar** — menunjukkan persentase selesai
- **Grid nomor 1–50** — hijau = sudah selesai, putih = belum

Anda tidak harus mengerjakan secara berurutan. Bisa lompat ke nomor tertentu.

---

## Langkah 8 — Backup Data (Penting!)

Jawaban tersimpan di browser Anda. Untuk mencegah data hilang:

1. Klik **☰** (menu) di pojok kanan atas
2. Pilih **💾 Backup JSON**
3. Simpan file yang terunduh di tempat aman

Lakukan backup setiap 20–30 review, atau setelah selesai semua.

> Jika ganti browser atau clear cache, data bisa hilang. Backup JSON bisa di-import kembali.

---

## Langkah 9 — Export Hasil

Setelah selesai 50 review:

1. Klik **☰** → **📥 Export CSV**
2. File `annotations_[nama_anda].csv` akan terunduh
3. Kirim file tersebut ke peneliti utama

---

## Tips Mengerjakan

✅ **Baca seluruh review** sebelum memberi label  
✅ **Fokus pada apa yang ditulis**, bukan apa yang tersirat  
✅ Gunakan **None** jika ragu apakah aspek dibahas  
✅ Gunakan **netral** jika ada dua sisi yang seimbang  
✅ Kerjakan **mandiri** tanpa mendiskusikan dengan anotator lain  
✅ Lakukan **backup** secara berkala  

❌ Jangan menebak-nebak jika aspek tidak disebutkan  
❌ Jangan terpengaruh oleh rating bintang (tidak ditampilkan)  
❌ Jangan mendiskusikan jawaban sebelum semua selesai  

---

## Pertanyaan Umum

**Q: Bagaimana jika review sangat pendek seperti "bagus" saja?**  
A: Beri semua aspek = None. Review terlalu umum tidak bisa dilabeli aspek spesifik.

**Q: Bagaimana jika satu aspek disebutkan dua kali dengan sentimen berbeda?**  
A: Pilih **netral** jika keduanya seimbang, atau pilih yang lebih dominan.

**Q: Apakah saya harus mengisi semua 7 aspek?**  
A: Tidak. Isi hanya aspek yang benar-benar dibahas dalam review. Sisanya biarkan None.

**Q: Bolehkah mengerjakan tidak sekaligus?**  
A: Boleh. Jawaban tersimpan otomatis. Tutup browser, buka lagi nanti, jawaban tetap ada. Pastikan pakai browser dan perangkat yang sama.

**Q: Bagaimana jika saya ingin mengubah jawaban review yang sudah disimpan?**  
A: Klik nomor review di grid progress → ubah label → klik Simpan lagi.

**Q: Data saya hilang setelah ganti HP/laptop?**  
A: Import file backup JSON yang sudah Anda simpan sebelumnya via menu → Import JSON.

---

## Kontak

Jika ada pertanyaan atau kendala teknis, hubungi peneliti utama.

---

*Terima kasih atas kontribusi Anda dalam penelitian ini.*
