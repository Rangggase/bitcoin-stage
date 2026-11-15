"""Tahap 6: klien JSON-RPC Bitcoin Core (REGTEST), parser blok, dan indeks SQLite.

Hanya library standar. Menolak chain selain regtest/test agar tidak tersambung ke mainnet.
"""
import base64
import hashlib
import json
import sqlite3
import struct
import urllib.request

ALLOWED_CHAINS = {"regtest", "test", "testnet4", "signet"}  # TIDAK termasuk "main"


class RpcError(Exception):
    pass


class RpcClient:
    def __init__(self, url="http://127.0.0.1:18443", user="labuser", password="", opener=urllib.request.urlopen):
        self.url, self.opener = url, opener
        self._auth = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()
        self._id = 0

    def call(self, method, *params):
        self._id += 1
        body = json.dumps({"jsonrpc": "1.0", "id": self._id, "method": method, "params": list(params)}).encode()
        req = urllib.request.Request(self.url, body, {"Content-Type": "application/json", "Authorization": self._auth})
        try:
            with self.opener(req, timeout=15) as r:
                resp = json.loads(r.read().decode())
        except Exception as e:  # HTTPError 500 dari Core tetap membawa JSON error
            if hasattr(e, "read"):
                try:
                    resp = json.loads(e.read().decode())
                except Exception:
                    raise RpcError(f"RPC gagal: {e}") from e
            else:
                raise RpcError(f"RPC gagal: {e}") from e
        if resp.get("error"):
            raise RpcError(str(resp["error"]))
        return resp["result"]


def assert_safe_chain(rpc) -> str:
    chain = rpc.call("getblockchaininfo")["chain"]
    if chain not in ALLOWED_CHAINS:
        raise RpcError(f"Chain '{chain}' ditolak: lab ini hanya untuk regtest/testnet.")
    return chain


# ---------- hash & merkle (dihitung sendiri untuk verifikasi) ----------
def dsha256(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def header_hash(version: int, prev_hash: str, merkle_root: str, time: int, bits: str, nonce: int) -> str:
    """Hash blok = SHA256d(header 80 byte), little-endian dibalik untuk tampilan."""
    header = (struct.pack("<i", version) + bytes.fromhex(prev_hash)[::-1] + bytes.fromhex(merkle_root)[::-1]
              + struct.pack("<III", time, int(bits, 16), nonce))
    assert len(header) == 80
    return dsha256(header)[::-1].hex()


def merkle_root(txids):
    """Merkle root dari daftar txid (hex, urutan tampilan). Level ganjil: elemen terakhir diduplikasi."""
    level = [bytes.fromhex(t)[::-1] for t in txids]
    if not level:
        raise ValueError("blok tanpa transaksi")
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [dsha256(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
    return level[0][::-1].hex()


# ---------- model data & parser ----------
def parse_block(b: dict) -> dict:
    """Respons `getblock <hash> 1` -> model kita. Memverifikasi hash dan merkle root sendiri."""
    model = {
        "height": b["height"], "hash": b["hash"], "prev_hash": b.get("previousblockhash", "0" * 64),
        "merkle_root": b["merkleroot"], "time": b["time"], "bits": b["bits"], "nonce": b["nonce"],
        "version": b["version"], "n_tx": len(b["tx"]), "size": b.get("size"), "weight": b.get("weight"),
        "txids": list(b["tx"]),
    }
    model["hash_ok"] = header_hash(model["version"], model["prev_hash"], model["merkle_root"], model["time"],
                                   model["bits"], model["nonce"]) == model["hash"]
    model["merkle_ok"] = merkle_root(model["txids"]) == model["merkle_root"]
    return model


DDL = """
CREATE TABLE IF NOT EXISTS blocks(height INTEGER PRIMARY KEY, hash TEXT UNIQUE, prev_hash TEXT, merkle_root TEXT,
  time INTEGER, bits TEXT, nonce INTEGER, version INTEGER, n_tx INTEGER, size INTEGER, weight INTEGER,
  hash_ok INTEGER, merkle_ok INTEGER);
CREATE TABLE IF NOT EXISTS txs(txid TEXT PRIMARY KEY, block_height INTEGER REFERENCES blocks(height), idx INTEGER);
"""


def init_db(path=":memory:"):
    con = sqlite3.connect(path)
    con.executescript(DDL)
    return con


def store_block(con, m: dict):
    con.execute("INSERT OR REPLACE INTO blocks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (m["height"], m["hash"], m["prev_hash"], m["merkle_root"], m["time"], m["bits"], m["nonce"],
                 m["version"], m["n_tx"], m["size"], m["weight"], int(m["hash_ok"]), int(m["merkle_ok"])))
    con.execute("DELETE FROM txs WHERE block_height=?", (m["height"],))
    con.executemany("INSERT INTO txs VALUES (?,?,?)", [(t, m["height"], i) for i, t in enumerate(m["txids"])])
    con.commit()


def sync(rpc, con) -> int:
    """Indeks semua blok sampai tip. Mendeteksi reorg sederhana: bila hash di DB != node, tulis ulang."""
    assert_safe_chain(rpc)
    tip = rpc.call("getblockcount")
    n = 0
    for h in range(0, tip + 1):
        node_hash = rpc.call("getblockhash", h)
        row = con.execute("SELECT hash FROM blocks WHERE height=?", (h,)).fetchone()
        if row and row[0] == node_hash:
            continue
        store_block(con, parse_block(rpc.call("getblock", node_hash, 1)))
        n += 1
    con.execute("DELETE FROM txs WHERE block_height>?", (tip,))
    con.execute("DELETE FROM blocks WHERE height>?", (tip,))
    con.commit()
    return n


def verify_against_node(rpc, con) -> list:
    """Kembalikan daftar ketidakcocokan (kosong = indeks sama dengan node)."""
    problems = []
    tip = rpc.call("getblockcount")
    cnt = con.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]
    if cnt != tip + 1:
        problems.append(f"jumlah blok indeks {cnt} != node {tip + 1}")
    for h in range(tip + 1):
        row = con.execute("SELECT hash, n_tx FROM blocks WHERE height=?", (h,)).fetchone()
        blk = rpc.call("getblock", rpc.call("getblockhash", h), 1)
        if not row or row[0] != blk["hash"] or row[1] != len(blk["tx"]):
            problems.append(f"blok {h} berbeda")
    return problems


if __name__ == "__main__":
    import argparse
    import os

    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:18443")
    p.add_argument("--user", default="labuser")
    p.add_argument("--password", default=os.environ.get("BTC_RPC_PASSWORD", ""))
    p.add_argument("--db", default=os.path.join("data", "regtest.sqlite"))
    a = p.parse_args()
    os.makedirs(os.path.dirname(a.db), exist_ok=True)
    rpc = RpcClient(a.url, a.user, a.password)
    con = init_db(a.db)
    print("Chain:", assert_safe_chain(rpc), "| blok baru diindeks:", sync(rpc, con))
    print("Ketidakcocokan:", verify_against_node(rpc, con) or "tidak ada")
