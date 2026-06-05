# Guideline Labeling ABSA Hotel Santika V3 Final Audit

Guideline ini merupakan penyempurnaan setelah review 255 kasus ambigu dan pembersihan 26 inkonsistensi label-alasan.

## Prinsip Final

- Label diberikan hanya jika aspek benar-benar muncul pada teks review.
- Jika label bukan `none`, kolom alasan wajib berisi bukti teks yang relevan.
- Jika label `none`, kolom alasan harus kosong.
- Kelas `netral` hanya dipakai untuk penyebutan aspek yang deskriptif tanpa evaluasi jelas, bukan untuk kasus campuran positif-negatif.
- Jika satu kalimat memuat beberapa aspek, label hanya diberikan pada aspek yang benar-benar dievaluasi.

## Definisi Label

- `positif`: terdapat evaluasi baik terhadap aspek, seperti nyaman, bersih, ramah, strategis, enak, murah, lengkap, berfungsi, luas, cepat, atau memuaskan.
- `negatif`: terdapat keluhan terhadap aspek, seperti kotor, bau, lambat, tidak berfungsi, tidak ada, mahal, tidak sesuai, sempit, berisik, kurang, rusak, atau mengecewakan.
- `netral`: aspek hanya disebutkan sebagai informasi, tanpa pujian atau keluhan yang cukup kuat.
- `none`: aspek tidak muncul atau tidak relevan pada review.

## Catatan Audit

- Beberapa label yang sebelumnya `none` dikonversi menjadi label sentimen ketika terdapat bukti aspek dan sentimen yang jelas.
- Beberapa label yang tidak memiliki bukti aspek dikembalikan menjadi `none`.
- Alasan yang berada di aspek salah dibersihkan atau dikonversi menjadi label jika teks memang mendukung aspek tersebut.
- Dataset final audit disimpan sebagai `dataset_absa_labeled_v3_final_audited.csv`.
