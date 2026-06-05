from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(r"C:\Users\cencen04_\Downloads\ABSA Hotel Santika")
ORIG_PATH = BASE_DIR / "Data Labeling" / "dataset_absa_labeled.csv"
V3_PATH = BASE_DIR / "Audit Error Analysis" / "Step 1-3 Final Manual Review" / "dataset_absa_labeled_v3_final_audited.csv"
OUT_DIR = BASE_DIR / "Audit Error Analysis" / "Original vs V3 Comparison"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ASPECTS = ["Kenyamanan", "Kebersihan", "Pelayanan", "Harga", "Lokasi", "Fasilitas", "Makanan"]
LABELS = ["positif", "negatif", "netral", "none"]
REASON_COL = {aspect: f"Alasan_{aspect}" for aspect in ASPECTS}


def norm_label(value: object) -> str:
    if pd.isna(value):
        return "none"
    text = str(value).strip().lower()
    if text in {"", "nan", "none", "-", "null"}:
        return "none"
    return text


def norm_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null", "-"}:
        return ""
    return " ".join(text.split())


def markdown_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
    if df.empty:
        return "_Tidak ada data._"
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in df.iterrows():
        vals = []
        for col in cols:
            value = row[col]
            if pd.isna(value):
                value = ""
            vals.append(str(value).replace("\n", " ").replace("|", "/"))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def main() -> None:
    orig = pd.read_csv(ORIG_PATH)
    v3 = pd.read_csv(V3_PATH)

    if orig.shape != v3.shape:
        raise ValueError(f"Shape berbeda: original={orig.shape}, v3={v3.shape}")
    if set(orig["ID_Review"]) != set(v3["ID_Review"]):
        raise ValueError("Set ID_Review berbeda antara dataset original dan v3.")

    orig = orig.sort_values("ID_Review").reset_index(drop=True)
    v3 = v3.sort_values("ID_Review").reset_index(drop=True)

    distribution_rows: list[dict[str, object]] = []
    label_change_rows: list[dict[str, object]] = []
    reason_change_rows: list[dict[str, object]] = []
    transition_rows: list[dict[str, object]] = []

    for aspect in ASPECTS:
        orig_labels = orig[aspect].map(norm_label)
        v3_labels = v3[aspect].map(norm_label)

        for label in LABELS:
            original_count = int((orig_labels == label).sum())
            v3_count = int((v3_labels == label).sum())
            distribution_rows.append(
                {
                    "aspect": aspect,
                    "label": label,
                    "original_count": original_count,
                    "v3_count": v3_count,
                    "delta": v3_count - original_count,
                    "original_pct": round(original_count / len(orig), 6),
                    "v3_pct": round(v3_count / len(v3), 6),
                }
            )

        changed_mask = orig_labels != v3_labels
        for old_label in LABELS:
            for new_label in LABELS:
                count = int(((orig_labels == old_label) & (v3_labels == new_label)).sum())
                if count:
                    transition_rows.append(
                        {
                            "aspect": aspect,
                            "original_label": old_label,
                            "v3_label": new_label,
                            "count": count,
                            "is_changed": old_label != new_label,
                        }
                    )

        changed_indices = changed_mask[changed_mask].index
        for idx in changed_indices:
            label_change_rows.append(
                {
                    "ID_Review": int(orig.at[idx, "ID_Review"]),
                    "aspect": aspect,
                    "original_label": orig_labels.iloc[idx],
                    "v3_label": v3_labels.iloc[idx],
                    "Platform": v3.at[idx, "Platform"],
                    "Nama_Hotel": v3.at[idx, "Nama_Hotel"],
                    "Review_Date": v3.at[idx, "Review_Date"],
                    "Text_Review": v3.at[idx, "Text_Review"],
                    "original_reason": norm_text(orig.at[idx, REASON_COL[aspect]]),
                    "v3_reason": norm_text(v3.at[idx, REASON_COL[aspect]]),
                }
            )

        orig_reason = orig[REASON_COL[aspect]].map(norm_text)
        v3_reason = v3[REASON_COL[aspect]].map(norm_text)
        reason_changed_mask = orig_reason != v3_reason
        for idx in reason_changed_mask[reason_changed_mask].index:
            reason_change_rows.append(
                {
                    "ID_Review": int(orig.at[idx, "ID_Review"]),
                    "aspect": aspect,
                    "original_label": orig_labels.iloc[idx],
                    "v3_label": v3_labels.iloc[idx],
                    "original_reason": orig_reason.iloc[idx],
                    "v3_reason": v3_reason.iloc[idx],
                    "Text_Review": v3.at[idx, "Text_Review"],
                }
            )

    distribution_df = pd.DataFrame(distribution_rows)
    transition_df = pd.DataFrame(transition_rows)
    label_changes_df = pd.DataFrame(label_change_rows)
    reason_changes_df = pd.DataFrame(reason_change_rows)

    aspect_change_summary = (
        label_changes_df.groupby("aspect").size().reset_index(name="label_changed_count")
        if not label_changes_df.empty
        else pd.DataFrame(columns=["aspect", "label_changed_count"])
    )
    aspect_reason_summary = (
        reason_changes_df.groupby("aspect").size().reset_index(name="reason_changed_count")
        if not reason_changes_df.empty
        else pd.DataFrame(columns=["aspect", "reason_changed_count"])
    )
    aspect_summary = pd.DataFrame({"aspect": ASPECTS})
    aspect_summary = aspect_summary.merge(aspect_change_summary, on="aspect", how="left")
    aspect_summary = aspect_summary.merge(aspect_reason_summary, on="aspect", how="left")
    aspect_summary[["label_changed_count", "reason_changed_count"]] = (
        aspect_summary[["label_changed_count", "reason_changed_count"]].fillna(0).astype(int)
    )
    aspect_summary["label_changed_pct_of_rows"] = (aspect_summary["label_changed_count"] / len(orig)).round(6)

    changed_transition_df = transition_df[transition_df["is_changed"]].copy()
    changed_transition_df = changed_transition_df.sort_values(["aspect", "count"], ascending=[True, False])

    distribution_df.to_csv(OUT_DIR / "label_distribution_original_vs_v3.csv", index=False, encoding="utf-8-sig")
    transition_df.to_csv(OUT_DIR / "label_transition_original_vs_v3.csv", index=False, encoding="utf-8-sig")
    changed_transition_df.to_csv(OUT_DIR / "label_transition_changed_only.csv", index=False, encoding="utf-8-sig")
    label_changes_df.to_csv(OUT_DIR / "label_changes_original_vs_v3.csv", index=False, encoding="utf-8-sig")
    reason_changes_df.to_csv(OUT_DIR / "reason_changes_original_vs_v3.csv", index=False, encoding="utf-8-sig")
    aspect_summary.to_csv(OUT_DIR / "aspect_change_summary_original_vs_v3.csv", index=False, encoding="utf-8-sig")

    total_label_cells = len(orig) * len(ASPECTS)
    total_label_changes = len(label_changes_df)
    total_reason_changes = len(reason_changes_df)
    reviews_with_any_label_change = label_changes_df["ID_Review"].nunique() if not label_changes_df.empty else 0
    reviews_with_any_reason_change = reason_changes_df["ID_Review"].nunique() if not reason_changes_df.empty else 0

    top_transitions = changed_transition_df.sort_values("count", ascending=False).head(15)
    non_zero_distribution = distribution_df[distribution_df["delta"] != 0].sort_values(["aspect", "label"])
    examples = label_changes_df.sort_values(["aspect", "ID_Review"]).head(20)

    summary = f"""# Perbandingan Dataset Original vs V3 Audited

## Integritas Dataset

- Dataset original: `{ORIG_PATH}`
- Dataset v3 audited: `{V3_PATH}`
- Jumlah review original: {len(orig):,}
- Jumlah review v3: {len(v3):,}
- Jumlah kolom: {orig.shape[1]}
- Set `ID_Review` sama: Ya

## Ringkasan Perubahan

- Total sel label yang dibandingkan: {total_label_cells:,} sel label ({len(orig):,} review x {len(ASPECTS)} aspek)
- Total perubahan label: {total_label_changes:,} sel label
- Persentase perubahan label terhadap seluruh sel label: {total_label_changes / total_label_cells:.4%}
- Review yang memiliki minimal satu perubahan label: {reviews_with_any_label_change:,}
- Total perubahan alasan: {total_reason_changes:,}
- Review yang memiliki minimal satu perubahan alasan: {reviews_with_any_reason_change:,}

## Perubahan Per Aspek

{markdown_table(aspect_summary)}

## Perubahan Distribusi Label

{markdown_table(non_zero_distribution)}

## Transisi Label Terbesar

{markdown_table(top_transitions)}

## Contoh Perubahan Label

{markdown_table(examples, max_rows=20)}

## Interpretasi Singkat

- Dataset v3 tidak mengubah struktur data, jumlah review, atau ID review.
- Perubahan v3 bersifat targeted correction dari hasil audit error analysis, bukan relabeling total.
- Kelas `netral` berkurang pada semua aspek karena guideline final memperketat penggunaan `netral`; kelas ini hanya dipakai ketika aspek disebut secara deskriptif tanpa evaluasi jelas.
- Beberapa label `none` berubah menjadi `positif` atau `negatif` ketika review sebenarnya memuat aspek dan sentimen yang jelas.
- Beberapa label sentimen berubah menjadi `none` ketika alasan/aspek tidak cukup kuat atau alasan berada di aspek yang salah.
"""
    (OUT_DIR / "comparison_summary_original_vs_v3.md").write_text(summary, encoding="utf-8")

    print(summary)
    print("Output directory:", OUT_DIR)


if __name__ == "__main__":
    main()
