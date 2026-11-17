# PROJECT CONTEXT — BOM Decision Support System (DSS)
> Dibuat: 2026-11-16 | Versi: 0.1.0 | Bahasa: Python + Streamlit

---

## 1. DEFINISI STRATEGI

| Parameter | Nilai |
|-----------|-------|
| Instrumen | XAUUSD (Gold) |
| Timeframe Entry | M1 (1-menit), candle ke-6 setelah buka (±5 menit) |
| Arah | BUY saja (Long) |
| Take Profit | +3.5 poin dari harga entry |
| Stop Loss | Tidak ada (averaging/grid jika floating) |
| Jam Entry | Open market harian (08:00 WIB atau sesuai broker) |
| Averaging | Grid jika harga turun sebelum TP |

---

## 2. FILE DATA (JANGAN DIHAPUS/EDIT LANGSUNG)

### A. Data Mentah M1 XAUUSD
| File | Lokasi | Rentang | Ukuran |
|------|--------|---------|--------|
| XAUUSDm_M1_202501012305_202512312009.csv | scratch/ | Jan–Des 2025 | 23.5 MB |
| XAUUSDm_M1_2026.csv | scratch/ | 2026 | 16.1 MB |

### B. Hasil Backtest BOM (Output Sudah Ada)
| File | Lokasi | Deskripsi | Rows |
|------|--------|-----------|------|
| bom_daily_analysis.csv | scratch/bom_analysis/ | 1 baris per hari trading | 435 |
| bom_category_summary.csv | scratch/bom_analysis/ | Ringkasan per candle class | 5 |
| bom_day_summary.csv | scratch/bom_analysis/ | Ringkasan per hari (Senin-Jumat) | 5 |
| bom_day_candle_combos.csv | scratch/bom_analysis/ | Combo hari × candle class | 25 |
| bom_sameday_tp_combos.csv | scratch/bom_analysis/ | Combo hari × class × OHLC/OLHC | 30 |
| bom_ohlc_combos.csv | scratch/bom_analysis/ | Sorted by instan TP% | 30 |
| bom_range_bucket.csv | scratch/bom_analysis/ | Analisis per bucket range D-1 | 10 |
| bom_range_class_bucket.csv | scratch/bom_analysis/ | Candle class × range bucket | 40+ |

### C. Kolom bom_daily_analysis.csv
```
date, entry_price, candle_class, d1_bull, d1_body, d1_range, d1_body_pct,
hit_tp, tp_minutes, max_adverse, max_favourable, needs_avg,
insta_tp, insta_tp_15m, insta_tp_30m, insta_tp_60m,
dayofweek, day_name
```
- Rentang: 2025-01-03 s/d 2026-09-07
- 435 hari trading, 403 TP (92.6%), 32 overnight (7.4%)

---

## 3. BACKTEST YANG SUDAH ADA (JANGAN DIULANG)

| Tanggal | Script | Deskripsi | Hasil Utama |
|---------|--------|-----------|-------------|
| Nov 2026 | bom_candle_analysis.py | Klasifikasi candle D-1 | WR 90.3–96.2% per class |
| Nov 2026 | bom_day_filter.py | Filter per hari + combo | Jumat 95.3%, Kamis 89.7% |
| Nov 2026 | bom_rabu_bear_break.py | Analisis spesifik Rabu Bear Break | 95.2% SameDay |
| Nov 2026 | bom_ohlc_analysis.py | OHLC vs OLHC pattern | OHLC 93.9% vs OLHC 91.6% |
| Nov 2026 | bom_sameday_tp.py | Combo 3-faktor: hari+class+seq | 7 combo 100% WR |
| Nov 2026 | bom_range_analysis.py | Pengaruh range D-1 | Range >200pts = 100% WR, instan |

---

## 4. KNOWLEDGE BASE — ATURAN TERVALIDASI

### Global Stats (435 hari)
- SameDay TP: 92.6%
- Overnight: 7.4% (32 hari)
- <30 menit: 55.4%
- <1 jam: 67.6%
- <2 jam: 78.4%
- AvgMAE: 10.3 pts | MedMAE: 3.4 pts | AvgTime: 93 mnt

### Per Hari
| Hari | N | SameDay% | Overnight% | <2h% | AvgMAE | AvgTime |
|------|---|----------|-----------|------|--------|---------|
| Senin | 88 | 93.2% | 6.8% | 78.4% | 11.4 | 93m |
| Selasa | 87 | 92.0% | 8.0% | 85.1% | 9.2 | 43m |
| Rabu | 87 | 93.1% | 6.9% | 78.2% | 10.8 | 110m |
| Kamis | 87 | 89.7% | 10.3% | 73.6% | 11.2 | 100m |
| Jumat | 86 | 95.3% | 4.7% | 76.7% | 8.8 | 118m |

### Top 7 Setup (100% SameDay TP)
1. Selasa + Bear Break + OHLC → n=12, <1h 83.3%, MAE med 1.8pts
2. Jumat + Inside Bar + OLHC → n=7, <1h 85.7%, MAE med 0.68pts
3. Rabu + Inside Bar + OHLC → n=5, <30m 80%, <2h 100%
4. Senin + Inside Bar + OLHC → n=10, <2h 90%
5. Senin + Bear Break + OHLC → n=15, <2h 80%
6. Selasa + Inside Bar + OLHC → n=5
7. Jumat + Bear Range + OLHC → n=4 ⚠️ sampel kecil

### Overnight Warning
- 100% overnight MAE > 15 poin — tidak ada overnight kecil
- Avg MAE overnight: 59.3 pts | Med: 52.8 pts
- Kamis paling sering overnight (10.3%)

### Range D-1 Impact
- Range 30-40 pts = BAHAYA → overnight 17.8%!
- Range 75-100 pts = normal, 94.8% SameDay
- Range >200 pts = terbaik, 100% SameDay, avg TP 8 menit!

---

## 5. ARSITEKTUR DSS (RENCANA)

```
scratch/bom_dss/
├── PROJECT_CONTEXT.md        ← file ini
├── data/
│   └── (symlink/copy dari bom_analysis/*.csv)
├── rules/
│   └── bom_rules.json        ← knowledge base terstruktur
├── engine/
│   ├── scorer.py             ← kalkulasi probabilitas
│   ├── lookup.py             ← lookup tabel historis
│   └── validator.py          ← cek kualitas input
├── backtest/
│   └── walk_forward.py       ← validasi out-of-sample
├── app/
│   ├── app.py                ← Streamlit UI
│   ├── pages/
│   │   ├── 1_input_harian.py
│   │   ├── 2_hasil_analisis.py
│   │   ├── 3_riwayat.py
│   │   └── 4_performa.py
│   └── components/
│       └── gauge.py
├── predictions/
│   └── history.json          ← riwayat prediksi + aktual
└── requirements.txt
```

---

## 6. STATUS DSS

| Komponen | Status | Keterangan |
|----------|--------|-----------|
| Data historis | ✅ Ada | 435 hari bom_daily_analysis.csv |
| Knowledge base CSV | ✅ Ada | 8 file CSV di bom_analysis/ |
| PROJECT_CONTEXT.md | ✅ Done | scratch/bom_dss/PROJECT_CONTEXT.md |
| build_rules.py | ✅ Done | Generate JSON dari semua CSV |
| rules/bom_rules.json | ✅ Done | 30 combo, 5 hari, 7 range bucket |
| engine/scorer.py | ✅ Done | Weighted probability + CI95 + tips |
| app/app.py | ✅ Done | Streamlit 4-tab, dark theme |
| .streamlit/config.toml | ✅ Done | Dark theme config |
| run_app.bat | ✅ Done | Double-click untuk jalankan |
| predictions/history.json | ✅ Auto | Dibuat otomatis saat pertama prediksi |
| Walk-forward validation | 🔲 Tahap 2 | Belum — jadwalkan setelah pakai 2 minggu |
| Model ML (Tahap 3) | 🔲 Opsional | Logistic regression / XGBoost |

## 7. CARA MENJALANKAN APP

```powershell
# Cara 1: Double-click file ini dari Windows Explorer
C:\Users\HYPE AMD\.gemini\antigravity\scratch\bom_dss\run_app.bat

# Cara 2: Manual dari PowerShell
Set-Location "C:\Users\HYPE AMD\.gemini\antigravity\scratch\bom_dss"
& "..\msnr_backtest\.venv\Scripts\streamlit.exe" run app/app.py --server.port 8501

# Buka browser:
http://localhost:8501
```

## 8. CARA PAKAI HARIAN

1. Buka chart XAUUSD Daily kemarin
2. Tentukan: Close > High D-2? → Bull Break. Close < Low D-2? → Bear Break. dll.
3. Lihat urutan terbentuknya High/Low → OHLC atau OLHC
4. Hitung range = High kemarin - Low kemarin
5. Buka app → isi sidebar → klik ANALISIS
6. Malam: update hasil aktual di tab Riwayat

---

## 7. KEPUTUSAN DESAIN

- Stack: **Python + Streamlit** (paling mudah, bisa run lokal, tidak perlu server)
- Rules disimpan di **JSON** agar mudah diedit tanpa ubah kode
- Tidak ada ML dulu — Tahap 1: rule-based probability saja
- Input: ketik manual (hari, candle class, OHLC/OLHC, range D-1)
- Output: probabilitas TP + kategori (tinggi/sedang/rendah) + n sampel + CI

---

## 8. TO-DO BERIKUTNYA

1. [ ] Buat `rules/bom_rules.json` dari semua CSV hasil backtest
2. [ ] Buat `engine/scorer.py` — logic conditional probability
3. [ ] Walk-forward validation (train: 2025, test: 2026)
4. [ ] Buat Streamlit app minimal (input harian + output skor)
5. [ ] Deploy local + test dengan data aktual

---
*Terakhir diperbarui: 2026-11-16 oleh DSS Builder*
