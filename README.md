# 🧠 BOM DSS — Decision Support System XAUUSD

**BOM (Buy on Market Open)** Decision Support System untuk XAUUSD.  
Menganalisis probabilitas TP +3.5 poin pada hari berjalan berdasarkan kondisi candle kemarin.

---

## 🚀 Cara Pakai

### Input Harian (5 menit sebelum market)
1. Buka chart XAUUSD Daily kemarin
2. Tentukan **class candle** (Bull Break / Bull Range / Inside / Bear Range / Bear Break)
3. Tentukan **urutan OHLC/OLHC** (High terbentuk dulu atau Low dulu)
4. Hitung **Range** = High − Low kemarin
5. Isi form → klik **ANALISIS**

### Output
- Probabilitas TP same-day (%)
- Kategori: TINGGI / SEDANG / RENDAH / WASPADA
- Confidence interval 95% dan jumlah sampel historis (n)
- Estimasi waktu TP dan floating MAE
- Tips & peringatan berdasarkan kondisi historis

---

## 📊 Data & Statistik

- **Data historis:** 435 hari (Jan 2025 – Sep 2026), XAUUSD Daily
- **Global Win Rate:** 92.6%
- **7 setup 100% WR** teridentifikasi
- Probabilitas dihitung dengan **Wilson CI 95%** untuk akurasi sampel kecil

---

## 🗂️ Struktur Project

```
bom_dss/
├── app/app.py              # Streamlit UI (mobile-first)
├── engine/scorer.py        # Probabilitas engine
├── rules/bom_rules.json    # Knowledge base (30 combo, 5 hari, 7 range bucket)
├── data/bom_daily_analysis.csv  # Data historis 435 hari
├── predictions/history.json     # Riwayat prediksi (lokal)
├── build_rules.py          # Script build ulang rules dari data
└── requirements.txt
```

---

## ⚡ Run Lokal

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

---

## ☁️ Deploy di Streamlit Community Cloud

1. Fork / push repo ini ke GitHub
2. Buka [share.streamlit.io](https://share.streamlit.io)
3. Klik **New app** → pilih repo ini
4. Set **Main file path:** `app/app.py`
5. Klik **Deploy**

---

## ⚠️ Disclaimer

> Probabilitas historis, **bukan prediksi pasti**.  
> Selalu siapkan manajemen risiko (averaging/grid).  
> Past performance does not guarantee future results.

---

*Built with Python + Streamlit | Data: XAUUSD Jan 2025–Sep 2026*
