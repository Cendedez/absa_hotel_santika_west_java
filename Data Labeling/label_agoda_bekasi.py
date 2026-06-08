"""
ABSA Auto-Labeler — Hotel Santika Megacity Bekasi, Platform Agoda
Input : dataset_absa_santika_clean_v2.csv
Output: labeled_agoda_bekasi.csv  (19 kolom format lama)
"""

import csv
import json
import os
import time
import anthropic

# ── paths ──────────────────────────────────────────────────────────────────
BASE    = r"C:\Users\cencen04_\Downloads\ABSA Hotel Santika"
SRC     = os.path.join(BASE, "Merge", "dataset_absa_santika_clean_v2.csv")
OUT_DIR = os.path.join(BASE, "Auto-Labelling")
OUT     = os.path.join(OUT_DIR, "labeled_agoda_bekasi.csv")

# ── constants ──────────────────────────────────────────────────────────────
ASPECTS   = ["Kenyamanan","Kebersihan","Pelayanan","Harga","Lokasi","Fasilitas","Makanan"]
POLARITAS = {"positif","negatif","netral",""}
OUT_COLS  = [
    "ID_Review","Platform","Nama_Hotel","Review_Date","Text_Review",
    "Kenyamanan","Kebersihan","Pelayanan","Harga","Lokasi","Fasilitas","Makanan",
    "Alasan_Kenyamanan","Alasan_Kebersihan","Alasan_Pelayanan","Alasan_Harga",
    "Alasan_Lokasi","Alasan_Fasilitas","Alasan_Makanan",
]

SYSTEM_PROMPT = """
Kamu adalah expert annotator ABSA (Aspect-Based Sentiment Analysis) domain perhotelan Indonesia.

TAKSONOMI 7 ASPEK:
1. Lokasi — posisi geografis & akses (lokasi, strategis, akses, dekat, jauh, pusat kota, mall, stasiun, tol)
2. Kenyamanan — kondisi & pengalaman di kamar (ukuran kamar, kasur, bantal, suhu AC sebagai pengalaman, kebisingan, pencahayaan, view, furniture, betah). "AC dingin"=Kenyamanan; "AC rusak/tidak ada"=Fasilitas.
3. Pelayanan — sikap/kecepatan/kompetensi staf (keramahan, check-in/out, respon staf, housekeeping aktivitas, antar-jemput). SEMUA tentang staf masuk Pelayanan.
4. Kebersihan — kondisi kebersihan eksplisit (bersih/kotor, debu, sampah, hama: semut/kecoa/nyamuk, noda, bau). "ada semut"=Kebersihan negatif.
5. Harga — penilaian nilai uang (mahal, murah, terjangkau, worth it, value). Sebut nominal tanpa penilaian → TIDAK label.
6. Makanan — makanan & minuman hotel (sarapan, restoran, rasa, variasi menu, porsi, welcome drink). "room service lambat"=Pelayanan; "room service makanannya enak"=Makanan.
7. Fasilitas — keberadaan/fungsi sarana fisik (kolam renang, gym, parkir, lift, wifi, mushola, TV, water heater, amenities). Fasilitas=ada/tidak/berfungsi; Kenyamanan=pengalaman pakai.

ATURAN SENTIMEN:
- positif: pujian eksplisit, rekomendasi, "cukup baik/lumayan"
- negatif: keluhan/kritik, negasi hal positif (kurang ramah, tidak bersih), saran perbaikan implisit
- netral: aspek tanpa kata sifat sentimen, mixed dalam 1 aspek, deskripsi faktual
- NEGASI: "tidak ada hairdryer"=Fasilitas negatif; "kurang bersih"=negatif; "tidak berisik"=Kenyamanan positif
- MIXED 1 aspek: "kamar luas tapi sudah tua"=Kenyamanan netral
- MULTI-ASPEK: "kamar bersih"=Kenyamanan positif + Kebersihan positif
- Review umum tanpa aspek konkret ("ok", "biasa aja") → semua aspek KOSONG
- Maksimal 1 entry per kategori per review

Snippet/Alasan WAJIB kutipan verbatim dari teks review.
""".strip()

LABEL_PROMPT_TEMPLATE = """
Labeli review berikut sesuai taksonomi 7 aspek ABSA.

REVIEW: {text}

Kembalikan JSON SAJA (tanpa markdown), format:
{{
  "Kenyamanan": "",
  "Kebersihan": "",
  "Pelayanan": "",
  "Harga": "",
  "Lokasi": "",
  "Fasilitas": "",
  "Makanan": "",
  "Alasan_Kenyamanan": "",
  "Alasan_Kebersihan": "",
  "Alasan_Pelayanan": "",
  "Alasan_Harga": "",
  "Alasan_Lokasi": "",
  "Alasan_Fasilitas": "",
  "Alasan_Makanan": ""
}}

Nilai polaritas: "positif", "negatif", "netral", atau "" (kosong jika tidak disebutkan).
Alasan WAJIB kutipan verbatim dari teks. Jika aspek kosong, Alasan juga kosong.
"""


def extract_json(text: str) -> dict:
    """Extract JSON from model response, stripping markdown fences if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)


def label_review(client: anthropic.Anthropic, text: str, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": LABEL_PROMPT_TEMPLATE.format(text=text)}],
            )
            # extract TextBlock (skip ThinkingBlock)
            response_text = ""
            for block in msg.content:
                if hasattr(block, "text"):
                    response_text = block.text
                    break

            result = extract_json(response_text)

            # validate & sanitize
            for asp in ASPECTS:
                val = result.get(asp, "").strip().lower()
                result[asp] = val if val in POLARITAS else ""
                alasan_key = f"Alasan_{asp}"
                if not result[asp]:
                    result[alasan_key] = ""
                else:
                    result[alasan_key] = result.get(alasan_key, "").strip()

            return result

        except (json.JSONDecodeError, Exception) as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  [WARN] Failed after {retries} attempts: {e}")
                return {k: "" for k in ASPECTS + [f"Alasan_{a}" for a in ASPECTS]}


def main():
    # ── load & filter ──────────────────────────────────────────────────────
    print("Loading source file...")
    with open(SRC, encoding="utf-8-sig") as f:
        all_rows = list(csv.DictReader(f))

    print(f"Total rows: {len(all_rows)}")
    print(f"Columns: {list(all_rows[0].keys())}")

    filtered = [
        r for r in all_rows
        if r["platform"].strip().lower() == "agoda"
        and "bekasi" in r["hotel_name"].strip().lower()
    ]
    print(f"\nAgoda + Bekasi rows: {len(filtered)}")
    if not filtered:
        print("Tidak ada baris yang lolos filter. Proses dihentikan.")
        return

    # ── label ──────────────────────────────────────────────────────────────
    client = anthropic.Anthropic()
    os.makedirs(OUT_DIR, exist_ok=True)

    # resume support: skip already-done IDs
    done_ids = set()
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                done_ids.add(row["ID_Review"])
        print(f"Resuming — {len(done_ids)} already labeled, skipping.")

    mode = "a" if done_ids else "w"
    with open(OUT, mode, encoding="utf-8-sig", newline="") as fout:
        writer = csv.DictWriter(fout, fieldnames=OUT_COLS)
        if mode == "w":
            writer.writeheader()

        for i, row in enumerate(filtered, 1):
            rid = row["review_id"]
            if rid in done_ids:
                continue

            text = row["text_review"].strip()
            print(f"[{i}/{len(filtered)}] ID={rid} ... ", end="", flush=True)

            labels = label_review(client, text)

            out_row = {
                "ID_Review":   rid,
                "Platform":    row["platform"],
                "Nama_Hotel":  row["hotel_name"],
                "Review_Date": row["date"],
                "Text_Review": text,
            }
            for asp in ASPECTS:
                out_row[asp] = labels.get(asp, "")
                out_row[f"Alasan_{asp}"] = labels.get(f"Alasan_{asp}", "")

            writer.writerow(out_row)
            fout.flush()

            pols = [labels[a] for a in ASPECTS if labels[a]]
            print(", ".join(pols) if pols else "(kosong)")

            # rate-limit buffer
            time.sleep(0.3)

    # ── summary ────────────────────────────────────────────────────────────
    print("\n=== SELESAI ===")
    with open(OUT, encoding="utf-8-sig") as f:
        results = list(csv.DictReader(f))

    print(f"Baris diproses : {len(filtered)}")
    print(f"Baris output   : {len(results)}")
    print(f"Match          : {'OK' if len(results) == len(filtered) else 'MISMATCH!'}\n")

    from collections import Counter
    print("Distribusi sentimen per aspek:")
    print(f"{'Aspek':<14} {'positif':>8} {'negatif':>8} {'netral':>8} {'kosong':>8}")
    print("-" * 50)
    for asp in ASPECTS:
        c = Counter(r[asp] for r in results)
        print(f"{asp:<14} {c.get('positif',0):>8} {c.get('negatif',0):>8} {c.get('netral',0):>8} {c.get('',0):>8}")

    print(f"\nOutput: {OUT}")


if __name__ == "__main__":
    main()
