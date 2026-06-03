"""
Validasi Model IndoBERT Fine-Tune 2 — ABSA Hotel Santika
=========================================================
Script ini memvalidasi bahwa model bisa di-load dan melakukan inferensi.
Tidak mengubah file apapun.

Fase 1: Load model_state.pt ke arsitektur MultiHead
Fase 2: Test prediksi 1 review manual
"""

import json
import sys
from pathlib import Path

# Fix Windows console encoding
sys.stdout.reconfigure(encoding="utf-8")

import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer

# ========================================
# KONFIGURASI
# ========================================
MODEL_DIR = Path(r"C:\Users\cencen04_\Downloads\ABSA Hotel Santika\Fine Tuning\best_absa_indobert")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ========================================
# LOAD CONFIG
# ========================================
print("=" * 60)
print("FASE 1: Validasi Load Model")
print("=" * 60)

config_path = MODEL_DIR / "config.json"
if not config_path.exists():
    print(f"[ERROR] config.json tidak ditemukan di {MODEL_DIR}")
    sys.exit(1)

with open(config_path, "r", encoding="utf-8") as f:
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

print(f"  Model name   : {MODEL_NAME}")
print(f"  Aspects ({NUM_ASPECTS}) : {ASPECTS}")
print(f"  Classes ({NUM_CLASSES}) : {list(LABEL2ID.keys())}")
print(f"  Max length   : {MAX_LEN}")
print(f"  Dropout      : {DROPOUT}")
print(f"  Freeze layers: {FREEZE}")
print(f"  Device       : {DEVICE}")
print()

# ========================================
# REKONSTRUKSI CLASS MULTIHEAD
# ========================================
class MultiHead(nn.Module):
    """
    Arsitektur model dari finetune2.ipynb:
    - IndoBERT encoder
    - Dropout pada [CLS] token
    - 7 classification heads (1 per aspek, masing-masing 4 kelas)
    """
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
# LOAD TOKENIZER
# ========================================
print("[1/4] Loading tokenizer...")
try:
    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
    print(f"  ✓ Tokenizer loaded (vocab size: {tokenizer.vocab_size})")
except Exception as e:
    print(f"  ✗ Tokenizer error: {e}")
    sys.exit(1)

# ========================================
# RECONSTRUCT MODEL
# ========================================
print("[2/4] Reconstructing MultiHead model...")
try:
    model = MultiHead(
        name=MODEL_NAME,
        na=NUM_ASPECTS,
        nc=NUM_CLASSES,
        dropout=DROPOUT,
        freeze=FREEZE,
    )
    print(f"  ✓ Model reconstructed")
    print(f"    Encoder hidden size: {model.enc.config.hidden_size}")
    print(f"    Number of heads: {len(model.heads)}")
    for i, head in enumerate(model.heads):
        print(f"    Head {i} ({ASPECTS[i]}): Linear({head.in_features} → {head.out_features})")
except Exception as e:
    print(f"  ✗ Model reconstruction error: {e}")
    sys.exit(1)

# ========================================
# LOAD STATE DICT
# ========================================
print("[3/4] Loading model_state.pt...")
state_path = MODEL_DIR / "model_state.pt"
if not state_path.exists():
    print(f"  ✗ model_state.pt tidak ditemukan!")
    sys.exit(1)

try:
    state_dict = torch.load(str(state_path), map_location=DEVICE, weights_only=True)
    result = model.load_state_dict(state_dict, strict=True)
    print(f"  ✓ State dict loaded successfully!")
    print(f"    Missing keys : {result.missing_keys if result.missing_keys else 'None'}")
    print(f"    Unexpected keys: {result.unexpected_keys if result.unexpected_keys else 'None'}")
except Exception as e:
    print(f"  ✗ State dict load error: {e}")
    sys.exit(1)

# ========================================
# MOVE TO DEVICE & EVAL MODE
# ========================================
print("[4/4] Setting eval mode...")
model = model.to(DEVICE)
model.eval()
print(f"  ✓ Model ready on {DEVICE}")

print()
print("=" * 60)
print("FASE 1 SELESAI — Model berhasil di-load! ✓")
print("=" * 60)

# ========================================
# FASE 2: TEST INFERENCE
# ========================================
print()
print("=" * 60)
print("FASE 2: Test Inference Manual")
print("=" * 60)

test_reviews = [
    "Kamarnya bersih dan luas, tapi makanannya kurang enak. Staf ramah sekali.",
    "Lokasi strategis dekat mall, harga terjangkau. Sarapan enak dan bervariasi.",
    "AC kamar tidak dingin, kamar mandi kotor. Tidak akan kembali lagi.",
]

for idx, review in enumerate(test_reviews):
    print(f"\n--- Review #{idx + 1} ---")
    print(f"Teks: \"{review}\"")
    print()

    # Tokenize
    encoded = tokenizer(
        review,
        truncation=True,
        max_length=MAX_LEN,
        padding="max_length",
        return_tensors="pt",
    )
    input_ids = encoded["input_ids"].to(DEVICE)
    attention_mask = encoded["attention_mask"].to(DEVICE)

    # Inference
    with torch.no_grad():
        logits = model(input_ids=input_ids, attention_mask=attention_mask)
        # logits shape: [1, 7, 4]
        probs = torch.softmax(logits, dim=-1)
        preds = torch.argmax(logits, dim=-1)

    # Display results
    print(f"  {'Aspek':<14} {'Prediksi':<10} {'Confidence':>10}   Distribusi Probabilitas")
    print(f"  {'─' * 14} {'─' * 10} {'─' * 10}   {'─' * 40}")
    for i, aspect in enumerate(ASPECTS):
        pred_id = preds[0, i].item()
        pred_label = ID2LABEL[str(pred_id)]
        confidence = probs[0, i, pred_id].item()
        prob_str = "  ".join(
            f"{ID2LABEL[str(c)]}:{probs[0, i, c].item():.3f}"
            for c in range(NUM_CLASSES)
        )
        marker = "◀" if pred_label != "none" else ""
        print(f"  {aspect:<14} {pred_label:<10} {confidence:>9.1%}   {prob_str}  {marker}")

print()
print("=" * 60)
print("FASE 2 SELESAI — Inferensi berhasil! ✓")
print("=" * 60)
print()
print("Kesimpulan: Model siap digunakan untuk batch prediction dan dashboard.")
