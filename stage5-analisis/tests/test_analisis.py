import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import analisis as A  # noqa: E402

RAW = [[1_700_000_000_000 + i * 86_400_000, "100", "110", "95", str(100 + i), "12.5", 0, 0, 0, 0, 0, 0] for i in range(5)]


def test_parse_klines():
    rows = A.parse_klines(RAW)
    assert rows[0] == (1_700_000_000, 100.0, 110.0, 95.0, 100.0, 12.5, "binance")
    assert len(rows) == 5


def test_parse_menolak_candle_tidak_konsisten():
    with pytest.raises(ValueError):
        A.parse_klines([[0, "100", "90", "95", "100", "1"]])  # high < open


def test_sqlite_roundtrip_dan_upsert(tmp_path):
    db = str(tmp_path / "x.sqlite")
    rows = A.parse_klines(RAW)
    A.save(db, rows)
    A.save(db, rows)  # idempoten
    got = A.load(db)
    assert len(got) == 5 and got[2][4] == 102.0


def test_log_return_dan_sifat_penjumlahan():
    closes = [100, 110, 99, 120]
    lr = A.log_returns(closes)
    assert math.isclose(sum(lr), math.log(120 / 100))  # log return bisa dijumlahkan
    assert not math.isclose(sum(A.simple_returns(closes)), 120 / 100 - 1)  # simple return tidak


def test_log_return_simetris():
    assert math.isclose(A.log_returns([100, 200])[0], -A.log_returns([200, 100])[0])


def test_volatilitas_nol_untuk_harga_tumbuh_konstan():
    closes = [100 * 1.01 ** i for i in range(30)]
    sd, ann = A.volatility(A.log_returns(closes))
    assert sd < 1e-12 and ann < 1e-10


def test_volatilitas_anualisasi():
    sd, ann = A.volatility([0.01, -0.01, 0.02, -0.02], periods_per_year=365)
    assert math.isclose(ann, sd * math.sqrt(365))


def test_bandingkan_dua_rentang_pada_data_sintetis():
    rows = A.synthetic_candles(n=400, seed=1)
    c = A.compare_windows(rows, (0, 200), (200, 400))
    assert c["B"][0] > c["A"][0]  # paruh 2 sengaja lebih bergejolak


def test_sintetis_deterministik():
    assert A.synthetic_candles(10, seed=3) == A.synthetic_candles(10, seed=3)


def test_plot_membuat_file(tmp_path):
    out = tmp_path / "g.png"
    A.plot(A.synthetic_candles(100), str(out))
    assert out.stat().st_size > 1000
