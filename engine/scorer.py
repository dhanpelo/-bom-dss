"""
engine/scorer.py
Mesin probabilitas DSS BOM.
Input  : kondisi hari ini (hari, candle_class, ohlc_seq, d1_range)
Output : skor probabilitas TP, kategori, detail matching, CI95, peringatan
"""

import json
import math
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

RULES_PATH = Path(__file__).parent.parent / "rules" / "bom_rules.json"

# ── Load rules sekali saat import ────────────────────────────
with open(RULES_PATH, encoding="utf-8") as f:
    RULES = json.load(f)


# ─────────────────────────────────────────────────────────────
@dataclass
class DSSInput:
    """Input kondisi hari ini dari user."""
    hari: str              # "Senin" / "Selasa" / "Rabu" / "Kamis" / "Jumat"
    candle_class: str      # "BULL_BREAK" / "BULL_RANGE" / "INSIDE" / "BEAR_RANGE" / "BEAR_BREAK"
    ohlc_seq: str          # "OHLC" atau "OLHC"
    d1_range: float        # range candle D-1 dalam poin (misal: 85.5)


@dataclass
class DSSResult:
    """Output DSS — probabilitas + detail."""
    # ── Skor Utama ──────────────────────────────────────────
    prob_sameday: float          # probabilitas TP hari ini (0-100)
    kategori: str                # "TINGGI" / "SEDANG" / "RENDAH" / "WASPADA"
    kategori_color: str          # "green" / "yellow" / "orange" / "red"
    kategori_desc: str           # deskripsi kategori

    # ── Breakdown Skor ──────────────────────────────────────
    score_combo: Optional[float]      # skor dari 3-faktor combo
    score_day_class: Optional[float]  # skor dari 2-faktor (hari+class)
    score_range: Optional[float]      # skor dari range bucket
    score_global: float               # prior global

    # ── Lookup Detail ───────────────────────────────────────
    combo_key: Optional[str]
    combo_data: Optional[dict]        # data historis combo 3-faktor
    day_class_data: Optional[dict]    # data historis 2-faktor
    range_data: Optional[dict]        # data historis range bucket
    global_data: dict

    # ── Ekspektasi ──────────────────────────────────────────
    expected_mae: float               # perkiraan MAE / floating
    expected_time_min: Optional[float] # perkiraan waktu TP
    overnight_risk: float             # risiko overnight (%)
    ci95: list                        # confidence interval [lo, hi]

    # ── Peringatan ──────────────────────────────────────────
    warnings: list = field(default_factory=list)
    tips: list = field(default_factory=list)
    n_samples: int = 0               # jumlah sampel historis yang cocok


# ─────────────────────────────────────────────────────────────
def _get_range_bucket_key(d1_range: float) -> str:
    """Mapping nilai range ke key bucket."""
    if d1_range < 30:    return "lt30"
    if d1_range < 50:    return "30to50"
    if d1_range < 75:    return "50to75"
    if d1_range < 100:   return "75to100"
    if d1_range < 150:   return "100to150"
    if d1_range < 200:   return "150to200"
    return "gt200"


def _normalize_class(cls: str) -> str:
    """Normalisasi input candle class ke format DB."""
    cls = cls.upper().strip()
    mapping = {
        "BULL BREAK": "BULL_BREAK",
        "BULL_BREAK": "BULL_BREAK",
        "BULL RANGE": "BULL_RANGE",
        "BULL_RANGE": "BULL_RANGE",
        "INSIDE BAR": "INSIDE",
        "INSIDE_BAR": "INSIDE",
        "INSIDE":     "INSIDE",
        "BEAR RANGE": "BEAR_RANGE",
        "BEAR_RANGE": "BEAR_RANGE",
        "BEAR BREAK": "BEAR_BREAK",
        "BEAR_BREAK": "BEAR_BREAK",
    }
    return mapping.get(cls, cls)


def _normalize_hari(hari: str) -> str:
    mapping = {
        "SENIN":   "Senin",
        "SELASA":  "Selasa",
        "RABU":    "Rabu",
        "KAMIS":   "Kamis",
        "JUMAT":   "Jumat",
        "MONDAY":  "Senin",
        "TUESDAY": "Selasa",
        "WEDNESDAY": "Rabu",
        "THURSDAY": "Kamis",
        "FRIDAY":  "Jumat",
    }
    return mapping.get(hari.upper().strip(), hari.strip())


def _get_kategori(prob: float) -> tuple:
    thresholds = RULES["scoring"]["thresholds"]
    for name in ["TINGGI", "SEDANG", "RENDAH", "WASPADA"]:
        t = thresholds[name]
        if prob >= t["min"]:
            return name, t["color"], t["desc"]
    return "WASPADA", "red", "Kondisi tidak dikenal"


def _wilson_ci(p_pct: float, n: int) -> list:
    """Wilson CI 95% dari persen (0-100) dan n."""
    p = p_pct / 100
    if n == 0:
        return [0.0, 100.0]
    z = 1.96
    center = (p + z*z/(2*n)) / (1 + z*z/n)
    margin = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return [round(max(0, center-margin)*100, 1), round(min(1, center+margin)*100, 1)]


# ─────────────────────────────────────────────────────────────
def score(inp: DSSInput) -> DSSResult:
    """
    Hitung skor DSS dari kondisi input.
    Returns DSSResult dengan semua detail.
    """
    # Normalisasi input
    hari  = _normalize_hari(inp.hari)
    cls   = _normalize_class(inp.candle_class)
    seq   = inp.ohlc_seq.upper().strip()
    rng   = inp.d1_range

    warnings = []
    tips     = []

    # ── Lookup 3-Faktor Combo ────────────────────────────────
    combo_key  = f"{hari}_{cls}_{seq}"
    combo_data = RULES["by_combo"].get(combo_key)

    # Fallback: coba swap seq jika tidak ada
    if combo_data is None:
        alt_seq  = "OLHC" if seq == "OHLC" else "OHLC"
        alt_key  = f"{hari}_{cls}_{alt_seq}"
        alt_data = RULES["by_combo"].get(alt_key)
        if alt_data:
            warnings.append(
                f"Combo {combo_key} tidak ada di data. "
                f"Menggunakan {alt_key} (seq berbeda) sebagai estimasi."
            )
            combo_data = alt_data
            combo_key  = alt_key

    score_combo = combo_data["sameday_pct"] if combo_data else None
    n_combo     = combo_data["n"] if combo_data else 0

    if combo_data and not combo_data.get("data_adequate"):
        warnings.append(
            f"⚠️ Sampel combo {combo_key} hanya n={n_combo} "
            f"(< 10) — estimasi kurang akurat."
        )

    # ── Lookup 2-Faktor (Hari x Class) ──────────────────────
    # Normalize class untuk day_class key
    cls_label_map = {
        "BULL_BREAK": "BULL_BREAK",
        "BULL_RANGE": "BULL_RANGE",
        "INSIDE":     "INSIDE",
        "BEAR_RANGE": "BEAR_RANGE",
        "BEAR_BREAK": "BEAR_BREAK",
    }
    day_class_key  = f"{hari}_{cls_label_map.get(cls, cls)}"
    day_class_data = RULES["by_day_class"].get(day_class_key)

    # Fallback: pakai by_day
    if day_class_data is None:
        day_class_data = None

    score_day_class = day_class_data["sameday_pct"] if day_class_data else \
                      RULES["by_day"].get(hari, {}).get("sameday_pct", 92.6)

    # ── Lookup Range Bucket ──────────────────────────────────
    range_key  = _get_range_bucket_key(rng)
    range_data = RULES["by_range_bucket"].get(range_key)
    score_range = range_data["sameday_pct"] if range_data else 92.6

    # ── Global Prior ─────────────────────────────────────────
    global_data  = RULES["global"]
    score_global = global_data["sameday_pct"]

    # ── Weighted Score ───────────────────────────────────────
    W = RULES["scoring"]["weights"]
    if combo_data:
        prob = (
            W["combo_3factor"]    * score_combo +
            W["day_class_2factor"] * score_day_class +
            W["range_bucket"]     * score_range +
            W["global_base"]      * score_global
        )
    else:
        # Tanpa combo, redistribusi bobot
        prob = (
            0.55 * score_day_class +
            0.30 * score_range +
            0.15 * score_global
        )
        warnings.append(
            "Kombinasi 3-faktor tidak ditemukan di data historis. "
            "Skor dihitung dari 2-faktor + range bucket."
        )

    prob = round(min(100, max(0, prob)), 1)

    # ── Confidence Interval ──────────────────────────────────
    n_ref = n_combo if n_combo >= 5 else \
            (day_class_data["n"] if day_class_data else global_data["n"])
    ci = _wilson_ci(prob, n_ref)

    # ── Ekspektasi ───────────────────────────────────────────
    # MAE: blend combo + day_class + range
    mae_parts = []
    if combo_data:
        mae_parts.append(combo_data["avg_mae"])
    if day_class_data:
        mae_parts.append(day_class_data["avg_mae"])
    if range_data:
        mae_parts.append(range_data["avg_mae"])
    expected_mae = round(sum(mae_parts) / len(mae_parts), 1) if mae_parts else global_data["avg_mae"]

    # Waktu TP
    expected_time = None
    if combo_data:
        expected_time = combo_data.get("avg_time_min")
    elif day_class_data:
        expected_time = day_class_data.get("avg_time_min")

    # Overnight risk
    overnight_risk = round(100 - prob, 1)

    # ── Kategori ─────────────────────────────────────────────
    kategori, kat_color, kat_desc = _get_kategori(prob)

    # ── Tips Otomatis ────────────────────────────────────────
    # Tip 1: Candle class definition
    cls_def = RULES["candle_class_definitions"].get(cls, {})
    if cls_def:
        tips.append(f"D-1 {cls_def['label']}: {cls_def['tips_bom']}")

    # Tip 2: Range
    if rng < 30:
        tips.append(f"Range D-1 kecil ({rng:.0f} pts) → TP cenderung LAMBAT (avg 222 mnt), WR tetap tinggi")
    elif rng < 50:
        tips.append(f"Range D-1 {rng:.0f} pts → Zona hati-hati, overnight rate di atas rata-rata ({range_data['overnight_pct'] if range_data else '?'}%)")
    elif rng > 200:
        tips.append(f"Range D-1 besar ({rng:.0f} pts) → Setup TERBAIK, historis 100% TP rata-rata 8 menit!")
    elif rng > 100:
        tips.append(f"Range D-1 {rng:.0f} pts → Bagus, speed TP di atas rata-rata (avg <60 mnt)")

    # Tip 3: Overnight warning
    if overnight_risk >= 10:
        tips.append(
            f"⚠️ Overnight risk {overnight_risk:.1f}% — siapkan grid averaging "
            f"minimal 50 pts (semua overnight MAE > 15 pts)"
        )
    elif overnight_risk >= 7:
        tips.append(f"Overnight risk {overnight_risk:.1f}% — siapkan averaging 15–30 pts sebagai antisipasi")
    else:
        tips.append(f"Overnight risk rendah ({overnight_risk:.1f}%) — averaging ringan sudah cukup")

    # Tip 4: Kamis warning
    if hari == "Kamis":
        warnings.append("Kamis = hari dengan overnight TERTINGGI (10.3%). Siapkan grid lebih dalam.")

    # Tip 5: Jumat tip
    if hari == "Jumat":
        tips.append("Jumat = hari paling aman (SameDay 95.3%, Overnight 4.7%)")

    # Tip 6: Speed TP hint
    if combo_data and combo_data.get("tp_30m_pct", 0) >= 70:
        tips.append(f"Setup ini {combo_data['tp_30m_pct']:.0f}% TP dalam 30 menit — potensi instan sangat tinggi!")
    elif combo_data and combo_data.get("tp_1h_pct", 0) >= 80:
        tips.append(f"Setup ini {combo_data['tp_1h_pct']:.0f}% TP dalam 1 jam pertama")

    # ── Sample count ─────────────────────────────────────────
    n_samples = n_combo if n_combo > 0 else \
                (day_class_data["n"] if day_class_data else global_data["n"])

    return DSSResult(
        prob_sameday=prob,
        kategori=kategori,
        kategori_color=kat_color,
        kategori_desc=kat_desc,
        score_combo=score_combo,
        score_day_class=score_day_class,
        score_range=score_range,
        score_global=score_global,
        combo_key=combo_key,
        combo_data=combo_data,
        day_class_data=day_class_data,
        range_data=range_data,
        global_data=global_data,
        expected_mae=expected_mae,
        expected_time_min=expected_time,
        overnight_risk=overnight_risk,
        ci95=ci,
        warnings=warnings,
        tips=tips,
        n_samples=n_samples,
    )


# ── CLI Test ─────────────────────────────────────────────────
if __name__ == "__main__":
    test_cases = [
        DSSInput("Selasa",  "BEAR_BREAK", "OHLC", 95.0),
        DSSInput("Jumat",   "INSIDE",     "OLHC", 68.0),
        DSSInput("Kamis",   "BULL_BREAK", "OLHC", 45.0),
        DSSInput("Rabu",    "BEAR_RANGE", "OHLC", 220.0),
        DSSInput("Senin",   "INSIDE",     "OLHC", 35.0),
    ]
    for inp in test_cases:
        r = score(inp)
        print(f"\n{'='*55}")
        print(f"Input  : {inp.hari} | {inp.candle_class} | {inp.ohlc_seq} | Range {inp.d1_range} pts")
        print(f"Prob   : {r.prob_sameday}%  [{r.ci95[0]}–{r.ci95[1]}%]  n={r.n_samples}")
        print(f"Kategori: {r.kategori}  |  Overnight risk: {r.overnight_risk}%")
        print(f"MAE est: ~{r.expected_mae} pts  |  Waktu TP: ~{r.expected_time_min} mnt")
        if r.warnings:
            for w in r.warnings: print(f"  ⚠️  {w}")
        if r.tips:
            for t in r.tips: print(f"  💡  {t}")
