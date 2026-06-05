"""
Audit Label dan Error Analysis Model ABSA Hotel Santika.

Script ini membaca dataset label, test split, dan hasil batch prediction untuk:
- menghitung distribusi label,
- mengevaluasi error model pada test split,
- mencari kandidat label yang perlu diaudit ulang,
- menyimpan contoh kesalahan model yang representatif.

Output disimpan ke folder: Audit Error Analysis/
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).parent
LABELED_PATH = BASE_DIR / "Data Labeling" / "dataset_absa_labeled.csv"
TEST_PATH = BASE_DIR / "Data Splitting" / "test.csv"
PRED_PATH = BASE_DIR / "dataset_with_predictions.csv"
CONFIG_PATH = BASE_DIR / "Fine Tuning" / "best_absa_indobert" / "config.json"
OUT_DIR = BASE_DIR / "Audit Error Analysis"

LABELS = ["none", "positif", "negatif", "netral"]


def normalize_label(value) -> str:
    if pd.isna(value):
        return "none"
    text = str(value).strip().lower()
    if text in {"", "-", "nan", "none", "tidak terdeteksi"}:
        return "none"
    return text


def has_text(value) -> bool:
    if pd.isna(value):
        return False
    return bool(str(value).strip())


def safe_div(a: float, b: float) -> float:
    return float(a / b) if b else 0.0


def f1_for_label(y_true: pd.Series, y_pred: pd.Series, label: str) -> dict:
    tp = int(((y_true == label) & (y_pred == label)).sum())
    fp = int(((y_true != label) & (y_pred == label)).sum())
    fn = int(((y_true == label) & (y_pred != label)).sum())
    support = int((y_true == label).sum())
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall)
    return {
        "label": label,
        "support": support,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def classification_metrics(y_true: pd.Series, y_pred: pd.Series) -> dict:
    n = int(len(y_true))
    correct = int((y_true == y_pred).sum())
    per_label = [f1_for_label(y_true, y_pred, label) for label in LABELS]
    macro_f1 = float(np.mean([row["f1"] for row in per_label]))
    weighted_f1 = safe_div(
        sum(row["f1"] * row["support"] for row in per_label),
        sum(row["support"] for row in per_label),
    )

    non_none = [row for row in per_label if row["label"] != "none"]
    non_none_macro_f1 = float(np.mean([row["f1"] for row in non_none]))

    true_present = y_true != "none"
    pred_present = y_pred != "none"
    tp = int((true_present & pred_present).sum())
    fp = int((~true_present & pred_present).sum())
    fn = int((true_present & ~pred_present).sum())
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    aspect_detection_f1 = safe_div(2 * precision * recall, precision + recall)

    true_none_n = int((~true_present).sum())
    true_present_n = int(true_present.sum())
    both_present = true_present & pred_present
    sentiment_error_present_n = int((both_present & (y_true != y_pred)).sum())
    both_present_n = int(both_present.sum())

    return {
        "n": n,
        "accuracy": safe_div(correct, n),
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "non_none_macro_f1": non_none_macro_f1,
        "aspect_detection_f1": aspect_detection_f1,
        "false_aspect_rate": safe_div(fp, true_none_n),
        "missed_aspect_rate": safe_div(fn, true_present_n),
        "sentiment_error_when_both_present": safe_div(sentiment_error_present_n, both_present_n),
        "support_none": true_none_n,
        "support_present": true_present_n,
        "correct": correct,
        "wrong": n - correct,
        "per_label": per_label,
    }


def confusion_matrix_df(y_true: pd.Series, y_pred: pd.Series) -> pd.DataFrame:
    rows = []
    for true_label in LABELS:
        row = {"true_label": true_label}
        for pred_label in LABELS:
            row[f"pred_{pred_label}"] = int(((y_true == true_label) & (y_pred == pred_label)).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def add_word_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["review_char_len"] = out["Text_Review"].fillna("").astype(str).str.len()
    out["review_word_len"] = out["Text_Review"].fillna("").astype(str).str.split().str.len()
    return out


def markdown_table(df: pd.DataFrame, floatfmt: str = ".4f") -> str:
    """Render DataFrame kecil menjadi Markdown tanpa dependency tabulate."""
    if df.empty:
        return "_Tidak ada data._"

    def fmt(value) -> str:
        if isinstance(value, (float, np.floating)):
            return format(float(value), floatfmt)
        if isinstance(value, (int, np.integer)):
            return str(int(value))
        if pd.isna(value):
            return ""
        text = str(value)
        return text.replace("|", "\\|").replace("\n", " ")

    cols = list(df.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(fmt(row[col]) for col in cols) + " |")
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    aspects = config["aspects"]

    labeled = pd.read_csv(LABELED_PATH)
    test = pd.read_csv(TEST_PATH)
    pred = pd.read_csv(PRED_PATH)

    labeled = add_word_features(labeled)
    pred = add_word_features(pred)

    for aspect in aspects:
        if aspect in labeled.columns:
            labeled[aspect] = labeled[aspect].map(normalize_label)
        label_col = f"label_{aspect}"
        pred_col = f"pred_{aspect}"
        if label_col in pred.columns:
            pred[label_col] = pred[label_col].map(normalize_label)
        if pred_col in pred.columns:
            pred[pred_col] = pred[pred_col].map(normalize_label)

    test_ids = set(test["ID_Review"].tolist())
    test_pred = pred[pred["ID_Review"].isin(test_ids)].copy()

    summary_rows = []
    confusion_sheets = []
    error_type_rows = []
    per_label_rows = []

    for aspect in aspects:
        label_col = f"label_{aspect}"
        pred_col = f"pred_{aspect}"
        conf_col = f"conf_{aspect}"
        y_true = test_pred[label_col]
        y_pred = test_pred[pred_col]

        metrics = classification_metrics(y_true, y_pred)
        summary_rows.append({
            "aspect": aspect,
            **{k: v for k, v in metrics.items() if k != "per_label"},
            "high_conf_wrong_80": int(((y_true != y_pred) & (test_pred[conf_col] >= 0.80)).sum()),
            "low_conf_pred_60": int((test_pred[conf_col] < 0.60).sum()),
            "avg_conf_correct": float(test_pred.loc[y_true == y_pred, conf_col].mean()),
            "avg_conf_wrong": float(test_pred.loc[y_true != y_pred, conf_col].mean()),
        })

        for row in metrics["per_label"]:
            per_label_rows.append({"aspect": aspect, **row})

        cm = confusion_matrix_df(y_true, y_pred)
        cm.insert(0, "aspect", aspect)
        confusion_sheets.append(cm)

        wrong = test_pred[y_true != y_pred].copy()
        if not wrong.empty:
            wrong["true_label"] = wrong[label_col]
            wrong["pred_label"] = wrong[pred_col]
            wrong["error_type"] = wrong["true_label"] + " -> " + wrong["pred_label"]
            type_counts = wrong["error_type"].value_counts().reset_index()
            type_counts.columns = ["error_type", "count"]
            for _, row in type_counts.iterrows():
                error_type_rows.append({
                    "aspect": aspect,
                    "error_type": row["error_type"],
                    "count": int(row["count"]),
                })

    summary = pd.DataFrame(summary_rows).sort_values(["non_none_macro_f1", "macro_f1"])
    per_label = pd.DataFrame(per_label_rows)
    confusion = pd.concat(confusion_sheets, ignore_index=True)
    error_types = pd.DataFrame(error_type_rows).sort_values(["aspect", "count"], ascending=[True, False])

    summary.to_csv(OUT_DIR / "model_error_summary_by_aspect.csv", index=False, encoding="utf-8-sig")
    per_label.to_csv(OUT_DIR / "model_error_per_label.csv", index=False, encoding="utf-8-sig")
    confusion.to_csv(OUT_DIR / "confusion_matrix_by_aspect.csv", index=False, encoding="utf-8-sig")
    error_types.to_csv(OUT_DIR / "error_type_counts.csv", index=False, encoding="utf-8-sig")

    # Full label distribution.
    label_dist_rows = []
    for aspect in aspects:
        counts = labeled[aspect].value_counts(dropna=False)
        for label in LABELS:
            label_dist_rows.append({
                "aspect": aspect,
                "label": label,
                "count": int(counts.get(label, 0)),
                "percentage": safe_div(int(counts.get(label, 0)), len(labeled)),
            })
    label_dist = pd.DataFrame(label_dist_rows)
    label_dist.to_csv(OUT_DIR / "label_distribution_full_dataset.csv", index=False, encoding="utf-8-sig")

    # Label consistency checks: label vs alasan.
    mismatch_rows = []
    for aspect in aspects:
        reason_col = f"Alasan_{aspect}"
        if reason_col not in labeled.columns:
            continue
        reason_present = labeled[reason_col].map(has_text)
        label_present = labeled[aspect] != "none"
        reason_but_none = labeled[reason_present & ~label_present].copy()
        label_but_no_reason = labeled[label_present & ~reason_present].copy()
        for kind, subset in [
            ("alasan_ada_tapi_label_none", reason_but_none),
            ("label_ada_tapi_alasan_kosong", label_but_no_reason),
        ]:
            for _, row in subset.head(300).iterrows():
                mismatch_rows.append({
                    "issue": kind,
                    "aspect": aspect,
                    "ID_Review": row["ID_Review"],
                    "Platform": row.get("Platform"),
                    "Nama_Hotel": row.get("Nama_Hotel"),
                    "Review_Date": row.get("Review_Date"),
                    "label": row[aspect],
                    "alasan": row.get(reason_col),
                    "Text_Review": row.get("Text_Review"),
                })
    label_reason_mismatch = pd.DataFrame(mismatch_rows)
    label_reason_mismatch.to_csv(OUT_DIR / "label_reason_mismatch_candidates.csv", index=False, encoding="utf-8-sig")

    # Duplicate text with conflicting aspect labels.
    label_cols = aspects
    dup_base = labeled.copy()
    dup_base["text_norm"] = dup_base["Text_Review"].fillna("").astype(str).str.lower().str.replace(r"\s+", " ", regex=True).str.strip()
    dup_groups = dup_base.groupby("text_norm", dropna=False)
    conflict_rows = []
    for text_norm, group in dup_groups:
        if len(group) <= 1 or not text_norm:
            continue
        conflicting_aspects = []
        for aspect in aspects:
            if group[aspect].nunique(dropna=False) > 1:
                conflicting_aspects.append(aspect)
        if conflicting_aspects:
            for _, row in group.iterrows():
                conflict_rows.append({
                    "issue": "duplicate_text_conflicting_labels",
                    "conflicting_aspects": ", ".join(conflicting_aspects),
                    "ID_Review": row["ID_Review"],
                    "Platform": row.get("Platform"),
                    "Nama_Hotel": row.get("Nama_Hotel"),
                    "Review_Date": row.get("Review_Date"),
                    "Text_Review": row.get("Text_Review"),
                    **{aspect: row[aspect] for aspect in aspects},
                })
    duplicate_conflicts = pd.DataFrame(conflict_rows)
    duplicate_conflicts.to_csv(OUT_DIR / "duplicate_text_conflicting_labels.csv", index=False, encoding="utf-8-sig")

    # Long reviews and multi-aspect reviews as truncation/complexity candidates.
    labeled["num_present_aspects"] = (labeled[aspects] != "none").sum(axis=1)
    complexity = labeled[
        (labeled["review_word_len"] >= 90)
        | (labeled["num_present_aspects"] >= 4)
    ].copy()
    complexity = complexity.sort_values(["num_present_aspects", "review_word_len"], ascending=[False, False])
    complexity_cols = [
        "ID_Review", "Platform", "Nama_Hotel", "Review_Date", "review_word_len",
        "review_char_len", "num_present_aspects", "Text_Review", *aspects
    ]
    complexity[complexity_cols].head(500).to_csv(
        OUT_DIR / "long_or_multi_aspect_review_candidates.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # Representative model errors from test split.
    error_sample_rows = []
    for aspect in aspects:
        label_col = f"label_{aspect}"
        pred_col = f"pred_{aspect}"
        conf_col = f"conf_{aspect}"
        wrong = test_pred[test_pred[label_col] != test_pred[pred_col]].copy()
        wrong["aspect"] = aspect
        wrong["true_label"] = wrong[label_col]
        wrong["pred_label"] = wrong[pred_col]
        wrong["confidence"] = wrong[conf_col]
        wrong["error_type"] = wrong["true_label"] + " -> " + wrong["pred_label"]
        wrong = wrong.sort_values(["confidence", "review_word_len"], ascending=[False, False])
        error_sample_rows.append(wrong.head(40)[[
            "aspect", "error_type", "confidence", "ID_Review", "Platform", "Nama_Hotel",
            "Review_Date", "review_word_len", "Text_Review", label_col, pred_col,
            f"Alasan_{aspect}",
        ]].rename(columns={label_col: "true_label_source", pred_col: "pred_label_source", f"Alasan_{aspect}": "alasan_aspect"}))
    error_samples = pd.concat(error_sample_rows, ignore_index=True)
    error_samples.to_csv(OUT_DIR / "high_confidence_error_samples.csv", index=False, encoding="utf-8-sig")

    # Prioritized manual audit candidates combine high-confidence wrong and label/reason mismatch.
    priority_rows = []
    for aspect in aspects:
        label_col = f"label_{aspect}"
        pred_col = f"pred_{aspect}"
        conf_col = f"conf_{aspect}"
        subset = test_pred[test_pred[label_col] != test_pred[pred_col]].copy()
        subset["aspect"] = aspect
        subset["true_label"] = subset[label_col]
        subset["pred_label"] = subset[pred_col]
        subset["confidence"] = subset[conf_col]
        subset["priority_reason"] = np.where(
            subset["confidence"] >= 0.80,
            "model_high_confidence_disagreement",
            "model_disagreement",
        )
        priority_rows.append(subset)
    priority = pd.concat(priority_rows, ignore_index=True)
    priority = priority.sort_values(["confidence", "review_word_len"], ascending=[False, False])
    priority[[
        "priority_reason", "aspect", "true_label", "pred_label", "confidence", "ID_Review",
        "Platform", "Nama_Hotel", "Review_Date", "review_word_len", "Text_Review",
    ]].head(300).to_csv(OUT_DIR / "priority_manual_audit_candidates.csv", index=False, encoding="utf-8-sig")

    # Compact markdown report.
    weakest = summary.head(3)
    highest_false = summary.sort_values("false_aspect_rate", ascending=False).head(3)
    highest_missed = summary.sort_values("missed_aspect_rate", ascending=False).head(3)
    label_summary = label_dist.pivot(index="aspect", columns="label", values="count").reset_index()
    weakest_label = per_label[per_label["label"] != "none"].sort_values("f1").head(7)
    total_high_conf_wrong = int(summary["high_conf_wrong_80"].sum())
    label_reason_issue_count = int(len(label_reason_mismatch))
    duplicate_conflict_count = int(len(duplicate_conflicts))
    complexity_count = int(len(complexity))

    report = []
    report.append("# Audit Label dan Error Analysis Model ABSA Hotel Santika\n")
    report.append("## Dataset\n")
    report.append(f"- Full labeled dataset: {len(labeled):,} review")
    report.append(f"- Test split: {len(test_pred):,} review")
    report.append(f"- Aspek: {', '.join(aspects)}\n")
    report.append("## Ringkasan Performa Test Split\n")
    report.append(markdown_table(summary[[
        "aspect", "accuracy", "macro_f1", "non_none_macro_f1", "aspect_detection_f1",
        "false_aspect_rate", "missed_aspect_rate", "high_conf_wrong_80",
    ]], floatfmt=".4f"))
    report.append("\n## Kesimpulan Cepat\n")
    report.append(
        f"- Total kandidat high-confidence wrong pada test split: {total_high_conf_wrong} prediksi aspek."
    )
    report.append(
        "- Aspek yang paling perlu diprioritaskan untuk audit model adalah "
        f"{', '.join(weakest['aspect'].tolist())} karena non-none macro F1 paling rendah."
    )
    report.append(
        "- Kelas netral adalah titik paling lemah hampir di semua aspek. Ini menunjukkan label netral perlu didefinisikan lebih tegas atau dipertimbangkan ulang."
    )
    report.append(
        f"- Ditemukan {label_reason_issue_count} kandidat inkonsistensi label-vs-alasan dan {duplicate_conflict_count} baris duplicate text dengan label berbeda."
    )
    report.append(
        f"- Ditemukan {complexity_count} review panjang atau multi-aspek yang rawan kehilangan konteks saat model memakai max_len 128."
    )
    report.append("\n## Aspek Prioritas Error Analysis\n")
    for _, row in weakest.iterrows():
        report.append(
            f"- {row['aspect']}: non-none macro F1 {row['non_none_macro_f1']:.2%}, "
            f"macro F1 {row['macro_f1']:.2%}, high-confidence wrong {int(row['high_conf_wrong_80'])}."
        )
    report.append("\n## Risiko False Aspect Tertinggi\n")
    for _, row in highest_false.iterrows():
        report.append(f"- {row['aspect']}: false aspect rate {row['false_aspect_rate']:.2%}.")
    report.append("\n## Risiko Missed Aspect Tertinggi\n")
    for _, row in highest_missed.iterrows():
        report.append(f"- {row['aspect']}: missed aspect rate {row['missed_aspect_rate']:.2%}.")
    report.append("\n## Distribusi Label Full Dataset\n")
    report.append(markdown_table(label_summary, floatfmt=".0f"))
    report.append("\n## Label Non-none dengan F1 Terlemah\n")
    report.append(markdown_table(weakest_label[[
        "aspect", "label", "support", "precision", "recall", "f1", "fp", "fn"
    ]], floatfmt=".4f"))
    report.append("\n## Catatan Audit Label\n")
    report.append(
        "- Kandidat audit utama ada pada file `priority_manual_audit_candidates.csv`, "
        "terutama baris dengan confidence tinggi tetapi prediksi berbeda dari label."
    )
    report.append(
        "- Review panjang dan multi-aspek ada pada `long_or_multi_aspect_review_candidates.csv`; "
        "kelompok ini rawan kehilangan konteks karena batas input model."
    )
    report.append(
        "- Cek juga `label_reason_mismatch_candidates.csv` dan `duplicate_text_conflicting_labels.csv` "
        "untuk mencari inkonsistensi label manual."
    )
    report.append("\n## Rekomendasi Urutan Perbaikan\n")
    report.append(
        "1. Audit 100 baris teratas pada `priority_manual_audit_candidates.csv`, terutama aspek Fasilitas dan Kenyamanan."
    )
    report.append(
        "2. Periksa semua baris pada `label_reason_mismatch_candidates.csv`; ini kandidat paling jelas untuk koreksi label atau alasan."
    )
    report.append(
        "3. Periksa `duplicate_text_conflicting_labels.csv` karena teks yang sama seharusnya tidak memiliki label aspek yang berbeda tanpa alasan kuat."
    )
    report.append(
        "4. Buat aturan guideline baru untuk kelas netral: kapan netral benar-benar dipakai dan kapan sebaiknya menjadi positif/negatif/none."
    )
    report.append(
        "5. Audit review panjang dan multi-aspek untuk menilai apakah perlu sentence chunking sebelum fine-tuning ulang."
    )
    report.append(
        "6. Setelah label dikoreksi, lakukan fine-tuning ulang dan bandingkan Macro F1, Non-none Macro F1, Aspect Detection F1, serta False Aspect Rate."
    )
    (OUT_DIR / "audit_error_analysis_report.md").write_text("\n".join(report), encoding="utf-8")

    manifest = {
        "outputs": [
            "audit_error_analysis_report.md",
            "model_error_summary_by_aspect.csv",
            "model_error_per_label.csv",
            "confusion_matrix_by_aspect.csv",
            "error_type_counts.csv",
            "label_distribution_full_dataset.csv",
            "label_reason_mismatch_candidates.csv",
            "duplicate_text_conflicting_labels.csv",
            "long_or_multi_aspect_review_candidates.csv",
            "high_confidence_error_samples.csv",
            "priority_manual_audit_candidates.csv",
        ]
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Audit selesai. Output: {OUT_DIR}")
    print(summary[["aspect", "macro_f1", "non_none_macro_f1", "aspect_detection_f1", "false_aspect_rate", "missed_aspect_rate"]].to_string(index=False))


if __name__ == "__main__":
    main()
