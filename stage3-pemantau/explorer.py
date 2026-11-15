"""Tahap 3: klien API explorer testnet (format Esplora: mempool.space & Blockstream).

Hanya library standar (urllib). Hanya TESTNET: alamat mainnet ditolak.
"""
import json
import re
import time
import urllib.error
import urllib.request

EXPLORERS = {
    "mempool": "https://mempool.space/testnet/api",
    "blockstream": "https://blockstream.info/testnet/api",
}

# Testnet: legacy m/n (P2PKH), 2 (P2SH), tb1 (bech32 / bech32m). Mainnet (1, 3, bc1) TIDAK lolos.
_ADDR_RE = re.compile(r"^(tb1[a-z0-9]{11,87}|[mn2][1-9A-HJ-NP-Za-km-z]{25,34})$")


class ExplorerError(Exception):
    pass


class InvalidAddress(ValueError):
    pass


def validate_testnet_address(addr: str) -> str:
    addr = (addr or "").strip()
    if not _ADDR_RE.match(addr):
        raise InvalidAddress("Alamat bukan alamat testnet yang valid (harus diawali m, n, 2, atau tb1).")
    return addr


class TTLCache:
    """Cache sederhana di memori dengan masa berlaku (detik)."""

    def __init__(self, ttl=30, clock=time.monotonic):
        self.ttl, self.clock, self._d = ttl, clock, {}

    def get(self, key):
        item = self._d.get(key)
        if item and self.clock() - item[0] < self.ttl:
            return item[1]
        self._d.pop(key, None)
        return None

    def set(self, key, value):
        self._d[key] = (self.clock(), value)


def http_get_json(url, timeout=10, retries=2, sleep=time.sleep):
    """GET JSON dengan timeout, retry untuk 429/5xx (backoff eksponensial), dan error jelas."""
    delay = 1.0
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "bitcoin-lab-belajar/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                retry_after = e.headers.get("Retry-After") if e.headers else None
                sleep(float(retry_after) if retry_after and retry_after.isdigit() else delay)
                delay *= 2
                continue
            raise ExplorerError(f"HTTP {e.code} dari {url}") from e
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if attempt < retries:
                sleep(delay)
                delay *= 2
                continue
            raise ExplorerError(f"Gagal mengambil {url}: {e}") from e


def net_effect(tx: dict, address: str) -> int:
    """Perubahan saldo alamat akibat transaksi ini (satoshi): output ke alamat - input dari alamat."""
    masuk = sum(o.get("value", 0) for o in tx.get("vout", []) if o.get("scriptpubkey_address") == address)
    keluar = sum(
        (i.get("prevout") or {}).get("value", 0)
        for i in tx.get("vin", [])
        if (i.get("prevout") or {}).get("scriptpubkey_address") == address
    )
    return masuk - keluar


class Explorer:
    def __init__(self, base_url=EXPLORERS["mempool"], fetch=http_get_json, cache=None):
        self.base_url = base_url.rstrip("/")
        self.fetch = fetch
        self.cache = cache if cache is not None else TTLCache()

    def _get(self, path):
        url = f"{self.base_url}{path}"
        hit = self.cache.get(url)
        if hit is not None:
            return hit
        data = self.fetch(url)
        self.cache.set(url, data)
        return data

    def tip_height(self) -> int:
        return int(self._get("/blocks/tip/height"))

    def utxos(self, address):
        return self._get(f"/address/{validate_testnet_address(address)}/utxo")

    def txs(self, address):
        return self._get(f"/address/{validate_testnet_address(address)}/txs")

    def summary(self, address) -> dict:
        """Saldo, UTXO (dengan konfirmasi), dan riwayat ringkas satu alamat."""
        address = validate_testnet_address(address)
        tip = self.tip_height()
        utxos = []
        for u in self.utxos(address):
            st = u.get("status", {})
            conf = tip - st["block_height"] + 1 if st.get("confirmed") else 0
            utxos.append({"txid": u["txid"], "vout": u["vout"], "value": u["value"], "confirmations": conf})
        history = []
        for tx in self.txs(address):
            st = tx.get("status", {})
            conf = tip - st["block_height"] + 1 if st.get("confirmed") else 0
            history.append({"txid": tx["txid"], "net": net_effect(tx, address), "confirmations": conf,
                            "fee": tx.get("fee")})
        return {
            "address": address,
            "balance": sum(u["value"] for u in utxos),
            "balance_confirmed": sum(u["value"] for u in utxos if u["confirmations"] > 0),
            "utxos": utxos,
            "history": history,
            "tip": tip,
            "source": self.base_url,
        }


def compare_explorers(address, explorers=None):
    """Latihan: bandingkan saldo/jumlah UTXO dari dua explorer untuk alamat yang sama."""
    explorers = explorers or {n: Explorer(u) for n, u in EXPLORERS.items()}
    out = {}
    for name, ex in explorers.items():
        try:
            s = ex.summary(address)
            out[name] = {"balance": s["balance"], "utxos": len(s["utxos"]), "txs": len(s["history"]), "tip": s["tip"]}
        except ExplorerError as e:
            out[name] = {"error": str(e)}
    return out


if __name__ == "__main__":
    import sys

    addr = sys.argv[1] if len(sys.argv) > 1 else "mrCDrCybB6J1vRfbwM5hemdJz73FwDBC8r"
    for nama, hasil in compare_explorers(addr).items():
        print(nama, hasil)
