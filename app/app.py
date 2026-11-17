"""
BOM Decision Support System — Streamlit App
Mobile-first, Android-friendly dark theme
Run: streamlit run app/app.py
"""

import sys
import json
import datetime
import pandas as pd
from pathlib import Path

import streamlit as st

# ── Path setup ───────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from engine.scorer import score, DSSInput, RULES

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="BOM DSS",
    page_icon="🎯",
    layout="centered",          # centered = lebih baik di HP
    initial_sidebar_state="collapsed",  # collapsed by default di HP
)

# ── Mobile-first CSS ─────────────────────────────────────────
st.markdown("""
<style>
/* ── Global ── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0d1117 !important;
    color: #e6edf3 !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
[data-testid="stSidebar"] {
    background-color: #161b22 !important;
    border-right: 1px solid #30363d;
}

/* ── Top header ── */
[data-testid="stHeader"] { background-color: #0d1117 !important; }

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 14px !important;
}
[data-testid="stMetricValue"] { color: #e6edf3 !important; }
[data-testid="stMetricLabel"] { color: #8b949e !important; }
[data-testid="stMetricDelta"] { font-size: 0.8rem !important; }

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #238636, #2ea043) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 14px 20px !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    width: 100% !important;
    min-height: 52px !important;    /* touch-friendly */
    letter-spacing: .02rem;
    box-shadow: 0 2px 8px rgba(35,134,54,.35);
    transition: all .2s;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #2ea043, #3fb950) !important;
    box-shadow: 0 4px 14px rgba(35,134,54,.5);
}
.stButton > button:active { transform: scale(.98); }

/* ── Selectbox / Inputs ── */
.stSelectbox > div > div,
.stNumberInput > div > div > input,
.stDateInput > div > div > input {
    background: #161b22 !important;
    color: #e6edf3 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    font-size: 1rem !important;
    min-height: 44px !important;   /* touch-friendly */
}
.stSelectbox label, .stNumberInput label,
.stDateInput label, .stRadio label span {
    color: #8b949e !important;
    font-size: 0.82rem !important;
    text-transform: uppercase;
    letter-spacing: .05rem;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #161b22;
    border-radius: 10px;
    padding: 4px;
    gap: 2px;
    overflow-x: auto;
    scrollbar-width: none;
}
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #8b949e !important;
    border-radius: 8px !important;
    padding: 8px 14px !important;
    font-size: 0.85rem !important;
    white-space: nowrap;
    min-height: 40px !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: #21262d !important;
    color: #e6edf3 !important;
    font-weight: 600 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
}
[data-testid="stExpander"] summary {
    color: #8b949e !important;
    font-size: 0.9rem !important;
}

/* ── DataFrames ── */
[data-testid="stDataFrame"] {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    overflow: hidden;
}

/* ── Dividers ── */
hr { border-color: #30363d !important; margin: 12px 0 !important; }

/* ── Scrollable horizontal container ── */
.scroll-x {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: thin;
}

/* ── Mobile padding ── */
.block-container {
    padding: 1rem 1rem 4rem 1rem !important;
    max-width: 540px !important;
}

/* ── Toasts ── */
[data-testid="stToast"] {
    background: #238636 !important;
    color: #fff !important;
    border-radius: 10px !important;
}

/* ── Info/Warning/Success ── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-size: 0.9rem !important;
}

/* ── Fix radio buttons ── */
[data-testid="stRadio"] > div { flex-direction: column; gap: 8px; }
[data-testid="stRadio"] label {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px 14px !important;
    min-height: 44px !important;
    display: flex;
    align-items: center;
}

/* ── Number input arrows (larger) ── */
[data-testid="stNumberInput"] button {
    min-height: 44px !important;
    min-width: 44px !important;
}
</style>
""", unsafe_allow_html=True)

# ── Konstan & helpers ─────────────────────────────────────────
HARI_LIST = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"]
CLASS_OPTIONS = {
    "📈 Bull Break  (Close > High D-2)":    "BULL_BREAK",
    "🔵 Bull Range  (Bullish, tidak break)": "BULL_RANGE",
    "⬜ Inside Bar  (Konsolidasi / kompres)": "INSIDE",
    "🔻 Bear Range  (Bearish, tidak break)": "BEAR_RANGE",
    "📉 Bear Break  (Close < Low D-2)":      "BEAR_BREAK",
}
SEQ_OPTIONS = ["OHLC (High dulu, lalu Low)", "OLHC (Low dulu, lalu High)"]
SEQ_MAP     = {"OHLC (High dulu, lalu Low)": "OHLC", "OLHC (Low dulu, lalu High)": "OLHC"}
COLOR_HEX   = {"green": "#3fb950", "yellow": "#d29922", "orange": "#f0883e", "red": "#f85149", "blue": "#58a6ff", "purple": "#bc8cff"}
PRED_FILE = ROOT / "predictions" / "history.json"

# ── Cloud-safe history (session_state sebagai primary, file sebagai backup) ──
def load_history():
    # Sudah ada di session? Pakai langsung (cloud & lokal)
    if "bom_history" in st.session_state:
        return st.session_state["bom_history"]
    # Coba baca dari file (lokal / pertama kali start)
    try:
        if PRED_FILE.exists():
            with open(PRED_FILE, encoding="utf-8") as f:
                data = json.load(f)
            st.session_state["bom_history"] = data
            return data
    except Exception:
        pass
    st.session_state["bom_history"] = []
    return []


def save_history(history):
    # Selalu simpan ke session_state (works di cloud maupun lokal)
    st.session_state["bom_history"] = history
    # Coba simpan ke file juga (lokal) — abaikan error jika cloud read-only
    try:
        PRED_FILE.parent.mkdir(exist_ok=True)
        with open(PRED_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def card(title, value, color="blue", sub="", big=False):
    """Single stat card, mobile-optimized."""
    hc  = COLOR_HEX.get(color, "#58a6ff")
    sz  = "2rem" if big else "1.5rem"
    sub_html = f'<div style="color:#8b949e;font-size:.75rem;margin-top:3px">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div style="background:#161b22;border:1px solid #30363d;
                border-left:4px solid {hc};border-radius:12px;
                padding:14px 16px;margin:4px 0;">
        <div style="color:#8b949e;font-size:.7rem;text-transform:uppercase;letter-spacing:.06rem">{title}</div>
        <div style="color:{hc};font-size:{sz};font-weight:700;margin-top:6px;line-height:1.1">{value}</div>
        {sub_html}
    </div>""", unsafe_allow_html=True)


def gauge(prob, color):
    """SVG arc gauge — mobile-optimized."""
    hc    = COLOR_HEX.get(color, "#58a6ff")
    # arc: total panjang = pi * r → circumference separuh lingkaran ≈ 251.3
    arc   = 251.3
    fill  = arc * prob / 100
    st.markdown(f"""
    <div style="display:flex;justify-content:center;padding:8px 0 4px">
      <svg width="220" height="120" viewBox="0 0 220 120">
        <!-- track -->
        <path d="M 15 110 A 95 95 0 0 1 205 110"
              stroke="#21262d" stroke-width="20" fill="none" stroke-linecap="round"/>
        <!-- fill -->
        <path d="M 15 110 A 95 95 0 0 1 205 110"
              stroke="{hc}" stroke-width="20" fill="none" stroke-linecap="round"
              stroke-dasharray="{fill:.1f} {arc:.1f}"
              style="transition:stroke-dasharray .6s ease"/>
        <!-- value -->
        <text x="110" y="100" text-anchor="middle"
              font-size="34" font-weight="800" fill="{hc}"
              font-family="-apple-system,sans-serif">{prob:.1f}%</text>
        <text x="18"  y="118" font-size="10" fill="#484f58">0%</text>
        <text x="186" y="118" font-size="10" fill="#484f58">100%</text>
      </svg>
    </div>""", unsafe_allow_html=True)


def badge(label, color, desc=""):
    """Kategori badge — full width."""
    hc = COLOR_HEX.get(color, "#58a6ff")
    desc_html = f'<div style="color:#8b949e;font-size:.78rem;margin-top:3px">{desc}</div>' if desc else ""
    st.markdown(f"""
    <div style="background:{hc}1a;border:1.5px solid {hc};border-radius:12px;
                padding:12px 16px;text-align:center;margin:6px 0">
        <span style="color:{hc};font-size:1.25rem;font-weight:800">{label}</span>
        {desc_html}
    </div>""", unsafe_allow_html=True)


def speed_pills(combo_data):
    """Speed TP bar — horizontal scroll di HP."""
    if not combo_data:
        return
    items = [
        ("<30m",   combo_data.get("tp_30m_pct", 0), "#3fb950"),
        ("<1 jam", combo_data.get("tp_1h_pct",  0), "#58a6ff"),
        ("<2 jam", combo_data.get("tp_2h_pct",  0), "#d29922"),
        ("<4 jam", combo_data.get("tp_4h_pct",  0), "#f0883e"),
        ("SameDay",combo_data.get("sameday_pct",0), "#bc8cff"),
    ]
    pills = "".join(f"""
        <div style="flex:0 0 auto;text-align:center;background:#161b22;
                    border:1px solid #30363d;border-radius:10px;
                    padding:10px 14px;min-width:70px;">
            <div style="color:{c};font-size:1.2rem;font-weight:800">{v:.0f}%</div>
            <div style="color:#8b949e;font-size:.7rem;margin-top:3px">{l}</div>
        </div>""" for l, v, c in items)
    st.markdown(f"""
    <div style="overflow-x:auto;-webkit-overflow-scrolling:touch;padding:4px 0">
        <div style="display:flex;gap:8px;padding:2px 0">{pills}</div>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# SIDEBAR  (collapsed by default on mobile)
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚙️ Tentang DSS")
    st.markdown("""
    <div style="color:#8b949e;font-size:.85rem;line-height:1.6">
    <b style="color:#e6edf3">BOM Decision Support System</b><br>
    XAUUSD · Buy on Market Open · TP +3.5 pts<br><br>
    Data historis: <b style="color:#3fb950">435 hari</b><br>
    Jan 2025 – Sep 2026<br><br>
    Global WR: <b style="color:#3fb950">92.6%</b>
    </div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown("**🕯️ Panduan Candle Class**")
    for cls_key, cls_info in RULES["candle_class_definitions"].items():
        d = RULES["by_candle_class"].get(cls_key, {})
        with st.expander(f"{cls_info['label']}"):
            st.markdown(f"**Definisi:** {cls_info['definisi']}")
            st.markdown(f"**Tips:** {cls_info['tips_bom']}")
            if d:
                st.markdown(f"📊 SameDay **{d['sameday_pct']}%** · MAE **{d['avg_mae']}** pts · n={d['n']}")


# ══════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════
st.markdown("""
<div style="text-align:center;padding:16px 0 8px">
    <div style="font-size:2rem">🎯</div>
    <div style="font-size:1.3rem;font-weight:800;color:#e6edf3">BOM DSS</div>
    <div style="color:#8b949e;font-size:.8rem">XAUUSD · Buy on Market Open · TP +3.5 pts</div>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Analisis", "📊 Tabel", "📋 Riwayat", "ℹ️ Panduan"])

# ─────────────────────────────────────────────────────────────
# TAB 1 — INPUT + HASIL
# ─────────────────────────────────────────────────────────────
with tab1:

    # ── Input ────────────────────────────────────────────────
    st.markdown("### 📥 Input Kondisi")

    today   = datetime.date.today()
    tgl     = st.date_input("Tanggal", value=today, label_visibility="collapsed")

    # Auto hari dari tanggal
    day_names = ["Senin","Selasa","Rabu","Kamis","Jumat","Sabtu","Minggu"]
    auto_hari = day_names[tgl.weekday()]
    hari_idx  = HARI_LIST.index(auto_hari) if auto_hari in HARI_LIST else 0

    col1, col2 = st.columns(2)
    with col1:
        hari = st.selectbox("📅 Hari", HARI_LIST, index=hari_idx)
    with col2:
        d1_range = st.number_input("📏 Range D-1 (pts)", min_value=1.0,
                                    max_value=1000.0, value=75.0, step=0.5)

    cls_label = st.selectbox("🕯️ Candle D-1 (kemarin)", list(CLASS_OPTIONS.keys()))
    candle_class = CLASS_OPTIONS[cls_label]

    seq_label = st.selectbox("🔄 Urutan OHLC/OLHC", SEQ_OPTIONS,
                              help="OHLC = High terbentuk dulu. OLHC = Low terbentuk dulu.")
    ohlc_seq = SEQ_MAP[seq_label]

    run_btn = st.button("🔍  ANALISIS SEKARANG", use_container_width=True)

    # ── Hasil ────────────────────────────────────────────────
    if not run_btn and "last_result" not in st.session_state:
        st.markdown("""
        <div style="text-align:center;padding:32px 0;color:#484f58">
            <div style="font-size:2.5rem">📊</div>
            <div style="margin-top:8px;font-size:.9rem">
                Isi kondisi di atas<br>lalu tekan <b>ANALISIS</b>
            </div>
        </div>""", unsafe_allow_html=True)

    else:
        if run_btn:
            inp = DSSInput(hari=hari, candle_class=candle_class,
                           ohlc_seq=ohlc_seq, d1_range=d1_range)
            result = score(inp)
            st.session_state["last_result"] = result
            st.session_state["last_input"]  = inp
            st.session_state["last_tgl"]    = tgl
        else:
            result = st.session_state["last_result"]
            inp    = st.session_state["last_input"]
            tgl    = st.session_state["last_tgl"]

        st.divider()

        # Header ringkas
        st.markdown(f"""
        <div style="text-align:center;margin-bottom:4px">
            <span style="color:#8b949e;font-size:.82rem">
                {inp.hari} · {tgl.strftime('%d %b %Y')} ·
                {inp.candle_class.replace('_',' ')} ·
                {inp.ohlc_seq} · {inp.d1_range:.0f} pts
            </span>
        </div>""", unsafe_allow_html=True)

        # Gauge
        gauge(result.prob_sameday, result.kategori_color)

        # CI & sampel
        lo, hi = result.ci95
        st.markdown(f"""
        <div style="text-align:center;color:#484f58;font-size:.78rem;margin-bottom:8px">
            CI 95%: {lo}% – {hi}%  ·  n = {result.n_samples} sampel historis
        </div>""", unsafe_allow_html=True)

        # Badge kategori
        icon_map = {"green":"🟢","yellow":"🟡","orange":"🟠","red":"🔴"}
        badge(
            f"{icon_map.get(result.kategori_color,'🔵')} {result.kategori}",
            result.kategori_color,
            result.kategori_desc
        )

        # Stat cards — 2 kolom
        c1, c2 = st.columns(2)
        with c1:
            ovn_color = "red" if result.overnight_risk >= 10 else \
                        "orange" if result.overnight_risk >= 7 else "green"
            card("Overnight Risk", f"{result.overnight_risk:.1f}%", ovn_color,
                 "kemungkinan tidak TP hari ini")
        with c2:
            card("Est. MAE / Floating", f"~{result.expected_mae} pts", "orange",
                 "avg floating sebelum TP")

        c3, c4 = st.columns(2)
        with c3:
            t_str = f"~{result.expected_time_min:.0f} mnt" \
                    if result.expected_time_min else "?"
            card("Est. Waktu TP", t_str, "blue", "rata-rata historis")
        with c4:
            # Instan TP
            insta = result.combo_data.get("tp_30m_pct", 0) \
                    if result.combo_data else 0
            card("Instan <30 mnt", f"{insta:.0f}%", "purple", "dari sampel combo ini")

        # Speed TP
        st.markdown("**⚡ Distribusi Kecepatan TP**")
        speed_pills(result.combo_data)

        # Score breakdown (collapsible)
        with st.expander("🔢 Detail Kalkulasi Skor"):
            breakdown = [
                ("3-Faktor (Hari+Class+Seq)", result.score_combo, 0.55),
                ("2-Faktor (Hari+Class)",     result.score_day_class, 0.25),
                ("Range Bucket D-1",          result.score_range, 0.10),
                ("Global Prior",              result.score_global, 0.10),
            ]
            for label, val, w in breakdown:
                if val is None:
                    continue
                hc = "#3fb950" if val >= 93 else "#d29922" if val >= 85 else "#f85149"
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;
                            align-items:center;padding:7px 0;
                            border-bottom:1px solid #21262d;font-size:.85rem">
                    <span style="color:#8b949e">{label}</span>
                    <span>
                        <b style="color:{hc}">{val:.1f}%</b>
                        <span style="color:#484f58;font-size:.75rem"> × {w:.0%}</span>
                    </span>
                </div>""", unsafe_allow_html=True)

        # Tips
        if result.tips:
            st.markdown("**💡 Tips & Insight**")
            for t in result.tips:
                col  = "#d29922" if "⚠️" in t else "#3fb950"
                icon = "⚠️" if "⚠️" in t else "💡"
                txt  = t.replace("⚠️", "").strip()
                st.markdown(f"""
                <div style="background:#161b22;border-left:3px solid {col};
                            border-radius:0 8px 8px 0;padding:9px 12px;
                            margin:5px 0;font-size:.85rem;color:#e6edf3">
                    {icon} {txt}
                </div>""", unsafe_allow_html=True)

        # Warnings
        if result.warnings:
            for w in result.warnings:
                st.warning(w)

        # Simpan riwayat
        if run_btn:
            history = load_history()
            entry = {
                "id": len(history) + 1,
                "tanggal": str(tgl),
                "hari": inp.hari,
                "candle_class": inp.candle_class,
                "ohlc_seq": inp.ohlc_seq,
                "d1_range": inp.d1_range,
                "prob_sameday": result.prob_sameday,
                "kategori": result.kategori,
                "ci95": result.ci95,
                "n_samples": result.n_samples,
                "expected_mae": result.expected_mae,
                "expected_time_min": result.expected_time_min,
                "aktual_tp": None,
                "aktual_menit": None,
                "timestamp": datetime.datetime.now().isoformat()
            }
            history.append(entry)
            save_history(history)
            st.toast(f"✅ Disimpan ke riwayat #{entry['id']}", icon="💾")


# ─────────────────────────────────────────────────────────────
# TAB 2 — TABEL
# ─────────────────────────────────────────────────────────────
with tab2:
    sub = st.radio("Pilih tabel:", ["Per Hari", "Per Candle Class", "Top Combo", "Range D-1"],
                   horizontal=True, label_visibility="collapsed")

    if sub == "Per Hari":
        rows = []
        for k, v in RULES["by_day"].items():
            rows.append({"Hari": k, "N": v["n"], "SameDay%": v["sameday_pct"],
                         "OvNight%": v["overnight_pct"], "<30m%": v["insta_30m_pct"],
                         "AvgMAE": v["avg_mae"], "AvgTime(m)": v["avg_time_min"]})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    elif sub == "Per Candle Class":
        rows = []
        for k, v in RULES["by_candle_class"].items():
            d = RULES["candle_class_definitions"].get(k, {})
            rows.append({"Class": d.get("label", k), "N": v["n"],
                         "SameDay%": v["sameday_pct"], "<30m%": v["insta_30m_pct"],
                         "AvgMAE": v["avg_mae"], "AvgTime(m)": v["avg_time_min"]})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    elif sub == "Top Combo":
        rows = []
        for k, v in RULES["by_combo"].items():
            rows.append({
                "Setup": f"{v['hari']}+{v['candle_class']}+{v['ohlc_seq']}",
                "N": v["n"], "SameDay%": v["sameday_pct"],
                "OvNight%": v["overnight_pct"], "<30m%": v["tp_30m_pct"],
                "<2h%": v["tp_2h_pct"], "MedMAE": v["med_mae"],
                "⚠️": "✓" if not v.get("warning") else "⚠️"
            })
        df = pd.DataFrame(rows).sort_values("SameDay%", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)

    else:  # Range D-1
        rows = []
        for k, v in RULES["by_range_bucket"].items():
            rows.append({"Range": v["label"], "N": v["n"],
                         "SameDay%": v["sameday_pct"], "OvNight%": v["overnight_pct"],
                         "<30m%": v["insta_30m_pct"], "AvgMAE": v["avg_mae"]})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────
# TAB 3 — RIWAYAT
# ─────────────────────────────────────────────────────────────
with tab3:
    history = load_history()

    if not history:
        st.info("Belum ada riwayat. Jalankan analisis pertama!")
    else:
        # Update aktual (paling atas, mudah dijangkau)
        pending = [h for h in history if h.get("aktual_tp") is None]
        if pending:
            last = pending[-1]
            st.markdown(f"""
            <div style="background:#161b22;border:1px solid #d29922;
                        border-radius:12px;padding:14px;margin-bottom:12px">
                <div style="color:#d29922;font-size:.75rem;text-transform:uppercase;
                            font-weight:600;letter-spacing:.05rem">
                    ✏️ Update Hasil — #{last['id']}
                </div>
                <div style="color:#e6edf3;margin:6px 0">
                    {last['tanggal']} · {last['hari']} ·
                    {last['candle_class']} · {last['ohlc_seq']}<br>
                    <span style="color:#8b949e">Prediksi: </span>
                    <b style="color:#3fb950">{last['prob_sameday']}%</b>
                    ({last['kategori']})
                </div>
            </div>""", unsafe_allow_html=True)

            aktual = st.radio("Hasil aktual:",
                              ["✅ TP Same Day", "❌ Overnight / Belum TP"],
                              horizontal=True)
            mnt = st.number_input("Waktu TP (menit, 0 jika overnight):",
                                   min_value=0, value=0)
            if st.button("💾 Simpan Hasil", use_container_width=True):
                for h in history:
                    if h["id"] == last["id"]:
                        h["aktual_tp"] = "TP" if "✅" in aktual else "OVERNIGHT"
                        h["aktual_menit"] = mnt if mnt > 0 else None
                save_history(history)
                st.success("✅ Tersimpan!")
                st.rerun()

        # Akurasi cepat
        done = [h for h in history if h.get("aktual_tp")]
        if done:
            correct = sum(1 for h in done if h["aktual_tp"] == "TP")
            acc = correct / len(done) * 100
            c1, c2, c3 = st.columns(3)
            c1.metric("Total", len(done))
            c2.metric("TP",    correct)
            c3.metric("Akurasi", f"{acc:.0f}%")
            st.divider()

        # List riwayat (card per entry)
        st.markdown(f"**📋 {len(history)} Prediksi**")
        for h in reversed(history[-20:]):   # 20 terakhir
            status_color = "#3fb950" if h.get("aktual_tp") == "TP" else \
                           "#f85149" if h.get("aktual_tp") == "OVERNIGHT" else "#8b949e"
            status_icon  = "✅" if h.get("aktual_tp") == "TP" else \
                           "❌" if h.get("aktual_tp") == "OVERNIGHT" else "⏳"
            prob_color   = "#3fb950" if h["prob_sameday"] >= 93 else \
                           "#d29922" if h["prob_sameday"] >= 85 else "#f0883e"
            st.markdown(f"""
            <div style="background:#161b22;border:1px solid #30363d;
                        border-radius:10px;padding:12px 14px;margin:6px 0">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <span style="color:#8b949e;font-size:.78rem">
                        #{h['id']} · {h['tanggal']} · {h['hari']}
                    </span>
                    <span style="font-size:1.1rem">{status_icon}</span>
                </div>
                <div style="margin-top:5px;font-size:.88rem;color:#e6edf3">
                    {h['candle_class'].replace('_',' ')} · {h['ohlc_seq']} ·
                    Range {h['d1_range']:.0f} pts
                </div>
                <div style="display:flex;justify-content:space-between;margin-top:6px">
                    <span style="color:{prob_color};font-weight:700;font-size:1rem">
                        {h['prob_sameday']}%
                    </span>
                    <span style="color:{status_color};font-size:.82rem;font-weight:600">
                        {h.get('aktual_tp') or 'Belum diisi'}
                        {f" ({h['aktual_menit']} mnt)" if h.get('aktual_menit') else ''}
                    </span>
                </div>
            </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# TAB 4 — PANDUAN
# ─────────────────────────────────────────────────────────────
with tab4:
    st.markdown("### ℹ️ Panduan BOM DSS")

    st.markdown("""
    <div style="background:#161b22;border-left:4px solid #58a6ff;
                border-radius:0 10px 10px 0;padding:14px;margin-bottom:12px">
        <b style="color:#58a6ff">Cara Pakai (5 menit sebelum market):</b><br>
        <ol style="color:#e6edf3;margin:8px 0 0 16px;line-height:2">
            <li>Buka chart XAUUSD Daily kemarin</li>
            <li>Tentukan <b>class candle</b> (lihat definisi di bawah)</li>
            <li>Tentukan <b>OHLC/OLHC</b> (urutan High & Low)</li>
            <li>Hitung <b>Range</b> = High − Low kemarin</li>
            <li>Isi form → klik <b>ANALISIS</b></li>
            <li>Malam: update hasil aktual di tab Riwayat</li>
        </ol>
    </div>""", unsafe_allow_html=True)

    st.markdown("#### 🕯️ Definisi Candle Class")
    for k, v in RULES["candle_class_definitions"].items():
        d = RULES["by_candle_class"].get(k, {})
        hc = {"BULL_BREAK":"#3fb950","BULL_RANGE":"#58a6ff","INSIDE":"#bc8cff",
              "BEAR_RANGE":"#f0883e","BEAR_BREAK":"#f85149"}.get(k,"#8b949e")
        with st.expander(f"{v['label']}"):
            st.markdown(f"""
            <div style="color:#e6edf3;font-size:.9rem;line-height:1.7">
                📌 <b>Definisi:</b> {v['definisi']}<br>
                📊 <b>Karakteristik:</b> {v['karakteristik']}<br>
                💡 <b>Tips BOM:</b> {v['tips_bom']}
            </div>""", unsafe_allow_html=True)
            if d:
                c1, c2, c3 = st.columns(3)
                c1.metric("SameDay%", f"{d['sameday_pct']}%")
                c2.metric("AvgMAE",   f"{d['avg_mae']} pts")
                c3.metric("N Hari",   d["n"])

    st.markdown("""
    ---
    #### 🔄 OHLC vs OLHC
    | Pola | Urutan | Artinya |
    |------|--------|---------|
    | **OHLC** | Open → **High** → Low → Close | High terbentuk dulu, lalu turun |
    | **OLHC** | Open → **Low** → High → Close | Low terbentuk dulu, lalu naik |

    ---
    #### ⚠️ Disclaimer
    > Probabilitas historis, **bukan prediksi pasti**.
    > Selalu siapkan manajemen risiko (averaging/grid).
    """)

    # Global stats
    st.markdown("#### 📊 Statistik Global")
    g = RULES["global"]
    c1, c2 = st.columns(2)
    c1.metric("Total Hari", g["n"])
    c1.metric("SameDay TP", f"{g['sameday_pct']}%")
    c2.metric("Avg MAE",    f"{g['avg_mae']} pts")
    c2.metric("Avg Waktu",  f"{g['avg_time_min']} mnt")
