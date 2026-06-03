from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "Data Preprocessing" / "dataset_absa_santika_clean.csv"
DEFAULT_PROMPT = PROJECT_ROOT / "Labeling" / "labeling_prompt.txt"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Labeling" / "output"

ASPECTS = [
    "Lokasi",
    "Kenyamanan",
    "Pelayanan",
    "Kebersihan",
    "Harga",
    "Makanan",
    "Fasilitas",
]

CATEGORIES = {
    "LOKASI": "Lokasi",
    "KENYAMANAN": "Kenyamanan",
    "PELAYANAN": "Pelayanan",
    "KEBERSIHAN": "Kebersihan",
    "HARGA": "Harga",
    "MAKANAN": "Makanan",
    "FASILITAS": "Fasilitas",
}

SENTIMENTS = {"positif", "negatif", "netral"}
REASON_PREFIX = "Alasan_"


@dataclass(frozen=True)
class Columns:
    review_id: str
    text: str
    platform: str | None
    hotel: str | None
    date: str | None


def detect_columns(df: pd.DataFrame) -> Columns:
    def pick(*names: str, required: bool = True) -> str | None:
        lookup = {c.lower(): c for c in df.columns}
        for name in names:
            if name.lower() in lookup:
                return lookup[name.lower()]
        if required:
            raise ValueError(f"Kolom tidak ditemukan. Kandidat: {names}. Kolom tersedia: {list(df.columns)}")
        return None

    return Columns(
        review_id=pick("ID_Review", "review_id", "id"),
        text=pick("Text_Review", "text_review", "review", "text"),
        platform=pick("Platform", "platform", required=False),
        hotel=pick("Nama_Hotel", "hotel_name", "Hotel", required=False),
        date=pick("Review_Date", "date", "Tanggal", required=False),
    )


def load_reviews(path: Path, start_id: int | None, end_id: int | None, limit: int | None) -> tuple[pd.DataFrame, Columns]:
    if not path.exists():
        raise FileNotFoundError(f"Input dataset tidak ditemukan: {path}")

    df = pd.read_csv(path, encoding="utf-8-sig").fillna("")
    cols = detect_columns(df)
    df[cols.review_id] = pd.to_numeric(df[cols.review_id], errors="coerce").astype("Int64")
    df = df.dropna(subset=[cols.review_id])
    df[cols.review_id] = df[cols.review_id].astype(int)
    df[cols.text] = df[cols.text].astype(str)
    df = df[df[cols.text].str.strip().ne("")]

    if start_id is not None:
        df = df[df[cols.review_id] >= start_id]
    if end_id is not None:
        df = df[df[cols.review_id] <= end_id]

    df = df.sort_values(cols.review_id)
    if limit is not None:
        df = df.head(limit)
    return df.reset_index(drop=True), cols


def clean_prompt(prompt: str) -> str:
    if "MULAI PROMPT" in prompt:
        prompt = prompt.split("MULAI PROMPT", 1)[1]
    if "AKHIR PROMPT" in prompt:
        prompt = prompt.split("AKHIR PROMPT", 1)[0]

    # The old interactive prompt asks the model to reply "SIAP".
    # For API batch labeling we remove that readiness instruction.
    prompt = re.sub(
        r"=+\s*SIAP MENERIMA INPUT\s*=+.*?(?=={20,}|\Z)",
        "",
        prompt,
        flags=re.IGNORECASE | re.DOTALL,
    )

    prompt += """

INSTRUKSI API BATCH:
- Jangan membalas SIAP.
- Labeli input batch yang diberikan user.
- Output HANYA JSON array valid.
- Jangan gunakan markdown, komentar, atau teks lain.
"""
    return prompt.strip()


def build_batch_payload(batch: pd.DataFrame, cols: Columns) -> list[dict[str, Any]]:
    items = []
    for _, row in batch.iterrows():
        items.append(
            {
                "review_id": int(row[cols.review_id]),
                "text": str(row[cols.text]).strip(),
            }
        )
    return items


def user_message_for_batch(payload: list[dict[str, Any]], validation_error: str | None = None) -> str:
    intro = (
        "Labeli batch review berikut sesuai taksonomi ABSA Hotel Santika. "
        "Output harus JSON array valid tanpa teks tambahan."
    )
    if validation_error:
        intro += (
            "\n\nOutput sebelumnya tidak valid karena:\n"
            f"{validation_error}\n\nUlangi labeling batch yang sama dan perbaiki formatnya."
        )
    return intro + "\n\nINPUT:\n" + json.dumps(payload, ensure_ascii=False)


def create_anthropic_client(api_key: str | None):
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError(
            "Package 'anthropic' belum terpasang. Jalankan: python -m pip install anthropic"
        ) from exc
    return Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))


def call_claude(
    client: Any,
    model: str,
    system_prompt: str,
    user_content: str,
    max_tokens: int,
    temperature: float,
) -> str:
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    parts = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def extract_json(text: str) -> Any:
    stripped = text.strip()
    stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
    stripped = re.sub(r"```$", "", stripped).strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    starts = [idx for idx in [stripped.find("["), stripped.find("{")] if idx != -1]
    if not starts:
        raise ValueError("Tidak menemukan awal JSON pada respons model.")
    start = min(starts)
    end = max(stripped.rfind("]"), stripped.rfind("}"))
    if end < start:
        raise ValueError("Tidak menemukan akhir JSON pada respons model.")
    return json.loads(stripped[start : end + 1])


def validate_model_output(data: Any, expected_reviews: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError("Output harus berupa JSON array atau object review.")

    expected_by_id = {int(item["review_id"]): item["text"] for item in expected_reviews}
    output_by_id: dict[int, dict[str, Any]] = {}

    for item in data:
        if not isinstance(item, dict):
            errors.append("Ada item output yang bukan object JSON.")
            continue
        review_id = item.get("review_id")
        try:
            review_id = int(review_id)
        except Exception:
            errors.append(f"review_id invalid: {review_id}")
            continue
        if review_id not in expected_by_id:
            errors.append(f"review_id tidak ada di input batch: {review_id}")
            continue

        aspects = item.get("aspects", [])
        if not isinstance(aspects, list):
            errors.append(f"aspects bukan list untuk review_id {review_id}")
            aspects = []

        seen = set()
        cleaned_aspects = []
        text = expected_by_id[review_id]
        for aspect in aspects:
            if not isinstance(aspect, dict):
                errors.append(f"Entry aspek bukan object untuk review_id {review_id}")
                continue
            category = str(aspect.get("category", "")).strip().upper()
            sentiment = str(aspect.get("sentiment", "")).strip().lower()
            snippet = str(aspect.get("snippet", "")).strip()

            if category not in CATEGORIES:
                errors.append(f"category invalid '{category}' pada review_id {review_id}")
                continue
            if sentiment not in SENTIMENTS:
                errors.append(f"sentiment invalid '{sentiment}' pada review_id {review_id}")
                continue
            if category in seen:
                errors.append(f"category duplikat '{category}' pada review_id {review_id}")
                continue
            if not snippet:
                errors.append(f"snippet kosong untuk {category} pada review_id {review_id}")
            elif snippet not in text:
                errors.append(f"snippet bukan substring review untuk {category} pada review_id {review_id}: {snippet}")
            if len(snippet) > 140:
                errors.append(f"snippet terlalu panjang untuk {category} pada review_id {review_id}")

            seen.add(category)
            cleaned_aspects.append(
                {
                    "category": category,
                    "sentiment": sentiment,
                    "snippet": snippet,
                }
            )

        output_by_id[review_id] = {"review_id": review_id, "aspects": cleaned_aspects}

    for review_id in expected_by_id:
        if review_id not in output_by_id:
            errors.append(f"review_id hilang dari output: {review_id}")
            output_by_id[review_id] = {"review_id": review_id, "aspects": []}

    return [output_by_id[int(item["review_id"])] for item in expected_reviews], errors


def convert_to_wide_rows(
    validated: list[dict[str, Any]],
    source_rows: pd.DataFrame,
    cols: Columns,
) -> list[dict[str, Any]]:
    source_by_id = {int(row[cols.review_id]): row for _, row in source_rows.iterrows()}
    wide_rows: list[dict[str, Any]] = []

    for item in validated:
        review_id = int(item["review_id"])
        source = source_by_id[review_id]
        row: dict[str, Any] = {
            "ID_Review": review_id,
            "Platform": source[cols.platform] if cols.platform else "",
            "Nama_Hotel": source[cols.hotel] if cols.hotel else "",
            "Review_Date": source[cols.date] if cols.date else "",
            "Text_Review": source[cols.text],
        }
        for aspect in ASPECTS:
            row[aspect] = ""
            row[f"{REASON_PREFIX}{aspect}"] = ""

        for aspect_result in item["aspects"]:
            aspect_name = CATEGORIES[aspect_result["category"]]
            row[aspect_name] = aspect_result["sentiment"]
            row[f"{REASON_PREFIX}{aspect_name}"] = aspect_result["snippet"]

        wide_rows.append(row)
    return wide_rows


def output_columns() -> list[str]:
    return (
        ["ID_Review", "Platform", "Nama_Hotel", "Review_Date", "Text_Review"]
        + ASPECTS
        + [f"{REASON_PREFIX}{aspect}" for aspect in ASPECTS]
    )


def append_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_columns())
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_done_ids(progress_path: Path, resume: bool) -> set[int]:
    if not resume or not progress_path.exists():
        return set()
    progress = json.loads(progress_path.read_text(encoding="utf-8"))
    return {int(x) for x in progress.get("done_review_ids", [])}


def log_errors(path: Path, batch_no: int, review_ids: list[int], error: str, raw_response: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["batch_no", "review_ids", "error", "raw_response"],
        )
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "batch_no": batch_no,
                "review_ids": json.dumps(review_ids),
                "error": error,
                "raw_response": raw_response[:5000],
            }
        )


def chunked(df: pd.DataFrame, size: int):
    for start in range(0, len(df), size):
        yield start // size + 1, df.iloc[start : start + size].copy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auto-labeling ABSA Hotel Santika memakai Claude API."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Path dataset input CSV.")
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT, help="Path prompt labeling.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Folder output.")
    parser.add_argument("--model", default=os.environ.get("ANTHROPIC_MODEL", ""), help="Model Claude API.")
    parser.add_argument("--api-key", default=os.environ.get("ANTHROPIC_API_KEY"), help="Anthropic API key.")
    parser.add_argument("--start-id", type=int, default=None, help="ID review awal.")
    parser.add_argument("--end-id", type=int, default=None, help="ID review akhir.")
    parser.add_argument("--limit", type=int, default=None, help="Batasi jumlah review.")
    parser.add_argument("--batch-size", type=int, default=10, help="Jumlah review per request.")
    parser.add_argument("--max-tokens", type=int, default=8000, help="Max output tokens.")
    parser.add_argument("--temperature", type=float, default=0.0, help="Temperature Claude.")
    parser.add_argument("--sleep", type=float, default=1.0, help="Jeda antar batch dalam detik.")
    parser.add_argument("--retries", type=int, default=2, help="Jumlah retry jika output invalid.")
    parser.add_argument("--resume", action="store_true", help="Lewati review yang sudah ada di progress.")
    parser.add_argument("--dry-run", action="store_true", help="Cetak batch pertama tanpa memanggil API.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.batch_size < 1:
        raise ValueError("--batch-size minimal 1")

    reviews, cols = load_reviews(args.input, args.start_id, args.end_id, args.limit)
    if reviews.empty:
        print("Tidak ada review untuk diproses.")
        return 0

    prompt_text = clean_prompt(args.prompt.read_text(encoding="utf-8"))
    progress_path = args.output_dir / "labeling_progress.json"
    errors_path = args.output_dir / "labeling_errors.csv"
    output_csv = args.output_dir / "labeled_output.csv"
    done_ids = load_done_ids(progress_path, args.resume)

    if done_ids:
        reviews = reviews[~reviews[cols.review_id].isin(done_ids)].reset_index(drop=True)

    print(f"Input dataset : {args.input}")
    print(f"Prompt        : {args.prompt}")
    print(f"Output dir    : {args.output_dir}")
    print(f"Total review  : {len(reviews)}")
    print(f"Batch size    : {args.batch_size}")

    first_payload = build_batch_payload(reviews.head(args.batch_size), cols)
    if args.dry_run:
        print("\nDRY RUN - payload batch pertama:")
        print(json.dumps(first_payload, ensure_ascii=False, indent=2))
        return 0

    if not args.model:
        raise ValueError(
            "Model Claude belum diisi. Gunakan --model atau set environment variable ANTHROPIC_MODEL."
        )
    if not args.api_key and not os.environ.get("ANTHROPIC_API_KEY"):
        raise ValueError(
            "ANTHROPIC_API_KEY belum tersedia. Isi env var atau gunakan --api-key."
        )

    client = create_anthropic_client(args.api_key)
    all_done = set(done_ids)

    for batch_no, batch in chunked(reviews, args.batch_size):
        payload = build_batch_payload(batch, cols)
        review_ids = [int(item["review_id"]) for item in payload]
        print(f"\nBatch {batch_no}: review_id {review_ids[0]} - {review_ids[-1]} ({len(review_ids)} review)")

        raw_response = ""
        validation_errors: list[str] = []
        validated: list[dict[str, Any]] | None = None

        for attempt in range(args.retries + 1):
            user_content = user_message_for_batch(
                payload,
                "\n".join(validation_errors[:20]) if validation_errors else None,
            )
            try:
                raw_response = call_claude(
                    client,
                    args.model,
                    prompt_text,
                    user_content,
                    args.max_tokens,
                    args.temperature,
                )
                parsed = extract_json(raw_response)
                validated, validation_errors = validate_model_output(parsed, payload)
                if not validation_errors:
                    break
                print(f"  Attempt {attempt + 1}: output invalid, retry. Error pertama: {validation_errors[0]}")
            except Exception as exc:
                validation_errors = [str(exc)]
                print(f"  Attempt {attempt + 1}: gagal, retry. Error: {exc}")

        if validated is None or validation_errors:
            error_text = "\n".join(validation_errors) if validation_errors else "Unknown validation error"
            log_errors(errors_path, batch_no, review_ids, error_text, raw_response)
            write_json(args.output_dir / f"batch_{batch_no:04d}_raw_failed.json", raw_response)
            print(f"  Batch gagal. Dicatat di {errors_path}")
            continue

        write_json(args.output_dir / f"batch_{batch_no:04d}.json", validated)
        wide_rows = convert_to_wide_rows(validated, batch, cols)
        append_csv(output_csv, wide_rows)
        all_done.update(review_ids)
        write_json(
            progress_path,
            {
                "input": str(args.input),
                "output_csv": str(output_csv),
                "done_count": len(all_done),
                "done_review_ids": sorted(all_done),
                "last_batch_no": batch_no,
                "model": args.model,
            },
        )
        print(f"  Sukses. Total selesai: {len(all_done)} review")
        if args.sleep:
            time.sleep(args.sleep)

    print(f"\nSelesai. Output utama: {output_csv}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nDihentikan user.")
        raise SystemExit(130)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)

