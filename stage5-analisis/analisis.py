"""Tahap 5: data harga harian -> SQLite -> log return, volatilitas, grafik.

LATIHAN TEKNIS, BUKAN SARAN KEUANGAN. Tidak ada sinyal beli/jual di sini.
"""
import argparse
import json
import math
import os
import random
import sqlite3
import statistics
import sys
import urllib.request

KLINES_URL = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit={limit}"
DDL = """CREATE TABLE IF NOT EXISTS candles(
  ts INTEGER PRIMARY KEY, open REAL, high REAL, low REAL, close REAL, volume REAL, source TEXT)"""


def fetch_klines(limit=365, opener=urllib.request.urlopen):
    req = urllib.request.Request(KLINES_URL.format(limit=limit), headers={"User-Agent": "bitcoin-lab-belajar/1.0"})
    with opener(req, timeout=15) as r:
        return json.loads(r.read().decode())


def parse_klines(raw, source="binance"):
    """Baris Binance: [open_time_ms, o, h, l, c, volume, ...] -> (ts_detik, o, h, l, c, vol, source)."""
    rows = []
    for k in raw:
        o, h, l, c, v = (float(x) for x in k[1:6])
        if not (h >= max(o, c, l) and l <= min(o, c, h)) or min(o, h, l, c) <= 0:
            raise ValueError(f"candle tidak konsisten: {k[:6]}")
        rows.append((int(k[0]) // 1000, o, h, l, c, v, source))
    return rows


def synthetic_candles(n=400, seed=42, start_price=30000.0, start_ts=1_600_000_000):
    """Data SINTETIS (random walk bersemi tetap) untuk demo offline. BUKAN data pasar asli."""
    rng = random.Random(seed)
    rows, price = [], start_price
    for i in range(n):
        vol = 0.02 if i < n // 2 else 0.05  # paruh kedua sengaja lebih bergejolak
        o = price
        c = o * math.exp(rng.gauss(0, vol))
        h, l = max(o, c) * (1 + abs(rng.gauss(0, vol / 3))), min(o, c) * (1 - abs(rng.gauss(0, vol / 3)))
        rows.append((start_ts + i * 86400, o, h, l, c, rng.uniform(100, 1000), "synthetic"))
        price = c
    return rows


def save(db_path, rows):
    with sqlite3.connect(db_path) as con:
        con.execute(DDL)
        con.executemany("INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?)", rows)


def load(db_path):
    with sqlite3.connect(db_path) as con:
        con.execute(DDL)
        return con.execute("SELECT ts,open,high,low,close,volume FROM candles ORDER BY ts").fetchall()


def log_returns(closes):
    """r_t = ln(P_t / P_{t-1}). Dipakai karena bisa dijumlahkan antar-periode dan simetris untuk naik/turun."""
    return [math.log(b / a) for a, b in zip(closes, closes[1:])]


def simple_returns(closes):
    return [b / a - 1 for a, b in zip(closes, closes[1:])]


def volatility(returns, periods_per_year=365):
    """Mengembalikan (std per periode, anualisasi = std * sqrt(periode/tahun))."""
    sd = statistics.stdev(returns)
    return sd, sd * math.sqrt(periods_per_year)


def rolling_volatility(returns, window=30):
    return [statistics.stdev(returns[i - window:i]) for i in range(window, len(returns) + 1)]


def compare_windows(rows, a, b):
    """Bandingkan volatilitas dua rentang indeks (start, end) pada data candle."""
    closes = [r[4] for r in rows]
    out = {}
    for nama, (s, e) in (("A", a), ("B", b)):
        out[nama] = volatility(log_returns(closes[s:e]))
    return out


def basic_stats(rows):
    closes = [r[4] for r in rows]
    lr = log_returns(closes)
    sd, ann = volatility(lr)
    return {"n_candle": len(rows), "min": min(closes), "max": max(closes), "rata2_log_return": statistics.mean(lr),
            "vol_harian": sd, "vol_tahunan": ann}


def plot(rows, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from datetime import datetime, timezone

    dates = [datetime.fromtimestamp(r[0], timezone.utc) for r in rows]
    closes = [r[4] for r in rows]
    lr = log_returns(closes)
    rv = rolling_volatility(lr, 30)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    a1.plot(dates, closes, lw=1.2)
    a1.set_ylabel("Harga penutupan")
    a1.set_title("Harga & volatilitas bergulir 30 hari (latihan teknis, bukan saran keuangan)")
    a2.plot(dates[-len(rv):], rv, color="tab:red", lw=1.2)
    a2.set_ylabel("Std log return harian")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=os.path.join("data", "harga.sqlite"))
    p.add_argument("--out", default=os.path.join("data", "harga.png"))
    p.add_argument("--synthetic", action="store_true", help="pakai data sintetis (offline)")
    p.add_argument("--limit", type=int, default=365)
    a = p.parse_args()
    os.makedirs(os.path.dirname(a.db) or ".", exist_ok=True)
    rows = synthetic_candles() if a.synthetic else parse_klines(fetch_klines(a.limit))
    save(a.db, rows)
    data = load(a.db)
    half = len(data) // 2
    print("Statistik:", json.dumps(basic_stats(data), indent=2))
    cmp = compare_windows(data, (0, half), (half, len(data)))
    print(f"Volatilitas harian paruh 1: {cmp['A'][0]:.4f}   paruh 2: {cmp['B'][0]:.4f}")
    plot(data, a.out)
    print("Grafik:", a.out, "\nCatatan: hanya latihan teknis, bukan saran keuangan.")


if __name__ == "__main__":
    sys.exit(main())
