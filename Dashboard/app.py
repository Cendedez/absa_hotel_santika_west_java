"""
Dashboard ABSA Hotel Santika — Flask Backend
=============================================
Sistem Dashboard Aspect-Based Sentiment Analysis
menggunakan IndoBERT pada Ulasan OTA Hotel Santika di Jawa Barat.
"""

import json
import sys
import os
from pathlib import Path
from functools import wraps

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
MODEL_DIR = BASE_DIR / "Fine Tuning" / "best_absa_indobert"
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
        "password": os.environ.get("ABSA_ADMIN_PASSWORD", "SantikaAdmin2026!"),
        "name": "Admin / Peneliti",
        "role": "admin",
        "role_label": "Admin / Peneliti",
    },
    "manajemen": {
        "password": os.environ.get("ABSA_MANAJEMEN_PASSWORD", "SantikaView2026!"),
        "name": "Manajemen Hotel",
        "role": "management",
        "role_label": "Manajemen Hotel",
    },
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


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user and user["role"] == "admin":
            return fn(*args, **kwargs)
        if request.path.startswith("/api/"):
            return jsonify({"error": "Akses hanya untuk Admin/Peneliti"}), 403
        return redirect(url_for("index"))
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
    aspect = args.get("aspect", "")
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
            sub = sub.copy()
            sub["_review_date_sort"] = pd.to_datetime(sub["Review_Date"], errors="coerce")
            sub = sub.sort_values("_review_date_sort", ascending=False, na_position="last")
            examples = sub.head(20)[["ID_Review", "Platform", "Nama_Hotel", "Review_Date", "Text_Review", col]].to_dict("records")
            aspect_examples[selected_aspect] = examples

    return jsonify({
        "aspect_stats": aspect_stats,
        "aspect_examples": aspect_examples,
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

    filtered = get_filtered_df(request.args)

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

@app.route("/api/predict", methods=["POST"])
def api_predict():
    """Prediksi manual review baru menggunakan model IndoBERT."""
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

@app.route("/api/model-performance")
@admin_required
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
