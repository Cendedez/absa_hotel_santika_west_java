"""
Batch Prediction — ABSA Hotel Santika
======================================
Memprediksi seluruh dataset_absa_labeled.csv menggunakan model fine-tune 2.
Hasil disimpan ke dataset_with_predictions.csv.

Script ini TIDAK mengubah dataset asli.
"""

import json
import sys
import time
from pathlib import Path

# Fix Windows console encoding
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import AutoModel, AutoTokenizer

# ========================================
# KONFIGURASI
# ========================================
MODEL_DIR = Path(r"C:\Users\cencen04_\Downloads\ABSA Hotel Santika\Fine Tuning\best_absa_indobert")
DATASET_PATH = Path(r"C:\Users\cencen04_\Downloads\ABSA Hotel Santika\Data Labeling\dataset_absa_labeled.csv")
OUTPUT_PATH = Path(r"C:\Users\cencen04_\Downloads\ABSA Hotel Santika\dataset_with_predictions.csv")
BATCH_SIZE = 64  # CPU-friendly batch size
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ========================================
# LOAD CONFIG
# ========================================
print("=" * 60)
print("Batch Prediction — ABSA Hotel Santika")
print("=" * 60)

with open(MODEL_DIR / "config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

ASPECTS = config["aspects"]
LABEL2ID = config["label2id"]
ID2LABEL = config["id2label"]
NUM_ASPECTS = len(ASPECTS)
NUM_CLASSES = len(LABEL2ID)
MODEL_NAME = config["model_name"]
MAX_LEN = config["max_len"]
DROPOUT = config["best_cfg"]["dropout"]
FREEZE = config["best_cfg"]["freeze_layers"]

print(f"  Device     : {DEVICE}")
print(f"  Batch size : {BATCH_SIZE}")
print(f"  Max length : {MAX_LEN}")
print()

# ========================================
# MODEL CLASS
# ========================================
class MultiHead(nn.Module):
    def __init__(self, name, na, nc, dropout=0.1, freeze=0):
        super().__init__()
        self.enc = AutoModel.from_pretrained(name)
        h = self.enc.config.hidden_size
        self.drop = nn.Dropout(dropout)
        self.heads = nn.ModuleList([nn.Linear(h, nc) for _ in range(na)])
        if freeze > 0:
            for p in self.enc.embeddings.parameters():
                p.requires_grad = False
            layers = getattr(self.enc.encoder, "layer", [])
            for l in layers[:freeze]:
                for p in l.parameters():
                    p.requires_grad = False

    def forward(self, input_ids, attention_mask, token_type_ids=None):
        o = self.enc(input_ids=input_ids, attention_mask=attention_mask)
        cls = self.drop(o.last_hidden_state[:, 0])
        return torch.stack([hd(cls) for hd in self.heads], dim=1)


# ========================================
# DATASET CLASS
# ========================================
class ReviewDataset(Dataset):
    def __init__(self, texts, tokenizer, max_len):
        self.texts = list(texts)
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        encoded = self.tokenizer(
            self.texts[idx],
            truncation=True,
            max_length=self.max_len,
            padding="max_length",
            return_tensors="pt",
        )
        return {k: v.squeeze(0) for k, v in encoded.items()}


# ========================================
# LOAD MODEL & TOKENIZER
# ========================================
print("[1/4] Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
print(f"  Done (vocab: {tokenizer.vocab_size})")

print("[2/4] Loading model...")
model = MultiHead(MODEL_NAME, NUM_ASPECTS, NUM_CLASSES, DROPOUT, FREEZE)
state_dict = torch.load(str(MODEL_DIR / "model_state.pt"), map_location=DEVICE, weights_only=True)
model.load_state_dict(state_dict, strict=True)
model = model.to(DEVICE)
model.eval()
print("  Done")

# ========================================
# LOAD DATASET
# ========================================
print("[3/4] Loading dataset...")
df = pd.read_csv(DATASET_PATH, encoding="utf-8-sig", dtype=str).fillna("")
print(f"  Loaded {len(df)} rows, {len(df.columns)} columns")

# Validasi kolom
TEXT_COL = "Text_Review"
assert TEXT_COL in df.columns, f"Kolom {TEXT_COL} tidak ditemukan!"

# Pastikan teks tidak kosong
empty_mask = df[TEXT_COL].str.strip().eq("")
if empty_mask.any():
    print(f"  [WARN] {empty_mask.sum()} baris dengan teks kosong, akan diisi 'kosong'")
    df.loc[empty_mask, TEXT_COL] = "kosong"

# ========================================
# BATCH PREDICTION
# ========================================
print("[4/4] Running batch prediction...")
dataset = ReviewDataset(df[TEXT_COL].tolist(), tokenizer, MAX_LEN)
loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

all_preds = []
all_confs = []
total_batches = len(loader)
t0 = time.time()

with torch.no_grad():
    for batch_idx, batch in enumerate(loader):
        inputs = {k: v.to(DEVICE) for k, v in batch.items() if k in ["input_ids", "attention_mask", "token_type_ids"]}
        logits = model(**inputs)  # [batch, 7, 4]
        probs = torch.softmax(logits, dim=-1)  # [batch, 7, 4]
        preds = torch.argmax(logits, dim=-1)   # [batch, 7]
        confs = probs.max(dim=-1).values        # [batch, 7]

        all_preds.append(preds.cpu().numpy())
        all_confs.append(confs.cpu().numpy())

        # Progress
        elapsed = time.time() - t0
        done = (batch_idx + 1) * BATCH_SIZE
        done = min(done, len(df))
        pct = done / len(df) * 100
        speed = done / elapsed if elapsed > 0 else 0
        eta = (len(df) - done) / speed if speed > 0 else 0
        print(f"\r  Batch {batch_idx + 1}/{total_batches} | {done}/{len(df)} ({pct:.1f}%) | {speed:.1f} reviews/s | ETA: {eta:.0f}s", end="", flush=True)

print()
elapsed_total = time.time() - t0
print(f"  Selesai dalam {elapsed_total:.1f} detik ({len(df) / elapsed_total:.1f} reviews/s)")

# ========================================
# GABUNGKAN HASIL
# ========================================
preds_array = np.concatenate(all_preds, axis=0)  # [N, 7]
confs_array = np.concatenate(all_confs, axis=0)   # [N, 7]

# Tambah kolom prediksi
for i, aspect in enumerate(ASPECTS):
    df[f"pred_{aspect}"] = [ID2LABEL[str(p)] for p in preds_array[:, i]]
    df[f"conf_{aspect}"] = confs_array[:, i].round(4)

# Rename kolom label asli agar jelas
for aspect in ASPECTS:
    if aspect in df.columns:
        # Normalisasi label asli: kosong/NaN → "none"
        df[aspect] = df[aspect].apply(lambda x: str(x).strip().lower() if str(x).strip().lower() in LABEL2ID else "none")
        df.rename(columns={aspect: f"label_{aspect}"}, inplace=True)

# ========================================
# SIMPAN
# ========================================
df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
print()
print(f"Hasil disimpan ke: {OUTPUT_PATH}")
print(f"  Kolom: {len(df.columns)}")
print(f"  Baris: {len(df)}")

# ========================================
# RINGKASAN DISTRIBUSI PREDIKSI
# ========================================
print()
print("=" * 60)
print("Ringkasan Distribusi Prediksi")
print("=" * 60)
print(f"  {'Aspek':<14} {'none':>6} {'positif':>8} {'negatif':>8} {'netral':>7}")
print(f"  {'─' * 14} {'─' * 6} {'─' * 8} {'─' * 8} {'─' * 7}")
for aspect in ASPECTS:
    counts = df[f"pred_{aspect}"].value_counts()
    none_n = counts.get("none", 0)
    pos_n = counts.get("positif", 0)
    neg_n = counts.get("negatif", 0)
    net_n = counts.get("netral", 0)
    print(f"  {aspect:<14} {none_n:>6} {pos_n:>8} {neg_n:>8} {net_n:>7}")

# Perbandingan pred vs label (agreement rate)
print()
print("=" * 60)
print("Agreement Rate: Prediksi vs Label Asli")
print("=" * 60)
for aspect in ASPECTS:
    pred_col = f"pred_{aspect}"
    label_col = f"label_{aspect}"
    if label_col in df.columns:
        agree = (df[pred_col] == df[label_col]).mean()
        print(f"  {aspect:<14} {agree:.1%}")

print()
print("Batch prediction selesai. File siap untuk dashboard.")
