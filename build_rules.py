"""
Build bom_rules.json dari semua CSV hasil backtest.
Jalankan sekali untuk generate knowledge base DSS.
"""
import pandas as pd
import json
import math
from pathlib import Path

BOM = Path(r"C:\Users\HYPE AMD\.gemini\antigravity\scratch\bom_analysis")
OUT = Path(r"C:\Users\HYPE AMD\.gemini\antigravity\scratch\bom_dss\rules\bom_rules.json")

# ── Load semua CSV ───────────────────────────────────────────
daily   = pd.read_csv(BOM / "bom_daily_analysis.csv")
day_sum = pd.read_csv(BOM / "bom_day_summary.csv")
cat_sum = pd.read_csv(BOM / "bom_category_summary.csv")
combos  = pd.read_csv(BOM / "bom_sameday_tp_combos.csv")
dc      = pd.read_csv(BOM / "bom_day_candle_combos.csv")


def ci95(p, n):
    """Wilson score interval 95%."""
    if n == 0:
        return (0.0, 0.0)
    z = 1.96
    center = (p + z*z/(2*n)) / (1 + z*z/n)
    margin = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return (round(max(0, center-margin)*100, 1), round(min(1, center+margin)*100, 1))


rules = {}

# ── 1. GLOBAL ────────────────────────────────────────────────
n_total = len(daily)
n_tp    = int(daily.hit_tp.sum())
p_global = n_tp / n_total
lo, hi = ci95(p_global, n_total)
tp_daily = daily[daily.hit_tp]
rules["global"] = {
    "n": n_total,
    "n_tp": n_tp,
    "sameday_pct": round(p_global * 100, 1),
    "overnight_pct": round((1 - p_global) * 100, 1),
    "insta_30m_pct": round(daily.insta_tp_30m.mean() * 100, 1),
    "insta_60m_pct": round(daily.insta_tp_60m.mean() * 100, 1),
    "avg_mae": round(daily.max_adverse.mean(), 2),
    "med_mae": round(daily.max_adverse.median(), 2),
    "avg_time_min": round(tp_daily.tp_minutes.mean(), 1),
    "ci95": [lo, hi],
    "date_range": [str(daily.date.min()), str(daily.date.max())]
}

# ── 2. PER HARI ──────────────────────────────────────────────
rules["by_day"] = {}
for _, r in day_sum.iterrows():
    hari = r["Hari"].strip()
    n = int(r["N"])
    p = r["TP%"] / 100
    lo, hi = ci95(p, n)
    rules["by_day"][hari] = {
        "n": n,
        "sameday_pct": float(r["TP%"]),
        "overnight_pct": round(100 - r["TP%"], 1),
        "insta_30m_pct": float(r["TP<30m%"]),
        "insta_60m_pct": float(r["TP<60m%"]),
        "avg_mae": round(float(r["AvgMAE"]), 2),
        "med_mae": round(float(r["MedMAE"]), 2),
        "avg_time_min": int(r["AvgTime_min"]),
        "ci95": [lo, hi]
    }

# ── 3. PER CANDLE CLASS ──────────────────────────────────────
rules["by_candle_class"] = {}
for _, r in cat_sum.iterrows():
    cls = r["Kategori"].strip()
    n = int(r["N"])
    p = r["TP Rate%"] / 100
    lo, hi = ci95(p, n)
    rules["by_candle_class"][cls] = {
        "n": n,
        "sameday_pct": float(r["TP Rate%"]),
        "insta_30m_pct": float(r["TP<30m%"]),
        "insta_60m_pct": float(r["TP<60m%"]),
        "avg_mae": round(float(r["Avg MAE (pts)"]), 2),
        "med_mae": round(float(r["Med MAE (pts)"]), 2),
        "avg_time_min": int(r["Avg TP Time (m)"]),
        "ci95": [lo, hi]
    }

# ── 4. COMBO: HARI x CLASS x OHLC ───────────────────────────
rules["by_combo"] = {}
for _, r in combos.iterrows():
    hari = r["Hari"].strip()
    cls  = r["Class"].strip()
    seq  = r["Seq"].strip()
    key  = "_".join([hari, cls, seq])
    n = int(r["N"])
    p = r["SameDay%"] / 100
    lo, hi = ci95(p, n)
    rules["by_combo"][key] = {
        "hari": hari,
        "candle_class": cls,
        "ohlc_seq": seq,
        "n": n,
        "sameday_pct": float(r["SameDay%"]),
        "overnight_pct": float(r["Overnight%"]),
        "tp_30m_pct": float(r["TP<30m%"]),
        "tp_1h_pct": float(r["TP<1h%"]),
        "tp_2h_pct": float(r["TP<2h%"]),
        "tp_4h_pct": float(r["TP<4h%"]),
        "avg_mae": round(float(r["AvgMAE"]), 2),
        "med_mae": round(float(r["MedMAE"]), 2),
        "avg_time_min": int(r["AvgTime_min"]),
        "ci95": [lo, hi],
        "data_adequate": n >= 10,
        "warning": "SAMPEL TERBATAS (n<10)" if n < 10 else None,
        "is_100pct": float(r["SameDay%"]) == 100.0
    }

# ── 5. RANGE BUCKET (dari daily langsung) ────────────────────
rules["by_range_bucket"] = {}
bucket_defs = [
    ("lt30",     0,   30),
    ("30to50",  30,   50),
    ("50to75",  50,   75),
    ("75to100", 75,  100),
    ("100to150",100, 150),
    ("150to200",150, 200),
    ("gt200",   200, 9999),
]
bucket_labels = {
    "lt30":     "< 30 pts",
    "30to50":   "30–50 pts",
    "50to75":   "50–75 pts",
    "75to100":  "75–100 pts",
    "100to150": "100–150 pts",
    "150to200": "150–200 pts",
    "gt200":    "> 200 pts",
}
for key, lo_r, hi_r in bucket_defs:
    sub = daily[(daily.d1_range >= lo_r) & (daily.d1_range < hi_r)]
    n = len(sub)
    if n == 0:
        continue
    p = sub.hit_tp.mean()
    lo_ci, hi_ci = ci95(p, n)
    tp_sub = sub[sub.hit_tp]
    rules["by_range_bucket"][key] = {
        "label": bucket_labels[key],
        "range_min": lo_r,
        "range_max": hi_r if hi_r < 9000 else 9999,
        "n": n,
        "sameday_pct": round(p * 100, 1),
        "overnight_pct": round((1 - p) * 100, 1),
        "insta_30m_pct": round(sub.insta_tp_30m.mean() * 100, 1),
        "insta_60m_pct": round(sub.insta_tp_60m.mean() * 100, 1),
        "avg_mae": round(sub.max_adverse.mean(), 2),
        "med_mae": round(sub.max_adverse.median(), 2),
        "avg_time_min": round(tp_sub.tp_minutes.mean(), 1) if len(tp_sub) > 0 else None,
        "ci95": [lo_ci, hi_ci]
    }

# ── 6. HARI x CLASS (2-faktor, tanpa OHLC) ──────────────────
rules["by_day_class"] = {}
for _, r in dc.iterrows():
    hari = r["Hari"].strip()
    cls  = r["Candle D-1"].strip()
    # normalize class ke format UPPER_SNAKE
    cls_key = cls.upper().replace(" ", "_").replace("INSIDE_BAR", "INSIDE")
    key  = "_".join([hari, cls_key])
    n = int(r["N"])
    p = r["TP Rate%"] / 100
    lo, hi = ci95(p, n)
    rules["by_day_class"][key] = {
        "hari": hari,
        "candle_class_label": cls,
        "n": n,
        "sameday_pct": float(r["TP Rate%"]),
        "insta_30m_pct": float(r["Instan TP%"]),
        "avg_mae": round(float(r["Avg MAE"]), 2),
        "avg_time_min": int(r["Avg Time (m)"]),
        "ci95": [lo, hi],
        "data_adequate": n >= 10
    }

# ── 7. SCORING CONFIG ────────────────────────────────────────
rules["scoring"] = {
    "description": "Bobot untuk menggabungkan sinyal menjadi skor akhir",
    "weights": {
        "combo_3factor": 0.55,
        "day_class_2factor": 0.25,
        "range_bucket": 0.10,
        "global_base": 0.10
    },
    "thresholds": {
        "TINGGI":  {"min": 93, "color": "green",  "desc": "Setup optimal, sangat tinggi probabilitas TP hari ini"},
        "SEDANG":  {"min": 85, "color": "yellow", "desc": "Setup cukup baik, siapkan averaging wajar (5-15 pts)"},
        "RENDAH":  {"min": 75, "color": "orange", "desc": "Hati-hati, risiko overnight lebih tinggi dari rata-rata"},
        "WASPADA": {"min": 0,  "color": "red",    "desc": "Kondisi tidak ideal, siapkan grid dalam (20+ pts)"}
    }
}

# ── 8. DEFINISI CANDLE CLASS ─────────────────────────────────
rules["candle_class_definitions"] = {
    "BULL_BREAK": {
        "label": "Bull Break",
        "definisi": "Close kemarin > High D-2 (breakout naik)",
        "karakteristik": "Momentum bullish kuat, candle sudah break resistance",
        "tips_bom": "OHLC lebih sering, BOM cenderung stabil"
    },
    "BULL_RANGE": {
        "label": "Bull Range",
        "definisi": "Bullish tapi Close < High D-2 (tidak break)",
        "karakteristik": "Bullish terbatas, belum konfirmasi momentum",
        "tips_bom": "OLHC lebih dominan, bisa ada dip dulu"
    },
    "INSIDE": {
        "label": "Inside Bar",
        "definisi": "High < D-2 High DAN Low > D-2 Low (konsolidasi)",
        "karakteristik": "Harga mengompres, potensi breakout besar",
        "tips_bom": "MAE median terendah (1.76 pts!), sering instan TP"
    },
    "BEAR_RANGE": {
        "label": "Bear Range",
        "definisi": "Bearish tapi Close > Low D-2 (tidak break bawah)",
        "karakteristik": "Penurunan moderat, belum breakout",
        "tips_bom": "BOM paling lambat (avg 140 mnt), siapkan averaging"
    },
    "BEAR_BREAK": {
        "label": "Bear Break",
        "definisi": "Close kemarin < Low D-2 (breakdown ke bawah)",
        "karakteristik": "Fake breakdown / reversal kandidat — WR TERTINGGI!",
        "tips_bom": "Hampir selalu OHLC, harga sering bounce kuat pagi"
    }
}

# ── SAVE ─────────────────────────────────────────────────────
OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rules, f, indent=2, ensure_ascii=False)

print(f"[OK] bom_rules.json saved: {OUT}")
print(f"     Keys: {list(rules.keys())}")
print(f"     by_combo: {len(rules['by_combo'])} entries")
print(f"     by_day: {len(rules['by_day'])} entries")
print(f"     by_range_bucket: {len(rules['by_range_bucket'])} entries")
print(f"     by_day_class: {len(rules['by_day_class'])} entries")
