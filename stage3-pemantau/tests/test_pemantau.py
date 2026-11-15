import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import explorer as ex  # noqa: E402
from app import create_app  # noqa: E402

ADDR = "mrCDrCybB6J1vRfbwM5hemdJz73FwDBC8r"
LAIN = "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx"


def fake_fetch_factory(calls):
    def fake(url):
        calls.append(url)
        if url.endswith("/blocks/tip/height"):
            return 1000
        if url.endswith("/utxo"):
            return [{"txid": "aa" * 32, "vout": 0, "value": 5000, "status": {"confirmed": True, "block_height": 995}},
                    {"txid": "bb" * 32, "vout": 1, "value": 700, "status": {"confirmed": False}}]
        if url.endswith("/txs"):
            return [
                {"txid": "aa" * 32, "fee": 200, "status": {"confirmed": True, "block_height": 995},
                 "vin": [{"prevout": {"scriptpubkey_address": LAIN, "value": 6000}}],
                 "vout": [{"scriptpubkey_address": ADDR, "value": 5000}, {"scriptpubkey_address": LAIN, "value": 800}]},
                {"txid": "cc" * 32, "fee": 100, "status": {"confirmed": True, "block_height": 990},
                 "vin": [{"prevout": {"scriptpubkey_address": ADDR, "value": 3000}}],
                 "vout": [{"scriptpubkey_address": LAIN, "value": 2900}]},
            ]
        raise AssertionError(url)
    return fake


def test_saldo_utxo_dan_konfirmasi():
    e = ex.Explorer("http://x/api", fetch=fake_fetch_factory([]))
    s = e.summary(ADDR)
    assert s["balance"] == 5700 and s["balance_confirmed"] == 5000
    assert [u["confirmations"] for u in s["utxos"]] == [6, 0]  # 1000-995+1
    assert [t["net"] for t in s["history"]] == [5000, -3000]


def test_cache_mencegah_panggilan_ulang():
    calls = []
    e = ex.Explorer("http://x/api", fetch=fake_fetch_factory(calls))
    e.summary(ADDR)
    n = len(calls)
    e.summary(ADDR)
    assert len(calls) == n


def test_cache_kedaluwarsa():
    t = [0.0]
    c = ex.TTLCache(ttl=10, clock=lambda: t[0])
    c.set("k", 1)
    assert c.get("k") == 1
    t[0] = 11
    assert c.get("k") is None


@pytest.mark.parametrize("bad", ["", "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2", "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
                                 "../../etc/passwd", "mabc"])
def test_alamat_mainnet_atau_aneh_ditolak(bad):
    with pytest.raises(ex.InvalidAddress):
        ex.validate_testnet_address(bad)


def test_alamat_testnet_diterima():
    assert ex.validate_testnet_address(ADDR) == ADDR
    assert ex.validate_testnet_address(LAIN) == LAIN


def test_retry_lalu_gagal(monkeypatch):
    import urllib.error

    def boom(*a, **k):
        raise urllib.error.URLError("putus")

    monkeypatch.setattr(ex.urllib.request, "urlopen", boom)
    tidur = []
    with pytest.raises(ex.ExplorerError):
        ex.http_get_json("http://x", retries=2, sleep=tidur.append)
    assert tidur == [1.0, 2.0]


def test_web_app():
    e = ex.Explorer("http://x/api", fetch=fake_fetch_factory([]))
    c = create_app(lambda name: e).test_client()
    assert c.get("/").status_code == 200
    r = c.get(f"/?address={ADDR}")
    assert r.status_code == 200 and b"5700" in r.data
    assert c.get("/?address=bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq").status_code == 400
