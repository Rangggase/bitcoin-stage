import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import tx as T  # noqa: E402

K = T.keys

# Kunci CONTOH TESTNET (diturunkan dari angka tetap; bukan dompet nyata)
PRIV = 0xC0FFEE
PUB = K.public_key_bytes(PRIV)
MY_ADDR = K.p2wpkh_address_testnet(PUB)
DEST1 = K.p2pkh_address_testnet(K.public_key_bytes(7))
DEST2 = K.p2wpkh_address_testnet(K.public_key_bytes(9))
U = lambda v, n=0: {"txid": f"{n + 1:064x}", "vout": n, "value": v}  # noqa: E731


def test_bip143_sighash_vektor_resmi():
    """Vektor 'Native P2WPKH' dari BIP143 (input ke-2, nilai 6 BTC)."""
    unsigned = bytes.fromhex(
        "0100000002fff7f7881a8099afa6940d42d1e7f6362bec38171ea3edf433541db4e4ad969f0000000000eeffffffef51e1b8"
        "04cc89d182d279655c3aa89e815b1b309fe287d9b2b55d57b90ec68a0100000000ffffffff02202cb206000000001976a914"
        "8280b37df378db99f66f85c95a783a76ac7a6d5988ac9093510d000000001976a9143bde42dbee7e4dbe6a21b2d50ce2f016"
        "7faa815988ac11000000")
    d = T.decode_tx(unsigned.hex())
    tx = {"version": d["version"], "locktime": d["locktime"],
          "vin": [{"txid": i["txid"], "vout": i["vout"], "sequence": int(i["sequence"], 16), "script_sig": b"",
                   "witness": []} for i in d["vin"]],
          "vout": [{"value": o["value_sat"], "script": bytes.fromhex(o["script"])} for o in d["vout"]]}
    script_code = bytes.fromhex("76a9141d0f172a0ecb48aee1be1f2687d2963ae33f71a188ac")
    h = T.bip143_sighash(tx, 1, script_code, 600000000)
    assert h.hex() == "c37af31116d1b27caf68aae9e3ac82f1477929014d5b917657d0eb49478cb670"


def test_fee_dihitung_dari_vsize():
    assert T.fee_for(141, 2.0) == 282
    assert T.fee_for(141, 1.5) == 212  # dibulatkan ke atas


def test_fee_sama_dengan_input_dikurangi_output_dan_tarif_terpenuhi():
    r = T.build_signed_tx(PRIV, [U(100_000)], [(DEST1, 30_000), (DEST2, 20_000)], MY_ADDR, fee_rate=3)
    d = T.decode_tx(r["hex"])
    assert 100_000 - sum(o["value_sat"] for o in d["vout"]) == r["fee"]
    assert r["fee"] >= r["vsize"] * 3  # tarif minimal terpenuhi (estimasi konservatif)
    assert r["fee"] <= (r["vsize"] + 6) * 3  # dan tidak boros


def test_change_dihitung_dan_kembali_ke_alamat_sendiri():
    r = T.build_signed_tx(PRIV, [U(100_000)], [(DEST1, 30_000)], MY_ADDR, fee_rate=2)
    d = T.decode_tx(r["hex"])
    assert r["change"] == 100_000 - 30_000 - r["fee"]
    assert d["vout"][-1]["address"] == MY_ADDR and d["vout"][-1]["value_sat"] == r["change"]
    assert [o["address"] for o in d["vout"][:1]] == [DEST1]


def test_kembalian_debu_masuk_fee():
    r = T.build_signed_tx(PRIV, [U(30_300)], [(DEST2, 30_000)], MY_ADDR, fee_rate=1)
    assert r["change"] == 0 and r["fee"] == 300
    assert len(T.decode_tx(r["hex"])["vout"]) == 1


def test_dana_tidak_cukup_ditolak():
    with pytest.raises(T.InsufficientFunds):
        T.build_signed_tx(PRIV, [U(10_000)], [(DEST1, 10_000)], MY_ADDR)  # tidak ada sisa untuk fee
    with pytest.raises(T.InsufficientFunds):
        T.build_signed_tx(PRIV, [U(1_000), U(2_000, 1)], [(DEST1, 50_000)], MY_ADDR)


def test_output_debu_ditolak():
    with pytest.raises(ValueError):
        T.build_signed_tx(PRIV, [U(100_000)], [(DEST1, 100)], MY_ADDR)


def test_alamat_mainnet_ditolak():
    with pytest.raises(ValueError):
        T.address_to_script("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4")
    with pytest.raises(ValueError):
        T.address_to_script("1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2")


def test_multi_input_dipilih_terbesar_dulu():
    r = T.build_signed_tx(PRIV, [U(5_000, 0), U(60_000, 1), U(9_000, 2)], [(DEST1, 40_000)], MY_ADDR)
    assert r["inputs"] == 1


def test_tanda_tangan_valid_dan_terikat_isi_tx():
    r = T.build_signed_tx(PRIV, [U(100_000)], [(DEST1, 30_000)], MY_ADDR)
    d = T.decode_tx(r["hex"])
    sig, pub = (bytes.fromhex(w) for w in d["vin"][0]["witness"])
    assert pub == PUB and sig[-1] == T.SIGHASH_ALL
    tx = {"version": 2, "locktime": 0,
          "vin": [{"txid": d["vin"][0]["txid"], "vout": 0, "sequence": 0xFFFFFFFD, "script_sig": b"", "witness": []}],
          "vout": [{"value": o["value_sat"], "script": bytes.fromhex(o["script"])} for o in d["vout"]]}
    sc = T.script_p2pkh(K.hash160(PUB))
    h = T.bip143_sighash(tx, 0, sc, 100_000)
    assert K.verify_hash(PUB, h, K.der_decode(sig[:-1]))
    tx["vout"][0]["value"] += 1  # ubah jumlah -> sighash berubah -> tanda tangan lama gagal
    assert not K.verify_hash(PUB, T.bip143_sighash(tx, 0, sc, 100_000), K.der_decode(sig[:-1]))


def test_decode_roundtrip_dan_txid():
    r = T.build_signed_tx(PRIV, [U(100_000)], [(DEST1, 30_000), (DEST2, 20_000)], MY_ADDR)
    d = T.decode_tx(r["hex"])
    assert d["segwit"] and d["version"] == 2 and d["locktime"] == 0
    assert len(d["vout"]) == 3 and len(r["txid"]) == 64
    assert d["vout"][0]["address"] == DEST1 and d["vout"][1]["address"] == DEST2


def test_varint():
    assert T.varint(252) == b"\xfc" and T.varint(253) == b"\xfd\xfd\x00" and T.varint(65536) == b"\xfe\x00\x00\x01\x00"
    assert T.read_varint(T.varint(70000), 0)[0] == 70000
