import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import indexer as I  # noqa: E402

GENESIS_MERKLE = "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b"
REGTEST_GENESIS = {
    "hash": "0f9188f13cb7b2c71f2a335e3a4fc328bf5beb436012afca590b1a11466e2206", "height": 0, "version": 1,
    "merkleroot": GENESIS_MERKLE, "time": 1296688602, "bits": "207fffff", "nonce": 2, "size": 285, "weight": 1140,
    "tx": [GENESIS_MERKLE],
}


def test_hash_blok_genesis_regtest_dihitung_sendiri():
    h = I.header_hash(1, "0" * 64, GENESIS_MERKLE, 1296688602, "207fffff", 2)
    assert h == REGTEST_GENESIS["hash"]


def test_merkle_satu_tx_adalah_txid_dan_dua_tx_di_hash():
    a, b = "aa" * 32, "bb" * 32
    assert I.merkle_root([a]) == a
    manual = I.dsha256(bytes.fromhex(a)[::-1] + bytes.fromhex(b)[::-1])[::-1].hex()
    assert I.merkle_root([a, b]) == manual
    # jumlah ganjil: elemen terakhir diduplikasi
    assert I.merkle_root([a, b, a]) == I.dsha256(
        bytes.fromhex(I.merkle_root([a, b]))[::-1] + bytes.fromhex(I.merkle_root([a, a]))[::-1])[::-1].hex()


def test_parse_block():
    m = I.parse_block(REGTEST_GENESIS)
    assert m["hash_ok"] and m["merkle_ok"] and m["n_tx"] == 1 and m["prev_hash"] == "0" * 64


def test_parse_block_mendeteksi_data_rusak():
    rusak = dict(REGTEST_GENESIS, nonce=3)
    assert not I.parse_block(rusak)["hash_ok"]
    assert not I.parse_block(dict(REGTEST_GENESIS, tx=["cc" * 32]))["merkle_ok"]


class FakeNode:
    """Node tiruan: rantai kecil dengan hash yang benar secara kriptografis."""

    def __init__(self, chain="regtest", n=3):
        self.chain, self.blocks = chain, []
        prev = "0" * 64
        for h in range(n):
            txid = f"{h + 1:064x}"
            mr = I.merkle_root([txid])
            hh = I.header_hash(1, prev, mr, 1_700_000_000 + h, "207fffff", h)
            b = {"hash": hh, "height": h, "version": 1, "merkleroot": mr, "time": 1_700_000_000 + h, "bits": "207fffff",
                 "nonce": h, "size": 200, "weight": 800, "tx": [txid]}
            if h:
                b["previousblockhash"] = prev
            self.blocks.append(b)
            prev = hh

    def call(self, method, *p):
        if method == "getblockchaininfo":
            return {"chain": self.chain}
        if method == "getblockcount":
            return len(self.blocks) - 1
        if method == "getblockhash":
            return self.blocks[p[0]]["hash"]
        if method == "getblock":
            return next(b for b in self.blocks if b["hash"] == p[0])
        raise AssertionError(method)


def test_sync_dan_cocok_dengan_node():
    node, con = FakeNode(n=5), I.init_db()
    assert I.sync(node, con) == 5
    assert I.verify_against_node(node, con) == []
    assert con.execute("SELECT SUM(hash_ok), SUM(merkle_ok) FROM blocks").fetchone() == (5, 5)
    assert I.sync(node, con) == 0  # idempoten


def test_sync_menangkap_blok_baru_dan_reorg():
    node, con = FakeNode(n=3), I.init_db()
    I.sync(node, con)
    node.blocks = FakeNode(n=2).blocks + [dict(FakeNode(n=4).blocks[2], hash="ee" * 32)]  # blok ke-3 berbeda
    assert I.sync(node, con) == 1
    assert I.verify_against_node(node, con) == []


def test_verifikasi_mendeteksi_perbedaan():
    node, con = FakeNode(n=3), I.init_db()
    I.sync(node, con)
    con.execute("UPDATE blocks SET n_tx=9 WHERE height=1")
    assert I.verify_against_node(node, con)


def test_menolak_mainnet():
    with pytest.raises(I.RpcError):
        I.sync(FakeNode(chain="main"), I.init_db())


def test_rpc_client_format_dan_error():
    seen = {}

    class Resp:
        def __init__(self, d): self.d = d
        def read(self): return json.dumps(self.d).encode()
        def __enter__(self): return self
        def __exit__(self, *a): pass

    def opener(req, timeout):
        seen["auth"] = req.headers["Authorization"]
        seen["body"] = json.loads(req.data)
        return Resp({"result": None, "error": {"code": -1, "message": "boom"}, "id": 1})

    c = I.RpcClient(user="u", password="p", opener=opener)
    with pytest.raises(I.RpcError):
        c.call("getblockcount")
    assert seen["auth"].startswith("Basic ") and seen["body"]["method"] == "getblockcount"
