# Audit Label dan Error Analysis Model ABSA Hotel Santika

## Dataset

- Full labeled dataset: 14,747 review
- Test split: 1,309 review
- Aspek: Lokasi, Kenyamanan, Pelayanan, Kebersihan, Harga, Makanan, Fasilitas

## Ringkasan Performa Test Split

| aspect | accuracy | macro_f1 | non_none_macro_f1 | aspect_detection_f1 | false_aspect_rate | missed_aspect_rate | high_conf_wrong_80 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Fasilitas | 0.8785 | 0.6931 | 0.6063 | 0.8785 | 0.0604 | 0.0862 | 47 |
| Kebersihan | 0.9542 | 0.6997 | 0.6082 | 0.9455 | 0.0357 | 0.0339 | 17 |
| Harga | 0.9656 | 0.7135 | 0.6220 | 0.8626 | 0.0174 | 0.0808 | 12 |
| Kenyamanan | 0.8648 | 0.7116 | 0.6456 | 0.8902 | 0.1153 | 0.0787 | 48 |
| Pelayanan | 0.9244 | 0.7548 | 0.6857 | 0.9580 | 0.0405 | 0.0389 | 32 |
| Makanan | 0.9320 | 0.7907 | 0.7286 | 0.9659 | 0.0280 | 0.0267 | 32 |
| Lokasi | 0.9481 | 0.8289 | 0.7819 | 0.9447 | 0.0397 | 0.0375 | 7 |

## Kesimpulan Cepat

- Total kandidat high-confidence wrong pada test split: 195 prediksi aspek.
- Aspek yang paling perlu diprioritaskan untuk audit model adalah Fasilitas, Kebersihan, Harga karena non-none macro F1 paling rendah.
- Kelas netral adalah titik paling lemah hampir di semua aspek. Ini menunjukkan label netral perlu didefinisikan lebih tegas atau dipertimbangkan ulang.
- Ditemukan 63 kandidat inkonsistensi label-vs-alasan dan 9 baris duplicate text dengan label berbeda.
- Ditemukan 2260 review panjang atau multi-aspek yang rawan kehilangan konteks saat model memakai max_len 128.

## Aspek Prioritas Error Analysis

- Fasilitas: non-none macro F1 60.63%, macro F1 69.31%, high-confidence wrong 47.
- Kebersihan: non-none macro F1 60.82%, macro F1 69.97%, high-confidence wrong 17.
- Harga: non-none macro F1 62.20%, macro F1 71.35%, high-confidence wrong 12.

## Risiko False Aspect Tertinggi

- Kenyamanan: false aspect rate 11.53%.
- Fasilitas: false aspect rate 6.04%.
- Pelayanan: false aspect rate 4.05%.

## Risiko Missed Aspect Tertinggi

- Fasilitas: missed aspect rate 8.62%.
- Harga: missed aspect rate 8.08%.
- Kenyamanan: missed aspect rate 7.87%.

## Distribusi Label Full Dataset

| aspect | negatif | netral | none | positif |
| --- | --- | --- | --- | --- |
| Fasilitas | 1505 | 568 | 11273 | 1401 |
| Harga | 239 | 142 | 13757 | 609 |
| Kebersihan | 588 | 73 | 10617 | 3469 |
| Kenyamanan | 1574 | 260 | 9028 | 3885 |
| Lokasi | 257 | 186 | 10225 | 4079 |
| Makanan | 890 | 567 | 9517 | 3773 |
| Pelayanan | 847 | 367 | 8588 | 4945 |

## Label Non-none dengan F1 Terlemah

| aspect | label | support | precision | recall | f1 | fp | fn |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Kebersihan | netral | 7 | 0.1250 | 0.1429 | 0.1333 | 7 | 6 |
| Kenyamanan | netral | 26 | 0.2581 | 0.3077 | 0.2807 | 23 | 18 |
| Fasilitas | netral | 57 | 0.3103 | 0.3158 | 0.3130 | 40 | 39 |
| Pelayanan | netral | 37 | 0.4074 | 0.2973 | 0.3438 | 16 | 26 |
| Harga | netral | 14 | 0.3846 | 0.3571 | 0.3704 | 8 | 9 |
| Makanan | netral | 57 | 0.4681 | 0.3860 | 0.4231 | 25 | 35 |
| Lokasi | netral | 19 | 0.6471 | 0.5789 | 0.6111 | 6 | 8 |

## Catatan Audit Label

- Kandidat audit utama ada pada file `priority_manual_audit_candidates.csv`, terutama baris dengan confidence tinggi tetapi prediksi berbeda dari label.
- Review panjang dan multi-aspek ada pada `long_or_multi_aspect_review_candidates.csv`; kelompok ini rawan kehilangan konteks karena batas input model.
- Cek juga `label_reason_mismatch_candidates.csv` dan `duplicate_text_conflicting_labels.csv` untuk mencari inkonsistensi label manual.

## Rekomendasi Urutan Perbaikan

1. Audit 100 baris teratas pada `priority_manual_audit_candidates.csv`, terutama aspek Fasilitas dan Kenyamanan.
2. Periksa semua baris pada `label_reason_mismatch_candidates.csv`; ini kandidat paling jelas untuk koreksi label atau alasan.
3. Periksa `duplicate_text_conflicting_labels.csv` karena teks yang sama seharusnya tidak memiliki label aspek yang berbeda tanpa alasan kuat.
4. Buat aturan guideline baru untuk kelas netral: kapan netral benar-benar dipakai dan kapan sebaiknya menjadi positif/negatif/none.
5. Audit review panjang dan multi-aspek untuk menilai apakah perlu sentence chunking sebelum fine-tuning ulang.
6. Setelah label dikoreksi, lakukan fine-tuning ulang dan bandingkan Macro F1, Non-none Macro F1, Aspect Detection F1, serta False Aspect Rate.