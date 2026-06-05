# Hasil Audit Manual-Triage Label ABSA Hotel Santika

## Ringkasan Eksekusi

- Total proposal audit yang dibuat: 363 baris.
- Sumber proposal: 300 model disagreement prioritas dan 63 label-vs-alasan mismatch.
- Duplicate text yang dipulihkan untuk review manual: 9 baris.
- Proposal ini belum menimpa dataset utama. Gunakan sebagai daftar kerja koreksi sebelum fine-tuning ulang.

## Ringkasan Aksi

| recommended_action | source | count |
| --- | --- | --- |
| sentiment_conflict_needs_expert | priority_model_disagreement | 90 |
| likely_missing_label | priority_model_disagreement | 73 |
| possible_missing_label | priority_model_disagreement | 36 |
| add_missing_reason_keep_label | label_reason_mismatch | 35 |
| possible_sentiment_label_review | priority_model_disagreement | 30 |
| likely_model_missed_aspect | priority_model_disagreement | 26 |
| reason_likely_wrong_aspect | label_reason_mismatch | 24 |
| possible_label_false_positive | priority_model_disagreement | 23 |
| likely_model_false_aspect | priority_model_disagreement | 22 |
| label_without_evidence_review | label_reason_mismatch | 2 |
| likely_missing_label_from_reason | label_reason_mismatch | 2 |

## Ringkasan Kandidat Perubahan Label Terbanyak

| aspect | current_label | suggested_label | count |
| --- | --- | --- | --- |
| Kenyamanan | none | positif | 18 |
| Fasilitas | none | negatif | 8 |
| Kebersihan | none | positif | 8 |
| Kenyamanan | none | negatif | 7 |
| Kenyamanan | positif | none | 6 |
| Pelayanan | none | positif | 6 |
| Makanan | none | positif | 6 |
| Kebersihan | none | negatif | 5 |
| Pelayanan | negatif | none | 4 |
| Fasilitas | none | positif | 4 |
| Fasilitas | positif | positif | 4 |
| Harga | none | positif | 4 |
| Pelayanan | positif | none | 4 |
| Fasilitas | netral | positif | 3 |
| Pelayanan | netral | positif | 3 |
| Harga | netral | negatif | 2 |
| Makanan | netral | positif | 2 |
| Makanan | positif | positif | 2 |
| Lokasi | none | positif | 2 |
| Kenyamanan | netral | positif | 2 |

## Interpretasi

- Banyak kasus `true_label = none` tetapi model memprediksi aspek tertentu dengan confidence tinggi. Pada beberapa review, teks memang memuat kata aspek yang jelas, sehingga kemungkinan ada label aspek yang terlewat.
- Kelas `netral` masih paling sulit. Banyak konflik netral-vs-negatif atau netral-vs-positif, sehingga guideline netral perlu diperketat.
- Beberapa mismatch bukan masalah label, melainkan kolom alasan yang kosong atau alasan masuk ke aspek yang kurang tepat.
- Hasil ini sebaiknya dipakai sebagai audit batch pertama. Setelah koreksi disetujui, dataset baru dapat dibuat dan model di-fine-tune ulang.

## File Output

- `manual_label_correction_proposals.csv`: daftar proposal koreksi/aksi utama.
- `manual_audit_action_summary.csv`: rekap aksi koreksi.
- `manual_audit_action_by_aspect.csv`: rekap aksi per aspek.
- `duplicate_text_rows_recovered_for_review.csv`: baris duplicate text yang perlu dicek ulang.