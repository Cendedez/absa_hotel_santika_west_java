from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path(r"C:\Users\cencen04_\Downloads\ABSA Hotel Santika")
AUDIT_DIR = BASE_DIR / "Audit Error Analysis"
DATASET_PATH = BASE_DIR / "Data Labeling" / "dataset_absa_labeled.csv"
PROPOSAL_PATH = AUDIT_DIR / "manual_label_correction_proposals.csv"

OUTPUT_DIR = AUDIT_DIR / "Step 1-4 Label Audit"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ASPECTS = [
    "Kenyamanan",
    "Kebersihan",
    "Pelayanan",
    "Harga",
    "Lokasi",
    "Fasilitas",
    "Makanan",
]

VALID_LABELS = {"positif", "negatif", "netral", "none"}
SENTIMENT_LABELS = {"positif", "negatif", "netral"}
REASON_COL = {aspect: f"Alasan_{aspect}" for aspect in ASPECTS}


def norm_label(value: object) -> str:
    if pd.isna(value):
        return "none"
    text = str(value).strip().lower()
    if text in {"", "nan", "na", "null", "-"}:
        return "none"
    if text not in VALID_LABELS and text != "needs_review":
        return text
    return text


def is_blank(value: object) -> bool:
    return pd.isna(value) or str(value).strip() in {"", "-", "nan", "NaN", "None"}


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def split_evidence_terms(value: object) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    if text.lower() in {"nan", "no aspect keyword detected"}:
        return []
    return [term.strip().lower() for term in text.split(",") if term.strip()]


def sentiment_terms(value: object) -> list[str]:
    text = clean_text(value).lower()
    if not text or text == "no aspect keyword detected":
        return []
    # The generated evidence text usually stores cues after "sentiment evidence:".
    text = text.replace("sentiment evidence:", "")
    text = text.replace("positive:", "")
    text = text.replace("negative:", "")
    text = text.replace("mixed/weak sentiment:", "")
    text = text.replace("aspect evidence:", "")
    terms = re.split(r"[,;:]", text)
    cleaned: list[str] = []
    for term in terms:
        term = term.strip()
        if not term:
            continue
        if term.startswith("aspect"):
            continue
        if len(term) <= 1:
            continue
        cleaned.append(term)
    return cleaned


def sentence_candidates(review: str) -> list[str]:
    review = clean_text(review)
    if not review:
        return []
    parts = re.split(r"(?<=[.!?])\s+|;\s+", review)
    parts = [clean_text(part) for part in parts if clean_text(part)]
    return parts or [review]


def make_reason(review: str, aspect_evidence: object, sentiment_evidence: object = "") -> str:
    terms = split_evidence_terms(aspect_evidence)
    sent_terms = sentiment_terms(sentiment_evidence)
    sentences = sentence_candidates(review)
    scored_sentences: list[tuple[float, str]] = []
    for sentence in sentences:
        sentence_lower = sentence.lower()
        aspect_hits = sum(1 for term in terms if term in sentence_lower)
        sentiment_hits = sum(1 for term in sent_terms if term in sentence_lower)
        if aspect_hits:
            # Prefer sentences that contain both the aspect cue and evaluative cue.
            # Length is a small tie-breaker so tiny fragments do not win over clearer evidence.
            score = aspect_hits * 4 + sentiment_hits * 3 + min(len(sentence), 180) / 180
            scored_sentences.append((score, sentence))
    if scored_sentences:
        scored_sentences.sort(key=lambda item: item[0], reverse=True)
        return scored_sentences[0][1][:320]

    sentiment_text = clean_text(sentiment_evidence)
    if sentiment_text.startswith("aspect evidence:"):
        # Keep the reason concise and readable for the label-alasan columns.
        sentiment_text = sentiment_text.replace("aspect evidence:", "").strip()
    if terms:
        return f"Mengandung indikator aspek: {', '.join(terms[:5])}"
    if sentiment_text:
        return sentiment_text[:320]
    return clean_text(review)[:320]


def should_auto_apply(row: pd.Series) -> tuple[str, bool, str]:
    action = clean_text(row.get("recommended_action"))
    current = norm_label(row.get("current_label"))
    suggested = norm_label(row.get("suggested_label"))
    confidence = row.get("model_confidence")
    try:
        confidence_float = float(confidence)
    except (TypeError, ValueError):
        confidence_float = None

    has_aspect_evidence = bool(split_evidence_terms(row.get("aspect_evidence")))
    has_reason = not is_blank(row.get("current_reason"))

    if action == "likely_missing_label":
        if (
            current == "none"
            and suggested in {"positif", "negatif"}
            and confidence_float is not None
            and confidence_float >= 0.90
            and has_aspect_evidence
        ):
            return "apply_label_and_reason", True, (
                "Label none dikoreksi karena model confidence tinggi, "
                "suggested_label jelas, dan bukti aspek ditemukan."
            )
        return "needs_manual_review", False, (
            "Kandidat missing label masih perlu review karena confidence lebih rendah, "
            "label netral, atau bukti aspek kurang kuat."
        )

    if action == "likely_missing_label_from_reason":
        if current == "none" and suggested in SENTIMENT_LABELS and has_reason:
            return "apply_label_keep_or_add_reason", True, (
                "Label none dikoreksi karena kolom alasan sudah menunjukkan aspek dan sentimen."
            )
        return "needs_manual_review", False, "Alasan/label belum cukup kuat untuk auto-apply."

    if action == "add_missing_reason_keep_label":
        if current in SENTIMENT_LABELS:
            return "apply_reason_only", True, (
                "Label sudah ada, tetapi alasan kosong; alasan dilengkapi dari teks review."
            )
        return "needs_manual_review", False, "Label tidak valid untuk penambahan alasan otomatis."

    if action == "likely_model_missed_aspect":
        if current in SENTIMENT_LABELS and suggested == current and not has_reason and has_aspect_evidence:
            return "apply_reason_only", True, (
                "Label dataset dipertahankan; alasan dilengkapi karena model kemungkinan melewatkan aspek."
            )
        return "no_dataset_change", False, "Label dataset dipertahankan; tidak ada perubahan aman."

    if action == "likely_model_false_aspect":
        return "no_dataset_change", False, (
            "Dataset sudah none; kasus ini lebih menunjukkan false aspect dari model, bukan error label."
        )

    if action in {
        "possible_missing_label",
        "possible_sentiment_label_review",
        "possible_label_false_positive",
        "sentiment_conflict_needs_expert",
        "label_without_evidence_review",
        "reason_likely_wrong_aspect",
    }:
        return "needs_manual_review", False, (
            "Kasus ambigu/berisiko; disimpan untuk audit manual agar tidak mengubah label penelitian secara spekulatif."
        )

    return "needs_manual_review", False, "Action tidak dikenali atau belum punya aturan auto-apply."


def main() -> None:
    dataset = pd.read_csv(DATASET_PATH)
    proposals = pd.read_csv(PROPOSAL_PATH)

    dataset_by_id = dataset.set_index("ID_Review", drop=False)
    corrected = dataset.copy()
    corrected_by_id = corrected.set_index("ID_Review", drop=False)

    decisions: list[dict[str, object]] = []
    change_log: list[dict[str, object]] = []

    for _, row in proposals.iterrows():
        aspect = clean_text(row.get("aspect"))
        review_id = int(row["ID_Review"])
        if aspect not in ASPECTS or review_id not in corrected_by_id.index:
            decisions.append(
                {
                    **row.to_dict(),
                    "audit_decision": "needs_manual_review",
                    "applied_to_dataset": False,
                    "final_label": row.get("current_label"),
                    "final_reason": row.get("current_reason"),
                    "validation_note": "Aspect atau ID_Review tidak ditemukan pada dataset.",
                }
            )
            continue

        decision, rule_auto_selected, note = should_auto_apply(row)
        current_label = norm_label(row.get("current_label"))
        suggested_label = norm_label(row.get("suggested_label"))
        label_col = aspect
        reason_col = REASON_COL[aspect]

        old_label = norm_label(corrected_by_id.at[review_id, label_col])
        old_reason = corrected_by_id.at[review_id, reason_col]
        new_label = old_label
        new_reason = old_reason

        actual_change = False
        if rule_auto_selected:
            if decision in {"apply_label_and_reason", "apply_label_keep_or_add_reason"}:
                new_label = suggested_label
                if is_blank(old_reason):
                    preferred_reason = row.get("current_reason")
                    new_reason = (
                        clean_text(preferred_reason)
                        if not is_blank(preferred_reason)
                        else make_reason(row.get("Text_Review", ""), row.get("aspect_evidence", ""), row.get("sentiment_evidence", ""))
                    )
            elif decision == "apply_reason_only":
                if is_blank(old_reason):
                    new_reason = make_reason(row.get("Text_Review", ""), row.get("aspect_evidence", ""), row.get("sentiment_evidence", ""))

            corrected_by_id.at[review_id, label_col] = pd.NA if new_label == "none" else new_label
            corrected_by_id.at[review_id, reason_col] = pd.NA if is_blank(new_reason) else new_reason

            if old_label != new_label or clean_text(old_reason) != clean_text(new_reason):
                actual_change = True
                change_log.append(
                    {
                        "ID_Review": review_id,
                        "aspect": aspect,
                        "change_type": decision,
                        "old_label": old_label,
                        "new_label": new_label,
                        "old_reason": clean_text(old_reason),
                        "new_reason": clean_text(new_reason),
                        "source_action": row.get("recommended_action"),
                        "model_prediction": row.get("model_prediction"),
                        "model_confidence": row.get("model_confidence"),
                        "Text_Review": row.get("Text_Review"),
                    }
                )

        final_label = norm_label(corrected_by_id.at[review_id, label_col])
        final_reason = corrected_by_id.at[review_id, reason_col]
        decisions.append(
            {
                **row.to_dict(),
                "audit_decision": decision,
                "rule_auto_selected": bool(rule_auto_selected),
                "applied_to_dataset": bool(actual_change),
                "final_label": final_label,
                "final_reason": clean_text(final_reason),
                "validation_note": note,
            }
        )

    corrected = corrected_by_id.reset_index(drop=True)
    decisions_df = pd.DataFrame(decisions)
    change_log_df = pd.DataFrame(change_log)
    needs_review_df = decisions_df[decisions_df["audit_decision"] == "needs_manual_review"].copy()

    consistency_issues: list[dict[str, object]] = []
    for _, data_row in corrected.iterrows():
        for aspect in ASPECTS:
            label = norm_label(data_row.get(aspect))
            reason_value = data_row.get(REASON_COL[aspect])
            reason_blank = is_blank(reason_value)
            if label in SENTIMENT_LABELS and reason_blank:
                consistency_issues.append(
                    {
                        "issue": "label_without_reason_remaining",
                        "ID_Review": data_row.get("ID_Review"),
                        "aspect": aspect,
                        "label": label,
                        "reason": "",
                        "Platform": data_row.get("Platform"),
                        "Nama_Hotel": data_row.get("Nama_Hotel"),
                        "Review_Date": data_row.get("Review_Date"),
                        "Text_Review": data_row.get("Text_Review"),
                    }
                )
            if label == "none" and not reason_blank:
                consistency_issues.append(
                    {
                        "issue": "reason_without_label_remaining",
                        "ID_Review": data_row.get("ID_Review"),
                        "aspect": aspect,
                        "label": label,
                        "reason": clean_text(reason_value),
                        "Platform": data_row.get("Platform"),
                        "Nama_Hotel": data_row.get("Nama_Hotel"),
                        "Review_Date": data_row.get("Review_Date"),
                        "Text_Review": data_row.get("Text_Review"),
                    }
                )

    consistency_df = pd.DataFrame(consistency_issues)

    corrected_path = OUTPUT_DIR / "dataset_absa_labeled_v2_audited.csv"
    decisions_path = OUTPUT_DIR / "validated_label_audit_decisions.csv"
    changelog_path = OUTPUT_DIR / "dataset_absa_labeled_v2_change_log.csv"
    needs_review_path = OUTPUT_DIR / "needs_manual_review_after_step_1_4.csv"
    consistency_path = OUTPUT_DIR / "remaining_label_reason_consistency_issues.csv"
    guideline_path = OUTPUT_DIR / "labeling_guideline_v2_after_audit.md"
    summary_path = OUTPUT_DIR / "step_1_to_4_summary.md"

    corrected.to_csv(corrected_path, index=False, encoding="utf-8-sig")
    decisions_df.to_csv(decisions_path, index=False, encoding="utf-8-sig")
    change_log_df.to_csv(changelog_path, index=False, encoding="utf-8-sig")
    needs_review_df.to_csv(needs_review_path, index=False, encoding="utf-8-sig")
    consistency_df.to_csv(consistency_path, index=False, encoding="utf-8-sig")

    label_changes = int((change_log_df["old_label"] != change_log_df["new_label"]).sum()) if not change_log_df.empty else 0
    reason_changes = int((change_log_df["old_reason"] != change_log_df["new_reason"]).sum()) if not change_log_df.empty else 0

    action_summary = (
        decisions_df.groupby(["audit_decision", "applied_to_dataset"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["applied_to_dataset", "count"], ascending=[False, False])
    )
    aspect_summary = (
        decisions_df.groupby(["aspect", "audit_decision"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["aspect", "count"], ascending=[True, False])
    )
    action_summary.to_csv(OUTPUT_DIR / "step_1_to_4_action_summary.csv", index=False, encoding="utf-8-sig")
    aspect_summary.to_csv(OUTPUT_DIR / "step_1_to_4_aspect_summary.csv", index=False, encoding="utf-8-sig")

    guideline_path.write_text(
        """# Guideline Labeling ABSA Hotel Santika V2 Setelah Audit

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
""",
        encoding="utf-8",
    )

    summary_text = f"""# Ringkasan Step 1-4 Audit Label ABSA Hotel Santika

## Status Pengerjaan

1. Proposal audit label sudah dibaca dari `manual_label_correction_proposals.csv`.
2. Sebanyak {len(decisions_df):,} proposal sudah diberi keputusan validasi.
3. Guideline labeling V2 sudah dibuat agar aturan label lebih konsisten.
4. Dataset koreksi baru sudah dibuat tanpa menimpa dataset asli.

## Hasil Validasi

- Total proposal divalidasi: {len(decisions_df):,}
- Total perubahan yang masuk change log: {len(change_log_df):,}
- Perubahan label otomatis: {label_changes:,}
- Perubahan/penambahan alasan: {reason_changes:,}
- Proposal yang masih perlu audit manual: {len(needs_review_df):,}
- Sisa inkonsistensi label-alasan di dataset v2: {len(consistency_df):,}

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
"""
    summary_path.write_text(summary_text, encoding="utf-8")

    print(summary_text)
    print("\nAction summary:")
    print(action_summary.to_string(index=False))
    print("\nTop aspect summary:")
    print(aspect_summary.head(30).to_string(index=False))


if __name__ == "__main__":
    main()
