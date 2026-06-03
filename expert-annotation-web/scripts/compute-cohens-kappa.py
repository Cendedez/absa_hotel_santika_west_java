"""
Compute Cohen's Kappa between annotators (and vs the initial AI labels).

Inputs (place the exported CSVs next to this script or in the project root):
    annotations_researcher.csv
    annotations_expert_1.csv
    annotations_expert_2.csv

Optionally compares against the initial labels in:
    ../Data Labeling/dataset_absa_labeled.csv   (the "ai" annotator)

Per-aspect Cohen's Kappa is computed for these aspects:
    Lokasi, Kenyamanan, Pelayanan, Kebersihan, Harga, Makanan, Fasilitas

Label classes considered: None, positif, negatif, netral
(Empty cells in the AI dataset are normalized to "None".)

Output:
    kappa_results.csv

Usage:
    python scripts/compute-cohens-kappa.py

No external dependencies required (pure Python implementation of Cohen's Kappa).
"""

import csv
import os
import itertools

ASPECTS = ["Lokasi", "Kenyamanan", "Pelayanan", "Kebersihan", "Harga", "Makanan", "Fasilitas"]
CLASSES = ["None", "positif", "negatif", "netral"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)            # expert-annotation-web
ABSA_ROOT = os.path.dirname(PROJECT_ROOT)             # ABSA Hotel Santika

LABELED_CSV = os.path.join(ABSA_ROOT, "Data Labeling", "dataset_absa_labeled.csv")
OUT_CSV = os.path.join(PROJECT_ROOT, "kappa_results.csv")

ANNOTATION_FILES = {
    "researcher": "annotations_researcher.csv",
    "expert_1": "annotations_expert_1.csv",
    "expert_2": "annotations_expert_2.csv",
}


def find_file(name):
    """Look for an exported CSV in project root, script dir, or ABSA root."""
    for base in (PROJECT_ROOT, SCRIPT_DIR, ABSA_ROOT):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return None


def norm_label(v):
    v = (v or "").strip()
    if v == "" or v.lower() == "none":
        return "None"
    return v


def load_annotation_csv(path):
    """Returns dict: {ID_Review: {aspect: label}}."""
    data = {}
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rid = str(row.get("ID_Review", "")).strip()
            if not rid:
                continue
            data[rid] = {a: norm_label(row.get(a, "")) for a in ASPECTS}
    return data


def load_ai_labels(path):
    """Initial AI labels from the labeled dataset (column names match aspects)."""
    data = {}
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rid = str(row.get("ID_Review", "")).strip()
            if not rid:
                continue
            data[rid] = {a: norm_label(row.get(a, "")) for a in ASPECTS}
    return data


def cohens_kappa(labels_a, labels_b):
    """Cohen's Kappa for two equally-ordered lists of categorical labels."""
    n = len(labels_a)
    if n == 0:
        return None
    # observed agreement
    agree = sum(1 for x, y in zip(labels_a, labels_b) if x == y)
    po = agree / n
    # expected agreement
    pe = 0.0
    for c in CLASSES:
        pa = sum(1 for x in labels_a if x == c) / n
        pb = sum(1 for y in labels_b if y == c) / n
        pe += pa * pb
    if pe == 1.0:
        # perfect expected agreement (all one class) -> kappa undefined; treat as 1 if po==1
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def kappa_for_pair(data_a, data_b):
    """Returns (per_aspect dict, macro_avg). Uses common review IDs only."""
    common = sorted(set(data_a) & set(data_b), key=lambda x: int(x) if x.isdigit() else x)
    per_aspect = {}
    valid = []
    for aspect in ASPECTS:
        la = [data_a[r][aspect] for r in common]
        lb = [data_b[r][aspect] for r in common]
        k = cohens_kappa(la, lb)
        per_aspect[aspect] = k
        if k is not None:
            valid.append(k)
    macro = sum(valid) / len(valid) if valid else None
    return per_aspect, macro, len(common)


def fmt(v):
    return "" if v is None else f"{v:.4f}"


def main():
    # Load whichever annotation files exist.
    loaded = {}
    for name, fname in ANNOTATION_FILES.items():
        p = find_file(fname)
        if p:
            loaded[name] = load_annotation_csv(p)
            print(f"Loaded {name}: {len(loaded[name])} reviews ({p})")
        else:
            print(f"[skip] {fname} not found")

    # Optionally load AI labels.
    if os.path.exists(LABELED_CSV):
        loaded["ai"] = load_ai_labels(LABELED_CSV)
        print(f"Loaded ai (initial labels): {len(loaded['ai'])} reviews")

    if len(loaded) < 2:
        print("\nNeed at least 2 annotators to compute Kappa. Export CSVs first.")
        return

    rows = []
    for a, b in itertools.combinations(loaded.keys(), 2):
        per_aspect, macro, n_common = kappa_for_pair(loaded[a], loaded[b])
        print(f"\n=== {a} vs {b} (n={n_common} reviews) ===")
        for aspect in ASPECTS:
            print(f"  {aspect:12s}: {fmt(per_aspect[aspect])}")
        print(f"  {'MACRO AVG':12s}: {fmt(macro)}")
        for aspect in ASPECTS:
            rows.append({
                "pair": f"{a}_vs_{b}",
                "aspect": aspect,
                "kappa": fmt(per_aspect[aspect]),
                "n_common": n_common,
            })
        rows.append({
            "pair": f"{a}_vs_{b}",
            "aspect": "MACRO_AVG",
            "kappa": fmt(macro),
            "n_common": n_common,
        })

    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["pair", "aspect", "kappa", "n_common"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved results to {OUT_CSV}")


if __name__ == "__main__":
    main()
