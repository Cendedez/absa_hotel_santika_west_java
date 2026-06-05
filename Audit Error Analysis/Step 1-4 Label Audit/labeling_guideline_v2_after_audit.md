# Guideline Labeling ABSA Hotel Santika V2 Setelah Audit

## Tujuan

Guideline ini dipakai untuk memperbaiki konsistensi label aspect-based sentiment analysis sebelum fine-tuning ulang model IndoBERT. Dataset lama tidak ditimpa; hasil koreksi disimpan sebagai versi baru.

## Unit Labeling

- Satu review dapat memiliki lebih dari satu aspek.
- Setiap aspek diberi salah satu label: `positif`, `negatif`, `netral`, atau kosong/`none`.
- Label diberikan hanya jika aspek benar-benar dibahas dalam teks review.
- Kolom alasan harus berisi potongan/frasa pendukung dari teks review, bukan interpretasi yang terlalu jauh dari teks.

## Definisi Label

- `positif`: aspek dibahas dengan penilaian baik, memuaskan, nyaman, bersih, strategis, enak, ramah, murah, lengkap, atau indikator kepuasan lain.
- `negatif`: aspek dibahas dengan keluhan, hambatan, ketidakpuasan, kerusakan, lambat, bau, kotor, mahal, kurang, tidak sesuai, tidak berfungsi, atau indikator masalah lain.
- `netral`: aspek dibahas secara deskriptif tanpa penilaian jelas, atau informasinya seimbang dan tidak cukup kuat untuk positif/negatif.
- `none`: aspek tidak dibahas secara eksplisit atau tidak ada bukti cukup dari teks review.

## Aturan Penting Per Aspek

- `Kenyamanan`: kamar, suasana tidur, AC, kebisingan, ukuran kamar, rasa nyaman/tidak nyaman tinggal.
- `Kebersihan`: bersih/kotor, bau, linen, handuk, noda, debu, kamar mandi kotor.
- `Pelayanan`: staf, resepsionis, proses check-in/check-out, respons, keramahan, bantuan, reminder layanan.
- `Harga`: murah/mahal, value for money, sepadan/tidak sepadan dengan harga.
- `Lokasi`: strategis, dekat/jauh, akses, parkir sebagai akses lokasi, mal, pusat kota, transportasi.
- `Fasilitas`: kolam renang, lift, TV, Wi-Fi, shower, air panas, parkir sebagai fasilitas, gym, perlengkapan kamar.
- `Makanan`: sarapan, restoran, rasa makanan, variasi menu, kualitas makanan/minuman.

## Aturan Khusus Netral

- Jangan memakai `netral` hanya karena review mengandung campuran positif dan negatif. Jika keluhan/aspek positifnya jelas, gunakan `positif` atau `negatif` sesuai konteks aspek.
- Gunakan `netral` jika teks hanya menyebut keberadaan aspek tanpa evaluasi, misalnya "ada kolam renang" tanpa kualitas.
- Jika ada frasa seperti "biasa saja", cek konteks. Untuk makanan/fasilitas, frasa ini sering lebih dekat ke `negatif` ringan daripada netral jika bernada kecewa.

## Aturan Alasan

- Jika label aspek bukan `none`, alasan sebaiknya tidak kosong.
- Jika label `none`, alasan harus kosong.
- Jika alasan muncul di aspek yang salah, jangan langsung dipindahkan tanpa review; cek apakah aspek tujuan juga perlu diberi label.
- Alasan yang baik berupa frasa pendek dari review, misalnya "bau linen sangat menyengat" atau "lokasinya strategis".

## Aturan Koreksi Otomatis Batch Ini

- Koreksi otomatis hanya dilakukan untuk `likely_missing_label` dengan confidence model minimal 0.90, suggested label `positif`/`negatif`, dan bukti aspek ditemukan.
- Koreksi otomatis juga dilakukan jika label sudah ada tetapi alasan kosong, dengan alasan diambil dari kalimat yang mengandung bukti aspek.
- Kasus `netral`, konflik sentimen, false positive, atau alasan di aspek yang salah tetap masuk daftar manual review.

## Rekomendasi Setelah Audit

- Review manual file `needs_manual_review_after_step_1_4.csv`.
- Setelah label manual selesai, lakukan splitting ulang agar tidak ada bias dari test split lama.
- Fine-tuning ulang model dan bandingkan dengan model lama menggunakan Macro F1, Non-none Macro F1, Aspect Detection F1, False Aspect Rate, dan confusion matrix per aspek.
