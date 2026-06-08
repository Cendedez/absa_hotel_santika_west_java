"""
Dashboard ABSA Hotel Santika — Flask Backend
=============================================
Sistem Dashboard Aspect-Based Sentiment Analysis
menggunakan IndoBERT pada Ulasan OTA Hotel Santika di Jawa Barat.
"""

import json
import sys
import os
import re
from pathlib import Path
from functools import wraps
from collections import Counter

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from flask import Flask, render_template, request, jsonify, send_file, redirect, session, url_for
from transformers import AutoConfig, AutoModel, AutoTokenizer, BertConfig

# ========================================
# KONFIGURASI PATH
# ========================================
BASE_DIR = Path(__file__).parent.parent  # ABSA Hotel Santika/
MODEL_CANDIDATES = [
    BASE_DIR / "Fine Tuning" / "Model Terbaik" / "best_absa_indobert",
    BASE_DIR / "Fine Tuning" / "Final Model",
    BASE_DIR / "Fine Tuning" / "best_absa_indobert",
]
MODEL_DIR = next(
    (
        path for path in MODEL_CANDIDATES
        if (path / "config.json").exists() and (path / "model_state.pt").exists()
    ),
    MODEL_CANDIDATES[-1],
)
PREDICTIONS_PATH = BASE_DIR / "dataset_with_predictions.csv"
LABELED_PATH = BASE_DIR / "Data Labeling" / "dataset_absa_labeled.csv"

# ========================================
# LOAD CONFIG
# ========================================
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
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ========================================
# MODEL CLASS (dari finetune2.ipynb)
# ========================================
class MultiHead(nn.Module):
    def __init__(self, name, na, nc, dropout=0.1, freeze=0, encoder_config=None):
        super().__init__()
        if encoder_config is None:
            self.enc = AutoModel.from_pretrained(name)
        else:
            self.enc = AutoModel.from_config(encoder_config)
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

def build_encoder_config():
    """Bangun konfigurasi encoder tanpa bergantung pada download saat demo lokal."""
    try:
        return AutoConfig.from_pretrained(MODEL_NAME, local_files_only=True)
    except Exception as exc:
        print(f"[Dashboard] Local AutoConfig unavailable, using BERT-base fallback: {exc}")
        return BertConfig(
            vocab_size=len(tokenizer),
            hidden_size=768,
            num_hidden_layers=12,
            num_attention_heads=12,
            intermediate_size=3072,
            hidden_act="gelu",
            hidden_dropout_prob=0.1,
            attention_probs_dropout_prob=0.1,
            max_position_embeddings=512,
            type_vocab_size=2,
            initializer_range=0.02,
            layer_norm_eps=1e-12,
            pad_token_id=tokenizer.pad_token_id or 0,
        )

# ========================================
# LOAD MODEL & TOKENIZER (saat startup)
# ========================================
print("[Dashboard] Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))

print("[Dashboard] Loading model...")
print(f"[Dashboard] Model directory: {MODEL_DIR}")
model = MultiHead(MODEL_NAME, NUM_ASPECTS, NUM_CLASSES, DROPOUT, FREEZE, build_encoder_config())
state_dict = torch.load(str(MODEL_DIR / "model_state.pt"), map_location=DEVICE, weights_only=True)
model.load_state_dict(state_dict, strict=True)
model = model.to(DEVICE)
model.eval()
print(f"[Dashboard] Model ready on {DEVICE}")

# ========================================
# LOAD PREDICTION DATA
# ========================================
print("[Dashboard] Loading prediction data...")
if PREDICTIONS_PATH.exists():
    df = pd.read_csv(PREDICTIONS_PATH, encoding="utf-8-sig", dtype=str).fillna("")
    print(f"[Dashboard] Loaded {len(df)} rows from predictions CSV")
else:
    print(f"[Dashboard] WARNING: {PREDICTIONS_PATH} not found! Run batch_predict.py first.")
    df = pd.DataFrame()

if not df.empty and "Review_Date" in df.columns:
    df["_Review_Date_Sort"] = pd.to_datetime(df["Review_Date"], errors="coerce")

# ========================================
# FLASK APP
# ========================================
app = Flask(__name__)
app.secret_key = os.environ.get("ABSA_DASHBOARD_SECRET", "absa-santika-local-research-secret")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

USERS = {
    "admin": {
        "password": "santika-login-123", # simple password for the single user
        "name": "Manajemen Hotel",
        "role": "admin",
        "role_label": "Stakeholder",
    }
}

PUBLIC_ENDPOINTS = {"login", "static"}

def current_user():
    username = session.get("username")
    if not username:
        return None
    user = USERS.get(username)
    if not user:
        return None
    return {
        "username": username,
        "name": user["name"],
        "role": user["role"],
        "role_label": user["role_label"],
    }

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if current_user():
            return fn(*args, **kwargs)
        if request.path.startswith("/api/"):
            return jsonify({"error": "Autentikasi diperlukan"}), 401
        return redirect(url_for("login"))
    return wrapper

@app.before_request
def require_authenticated_session():
    if request.endpoint in PUBLIC_ENDPOINTS or request.endpoint is None:
        return None
    if current_user():
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "Autentikasi diperlukan"}), 401
    return redirect(url_for("login"))

# ========================================
# HELPER FUNCTIONS
# ========================================
def get_filtered_df(args):
    """Filter dataframe berdasarkan query parameters."""
    filtered = df.copy()

    hotel = args.get("hotel", "")
    platform = args.get("platform", "")
    date_from = args.get("date_from", "")
    date_to = args.get("date_to", "")
    aspect = args.get("aspect", args.get("trend_aspect", ""))
    sentiment = args.get("sentiment", "")
    keyword = args.get("keyword", "")

    if hotel and hotel != "all":
        filtered = filtered[filtered["Nama_Hotel"] == hotel]
    if platform and platform != "all":
        filtered = filtered[filtered["Platform"] == platform]

    if date_from:
        start_date = pd.to_datetime(date_from, errors="coerce")
        if not pd.isna(start_date):
            review_dates = pd.to_datetime(filtered["Review_Date"], errors="coerce")
            filtered = filtered[review_dates >= start_date]

    if date_to:
        end_date = pd.to_datetime(date_to, errors="coerce")
        if not pd.isna(end_date):
            review_dates = pd.to_datetime(filtered["Review_Date"], errors="coerce")
            filtered = filtered[review_dates <= end_date]

    if aspect and aspect != "all":
        col = f"pred_{aspect}"
        if col in filtered.columns:
            if sentiment and sentiment != "all":
                filtered = filtered[filtered[col] == sentiment]
            else:
                filtered = filtered[filtered[col] != "none"]
    elif sentiment and sentiment != "all":
        sentiment_cols = [f"pred_{aspect_name}" for aspect_name in ASPECTS]
        sentiment_cols = [col for col in sentiment_cols if col in filtered.columns]
        if sentiment_cols:
            filtered = filtered[filtered[sentiment_cols].eq(sentiment).any(axis=1)]

    if keyword:
        filtered = filtered[filtered["Text_Review"].str.contains(keyword, case=False, na=False)]

    return filtered

def sort_reviews_newest_first(dataframe):
    """Urutkan review dari tanggal terbaru agar contoh dan explorer lebih actionable."""
    if dataframe.empty:
        return dataframe
    sorted_df = dataframe.copy()
    if "_Review_Date_Sort" in sorted_df.columns:
        sorted_df = sorted_df.sort_values("_Review_Date_Sort", ascending=False, na_position="last")
    elif "Review_Date" in sorted_df.columns:
        sorted_df["_review_date_sort"] = pd.to_datetime(sorted_df["Review_Date"], errors="coerce")
        sorted_df = sorted_df.sort_values("_review_date_sort", ascending=False, na_position="last")
    return sorted_df

def compute_sentiment_stats(filtered_df):
    """Hitung statistik sentimen per aspek."""
    stats = {}
    for aspect in ASPECTS:
        col = f"pred_{aspect}"
        if col in filtered_df.columns:
            counts = filtered_df[col].value_counts().to_dict()
            total_with_sentiment = sum(v for k, v in counts.items() if k != "none")
            stats[aspect] = {
                "none": counts.get("none", 0),
                "positif": counts.get("positif", 0),
                "negatif": counts.get("negatif", 0),
                "netral": counts.get("netral", 0),
                "total_with_sentiment": total_with_sentiment,
            }
    return stats

def compute_priority_improvements(filtered_df, limit=40):
    """Bangun prioritas perbaikan dari kombinasi cabang hotel dan aspek layanan."""
    if filtered_df.empty or "Nama_Hotel" not in filtered_df.columns:
        return []

    rows = []
    sentiment_labels = {"positif", "negatif", "netral"}

    for hotel in sorted(filtered_df["Nama_Hotel"].dropna().unique()):
        hotel_df = filtered_df[filtered_df["Nama_Hotel"] == hotel]
        for aspect in ASPECTS:
            col = f"pred_{aspect}"
            if col not in hotel_df.columns:
                continue

            aspect_labeled = hotel_df[hotel_df[col].isin(sentiment_labels)]
            total_aspect_sentiment = int(len(aspect_labeled))
            negative_rows = hotel_df[hotel_df[col] == "negatif"]
            negative_count = int(len(negative_rows))
            if negative_count == 0 or total_aspect_sentiment == 0:
                continue

            negative_rate = (negative_count / total_aspect_sentiment) * 100
            platform_counts = (
                negative_rows["Platform"].value_counts()
                if "Platform" in negative_rows.columns
                else pd.Series(dtype=int)
            )
            dominant_platform = platform_counts.index[0] if len(platform_counts) > 0 else "-"
            dominant_platform_count = int(platform_counts.iloc[0]) if len(platform_counts) > 0 else 0

            newest = sort_reviews_newest_first(negative_rows).head(1)
            supporting_review = {}
            if not newest.empty:
                item = newest.iloc[0]
                supporting_review = {
                    "id": item.get("ID_Review", ""),
                    "date": item.get("Review_Date", ""),
                    "platform": item.get("Platform", ""),
                    "text": item.get("Text_Review", ""),
                }

            rows.append({
                "hotel": hotel,
                "hotel_short": hotel.replace("Hotel Santika ", ""),
                "aspect": aspect,
                "negative_count": negative_count,
                "total_aspect_sentiment": total_aspect_sentiment,
                "negative_rate": round(negative_rate, 1),
                "dominant_platform": dominant_platform,
                "dominant_platform_count": dominant_platform_count,
                "supporting_review": supporting_review,
            })

    rows.sort(
        key=lambda item: (
            item["negative_count"],
            item["negative_rate"],
            item["total_aspect_sentiment"],
        ),
        reverse=True,
    )
    return rows[:limit]

STOPWORDS_ID = {
    "yang", "dan", "di", "ke", "dari", "ini", "itu", "untuk", "dengan", "saya",
    "kami", "kita", "anda", "mereka", "adalah", "atau", "juga", "karena",
    "pada", "dalam", "sebagai", "akan", "jadi", "sudah", "belum", "masih", "lebih",
    "sangat", "cukup", "agak", "banget", "sekali", "nya", "pun", "lah", "ya",
    "hotel", "santika", "kamar", "menginap", "stay", "tinggal", "tempat", "saat",
    "pas", "kalau", "bila", "dapat", "perlu", "harap", "tolong", "mohon",
    "sih", "aja", "saja", "namun",
    "tetapi", "tapi", "hanya", "semua", "overall", "selama", "sebelum", "setelah",
}

COMPLAINT_STOP_PHRASES = {
    "tidak ada", "tidak bisa", "tidak terlalu", "kurang baik", "sangat baik", "cukup baik",
    "hotel santika", "santika hotel", "saya menginap", "kami menginap",
    "lain kali", "akan kembali",
}

COMPLAINT_CUES = {
    "tidak", "kurang", "belum", "lama", "lambat", "kotor", "bau", "rusak",
    "buruk", "jelek", "mahal", "sempit", "panas", "berisik", "ribut", "antri",
    "antre", "menunggu", "tunggu", "kecewa", "mengecewakan", "masalah",
    "kendala", "komplain", "keluhan", "susah", "sulit", "bocor", "mati",
    "minus", "sayang", "sayangnya", "cuma", "hanya", "perlu", "tolong",
    "harus", "sebaiknya", "terlalu",
}

POSITIVE_CONTEXT_WORDS = {
    "baik", "bagus", "nyaman", "bersih", "ramah", "enak", "strategis", "puas",
    "memuaskan", "terima", "kasih", "rekomendasi", "recommended", "mantap",
}

INCOMPLETE_END_CUES = {
    "tidak", "kurang", "belum", "terlalu", "hanya", "cuma", "perlu", "harus",
    "tolong", "sebaiknya",
}

NEGATION_ALIASES = {
    "gak": "tidak",
    "ga": "tidak",
    "nggak": "tidak",
    "ngga": "tidak",
    "tdk": "tidak",
    "tak": "tidak",
}

IMPORTANT_SHORT_TOKENS = {"ac", "tv", "wc"}

# Kamus kata kunci per aspek untuk memfilter frasa keluhan agar relevan
# dengan aspeknya. Tanpa filter ini, frasa dari seluruh review yang berlabel
# negatif pada suatu aspek akan masuk ke aspek tersebut meskipun tidak relevan
# (contoh: "AC tidak dingin" muncul di aspek Lokasi).
ASPECT_KEYWORDS = {
    "Lokasi": {
        "lokasi", "akses", "jarak", "jauh", "dekat", "strategis", "pusat",
        "kota", "jalan", "transportasi", "bandara", "stasiun", "terminal",
        "mall", "area", "posisi", "letak", "tempuh", "macet", "terjangkau",
        "navigasi", "rute", "arah", "lewat", "melalui",
        "gang", "lorong", "alamat", "wilayah", "daerah", "lingkungan",
        "sekitar", "pinggir", "pelosok", "perjalanan", "jangkau",
    },
    "Kenyamanan": {
        "nyaman", "kenyamanan", "kamar", "tidur", "kasur", "bantal", "guling",
        "bed", "bising", "berisik", "ribut", "suara", "sempit", "luas",
        "ruang", "ac", "conditioner", "suhu", "gelap", "terang",
        "pencahayaan", "ventilasi", "jendela", "view", "pemandangan",
        "istirahat", "tenang", "pengap", "sesak", "adem", "sejuk",
        "panas", "dingin", "gerah", "bau", "rokok", "merokok",
        "sprei", "seprai", "selimut",
    },
    "Pelayanan": {
        "staf", "staff", "karyawan", "resepsionis", "reception", "receptionist",
        "check", "checkin", "checkout", "layanan", "pelayanan", "service",
        "ramah", "lambat", "lama", "tunggu", "menunggu", "antri", "antre",
        "respon", "tanggap", "security", "satpam", "proses", "prosedur",
        "komplain", "handling", "sikap", "petugas", "bellboy",
        "concierge", "housekeeping", "senyum", "sopan",
        "jutek", "cuek", "acuh", "responsif", "komunikasi",
        "booking", "reservasi", "konfirmasi",
    },
    "Kebersihan": {
        "bersih", "kebersihan", "kotor", "debu", "noda", "bau", "jamur",
        "apek", "sampah", "kuman", "higienis", "sanitasi", "jorok",
        "becek", "lengket", "berdebu", "kusam", "berkarat", "lumut",
        "bekas", "rambut", "serangga", "semut", "kecoa", "nyamuk",
        "lalat", "rayap", "mandi", "lantai", "dinding",
    },
    "Harga": {
        "harga", "mahal", "murah", "tarif", "biaya", "bayar", "worth",
        "value", "sebanding", "sesuai", "rate", "diskon", "promo",
        "budget", "charge", "ongkos", "cost", "terjangkau", "ekonomis",
        "premium", "overprice", "kemahalan", "price", "rupiah", "deposit",
    },
    "Makanan": {
        "makan", "makanan", "sarapan", "breakfast", "menu", "rasa",
        "masakan", "nasi", "lauk", "buah", "kopi", "minuman", "buffet",
        "restoran", "restaurant", "variasi", "porsi", "enak", "hambar",
        "asin", "pedas", "hangat", "basi", "segar", "dessert", "snack",
        "kue", "bumbu", "sayur", "daging", "teh", "juice", "hidangan",
        "dining", "lunch", "dinner", "minum", "dapur",
    },
    "Fasilitas": {
        "fasilitas", "kolam", "renang", "pool", "gym", "fitness", "lift",
        "elevator", "tv", "ac", "conditioner", "kulkas", "parkir",
        "wifi", "internet", "handuk", "linen", "toilet",
        "lobby", "lobi", "meeting", "furniture", "lampu", "cermin",
        "peralatan", "shower", "bathup", "bathtub", "amenities",
        "sabun", "shampoo", "remote", "colokan", "perlengkapan",
        "wastafel", "closet", "kloset", "keran", "kran",
        "selimut", "gordyn", "gorden", "tirai", "air",
        "sprei", "seprai", "renovasi",
    },
}


def is_phrase_relevant_to_aspect(phrase, aspect):
    """Periksa apakah frasa keluhan relevan dengan aspek tertentu.

    Mencocokkan token dalam frasa dengan kamus kata kunci per aspek.
    Frasa dianggap relevan jika minimal satu token-nya ada di kamus aspek.
    """
    keywords = ASPECT_KEYWORDS.get(aspect)
    if not keywords:
        return True  # Tidak ada kamus untuk aspek ini, terima semua
    phrase_tokens = set(phrase.split())
    return bool(phrase_tokens.intersection(keywords))


def raw_terms(text):
    text = str(text or "").lower()
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return [NEGATION_ALIASES.get(token, token) for token in text.split()]

def normalize_terms(text):
    tokens = []
    for raw_token in raw_terms(text):
        token = NEGATION_ALIASES.get(raw_token, raw_token)
        if token in STOPWORDS_ID or token.isdigit():
            continue
        if len(token) >= 3 or token in IMPORTANT_SHORT_TOKENS:
            tokens.append(token)
    return tokens

def split_complaint_segments(text):
    """Ambil hanya segmen kalimat yang mengandung sinyal keluhan."""
    raw_text = str(text or "").lower()
    segments = re.split(
        r"(?<=[.!?])\s+|[;\n]+|\b(?:positif|positive|negatif|negative)\s*:|\b(?:tapi|namun|tetapi|sayangnya)\b",
        raw_text,
    )
    complaint_segments = []
    for segment in segments:
        terms = set(raw_terms(segment))
        if terms.intersection(COMPLAINT_CUES):
            complaint_segments.append(segment)
    return complaint_segments

def extract_complaint_phrases(text):
    phrases = []
    for segment in split_complaint_segments(text):
        tokens = normalize_terms(segment)
        for n in (2, 3):
            for index in range(0, max(len(tokens) - n + 1, 0)):
                phrase_tokens = tokens[index:index + n]
                phrase = " ".join(phrase_tokens)
                if phrase in COMPLAINT_STOP_PHRASES:
                    continue
                if phrase_tokens[-1] in INCOMPLETE_END_CUES:
                    continue
                if (
                    set(phrase_tokens).intersection(POSITIVE_CONTEXT_WORDS)
                    and not set(phrase_tokens).intersection(COMPLAINT_CUES)
                ):
                    continue
                phrases.append(phrase)
    return phrases

def phrase_rank_score(phrase, count):
    phrase_tokens = phrase.split()
    cue_bonus = 12 if set(phrase_tokens).intersection(COMPLAINT_CUES) else 0
    length_bonus = min(len(phrase_tokens), 3) * 2
    return count + cue_bonus + length_bonus

def compute_top_complaint_phrases(filtered_df, selected_aspect="all", limit=10):
    """Hitung frasa keluhan terbanyak dari review berlabel negatif per aspek."""
    if filtered_df.empty:
        return {}

    aspects = [selected_aspect] if selected_aspect in ASPECTS else ASPECTS
    output = {}

    for aspect in aspects:
        col = f"pred_{aspect}"
        if col not in filtered_df.columns:
            continue

        negative_rows = filtered_df[filtered_df[col] == "negatif"]
        counter = Counter()
        examples = {}

        for _, row in negative_rows.iterrows():
            text = row.get("Text_Review", "")
            for phrase in extract_complaint_phrases(text):
                if not is_phrase_relevant_to_aspect(phrase, aspect):
                    continue
                counter[phrase] += 1
                if phrase not in examples:
                    examples[phrase] = {
                        "review_id": row.get("ID_Review", ""),
                        "hotel": row.get("Nama_Hotel", ""),
                        "platform": row.get("Platform", ""),
                        "date": row.get("Review_Date", ""),
                        "text": text,
                    }

        top_items = []
        ranked_phrases = sorted(
            counter.items(),
            key=lambda item: (phrase_rank_score(item[0], item[1]), item[1], len(item[0].split())),
            reverse=True,
        )
        selected_phrases = []

        for phrase, count in ranked_phrases:
            if any(phrase != selected and phrase in selected for selected in selected_phrases):
                continue

            top_items.append({
                "phrase": phrase,
                "count": int(count),
                "example": examples.get(phrase, {}),
            })
            selected_phrases.append(phrase)

            if len(top_items) >= limit:
                break

        output[aspect] = {
            "negative_reviews": int(len(negative_rows)),
            "phrases": top_items,
        }

    return output

# ========================================
# ROUTES — HALAMAN
# ========================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("index"))

    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = USERS.get(username)

        if user and password == user["password"]:
            session.clear()
            session["username"] = username
            return redirect(url_for("index"))
        error = "ID pengguna atau kata sandi tidak sesuai."

    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def index():
    return render_template("index.html", user=current_user())

# ========================================
# API ROUTES — DATA
# ========================================
@app.route("/api/session")
def api_session():
    return jsonify({"user": current_user()})


@app.route("/api/overview")
def api_overview():
    """Data untuk halaman Overview."""
    if df.empty:
        return jsonify({"error": "Data belum dimuat"})

    filtered = get_filtered_df(request.args)

    # Statistik dasar
    total_reviews = len(filtered)
    hotels = sorted(filtered["Nama_Hotel"].unique().tolist()) if "Nama_Hotel" in filtered.columns else []
    platforms = sorted(filtered["Platform"].unique().tolist()) if "Platform" in filtered.columns else []

    # Distribusi sentimen global (aggregate semua aspek)
    sentiment_counts = {"positif": 0, "negatif": 0, "netral": 0, "none": 0}
    for aspect in ASPECTS:
        col = f"pred_{aspect}"
        if col in filtered.columns:
            for sent in sentiment_counts:
                sentiment_counts[sent] += int((filtered[col] == sent).sum())

    # Aspek negatif dominan
    aspect_stats = compute_sentiment_stats(filtered)
    aspect_negative = {a: s["negatif"] for a, s in aspect_stats.items()}
    top_negative = sorted(aspect_negative.items(), key=lambda x: -x[1])

    # Aspek positif dominan
    aspect_positive = {a: s["positif"] for a, s in aspect_stats.items()}
    top_positive = sorted(aspect_positive.items(), key=lambda x: -x[1])
    priority_improvements = compute_priority_improvements(filtered)

    return jsonify({
        "total_reviews": total_reviews,
        "total_hotels": len(hotels),
        "total_platforms": len(platforms),
        "hotels": hotels,
        "platforms": platforms,
        "sentiment_counts": sentiment_counts,
        "aspect_stats": aspect_stats,
        "top_negative_aspects": top_negative[:5],
        "top_positive_aspects": top_positive[:5],
        "priority_improvements": priority_improvements,
    })

@app.route("/api/aspect-analysis")
def api_aspect_analysis():
    """Data untuk halaman Analisis Aspek."""
    if df.empty:
        return jsonify({"error": "Data belum dimuat"})

    filtered = get_filtered_df(request.args)
    aspect_stats = compute_sentiment_stats(filtered)

    # Contoh review per aspek
    aspect_examples = {}
    selected_aspect = request.args.get("aspect", "")
    selected_sentiment = request.args.get("sentiment", "")

    if selected_aspect and selected_aspect != "all":
        col = f"pred_{selected_aspect}"
        if col in filtered.columns:
            sub = filtered
            if selected_sentiment and selected_sentiment != "all":
                sub = sub[sub[col] == selected_sentiment]
            else:
                sub = sub[sub[col] != "none"]
            sub = sort_reviews_newest_first(sub)
            examples = sub.head(10)[["ID_Review", "Platform", "Nama_Hotel", "Review_Date", "Text_Review", col]].to_dict("records")
            aspect_examples[selected_aspect] = examples

    return jsonify({
        "aspect_stats": aspect_stats,
        "aspect_examples": aspect_examples,
    })

@app.route("/api/complaint-phrases")
def api_complaint_phrases():
    """Top frasa keluhan dari review negatif per aspek."""
    if df.empty:
        return jsonify({"error": "Data belum dimuat"})

    filtered = get_filtered_df(request.args)
    selected_aspect = request.args.get("aspect", "all")
    top_phrases = compute_top_complaint_phrases(filtered, selected_aspect=selected_aspect, limit=10)

    return jsonify({
        "top_phrases": top_phrases,
        "aspect_scope": selected_aspect if selected_aspect in ASPECTS else "all",
    })

@app.route("/api/hotel-platform")
def api_hotel_platform():
    """Data untuk halaman Analisis Hotel & Platform."""
    if df.empty:
        return jsonify({"error": "Data belum dimuat"})

    filtered = get_filtered_df(request.args)

    # Per hotel
    hotel_stats = {}
    for hotel in sorted(filtered["Nama_Hotel"].unique()):
        hotel_df = filtered[filtered["Nama_Hotel"] == hotel]
        hotel_stats[hotel] = compute_sentiment_stats(hotel_df)

    # Per platform
    platform_stats = {}
    for platform in sorted(filtered["Platform"].unique()):
        platform_df = filtered[filtered["Platform"] == platform]
        platform_stats[platform] = compute_sentiment_stats(platform_df)

    return jsonify({
        "hotel_stats": hotel_stats,
        "platform_stats": platform_stats,
    })

@app.route("/api/trend")
def api_trend():
    """Data untuk halaman Tren Waktu."""
    if df.empty:
        return jsonify({"error": "Data belum dimuat"})

    filtered = get_filtered_df(request.args)

    # Parse date
    filtered_copy = filtered.copy()
    filtered_copy["_date"] = pd.to_datetime(filtered_copy["Review_Date"], errors="coerce")
    filtered_copy = filtered_copy.dropna(subset=["_date"])

    granularity = request.args.get("granularity", "year")
    aspect_filter = request.args.get("trend_aspect", "all")

    if granularity == "day":
        filtered_copy["_period"] = filtered_copy["_date"].dt.strftime("%Y-%m-%d")
    elif granularity == "week":
        iso_calendar = filtered_copy["_date"].dt.isocalendar()
        filtered_copy["_period"] = (
            iso_calendar["year"].astype(str)
            + "-W"
            + iso_calendar["week"].astype(str).str.zfill(2)
        )
    elif granularity == "month":
        filtered_copy["_period"] = filtered_copy["_date"].dt.to_period("M").astype(str)
    else:
        granularity = "year"
        filtered_copy["_period"] = filtered_copy["_date"].dt.year.astype(str)

    periods = sorted(filtered_copy["_period"].unique())

    trend_data = {}
    aspects_to_analyze = [aspect_filter] if aspect_filter != "all" else ASPECTS
    total_sentiment_points = 0

    for period in periods:
        period_df = filtered_copy[filtered_copy["_period"] == period]
        period_counts = {"positif": 0, "negatif": 0, "netral": 0}

        for aspect in aspects_to_analyze:
            col = f"pred_{aspect}"
            if col in period_df.columns:
                for sent in period_counts:
                    period_counts[sent] += int((period_df[col] == sent).sum())

        total_sentiment_points += sum(period_counts.values())
        trend_data[period] = period_counts

    return jsonify({
        "periods": periods,
        "trend_data": trend_data,
        "granularity": granularity,
        "total_reviews": len(filtered_copy),
        "total_sentiment_points": total_sentiment_points,
        "aspect_scope": aspect_filter,
    })

@app.route("/api/reviews")
def api_reviews():
    """Data untuk halaman Review Explorer."""
    if df.empty:
        return jsonify({"error": "Data belum dimuat"})

    filtered = sort_reviews_newest_first(get_filtered_df(request.args))

    # Pagination
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 25))
    start = (page - 1) * per_page
    end = start + per_page

    total = len(filtered)
    page_data = filtered.iloc[start:end]

    # Pilih kolom untuk response
    columns = ["ID_Review", "Platform", "Nama_Hotel", "Review_Date", "Text_Review"]
    for aspect in ASPECTS:
        columns.append(f"pred_{aspect}")
        columns.append(f"conf_{aspect}")
        if f"label_{aspect}" in page_data.columns:
            columns.append(f"label_{aspect}")

    available_cols = [c for c in columns if c in page_data.columns]
    records = page_data[available_cols].to_dict("records")

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
        "reviews": records,
    })

@app.route("/api/export")
def api_export():
    """Export filtered data ke CSV."""
    if df.empty:
        return jsonify({"error": "Data belum dimuat"})

    filtered = get_filtered_df(request.args)
    export_path = BASE_DIR / "Dashboard" / "export_temp.csv"
    filtered.to_csv(export_path, index=False, encoding="utf-8-sig")
    return send_file(str(export_path), as_attachment=True, download_name="absa_export.csv")

@app.route("/api/export-summary")
def api_export_summary():
    """Data ringkasan untuk export laporan briefing meeting."""
    if df.empty:
        return jsonify({"error": "Data belum dimuat"})

    filtered = get_filtered_df(request.args)
    total_reviews = len(filtered)

    hotels = sorted(filtered["Nama_Hotel"].unique().tolist()) if "Nama_Hotel" in filtered.columns else []
    platforms = sorted(filtered["Platform"].unique().tolist()) if "Platform" in filtered.columns else []

    sentiment_counts = {"positif": 0, "negatif": 0, "netral": 0}
    for aspect in ASPECTS:
        col = f"pred_{aspect}"
        if col in filtered.columns:
            for sent in sentiment_counts:
                sentiment_counts[sent] += int((filtered[col] == sent).sum())

    total_sentiment = sum(sentiment_counts.values())
    pos_rate = round((sentiment_counts["positif"] / total_sentiment) * 100, 1) if total_sentiment > 0 else 0

    aspect_stats = compute_sentiment_stats(filtered)

    top_negative = sorted(
        [(a, s["negatif"], s["total_with_sentiment"]) for a, s in aspect_stats.items()],
        key=lambda x: -x[1],
    )[:3]

    top_positive = sorted(
        [(a, s["positif"], s["total_with_sentiment"]) for a, s in aspect_stats.items()],
        key=lambda x: -x[1],
    )[:3]

    all_phrases = compute_top_complaint_phrases(filtered, limit=3)
    phrases_summary = {}
    for aspect_name, phrase_data in all_phrases.items():
        phrases_summary[aspect_name] = phrase_data.get("phrases", [])[:3]

    priority = compute_priority_improvements(filtered, limit=5)

    recent_neg = []
    seen_ids = set()
    for aspect in ASPECTS:
        col = f"pred_{aspect}"
        if col not in filtered.columns:
            continue
        neg_df = filtered[filtered[col] == "negatif"]
        neg_df = sort_reviews_newest_first(neg_df).head(3)
        for _, row in neg_df.iterrows():
            review_id = str(row.get("ID_Review", ""))
            if review_id in seen_ids:
                continue
            seen_ids.add(review_id)
            recent_neg.append({
                "id": review_id,
                "hotel": row.get("Nama_Hotel", ""),
                "platform": row.get("Platform", ""),
                "date": row.get("Review_Date", ""),
                "text": row.get("Text_Review", ""),
                "aspect": aspect,
            })
    recent_neg = recent_neg[:10]

    dates = pd.to_datetime(filtered["Review_Date"], errors="coerce").dropna()
    date_min = dates.min().strftime("%Y-%m-%d") if len(dates) > 0 else ""
    date_max = dates.max().strftime("%Y-%m-%d") if len(dates) > 0 else ""

    return jsonify({
        "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "total_reviews": total_reviews,
        "hotels": hotels,
        "platforms": platforms,
        "date_range": {"min": date_min, "max": date_max},
        "sentiment_counts": sentiment_counts,
        "positive_rate": pos_rate,
        "top_negative_aspects": [{"aspect": a, "count": c, "total": t} for a, c, t in top_negative],
        "top_positive_aspects": [{"aspect": a, "count": c, "total": t} for a, c, t in top_positive],
        "phrases_summary": phrases_summary,
        "priority_improvements": priority,
        "recent_negative_reviews": recent_neg,
    })

@app.route("/api/price-quality")
def api_price_quality():
    """Analisis korelasi sentimen Harga vs Pelayanan dan Fasilitas per hotel."""
    if df.empty:
        return jsonify({"error": "Data belum dimuat"})

    filtered = get_filtered_df(request.args)
    target_aspects = ["Harga", "Pelayanan", "Fasilitas"]
    hotels = sorted(filtered["Nama_Hotel"].dropna().unique()) if "Nama_Hotel" in filtered.columns else []

    hotel_data = []
    for hotel in hotels:
        hotel_df = filtered[filtered["Nama_Hotel"] == hotel]
        aspects_data = {}
        for aspect in target_aspects:
            col = f"pred_{aspect}"
            if col not in hotel_df.columns:
                continue
            sentiment_labels = {"positif", "negatif", "netral"}
            labeled = hotel_df[hotel_df[col].isin(sentiment_labels)]
            total = len(labeled)
            neg = int((hotel_df[col] == "negatif").sum())
            pos = int((hotel_df[col] == "positif").sum())
            aspects_data[aspect] = {
                "total": total,
                "positif": pos,
                "negatif": neg,
                "negative_rate": round((neg / total) * 100, 1) if total > 0 else 0,
                "positive_rate": round((pos / total) * 100, 1) if total > 0 else 0,
            }

        harga_neg = aspects_data.get("Harga", {}).get("negative_rate", 0)
        pel_neg = aspects_data.get("Pelayanan", {}).get("negative_rate", 0)
        fas_neg = aspects_data.get("Fasilitas", {}).get("negative_rate", 0)
        service_avg = (pel_neg + fas_neg) / 2

        gap = round(harga_neg - service_avg, 1)
        if gap > 5:
            verdict = "Harga dipersepsikan tidak sesuai"
        elif gap < -5:
            verdict = "Harga dinilai sepadan/baik"
        else:
            verdict = "Harga cukup sesuai"

        hotel_data.append({
            "hotel": hotel,
            "hotel_short": hotel.replace("Hotel Santika ", ""),
            "aspects": aspects_data,
            "gap": gap,
            "verdict": verdict,
        })

    return jsonify({"hotels": hotel_data, "target_aspects": target_aspects})

@app.route("/api/predict", methods=["POST"])
def api_predict():
    """Prediksi AI review baru menggunakan model IndoBERT."""
    data = request.get_json()
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "Teks review tidak boleh kosong"}), 400

    # Tokenize
    encoded = tokenizer(
        text,
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
        probs = torch.softmax(logits, dim=-1)
        preds = torch.argmax(logits, dim=-1)

    results = []
    for i, aspect in enumerate(ASPECTS):
        pred_id = preds[0, i].item()
        pred_label = ID2LABEL[str(pred_id)]
        confidence = probs[0, i, pred_id].item()
        prob_dist = {
            ID2LABEL[str(c)]: round(probs[0, i, c].item(), 4)
            for c in range(NUM_CLASSES)
        }
        results.append({
            "aspect": aspect,
            "prediction": pred_label,
            "confidence": round(confidence, 4),
            "probabilities": prob_dist,
        })

    return jsonify({
        "text": text,
        "results": results,
    })

@app.route("/api/save-prediction", methods=["POST"])
def api_save_prediction():
    """Simpan hasil prediksi ke dataset."""
    global df
    data = request.get_json()
    
    text = data.get("text", "").strip()
    hotel = data.get("hotel", "").strip()
    platform = data.get("platform", "").strip()
    date = data.get("date", "").strip()
    predictions = data.get("predictions", [])

    if not all([text, hotel, platform, date, predictions]):
        return jsonify({"error": "Data tidak lengkap"}), 400

    # Generate unique ID
    new_id = f"M-{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}"
    
    # Construct row mapping
    row_data = {
        "ID_Review": new_id,
        "Platform": platform,
        "Nama_Hotel": hotel,
        "Review_Date": date,
        "Text_Review": text,
    }
    
    # Initialize empty columns
    for aspect in ASPECTS:
        row_data[f"label_{aspect}"] = "none"
        row_data[f"Alasan_{aspect}"] = ""
        row_data[f"pred_{aspect}"] = "none"
        row_data[f"conf_{aspect}"] = 0.0

    # Fill predictions
    for p in predictions:
        asp = p["aspect"]
        prediction = p["prediction"]
        row_data[f"pred_{asp}"] = prediction
        row_data[f"conf_{asp}"] = p["confidence"]
        if p.get("manual_override"):
            row_data[f"label_{asp}"] = prediction
            row_data[f"Alasan_{asp}"] = "Validasi manual karena confidence model di bawah 60%."

    # Convert to single-row dataframe
    new_row_df = pd.DataFrame([row_data])
    
    # Preprocess for memory df (similar to load_data)
    try:
        new_row_df["_Review_Date_Sort"] = pd.to_datetime(new_row_df["Review_Date"])
        new_row_df["_Review_Year"] = new_row_df["_Review_Date_Sort"].dt.year
        new_row_df["_Review_Month"] = new_row_df["_Review_Date_Sort"].dt.month
    except Exception:
        new_row_df["_Review_Date_Sort"] = pd.NaT
        new_row_df["_Review_Year"] = np.nan
        new_row_df["_Review_Month"] = np.nan

    # Get original columns to ensure correct order
    try:
        original_cols = pd.read_csv(PREDICTIONS_PATH, nrows=0).columns
        # Ensure new_row_df has all original_cols, fill missing with empty
        for col in original_cols:
            if col not in new_row_df.columns:
                new_row_df[col] = ""
                
        csv_row = new_row_df[original_cols]
        csv_row.to_csv(PREDICTIONS_PATH, mode='a', header=False, index=False, encoding='utf-8-sig')
    except Exception as e:
        return jsonify({"error": f"Gagal menyimpan ke CSV: {str(e)}"}), 500

    # Append to memory df at the top
    df = pd.concat([new_row_df, df], ignore_index=True)

    return jsonify({"success": True, "message": "Data berhasil disimpan"})

@app.route("/api/model-performance")
def api_model_performance():
    """Data untuk halaman Performa Model."""
    test_metrics = config.get("test", {})
    return jsonify({
        "overall": {
            "macro_f1": test_metrics.get("macro_f1"),
            "weighted_f1": test_metrics.get("weighted_f1"),
            "accuracy": test_metrics.get("acc"),
            "non_none_f1": test_metrics.get("non_none_macro_f1"),
            "aspect_detection_f1": test_metrics.get("aspect_detection_f1"),
            "false_aspect_rate": test_metrics.get("false_aspect_rate"),
        },
        "per_aspect": test_metrics.get("per_aspect", {}),
        "total_reviews": int(len(df)),
        "model_config": {
            "model_name": MODEL_NAME,
            "max_len": MAX_LEN,
            "dropout": DROPOUT,
            "freeze_layers": FREEZE,
            "learning_rate": config["best_cfg"]["lr"],
            "batch_size": config["best_cfg"]["batch_size"],
            "epochs": config["best_cfg"]["max_epochs"],
            "class_weight": config["best_cfg"]["class_weight"],
            "label_smoothing": config["best_cfg"]["label_smoothing"],
        },
        "aspects": ASPECTS,
        "labels": list(LABEL2ID.keys()),
    })

@app.route("/api/filters")
def api_filters():
    """Data untuk dropdown filter."""
    if df.empty:
        return jsonify({"hotels": [], "platforms": [], "aspects": ASPECTS})

    hotels = sorted(df["Nama_Hotel"].unique().tolist()) if "Nama_Hotel" in df.columns else []
    platforms = sorted(df["Platform"].unique().tolist()) if "Platform" in df.columns else []

    # Rentang tanggal
    dates = pd.to_datetime(df["Review_Date"], errors="coerce").dropna()
    date_min = dates.min().strftime("%Y-%m-%d") if len(dates) > 0 else ""
    date_max = dates.max().strftime("%Y-%m-%d") if len(dates) > 0 else ""

    return jsonify({
        "hotels": hotels,
        "platforms": platforms,
        "aspects": ASPECTS,
        "sentiments": list(LABEL2ID.keys()),
        "date_range": {"min": date_min, "max": date_max},
    })

# ========================================
# RUN
# ========================================
if __name__ == "__main__":
    print("[Dashboard] Starting server on http://localhost:5000")
    app.run(debug=False, host="0.0.0.0", port=5000)
