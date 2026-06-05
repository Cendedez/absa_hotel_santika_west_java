"""
Generate proposal koreksi label dari hasil audit error analysis.

Output ini tidak menimpa dataset utama. Tujuannya adalah memberi daftar
prioritas koreksi yang aman untuk direview sebelum fine-tuning ulang.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).parent
AUDIT_DIR = BASE_DIR / "Audit Error Analysis"
LABELED_PATH = BASE_DIR / "Data Labeling" / "dataset_absa_labeled.csv"

ASPECTS = ["Lokasi", "Kenyamanan", "Pelayanan", "Kebersihan", "Harga", "Makanan", "Fasilitas"]
LABELS = ["none", "positif", "negatif", "netral"]

ASPECT_KEYWORDS = {
    "Lokasi": [
        "lokasi", "strategis", "dekat", "akses", "mall", "mal", "pusat kota",
        "stasiun", "jalan", "sebelah", "kawasan", "area", "botani", "bip",
        "pusat hiburan", "pusat perbelanjaan",
    ],
    "Kenyamanan": [
        "nyaman", "kamar", "room", "tempat tidur", "kasur", "ac", "air conditioner",
        "tidur", "berisik", "suara", "gelap", "luas", "sempit", "panas", "dingin",
        "bau rokok", "view", "pemandangan",
    ],
    "Pelayanan": [
        "pelayanan", "layanan", "staf", "staff", "petugas", "resepsionis",
        "receptionist", "security", "doorman", "ramah", "membantu", "check-in",
        "check in", "check-out", "check out", "responsif",
    ],
    "Kebersihan": [
        "bersih", "kotor", "kebersihan", "handuk", "linen", "sprei", "noda",
        "debu", "bau", "terawat", "pengharum", "lubang di handuk",
    ],
    "Harga": [
        "harga", "tarif", "mahal", "murah", "sepadan", "worth", "value",
        "biaya", "bayar", "budget", "uang", "rate",
    ],
    "Makanan": [
        "makanan", "makan", "sarapan", "breakfast", "menu", "rasa", "restoran",
        "hidangan", "lezat", "enak", "variasi", "prasmanan",
    ],
    "Fasilitas": [
        "fasilitas", "kolam", "kolam renang", "parkir", "lift", "wifi", "shower",
        "water heater", "air panas", "kulkas", "hairdryer", "tv", "kamar mandi",
        "toilet", "air", "pool", "gym", "handuk", "ac", "soundproof",
    ],
}

POSITIVE_CUES = [
    "bagus", "baik", "ramah", "nyaman", "bersih", "strategis", "enak", "lezat",
    "lengkap", "puas", "memuaskan", "mantap", "top", "cepat", "mudah", "luas",
    "terang", "aman", "dekat", "rekomendasi", "recommended", "berfungsi",
    "terawat", "menarik", "cukup baik", "pas", "murah", "worth",
]

NEGATIVE_CUES = [
    "kurang", "tidak", "nggak", "gak", "ga ", "lambat", "bau", "kotor", "rusak",
    "mahal", "mengecewakan", "buruk", "gelap", "kecil", "sempit", "tua", "mampet",
    "bocor", "panas", "susah", "berisik", "horor", "lama", "biasa saja", "minim",
    "ribet", "tidak ada", "tidak bisa", "tidak sesuai", "close", "terganggu",
    "komplain", "mengeluh", "parah",
]

NEUTRAL_CUES = [
    "biasa", "standar", "cukup", "lumayan", "agak", "normal", "rata-rata",
]


def normalize_label(value) -> str:
    if pd.isna(value):
        return "none"
    text = str(value).strip().lower()
    if text in {"", "-", "nan", "none", "tidak terdeteksi"}:
        return "none"
    return text


def clean_text(value) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def find_keywords(text: str, keywords: list[str]) -> list[str]:
    text_l = clean_text(text)
    return [kw for kw in keywords if kw in text_l]


def infer_sentiment(text: str) -> tuple[str, str]:
    text_l = clean_text(text)
    pos = find_keywords(text_l, POSITIVE_CUES)
    neg = find_keywords(text_l, NEGATIVE_CUES)
    neu = find_keywords(text_l, NEUTRAL_CUES)

    # Negatif diprioritaskan karena keluhan biasanya lebih eksplisit dan lebih
    # penting untuk audit perbaikan layanan.
    if neg and not pos:
        return "negatif", ", ".join(neg[:5])
    if pos and not neg:
        return "positif", ", ".join(pos[:5])
    if neg and pos:
        return "ambiguous", f"positive: {', '.join(pos[:3])}; negative: {', '.join(neg[:3])}"
    if neu:
        return "netral", ", ".join(neu[:5])
    return "unknown", ""


def infer_aspect_evidence(aspect: str, text: str) -> str:
    return ", ".join(find_keywords(text, ASPECT_KEYWORDS.get(aspect, []))[:8])


def label_from_text_for_aspect(aspect: str, text: str) -> tuple[str, str]:
    aspect_evidence = infer_aspect_evidence(aspect, text)
    sentiment, sentiment_evidence = infer_sentiment(text)
    if not aspect_evidence:
        return "none", "no aspect keyword detected"
    if sentiment in {"positif", "negatif", "netral"}:
        return sentiment, f"aspect evidence: {aspect_evidence}; sentiment evidence: {sentiment_evidence}"
    return "needs_review", f"aspect evidence: {aspect_evidence}; mixed/weak sentiment: {sentiment_evidence}"


def action_for_priority(row: pd.Series) -> dict:
    aspect = row["aspect"]
    true_label = normalize_label(row["true_label"])
    pred_label = normalize_label(row["pred_label"])
    confidence = float(row["confidence"])
    text = row["Text_Review"]
    aspect_evidence = infer_aspect_evidence(aspect, text)
    heuristic_label, evidence = label_from_text_for_aspect(aspect, text)

    if true_label == "none" and pred_label != "none":
        if aspect_evidence and confidence >= 0.80:
            action = "likely_missing_label"
            suggested = pred_label if heuristic_label in {"needs_review", "none"} else heuristic_label
        elif aspect_evidence:
            action = "possible_missing_label"
            suggested = pred_label if heuristic_label in {"needs_review", "none"} else heuristic_label
        else:
            action = "likely_model_false_aspect"
            suggested = true_label
    elif true_label != "none" and pred_label == "none":
        if aspect_evidence:
            action = "likely_model_missed_aspect"
            suggested = true_label
        else:
            action = "possible_label_false_positive"
            suggested = "none"
    elif true_label != "none" and pred_label != "none" and true_label != pred_label:
        if heuristic_label in LABELS and heuristic_label != "none":
            action = "possible_sentiment_label_review"
            suggested = heuristic_label
        else:
            action = "sentiment_conflict_needs_expert"
            suggested = "needs_review"
    else:
        action = "no_action"
        suggested = true_label

    return {
        "source": "priority_model_disagreement",
        "issue": row["priority_reason"],
        "aspect": aspect,
        "ID_Review": row["ID_Review"],
        "current_label": true_label,
        "model_prediction": pred_label,
        "model_confidence": confidence,
        "suggested_label": suggested,
        "recommended_action": action,
        "aspect_evidence": aspect_evidence,
        "sentiment_evidence": evidence,
        "Platform": row.get("Platform"),
        "Nama_Hotel": row.get("Nama_Hotel"),
        "Review_Date": row.get("Review_Date"),
        "Text_Review": row.get("Text_Review"),
    }


def action_for_label_reason(row: pd.Series) -> dict:
    aspect = row["aspect"]
    label = normalize_label(row["label"])
    text = row["Text_Review"]
    alasan = row.get("alasan", "")
    aspect_evidence = infer_aspect_evidence(aspect, text)
    reason_aspect_evidence = infer_aspect_evidence(aspect, alasan)
    heuristic_label, evidence = label_from_text_for_aspect(aspect, f"{text} {alasan}")

    if row["issue"] == "alasan_ada_tapi_label_none":
        if reason_aspect_evidence or aspect_evidence:
            action = "likely_missing_label_from_reason"
            suggested = heuristic_label if heuristic_label in LABELS and heuristic_label != "none" else "needs_review"
        else:
            action = "reason_likely_wrong_aspect"
            suggested = "none"
    else:
        if aspect_evidence:
            action = "add_missing_reason_keep_label"
            suggested = label
        else:
            action = "label_without_evidence_review"
            suggested = "needs_review"

    return {
        "source": "label_reason_mismatch",
        "issue": row["issue"],
        "aspect": aspect,
        "ID_Review": row["ID_Review"],
        "current_label": label,
        "model_prediction": "",
        "model_confidence": np.nan,
        "suggested_label": suggested,
        "recommended_action": action,
        "aspect_evidence": aspect_evidence or reason_aspect_evidence,
        "sentiment_evidence": evidence,
        "Platform": row.get("Platform"),
        "Nama_Hotel": row.get("Nama_Hotel"),
        "Review_Date": row.get("Review_Date"),
        "Text_Review": row.get("Text_Review"),
        "current_reason": alasan,
    }


def main() -> None:
    priority = pd.read_csv(AUDIT_DIR / "priority_manual_audit_candidates.csv")
    mismatch = pd.read_csv(AUDIT_DIR / "label_reason_mismatch_candidates.csv")
    duplicates = pd.read_csv(AUDIT_DIR / "duplicate_text_conflicting_labels.csv")
    labeled = pd.read_csv(LABELED_PATH)

    rows = []
    for _, row in priority.iterrows():
        rows.append(action_for_priority(row))
    for _, row in mismatch.iterrows():
        rows.append(action_for_label_reason(row))

    proposals = pd.DataFrame(rows)
    action_rank = {
        "likely_missing_label": 1,
        "likely_missing_label_from_reason": 1,
        "add_missing_reason_keep_label": 2,
        "possible_sentiment_label_review": 3,
        "sentiment_conflict_needs_expert": 4,
        "possible_missing_label": 5,
        "likely_model_missed_aspect": 6,
        "possible_label_false_positive": 7,
        "label_without_evidence_review": 8,
        "reason_likely_wrong_aspect": 9,
        "likely_model_false_aspect": 10,
    }
    proposals["action_rank"] = proposals["recommended_action"].map(action_rank).fillna(99).astype(int)
    proposals = proposals.sort_values(["action_rank", "model_confidence"], ascending=[True, False])
    proposals.to_csv(AUDIT_DIR / "manual_label_correction_proposals.csv", index=False, encoding="utf-8-sig")

    # Summary by action and aspect.
    summary_action = (
        proposals.groupby(["recommended_action", "source"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    summary_aspect = (
        proposals.groupby(["aspect", "recommended_action"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["aspect", "count"], ascending=[True, False])
    )
    summary_action.to_csv(AUDIT_DIR / "manual_audit_action_summary.csv", index=False, encoding="utf-8-sig")
    summary_aspect.to_csv(AUDIT_DIR / "manual_audit_action_by_aspect.csv", index=False, encoding="utf-8-sig")

    # Duplicate text review: original extraction showed '#NAME?' text, so recover rows by ID from full dataset.
    dup_ids = duplicates["ID_Review"].tolist()
    dup_full = labeled[labeled["ID_Review"].isin(dup_ids)].copy()
    for aspect in ASPECTS:
        dup_full[aspect] = dup_full[aspect].map(normalize_label)
    dup_full.to_csv(AUDIT_DIR / "duplicate_text_rows_recovered_for_review.csv", index=False, encoding="utf-8-sig")

    # Build compact final report.
    top_actions = summary_action.head(12)
    top_label_change = proposals[
        proposals["recommended_action"].isin([
            "likely_missing_label",
            "likely_missing_label_from_reason",
            "possible_sentiment_label_review",
            "possible_label_false_positive",
        ])
    ]
    label_change_summary = (
        top_label_change.groupby(["aspect", "current_label", "suggested_label"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(20)
    )

    def md_table(df: pd.DataFrame) -> str:
        if df.empty:
            return "_Tidak ada data._"
        cols = list(df.columns)
        lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
        for _, r in df.iterrows():
            vals = []
            for c in cols:
                v = r[c]
                if isinstance(v, float):
                    vals.append("" if np.isnan(v) else f"{v:.4f}")
                else:
                    vals.append(str(v).replace("|", "\\|").replace("\n", " "))
            lines.append("| " + " | ".join(vals) + " |")
        return "\n".join(lines)

    report = []
    report.append("# Hasil Audit Manual-Triage Label ABSA Hotel Santika\n")
    report.append("## Ringkasan Eksekusi\n")
    report.append(f"- Total proposal audit yang dibuat: {len(proposals)} baris.")
    report.append(f"- Sumber proposal: {len(priority)} model disagreement prioritas dan {len(mismatch)} label-vs-alasan mismatch.")
    report.append(f"- Duplicate text yang dipulihkan untuk review manual: {len(dup_full)} baris.")
    report.append(
        "- Proposal ini belum menimpa dataset utama. Gunakan sebagai daftar kerja koreksi sebelum fine-tuning ulang.\n"
    )
    report.append("## Ringkasan Aksi\n")
    report.append(md_table(top_actions))
    report.append("\n## Ringkasan Kandidat Perubahan Label Terbanyak\n")
    report.append(md_table(label_change_summary))
    report.append("\n## Interpretasi\n")
    report.append(
        "- Banyak kasus `true_label = none` tetapi model memprediksi aspek tertentu dengan confidence tinggi. Pada beberapa review, teks memang memuat kata aspek yang jelas, sehingga kemungkinan ada label aspek yang terlewat."
    )
    report.append(
        "- Kelas `netral` masih paling sulit. Banyak konflik netral-vs-negatif atau netral-vs-positif, sehingga guideline netral perlu diperketat."
    )
    report.append(
        "- Beberapa mismatch bukan masalah label, melainkan kolom alasan yang kosong atau alasan masuk ke aspek yang kurang tepat."
    )
    report.append(
        "- Hasil ini sebaiknya dipakai sebagai audit batch pertama. Setelah koreksi disetujui, dataset baru dapat dibuat dan model di-fine-tune ulang."
    )
    report.append("\n## File Output\n")
    report.append("- `manual_label_correction_proposals.csv`: daftar proposal koreksi/aksi utama.")
    report.append("- `manual_audit_action_summary.csv`: rekap aksi koreksi.")
    report.append("- `manual_audit_action_by_aspect.csv`: rekap aksi per aspek.")
    report.append("- `duplicate_text_rows_recovered_for_review.csv`: baris duplicate text yang perlu dicek ulang.")
    (AUDIT_DIR / "manual_audit_final_results.md").write_text("\n".join(report), encoding="utf-8")

    print("Proposal audit selesai.")
    print("Output:", AUDIT_DIR)
    print(summary_action.to_string(index=False))


if __name__ == "__main__":
    main()
