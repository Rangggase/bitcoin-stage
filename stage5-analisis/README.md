# Tahap 5 — Analisis data pasar (latihan teknis)

> **Bukan saran keuangan.** Tidak ada rekomendasi beli/jual, sinyal, atau prediksi. Ini latihan pengolahan data time series. Data historis tidak menjamin apa pun di masa depan.

## Konsep kunci
- **OHLCV**: per periode — *open, high, low, close, volume*. Konsistensi: `low ≤ open,close ≤ high`; `parse_klines` menolak baris yang melanggar.
- **Log return** `r = ln(Pt/Pt-1)`: bisa dijumlahkan antar-periode (Σ r = ln(P_akhir/P_awal)), simetris (+10% lalu −10% ≠ 0 pada return sederhana, tetapi ln(2) dan −ln(2) saling meniadakan), dan lebih mendekati distribusi simetris. Keduanya hampir sama untuk perubahan kecil.
- **Volatilitas** = simpangan baku return. Anualisasi harian→tahunan: `× √365` (kripto diperdagangkan 365 hari; asumsi return independen).
- **Visualisasi**: harga memakai garis (skala nilai); volatilitas bergulir 30 hari di panel terpisah dengan sumbu-x yang sama, agar terlihat kapan gejolak naik.
- **Keterbatasan**: sampel pendek, rezim pasar berubah, ekor gemuk (kejadian ekstrem lebih sering daripada distribusi normal), *survivorship*. **Overfitting**: bila mencoba banyak parameter pada satu data historis, "pola" yang ditemukan sering hanya kebetulan.

## Cara menjalankan
```powershell
cd D:\new another projecte\bitcoin-lab\stage5-analisis
..\.venv\Scripts\Activate.ps1
python analisis.py --synthetic          # offline, data SINTETIS (demo)
python analisis.py --limit 365          # data nyata dari API publik Binance (butuh internet)
pytest -q
```
Hasil: `data\harga.sqlite` dan `data\harga.png` (folder `data\` di-.gitignore).

## Latihan (Anda kerjakan)
Jalankan dengan data nyata, lalu bandingkan volatilitas dua rentang (mis. 90 hari terakhir vs 90 hari sebelumnya) memakai `compare_windows`. Jelaskan perbedaannya (mis. berita/regulasi/likuiditas, *volatility clustering*: gejolak cenderung berkelompok) — dan mengapa satu perbandingan tidak membuktikan sebab-akibat.

## Keputusan teknis & catatan
- Sumber: endpoint publik Binance (`/api/v3/klines`, tanpa kunci API). Bila diblokir di wilayah Anda, ganti `KLINES_URL`/parser dengan sumber lain (mis. Kraken, Coinbase) — verifikasi format di dokumentasi resmi.
- Mode `--synthetic`: data acak bersemi tetap, paruh kedua sengaja lebih bergejolak, supaya tes & demo deterministik. **Bukan data pasar.**
- `matplotlib` dipakai hanya untuk grafik; seluruh perhitungan memakai stdlib (`statistics`, `math`, `sqlite3`).
- Lingkungan pengembangan tak punya internet; jalur data nyata baru diuji dengan baris contoh (bukan panggilan jaringan nyata).

## Definition of done
10 tes lulus; data tersimpan ke SQLite; grafik dihasilkan dari data itu; catatan risiko ada di atas.
