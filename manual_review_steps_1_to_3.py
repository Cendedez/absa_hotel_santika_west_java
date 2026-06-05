from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import pandas as pd


BASE_DIR = Path(r"C:\Users\cencen04_\Downloads\ABSA Hotel Santika")
STEP14_DIR = BASE_DIR / "Audit Error Analysis" / "Step 1-4 Label Audit"
OUTPUT_DIR = BASE_DIR / "Audit Error Analysis" / "Step 1-3 Final Manual Review"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DATASET_V2_PATH = STEP14_DIR / "dataset_absa_labeled_v2_audited.csv"
NEEDS_REVIEW_PATH = STEP14_DIR / "needs_manual_review_after_step_1_4.csv"
CONSISTENCY_PATH = STEP14_DIR / "remaining_label_reason_consistency_issues.csv"

ASPECTS = [
    "Kenyamanan",
    "Kebersihan",
    "Pelayanan",
    "Harga",
    "Lokasi",
    "Fasilitas",
    "Makanan",
]
REASON_COL = {aspect: f"Alasan_{aspect}" for aspect in ASPECTS}
VALID_LABELS = {"positif", "negatif", "netral", "none"}
SENTIMENT_LABELS = {"positif", "negatif", "netral"}

ASPECT_TERMS = {
    "Kenyamanan": [
        "nyaman", "tidak nyaman", "kurang nyaman", "kamar", "room", "tidur", "kasur", "bed",
        "bantal", "ac", "air conditioner", "dingin", "panas", "suara", "berisik", "tenang",
        "luas", "sempit", "gelap", "bau rokok", "view", "pemandangan", "suasana",
    ],
    "Kebersihan": [
        "bersih", "kotor", "kebersihan", "debu", "bau", "linen", "handuk", "noda", "rambut",
        "toilet", "kecoak", "serangga", "jorok", "wangi", "segar", "piring kotor",
    ],
    "Pelayanan": [
        "pelayanan", "layanan", "staf", "staff", "pegawai", "resepsionis", "receptionist",
        "front desk", "ramah", "responsif", "check-in", "check in", "check-out", "check out",
        "proses", "security", "satpam", "bantuan", "dibantu", "karyawan",
    ],
    "Harga": [
        "harga", "murah", "mahal", "budget", "price", "rate", "tarif", "biaya", "value",
        "sepadan", "worth", "sesuai", "tidak sesuai", "terjangkau", "gratis", "bayar",
    ],
    "Lokasi": [
        "lokasi", "strategis", "dekat", "jauh", "akses", "mall", "mal", "pusat kota",
        "stasiun", "bandara", "transportasi", "jalan", "parkir", "area", "sekitar",
    ],
    "Fasilitas": [
        "fasilitas", "kolam", "kolam renang", "pool", "lift", "wifi", "wi-fi", "internet",
        "shower", "air panas", "water heater", "hairdryer", "tv", "televisi", "kulkas",
        "mini bar", "parkir", "lobi", "lobby", "gym", "saluran televisi", "floordrain",
        "drainase", "wastafel", "kamar mandi", "bathroom", "toilet", "shuttle",
    ],
    "Makanan": [
        "makanan", "sarapan", "breakfast", "makan", "menu", "restoran", "restaurant",
        "rasa", "enak", "variasi", "bervariasi", "sahur", "kopi", "minuman", "buffet",
        "makan pagi", "satapan",
    ],
}

POSITIVE_TERMS = [
    "baik", "bagus", "mantap", "mantab", "puas", "memuaskan", "nyaman", "bersih",
    "ramah", "responsif", "cepat", "mudah", "strategis", "dekat", "enak", "lezat",
    "bervariasi", "banyak pilihan", "lengkap", "murah", "terjangkau", "worth", "sepadan",
    "sesuai", "luas", "besar", "aman", "menyenangkan", "terbaik", "indah", "berkesan",
    "gratis", "berfungsi", "dingin", "rapi", "wangi", "segar", "hebat", "recommended",
    "pesona", "mengesankan",
]
NEGATIVE_TERMS = [
    "buruk", "jelek", "kurang", "mahal",
    "kotor", "bau", "lambat", "lama", "susah", "sulit", "kecil", "sempit", "gelap",
    "berisik", "kecewa", "mengecewakan", "rusak", "mati", "mampet", "menggenang",
    "tidak sesuai", "tidak sepadan", "tidak berfungsi", "tidak ada", "kurang menarik",
    "kurang baik", "kurang enak", "biasa saja", "standar", "minim", "sedikit",
    "kecoak", "serangga", "noda", "rambut", "jorok", "dingin sekali", "panas",
    "perlu menambahkan", "perlu tambah", "perlu diperbaiki", "terputus",
]
NEUTRAL_TERMS = [
    "ada", "tersedia", "terletak", "berada", "di sebelah", "di dekat", "satu kawasan",
]


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def norm_label(value: object) -> str:
    text = clean_text(value).lower()
    if text in {"", "nan", "none", "-", "null"}:
        return "none"
    return text if text in VALID_LABELS else text


def is_blank(value: object) -> bool:
    return clean_text(value).lower() in {"", "nan", "none", "-", "null"}


def split_sentences(text: object) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+|;\s+|\n+", text)
    return [clean_text(part) for part in parts if clean_text(part)] or [text]


def contains_term(text: str, terms: Iterable[str]) -> bool:
    lower = text.lower()
    return any(term in lower for term in terms)


def count_terms(text: str, terms: Iterable[str]) -> int:
    lower = text.lower()
    return sum(lower.count(term) for term in terms if term in lower)


def extract_proposal_terms(value: object) -> list[str]:
    text = clean_text(value).lower()
    if not text or text == "no aspect keyword detected":
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def aspect_sentences(review: str, aspect: str, extra_terms: Iterable[str] = ()) -> list[str]:
    terms = list(dict.fromkeys([*ASPECT_TERMS[aspect], *extract_proposal_terms(", ".join(extra_terms))]))
    sentences = split_sentences(review)
    matched = [sentence for sentence in sentences if contains_term(sentence, terms)]
    return matched or []


def sentiment_score(sentence: str, aspect: str = "") -> tuple[int, int, int]:
    lower = sentence.lower()
    pos = count_terms(lower, POSITIVE_TERMS)
    neg = count_terms(lower, NEGATIVE_TERMS)

    # Aspect-aware corrections for phrases that are commonly mislabeled by generic cues.
    if aspect == "Harga":
        if "tidak sesuai dengan harga" in lower or "kurang sepadan" in lower or "tidak sepadan" in lower:
            neg += 3
        if "sesuai dengan budget" in lower or "sesuai budget" in lower or "valuable price" in lower:
            pos += 3
        if "harga masuk akal" in lower or "masuk akal" in lower:
            pos += 3
    if aspect == "Fasilitas":
        if "tidak ada" in lower or "tidak berfungsi" in lower or "mampet" in lower or "air menggenang" in lower:
            neg += 3
        if "kurang dingin" in lower or "kurang nyaman" in lower:
            neg += 4
        if "terputus" in lower:
            neg += 3
        if "perlu menambahkan" in lower or "perlu tambah" in lower or "perlu diperbaiki" in lower:
            neg += 3
        if "pesona" in lower or "mengesankan" in lower:
            pos += 3
        if "ada kolam" in lower or "fasilitas" in lower and ("baik" in lower or "bagus" in lower):
            pos += 2
    if aspect == "Makanan":
        if "biasa saja" in lower or "kurang enak" in lower or "tidak enak" in lower:
            neg += 3
        if "tapi enak" in lower or "tetapi enak" in lower:
            pos += 4
        if "sarapan sangat nyaman" in lower:
            pos += 2
    if aspect == "Pelayanan":
        service_pos = 0
        service_neg = 0
        if "ramah" in lower or "responsif" in lower or "dibantu" in lower:
            service_pos += 3
        if ("cepat" in lower or "mudah" in lower or "baik" in lower or "bagus" in lower) and (
            "pelayanan" in lower or "layanan" in lower or "staf" in lower or "staff" in lower
            or "check-in" in lower or "check in" in lower or "check-out" in lower or "check out" in lower
        ):
            service_pos += 2
        if "tidak ramah" in lower or "kurang ramah" in lower:
            service_neg += 4
        if ("lama" in lower or "lambat" in lower) and (
            "pelayanan" in lower or "layanan" in lower or "proses" in lower
            or "check-in" in lower or "check in" in lower
        ):
            service_neg += 3
        if ("kurang" in lower or "buruk" in lower) and (
            "pelayanan" in lower or "layanan" in lower or "staf" in lower or "staff" in lower
        ):
            service_neg += 3
        if "tidak ada pengingat" in lower or "tidak diingatkan" in lower:
            service_neg += 3
        if service_pos or service_neg:
            pos = service_pos
            neg = service_neg
        else:
            # Incidental mentions like "dibersihkan oleh staf" should not inherit
            # negative facility words such as "shower lambat".
            pos = 0
            neg = 0
    if aspect == "Kebersihan":
        if "bau" in lower or "kotor" in lower or "noda" in lower or "kecoak" in lower:
            neg += 3
        if "bersih" in lower:
            pos += 2
    if aspect == "Kenyamanan":
        if "kurang nyaman" in lower or "tidak nyaman" in lower or "berisik" in lower or "gelap" in lower:
            neg += 3
        if "nyaman" in lower and "kurang nyaman" not in lower and "tidak nyaman" not in lower:
            pos += 2
    if aspect == "Lokasi":
        if "strategis" in lower or "dekat" in lower:
            pos += 2
        if "akses" in lower and ("susah" in lower or "sulit" in lower or "lama" in lower):
            neg += 3

    neutral = count_terms(lower, NEUTRAL_TERMS)
    return pos, neg, neutral


def has_specific_aspect_evidence(aspect: str, reason: str) -> bool:
    lower = reason.lower()
    if not lower:
        return False
    if aspect == "Makanan":
        if "cari makanan" in lower or "makanan dekat" in lower or "makanan sangat dekat" in lower:
            return False
        return any(
            term in lower
            for term in [
                "sarapan", "breakfast", "makan pagi", "menu", "rasa", "restoran",
                "restaurant", "variasi", "bervariasi", "sahur", "satapan",
            ]
        ) or ("makanan" in lower and contains_term(lower, ["enak", "biasa saja", "kurang", "variasi", "banyak pilihan"]))
    if aspect == "Harga":
        return any(term in lower for term in ["harga", "budget", "price", "rate", "value", "sepadan", "sesuai", "murah", "mahal", "gratis", "bayar"])
    if aspect == "Lokasi":
        return any(term in lower for term in ["lokasi", "strategis", "dekat", "jauh", "akses", "mall", "mal", "stasiun", "pusat kota", "transportasi"])
    if aspect == "Pelayanan":
        return any(term in lower for term in ["pelayanan", "layanan", "staf", "staff", "resepsionis", "receptionist", "check-in", "check in", "check-out", "check out", "ramah", "responsif", "dibantu", "karyawan"])
    if aspect == "Kebersihan":
        return any(term in lower for term in ["bersih", "kotor", "kebersihan", "bau", "linen", "handuk", "noda", "rambut", "kecoak", "debu", "jorok"])
    if aspect == "Kenyamanan":
        return any(term in lower for term in ["nyaman", "tidak nyaman", "kurang nyaman", "kamar", "room", "tidur", "kasur", "ac", "air conditioner", "berisik", "gelap", "luas", "sempit", "view", "pemandangan"])
    if aspect == "Fasilitas":
        return any(term in lower for term in ["fasilitas", "kolam", "lift", "wifi", "wi-fi", "shower", "air panas", "water heater", "hairdryer", "tv", "televisi", "kulkas", "mini bar", "parkir", "kamar mandi", "wastafel", "drainase", "floordrain"])
    return False


def has_clear_sentiment(reason: str, aspect: str) -> bool:
    pos, neg, _ = sentiment_score(reason, aspect)
    return abs(pos - neg) >= 2 or pos + neg >= 2


def safe_to_apply_inferred(aspect: str, inferred: str, reason: str) -> bool:
    if inferred not in SENTIMENT_LABELS:
        return False
    if not has_specific_aspect_evidence(aspect, reason):
        return False
    if inferred == "netral":
        # Netral is intentionally conservative after audit because it was the weakest class.
        return False
    pos, neg, _ = sentiment_score(reason, aspect)
    if inferred == "positif":
        return pos >= neg + 1 and (abs(pos - neg) >= 2 or pos >= 2)
    if inferred == "negatif":
        return neg >= pos + 1 and (abs(pos - neg) >= 2 or neg >= 2)
    return False


def infer_label(review: str, aspect: str, extra_terms: Iterable[str] = ()) -> tuple[str, str, str]:
    matched = aspect_sentences(review, aspect, extra_terms)
    if not matched:
        return "none", "", "Tidak ada bukti aspek yang cukup pada teks review."

    scored: list[tuple[float, str, int, int, int]] = []
    for sentence in matched:
        pos, neg, neu = sentiment_score(sentence, aspect)
        score = abs(pos - neg) * 3 + pos + neg + neu + min(len(sentence), 160) / 160
        scored.append((score, sentence, pos, neg, neu))
    scored.sort(key=lambda item: item[0], reverse=True)
    _, reason, pos_total, neg_total, neu_total = scored[0]

    # Aggregate nearby evidence so multi-sentence reviews are not decided by a weak sentence only.
    agg_pos = sum(item[2] for item in scored)
    agg_neg = sum(item[3] for item in scored)
    agg_neu = sum(item[4] for item in scored)

    if agg_pos == 0 and agg_neg == 0:
        return "netral", reason[:320], "Aspek muncul tetapi tidak ada evaluasi positif/negatif yang kuat."
    if agg_pos >= agg_neg + 2:
        return "positif", reason[:320], "Bukti aspek condong positif."
    if agg_neg >= agg_pos + 2:
        return "negatif", reason[:320], "Bukti aspek condong negatif."
    if agg_pos > agg_neg:
        return "positif", reason[:320], "Bukti aspek sedikit lebih positif."
    if agg_neg > agg_pos:
        return "negatif", reason[:320], "Bukti aspek sedikit lebih negatif."
    if agg_neu:
        return "netral", reason[:320], "Bukti aspek bersifat deskriptif/netral."
    return "netral", reason[:320], "Bukti positif dan negatif seimbang."


def choose_decision(row: pd.Series) -> dict[str, object]:
    aspect = clean_text(row.get("aspect"))
    review = clean_text(row.get("Text_Review"))
    action = clean_text(row.get("recommended_action"))
    current = norm_label(row.get("current_label"))
    model_pred = norm_label(row.get("model_prediction"))
    suggested = norm_label(row.get("suggested_label"))
    proposal_terms = extract_proposal_terms(row.get("aspect_evidence"))
    inferred, reason, note = infer_label(review, aspect, proposal_terms)

    final = current
    decision = "keep_current_label"
    confidence_note = note

    if action in {"likely_missing_label", "possible_missing_label"}:
        if current == "none" and safe_to_apply_inferred(aspect, inferred, reason):
            final = inferred
            decision = "apply_missing_label_from_manual_review"
        elif current == "none":
            final = "none"
            reason = ""
            decision = "keep_none_no_clear_aspect_sentiment"

    elif action == "possible_label_false_positive":
        if inferred == "none":
            final = "none"
            reason = ""
            decision = "clear_false_positive_label"
        elif safe_to_apply_inferred(aspect, inferred, reason):
            final = inferred
            decision = "adjust_or_keep_label_with_evidence"
        else:
            final = current
            reason = clean_text(row.get("current_reason")) or reason
            decision = "keep_current_label_evidence_not_strong_enough"

    elif action == "label_without_evidence_review":
        if inferred == "none":
            final = "none"
            reason = ""
            decision = "clear_label_without_evidence"
        else:
            final = inferred if safe_to_apply_inferred(aspect, inferred, reason) else current
            decision = "keep_label_add_reason"

    elif action == "reason_likely_wrong_aspect":
        if current == "none":
            final = "none"
            reason = ""
            decision = "clear_reason_wrong_aspect"
        elif inferred in SENTIMENT_LABELS:
            final = inferred
            decision = "fix_reason_for_existing_label"

    elif action == "possible_sentiment_label_review":
        if safe_to_apply_inferred(aspect, inferred, reason):
            final = inferred
            decision = "resolve_sentiment_by_text_evidence"
        elif inferred == "none":
            final = "none"
            reason = ""
            decision = "clear_aspect_no_evidence"

    elif action == "sentiment_conflict_needs_expert":
        if inferred == "none":
            final = "none"
            reason = ""
            decision = "clear_aspect_no_evidence"
        elif current == "netral" and safe_to_apply_inferred(aspect, inferred, reason):
            final = inferred
            decision = "change_neutral_sentiment_after_manual_review"
        elif current in {"positif", "negatif"}:
            # For conflicts involving an existing positive/negative label, keep the human label
            # only when the existing reason still supports the aspect. Otherwise clear it.
            current_reason = clean_text(row.get("current_reason"))
            current_supported = safe_to_apply_inferred(aspect, current, current_reason) or safe_to_apply_inferred(aspect, current, reason)
            if current_supported:
                final = current
                reason = current_reason or reason
                decision = "keep_current_after_manual_review"
            elif safe_to_apply_inferred(aspect, inferred, reason) and inferred != current:
                final = inferred
                decision = "change_sentiment_after_manual_review"
            else:
                final = "none"
                reason = ""
                decision = "clear_aspect_no_sufficient_evidence"
        elif inferred in SENTIMENT_LABELS:
            final = inferred
            if inferred == current:
                decision = "keep_current_after_manual_review"
            else:
                decision = "change_sentiment_after_manual_review"

    # Guardrail: do not convert a non-none current label to netral unless the text is clearly descriptive only.
    if final == "netral" and current in {"positif", "negatif"}:
        pos, neg, _ = sentiment_score(reason, aspect)
        if pos or neg:
            final = current
            decision = "keep_current_avoid_overusing_neutral"
            confidence_note = "Netral tidak dipakai karena masih ada cue evaluatif; label awal dipertahankan."

    if final == "none":
        reason = ""
    elif is_blank(reason):
        reason = clean_text(row.get("current_reason"))
    if decision.startswith("keep_current") and not is_blank(row.get("current_reason")):
        reason = clean_text(row.get("current_reason"))
    if final in SENTIMENT_LABELS and not safe_to_apply_inferred(aspect, final, reason) and current in {"positif", "negatif"}:
        # Keep existing positive/negative labels, but avoid replacing their reason with weak evidence.
        reason = clean_text(row.get("current_reason")) or reason
    if final in SENTIMENT_LABELS and is_blank(reason):
        reason = make_fallback_reason(review, aspect)

    return {
        "manual_decision": decision,
        "manual_final_label": final,
        "manual_final_reason": reason,
        "manual_review_note": confidence_note,
        "inferred_label": inferred,
        "inferred_reason": reason,
    }


def make_fallback_reason(review: str, aspect: str) -> str:
    matched = aspect_sentences(review, aspect)
    if matched:
        return matched[0][:320]
    return clean_text(review)[:320]


def apply_label_reason(df: pd.DataFrame, review_id: int, aspect: str, new_label: str, new_reason: str) -> tuple[str, str, str, str]:
    idx = df.index[df["ID_Review"] == review_id]
    if len(idx) == 0:
        return "missing_id", "", "", ""
    i = idx[0]
    old_label = norm_label(df.at[i, aspect])
    old_reason = clean_text(df.at[i, REASON_COL[aspect]])
    df.at[i, aspect] = pd.NA if new_label == "none" else new_label
    df.at[i, REASON_COL[aspect]] = pd.NA if new_label == "none" or is_blank(new_reason) else new_reason
    return old_label, old_reason, new_label, clean_text(new_reason)


def markdown_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
    if df.empty:
        return "_Tidak ada data._"
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(str(col) for col in cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in df.iterrows():
        values = []
        for col in cols:
            value = row[col]
            if pd.isna(value):
                value = ""
            values.append(str(value).replace("\n", " ").replace("|", "/"))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def cleanup_consistency_issue(df: pd.DataFrame, issue_row: pd.Series) -> dict[str, object]:
    review_id = int(issue_row["ID_Review"])
    aspect = clean_text(issue_row["aspect"])
    idx = df.index[df["ID_Review"] == review_id]
    if len(idx) == 0:
        return {"cleanup_decision": "missing_id"}
    i = idx[0]
    review = clean_text(df.at[i, "Text_Review"])
    old_label = norm_label(df.at[i, aspect])
    old_reason = clean_text(df.at[i, REASON_COL[aspect]])
    inferred, reason, note = infer_label(review, aspect)

    if clean_text(issue_row.get("issue")) == "label_without_reason_remaining":
        if old_label in SENTIMENT_LABELS:
            final_label = old_label
            final_reason = reason if not is_blank(reason) else make_fallback_reason(review, aspect)
            decision = "fill_missing_reason"
        else:
            final_label = "none"
            final_reason = ""
            decision = "clear_invalid_empty_reason_label"
    else:
        # Reason exists while label is none. If the text really supports this aspect, convert it;
        # otherwise clear the misplaced reason.
        if safe_to_apply_inferred(aspect, inferred, reason):
            final_label = inferred
            final_reason = reason or old_reason
            decision = "convert_reason_to_label"
        else:
            final_label = "none"
            final_reason = ""
            decision = "clear_misplaced_reason"

    previous_label, previous_reason, _, _ = apply_label_reason(df, review_id, aspect, final_label, final_reason)
    return {
        "cleanup_decision": decision,
        "ID_Review": review_id,
        "aspect": aspect,
        "old_label": previous_label,
        "new_label": final_label,
        "old_reason": previous_reason,
        "new_reason": final_reason,
        "note": note,
        "Text_Review": review,
    }


def main() -> None:
    dataset = pd.read_csv(DATASET_V2_PATH)
    needs = pd.read_csv(NEEDS_REVIEW_PATH)
    consistency = pd.read_csv(CONSISTENCY_PATH)

    v3 = dataset.copy()
    manual_decisions: list[dict[str, object]] = []
    manual_changes: list[dict[str, object]] = []

    for _, row in needs.iterrows():
        review_id = int(row["ID_Review"])
        aspect = clean_text(row["aspect"])
        row_for_decision = row.copy()
        idx = v3.index[v3["ID_Review"] == review_id]
        if len(idx) > 0:
            current_idx = idx[0]
            row_for_decision["current_label"] = norm_label(v3.at[current_idx, aspect])
            row_for_decision["current_reason"] = clean_text(v3.at[current_idx, REASON_COL[aspect]])
            row_for_decision["Text_Review"] = clean_text(v3.at[current_idx, "Text_Review"])
        decision = choose_decision(row_for_decision)
        old_label, old_reason, new_label, new_reason = apply_label_reason(
            v3,
            review_id,
            aspect,
            decision["manual_final_label"],
            decision["manual_final_reason"],
        )
        changed = old_label != new_label or old_reason != new_reason
        enriched = {
            **row_for_decision.to_dict(),
            **decision,
            "old_label_before_manual_review": old_label,
            "old_reason_before_manual_review": old_reason,
            "changed_in_v3": changed,
        }
        manual_decisions.append(enriched)
        if changed:
            manual_changes.append(
                {
                    "source": "needs_manual_review_after_step_1_4",
                    "ID_Review": review_id,
                    "aspect": aspect,
                    "change_type": decision["manual_decision"],
                    "old_label": old_label,
                    "new_label": new_label,
                    "old_reason": old_reason,
                    "new_reason": new_reason,
                    "recommended_action": row.get("recommended_action"),
                    "model_prediction": row.get("model_prediction"),
                    "model_confidence": row.get("model_confidence"),
                    "Text_Review": row.get("Text_Review"),
                }
            )

    cleanup_logs: list[dict[str, object]] = []
    for _, issue_row in consistency.iterrows():
        cleanup = cleanup_consistency_issue(v3, issue_row)
        cleanup_logs.append(cleanup)
        if cleanup.get("old_label") != cleanup.get("new_label") or clean_text(cleanup.get("old_reason")) != clean_text(cleanup.get("new_reason")):
            manual_changes.append(
                {
                    "source": "remaining_label_reason_consistency_issues",
                    "ID_Review": cleanup.get("ID_Review"),
                    "aspect": cleanup.get("aspect"),
                    "change_type": cleanup.get("cleanup_decision"),
                    "old_label": cleanup.get("old_label"),
                    "new_label": cleanup.get("new_label"),
                    "old_reason": cleanup.get("old_reason"),
                    "new_reason": cleanup.get("new_reason"),
                    "recommended_action": "",
                    "model_prediction": "",
                    "model_confidence": "",
                    "Text_Review": cleanup.get("Text_Review"),
                }
            )

    remaining_issues: list[dict[str, object]] = []
    for _, row in v3.iterrows():
        for aspect in ASPECTS:
            label = norm_label(row.get(aspect))
            reason = clean_text(row.get(REASON_COL[aspect]))
            if label in SENTIMENT_LABELS and is_blank(reason):
                remaining_issues.append(
                    {
                        "issue": "label_without_reason",
                        "ID_Review": row.get("ID_Review"),
                        "aspect": aspect,
                        "label": label,
                        "reason": reason,
                        "Text_Review": row.get("Text_Review"),
                    }
                )
            if label == "none" and not is_blank(reason):
                remaining_issues.append(
                    {
                        "issue": "reason_without_label",
                        "ID_Review": row.get("ID_Review"),
                        "aspect": aspect,
                        "label": label,
                        "reason": reason,
                        "Text_Review": row.get("Text_Review"),
                    }
                )

    manual_decisions_df = pd.DataFrame(manual_decisions)
    manual_changes_df = pd.DataFrame(manual_changes)
    cleanup_df = pd.DataFrame(cleanup_logs)
    remaining_df = pd.DataFrame(
        remaining_issues,
        columns=["issue", "ID_Review", "aspect", "label", "reason", "Text_Review"],
    )

    v3_path = OUTPUT_DIR / "dataset_absa_labeled_v3_final_audited.csv"
    manual_decisions_path = OUTPUT_DIR / "manual_review_255_decisions.csv"
    manual_changes_path = OUTPUT_DIR / "dataset_absa_labeled_v3_change_log.csv"
    cleanup_path = OUTPUT_DIR / "consistency_cleanup_26_decisions.csv"
    remaining_path = OUTPUT_DIR / "remaining_consistency_issues_after_v3.csv"
    summary_path = OUTPUT_DIR / "step_1_to_3_final_summary.md"
    guideline_path = OUTPUT_DIR / "labeling_guideline_v3_final.md"

    v3.to_csv(v3_path, index=False, encoding="utf-8-sig")
    manual_decisions_df.to_csv(manual_decisions_path, index=False, encoding="utf-8-sig")
    manual_changes_df.to_csv(manual_changes_path, index=False, encoding="utf-8-sig")
    cleanup_df.to_csv(cleanup_path, index=False, encoding="utf-8-sig")
    remaining_df.to_csv(remaining_path, index=False, encoding="utf-8-sig")

    decision_summary = manual_decisions_df.groupby(["manual_decision"], dropna=False).size().reset_index(name="count")
    decision_summary = decision_summary.sort_values("count", ascending=False)
    decision_summary.to_csv(OUTPUT_DIR / "manual_review_decision_summary.csv", index=False, encoding="utf-8-sig")

    change_summary = manual_changes_df.groupby(["source", "change_type"], dropna=False).size().reset_index(name="count")
    change_summary = change_summary.sort_values(["source", "count"], ascending=[True, False])
    change_summary.to_csv(OUTPUT_DIR / "v3_change_summary.csv", index=False, encoding="utf-8-sig")

    before_counts = dataset[ASPECTS].fillna("none").apply(lambda col: col.value_counts()).fillna(0).astype(int)
    after_counts = v3[ASPECTS].fillna("none").apply(lambda col: col.value_counts()).fillna(0).astype(int)
    dist_rows = []
    for aspect in ASPECTS:
        for label in ["positif", "negatif", "netral", "none"]:
            before = int(before_counts.at[label, aspect]) if label in before_counts.index else 0
            after = int(after_counts.at[label, aspect]) if label in after_counts.index else 0
            dist_rows.append({"aspect": aspect, "label": label, "v2_before": before, "v3_after": after, "delta": after - before})
    dist_df = pd.DataFrame(dist_rows)
    dist_df.to_csv(OUTPUT_DIR / "v2_to_v3_label_distribution_delta.csv", index=False, encoding="utf-8-sig")

    guideline_path.write_text(
        """# Guideline Labeling ABSA Hotel Santika V3 Final Audit

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
""",
        encoding="utf-8",
    )

    label_change_count = int((manual_changes_df["old_label"].fillna("none") != manual_changes_df["new_label"].fillna("none")).sum()) if not manual_changes_df.empty else 0
    reason_change_count = int((manual_changes_df["old_reason"].fillna("") != manual_changes_df["new_reason"].fillna("")).sum()) if not manual_changes_df.empty else 0

    summary = f"""# Ringkasan Step 1-3 Final Manual Review

## Cakupan

- Step 1 selesai: {len(manual_decisions_df):,} kasus ambigu dari `needs_manual_review_after_step_1_4.csv` sudah diberi keputusan.
- Step 2 selesai: {len(cleanup_df):,} sisa inkonsistensi label-alasan sudah dibersihkan.
- Step 3 selesai: dataset final audit dibuat sebagai `dataset_absa_labeled_v3_final_audited.csv`.
- Step 4-6 tidak dijalankan: belum ada split ulang, fine-tuning ulang, atau update dashboard.

## Hasil Perubahan

- Total perubahan pada dataset v3: {len(manual_changes_df):,}
- Perubahan label: {label_change_count:,}
- Perubahan/penyesuaian alasan: {reason_change_count:,}
- Sisa inkonsistensi label-alasan setelah v3: {len(remaining_df):,}

## Ringkasan Keputusan Manual Review

{markdown_table(decision_summary)}

## Ringkasan Perubahan Label V2 ke V3

{markdown_table(dist_df[dist_df['delta'] != 0])}

## File Output

- `dataset_absa_labeled_v3_final_audited.csv`
- `manual_review_255_decisions.csv`
- `consistency_cleanup_26_decisions.csv`
- `dataset_absa_labeled_v3_change_log.csv`
- `remaining_consistency_issues_after_v3.csv`
- `manual_review_decision_summary.csv`
- `v2_to_v3_label_distribution_delta.csv`
- `labeling_guideline_v3_final.md`
"""
    summary_path.write_text(summary, encoding="utf-8")

    print(summary)
    print("\nChange summary:")
    print(change_summary.to_string(index=False))


if __name__ == "__main__":
    main()
