# Ringkasan Step 1-4 Audit Label ABSA Hotel Santika

## Status Pengerjaan

1. Proposal audit label sudah dibaca dari `manual_label_correction_proposals.csv`.
2. Sebanyak 363 proposal sudah diberi keputusan validasi.
3. Guideline labeling V2 sudah dibuat agar aturan label lebih konsisten.
4. Dataset koreksi baru sudah dibuat tanpa menimpa dataset asli.

## Hasil Validasi

- Total proposal divalidasi: 363
- Total perubahan yang masuk change log: 60
- Perubahan label otomatis: 25
- Perubahan/penambahan alasan: 58
- Proposal yang masih perlu audit manual: 255
- Sisa inkonsistensi label-alasan di dataset v2: 26

## Prinsip Koreksi

- Dataset asli tetap aman dan tidak ditimpa.
- Koreksi otomatis hanya diterapkan pada kasus dengan bukti kuat.
- Kasus ambigu tetap dipisahkan sebagai manual review.
- Kelas `netral` tidak diubah otomatis karena menjadi sumber error utama dan butuh keputusan konseptual yang konsisten.

## File Output

- `dataset_absa_labeled_v2_audited.csv`
- `validated_label_audit_decisions.csv`
- `dataset_absa_labeled_v2_change_log.csv`
- `needs_manual_review_after_step_1_4.csv`
- `remaining_label_reason_consistency_issues.csv`
- `labeling_guideline_v2_after_audit.md`
- `step_1_to_4_action_summary.csv`
- `step_1_to_4_aspect_summary.csv`
