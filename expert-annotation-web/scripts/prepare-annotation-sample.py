"""
Prepare 50 review sample for expert annotation.

- Reads the labeled dataset to find reviews that have >= 1 aspect labeled.
- Applies a QUALITY FILTER so only human-understandable reviews are eligible
  (no truncation markers like "selengkapnya"/"lihat lebih sedikit", no #NAME?
  errors, no overly-short or noisy text).
- Samples 50 review_ids with a FIXED random seed (reproducible).
- Joins with the clean dataset to get the display text/metadata.
- Writes src/data/annotation_reviews.json WITHOUT any label info.

The output JSON only contains:
    ID_Review, Platform, Nama_Hotel, Review_Date, Text_Review

Run from the project root:
    python scripts/prepare-annotation-sample.py
"""

import csv
import json
import os
import random
import re
from datetime import date, datetime

# --- configuration ---
SEED = 42
SAMPLE_SIZE = 50
MIN_REVIEW_DATE = date(2017, 5, 1)
MIN_LEN = 40   # minimum characters for a review to be understandable
MIN_WORDS = 6  # minimum word count
MAX_LEN = 700  # keep expert annotation readable and not too time-consuming
MAX_WORDS = 120
ASPECTS = ["Kenyamanan", "Kebersihan", "Pelayanan", "Harga", "Lokasi", "Fasilitas", "Makanan"]

# Truncation / scraping artefacts that make a review confusing to annotate.
# These typically appear at (or near) the END of a cut-off review.
TRUNCATION_TAIL = [
    "selengkapnya",
    "baca selengkapnya",
    "lihat lebih sedikit",
    "lihat lebih banyak",
    "lihat selengkapnya",
    "tampilkan lebih sedikit",
    "tampilkan lebih banyak",
    "show more",
    "show less",
    "see more",
    "see less",
    "read more",
]

# Hard junk that should never be annotated.
JUNK_EXACT = {"#name?", "#value!", "#ref!", "#n/a", "null", "none", "-", ".", ""}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)                 # expert-annotation-web
ABSA_ROOT = os.path.dirname(PROJECT_ROOT)                  # ABSA Hotel Santika

LABELED_CSV = os.path.join(ABSA_ROOT, "Data Labeling", "dataset_absa_labeled.csv")
CLEAN_CSV = os.path.join(ABSA_ROOT, "Data Preprocessing", "dataset_absa_santika_clean.csv")
OUT_JSON = os.path.join(PROJECT_ROOT, "src", "data", "annotation_reviews.json")


def read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def parse_review_date(value):
    """Parse the date formats found in the clean dataset."""
    text = (value or "").strip()
    if not text:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def is_good_quality(text):
    """Return True if the review text is clean enough for human annotation."""
    t = (text or "").strip()
    low = t.lower()

    # 1. Junk / formula errors
    if low in JUNK_EXACT:
        return False
    if low.startswith("#") and low.endswith("?"):
        return False

    # 2. Truncation markers (cut-off reviews are confusing)
    for m in TRUNCATION_TAIL:
        # marker anywhere is suspicious; truncation usually sits in the last 30 chars
        if m in low:
            return False
    # standalone "selengkapnya" / ellipsis at the end
    if low.rstrip(" .…").endswith("dst") or low.endswith("…") or low.endswith("..."):
        return False

    # 3. Length / word-count thresholds (must have enough content)
    if len(t) < MIN_LEN:
        return False
    words = re.findall(r"\w+", low)
    if len(words) < MIN_WORDS:
        return False
    if len(t) > MAX_LEN:
        return False
    if len(words) > MAX_WORDS:
        return False

    # 4. Mostly non-letters (e.g. emoji/symbol spam)
    letters = sum(c.isalpha() for c in t)
    if letters < len(t) * 0.5:
        return False

    return True


def main():
    labeled = read_csv(LABELED_CSV)
    clean = read_csv(CLEAN_CSV)

    # Build clean lookup by review id (clean uses lowercase column names).
    clean_map = {}
    for row in clean:
        rid = (row.get("review_id") or row.get("\ufeffreview_id") or "").strip()
        if rid:
            clean_map[rid] = row

    # Eligibility:
    # - labeled (>=1 aspect)
    # - present in clean data
    # - dated from May 2017 onward
    # - readable enough for expert annotation
    eligible_ids = []
    skipped_date = 0
    skipped_quality = 0
    for row in labeled:
        rid = str(row.get("ID_Review", "")).strip()
        if not rid or rid not in clean_map:
            continue
        has_aspect = any((row.get(a) or "").strip() for a in ASPECTS)
        if not has_aspect:
            continue
        review_date = parse_review_date(clean_map[rid].get("date", ""))
        if review_date is None or review_date < MIN_REVIEW_DATE:
            skipped_date += 1
            continue
        text = clean_map[rid].get("text_review", "")
        if not is_good_quality(text):
            skipped_quality += 1
            continue
        eligible_ids.append(rid)

    eligible_ids = sorted(set(eligible_ids), key=lambda x: int(x))
    print(
        "Eligible reviews (>=1 aspect, in clean, "
        f"date >= {MIN_REVIEW_DATE.isoformat()}, good quality): {len(eligible_ids)}"
    )
    print(f"Skipped because date is before May 2017 / invalid     : {skipped_date}")
    print(f"Skipped due to low quality / truncation / junk        : {skipped_quality}")
    if len(eligible_ids) < SAMPLE_SIZE:
        raise RuntimeError(
            f"Only {len(eligible_ids)} eligible reviews found; need {SAMPLE_SIZE}."
        )

    # Reproducible sampling.
    rng = random.Random(SEED)
    if len(eligible_ids) <= SAMPLE_SIZE:
        sampled = eligible_ids
    else:
        sampled = rng.sample(eligible_ids, SAMPLE_SIZE)
    sampled = sorted(sampled, key=lambda x: int(x))

    out = []
    for rid in sampled:
        c = clean_map[rid]
        out.append({
            "ID_Review": rid,
            "Platform": (c.get("platform") or "").strip(),
            "Nama_Hotel": (c.get("hotel_name") or "").strip(),
            "Review_Date": (c.get("date") or "").strip(),
            "Text_Review": (c.get("text_review") or "").strip(),
        })

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(out)} reviews to {OUT_JSON}")
    print(f"Seed={SEED} (sampling is reproducible)")


if __name__ == "__main__":
    main()
