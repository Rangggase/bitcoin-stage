"""Tahap 4: menyusun, menandatangani (P2WPKH, BIP143), dan men-decode transaksi testnet.

TIDAK ADA fungsi broadcast di sini. Hasilnya hanya raw hex; Anda yang menyiarkan sendiri.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "stage2-kunci"))
import keys  # noqa: E402

SIGHASH_ALL = 1
DUST_P2WPKH = 294  # sat; output di bawah ini tidak ekonomis (aturan relay standar)


class InsufficientFunds(Exception):
    pass


# ---------- serialisasi dasar ----------
def varint(n: int) -> bytes:
    if n < 0xFD:
        return bytes([n])
    if n <= 0xFFFF:
        return b"\xfd" + n.to_bytes(2, "little")
    if n <= 0xFFFFFFFF:
        return b"\xfe" + n.to_bytes(4, "little")
    return b"\xff" + n.to_bytes(8, "little")


def read_varint(b: bytes, pos: int):
    f = b[pos]
    if f < 0xFD:
        return f, pos + 1
    size = {0xFD: 2, 0xFE: 4, 0xFF: 8}[f]
    return int.from_bytes(b[pos + 1:pos + 1 + size], "little"), pos + 1 + size


def push(data: bytes) -> bytes:
    assert len(data) < 0x4C
    return bytes([len(data)]) + data


# ---------- script & alamat ----------
def script_p2pkh(h160: bytes) -> bytes:
    return b"\x76\xa9\x14" + h160 + b"\x88\xac"


def script_p2wpkh(h160: bytes) -> bytes:
    return b"\x00\x14" + h160


def address_to_script(addr: str) -> bytes:
    """Alamat TESTNET -> scriptPubKey. Alamat mainnet ditolak."""
    if addr.lower().startswith("tb1"):
        hrp, ver, prog = keys.bech32_decode_segwit(addr)
        if hrp != "tb" or ver != 0 or len(prog) != 20:
            raise ValueError("hanya P2WPKH (witness v0, 20 byte) yang didukung")
        return script_p2wpkh(prog)
    payload = keys.base58check_decode(addr)
    if payload[0] == keys.TESTNET_P2PKH and len(payload) == 21:
        return script_p2pkh(payload[1:])
    raise ValueError("bukan alamat testnet P2PKH/P2WPKH yang didukung")


def script_to_address(script: bytes):
    if len(script) == 22 and script[:2] == b"\x00\x14":
        return keys.bech32_encode_segwit("tb", 0, script[2:])
    if len(script) == 25 and script[:3] == b"\x76\xa9\x14" and script[-2:] == b"\x88\xac":
        return keys.base58check_encode(bytes([keys.TESTNET_P2PKH]) + script[3:23])
    return None


# ---------- ukuran & fee ----------
def estimate_vsize(n_in_p2wpkh: int, out_scripts) -> int:
    """Perkiraan konservatif (batas atas) vsize untuk input P2WPKH."""
    overhead = 11  # version 4 + marker/flag 0.5 (dibulatkan) + counts 2 + locktime 4
    vin = 68 * n_in_p2wpkh  # 41 non-witness + ~27 witness (sig 72 + pubkey 33 + 2 = 108 WU / 4)
    vout = sum(8 + len(varint(len(s))) + len(s) for s in out_scripts)
    return overhead + vin + vout


def fee_for(vsize: int, fee_rate: float) -> int:
    """fee_rate dalam sat/vbyte; dibulatkan ke atas."""
    return int(-(-vsize * fee_rate // 1))


# ---------- struktur transaksi ----------
def tx_input(txid_hex, vout, sequence=0xFFFFFFFD):
    return {"txid": txid_hex, "vout": vout, "sequence": sequence, "script_sig": b"", "witness": []}


def serialize(tx: dict, with_witness=True) -> bytes:
    segwit = with_witness and any(i["witness"] for i in tx["vin"])
    out = tx["version"].to_bytes(4, "little")
    if segwit:
        out += b"\x00\x01"
    out += varint(len(tx["vin"]))
    for i in tx["vin"]:
        out += bytes.fromhex(i["txid"])[::-1] + i["vout"].to_bytes(4, "little")
        out += varint(len(i["script_sig"])) + i["script_sig"] + i["sequence"].to_bytes(4, "little")
    out += varint(len(tx["vout"]))
    for o in tx["vout"]:
        out += o["value"].to_bytes(8, "little") + varint(len(o["script"])) + o["script"]
    if segwit:
        for i in tx["vin"]:
            out += varint(len(i["witness"])) + b"".join(varint(len(w)) + w for w in i["witness"])
    return out + tx["locktime"].to_bytes(4, "little")


def txid(tx: dict) -> str:
    return keys.hash256(serialize(tx, with_witness=False))[::-1].hex()


def vsize(tx: dict) -> int:
    base = len(serialize(tx, with_witness=False))
    total = len(serialize(tx, with_witness=True))
    weight = base * 3 + total
    return -(-weight // 4)


# ---------- sighash BIP143 (P2WPKH) ----------
def bip143_sighash(tx: dict, index: int, script_code: bytes, value: int, sighash_type=SIGHASH_ALL) -> bytes:
    prevouts = b"".join(bytes.fromhex(i["txid"])[::-1] + i["vout"].to_bytes(4, "little") for i in tx["vin"])
    sequences = b"".join(i["sequence"].to_bytes(4, "little") for i in tx["vin"])
    outputs = b"".join(o["value"].to_bytes(8, "little") + varint(len(o["script"])) + o["script"] for o in tx["vout"])
    i = tx["vin"][index]
    preimage = (
        tx["version"].to_bytes(4, "little")
        + keys.hash256(prevouts)
        + keys.hash256(sequences)
        + bytes.fromhex(i["txid"])[::-1] + i["vout"].to_bytes(4, "little")
        + varint(len(script_code)) + script_code
        + value.to_bytes(8, "little")
        + i["sequence"].to_bytes(4, "little")
        + keys.hash256(outputs)
        + tx["locktime"].to_bytes(4, "little")
        + sighash_type.to_bytes(4, "little")
    )
    return keys.hash256(preimage)


def sign_p2wpkh_input(tx: dict, index: int, priv: int, value: int) -> None:
    pub = keys.public_key_bytes(priv, compressed=True)
    script_code = script_p2pkh(keys.hash160(pub))  # scriptCode P2WPKH = skrip P2PKH
    sig = keys.der_encode(keys.sign_hash(priv, bip143_sighash(tx, index, script_code, value))) + bytes([SIGHASH_ALL])
    tx["vin"][index]["witness"] = [sig, pub]


# ---------- pemilihan UTXO & pembuatan transaksi ----------
def select_utxos(utxos, target: int, fee_rate: float, out_scripts):
    """Greedy terbesar-dulu. Mengembalikan (utxo_terpilih, fee, change); change=0 jika debu/habis."""
    chosen, total = [], 0
    for u in sorted(utxos, key=lambda u: -u["value"]):
        chosen.append(u)
        total += u["value"]
        change_script = b"\x00" * 22
        fee_with_change = fee_for(estimate_vsize(len(chosen), list(out_scripts) + [change_script]), fee_rate)
        fee_no_change = fee_for(estimate_vsize(len(chosen), out_scripts), fee_rate)
        if total >= target + fee_with_change and total - target - fee_with_change >= DUST_P2WPKH:
            return chosen, fee_with_change, total - target - fee_with_change
        if total >= target + fee_no_change:  # kembalian terlalu kecil -> jadi fee tambahan
            return chosen, total - target, 0
    raise InsufficientFunds(f"dana tidak cukup: butuh >= {target} + fee, tersedia {total} sat")


def build_signed_tx(priv: int, utxos, outputs, change_address: str, fee_rate: float = 2.0, locktime=0) -> dict:
    """utxos: [{'txid','vout','value'}] milik alamat P2WPKH dari `priv`.
    outputs: [(alamat_testnet, sat)]. Mengembalikan {'hex','txid','fee','change','vsize'}."""
    if not outputs:
        raise ValueError("minimal satu output")
    out_scripts = [address_to_script(a) for a, _ in outputs]
    for _, v in outputs:
        if v < DUST_P2WPKH:
            raise ValueError(f"output {v} sat di bawah batas debu ({DUST_P2WPKH})")
    target = sum(v for _, v in outputs)
    chosen, fee, change = select_utxos(utxos, target, fee_rate, out_scripts)
    tx = {
        "version": 2,
        "locktime": locktime,
        "vin": [tx_input(u["txid"], u["vout"]) for u in chosen],
        "vout": [{"value": v, "script": s} for (_, v), s in zip(outputs, out_scripts)],
    }
    if change:
        tx["vout"].append({"value": change, "script": address_to_script(change_address)})
    for idx, u in enumerate(chosen):
        sign_p2wpkh_input(tx, idx, priv, u["value"])
    total_in = sum(u["value"] for u in chosen)
    assert total_in - sum(o["value"] for o in tx["vout"]) == fee
    return {"hex": serialize(tx).hex(), "txid": txid(tx), "fee": fee, "change": change, "vsize": vsize(tx),
            "inputs": len(chosen)}


# ---------- decode (latihan) ----------
def decode_tx(raw_hex: str) -> dict:
    b = bytes.fromhex(raw_hex)
    pos = 0
    version = int.from_bytes(b[0:4], "little")
    pos = 4
    segwit = b[pos] == 0 and b[pos + 1] == 1
    if segwit:
        pos += 2
    n_in, pos = read_varint(b, pos)
    vin = []
    for _ in range(n_in):
        t = b[pos:pos + 32][::-1].hex()
        vo = int.from_bytes(b[pos + 32:pos + 36], "little")
        pos += 36
        sl, pos = read_varint(b, pos)
        ss = b[pos:pos + sl]
        pos += sl
        seq = int.from_bytes(b[pos:pos + 4], "little")
        pos += 4
        vin.append({"txid": t, "vout": vo, "script_sig": ss.hex(), "sequence": hex(seq), "witness": []})
    n_out, pos = read_varint(b, pos)
    vout = []
    for _ in range(n_out):
        val = int.from_bytes(b[pos:pos + 8], "little")
        pos += 8
        sl, pos = read_varint(b, pos)
        sc = b[pos:pos + sl]
        pos += sl
        vout.append({"value_sat": val, "script": sc.hex(), "address": script_to_address(sc)})
    if segwit:
        for i in vin:
            n_items, pos = read_varint(b, pos)
            for _ in range(n_items):
                l, pos = read_varint(b, pos)
                i["witness"].append(b[pos:pos + l].hex())
                pos += l
    locktime = int.from_bytes(b[pos:pos + 4], "little")
    assert pos + 4 == len(b), "ada sisa byte"
    return {"version": version, "segwit": segwit, "vin": vin, "vout": vout, "locktime": locktime}
