"""Tahap 7b: multisig P2WSH 2-of-3 (TESTNET) dengan penandatanganan BIP143.

Tidak ada kode broadcast; hasilnya raw hex untuk Anda periksa.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "stage4-transaksi"))
import tx as T  # noqa: E402

K = T.keys
OP_2, OP_3, OP_CHECKMULTISIG = 0x52, 0x53, 0xAE


def witness_script(pubkeys, m=2) -> bytes:
    """OP_m <pk...> OP_n OP_CHECKMULTISIG, kunci diurutkan (BIP67) agar alamat tak bergantung urutan."""
    pubs = sorted(pubkeys)
    if not (1 <= m <= len(pubs) <= 16) or any(len(p) != 33 for p in pubs):
        raise ValueError("parameter multisig tidak valid")
    return bytes([0x50 + m]) + b"".join(bytes([33]) + p for p in pubs) + bytes([0x50 + len(pubs), OP_CHECKMULTISIG])


def p2wsh_script(ws: bytes) -> bytes:
    return b"\x00\x20" + K.sha256(ws)  # scriptPubKey: witness v0 + SHA256(witnessScript)


def p2wsh_address_testnet(ws: bytes) -> str:
    return K.bech32_encode_segwit("tb", 0, K.sha256(ws))


def spend(utxo: dict, ws: bytes, signer_privs, dest_script: bytes, fee: int) -> dict:
    """Belanjakan satu UTXO P2WSH ke satu output. Perlu >= m tanda tangan, urutan harus mengikuti urutan kunci di script."""
    value = utxo["value"] - fee
    if value < T.DUST_P2WPKH:
        raise ValueError("nilai terlalu kecil")
    tx = {"version": 2, "locktime": 0, "vin": [T.tx_input(utxo["txid"], utxo["vout"])],
          "vout": [{"value": value, "script": dest_script}]}
    h = T.bip143_sighash(tx, 0, ws, utxo["value"])  # scriptCode = witnessScript lengkap
    order = {p: i for i, p in enumerate(sorted(K.public_key_bytes(k) for k in signer_privs))}
    script_pubs = [ws[1 + 34 * i + 1: 1 + 34 * i + 34] for i in range((len(ws) - 3) // 34)]
    need = ws[0] - 0x50
    if len(signer_privs) < need:
        raise ValueError(f"butuh {need} penanda tangan")
    sigs = []
    for k in sorted(signer_privs, key=lambda k: script_pubs.index(K.public_key_bytes(k)))[:need]:
        sigs.append(K.der_encode(K.sign_hash(k, h)) + bytes([T.SIGHASH_ALL]))
    # witness: item kosong (bug off-by-one OP_CHECKMULTISIG), tanda tangan, witnessScript
    tx["vin"][0]["witness"] = [b""] + sigs + [ws]
    return {"hex": T.serialize(tx).hex(), "txid": T.txid(tx), "sighash": h, "tx": tx, "order": order}


def verify_multisig_witness(tx: dict, ws: bytes, value: int) -> bool:
    """Verifikasi ala OP_CHECKMULTISIG: tiap tanda tangan harus cocok dengan kunci, berurutan."""
    wit = tx["vin"][0]["witness"]
    if wit[0] != b"" or wit[-1] != ws:
        return False
    sigs = wit[1:-1]
    pubs = [ws[1 + 34 * i + 1: 1 + 34 * i + 34] for i in range((len(ws) - 3) // 34)]
    if len(sigs) != ws[0] - 0x50:
        return False
    h = T.bip143_sighash(tx, 0, ws, value)
    pi = 0
    for s in sigs:
        if s[-1] != T.SIGHASH_ALL:
            return False
        sig = K.der_decode(s[:-1])
        while pi < len(pubs) and not K.verify_hash(pubs[pi], h, sig):
            pi += 1
        if pi == len(pubs):
            return False
        pi += 1
    return True


if __name__ == "__main__":
    privs = [0xA11CE, 0xB0B, 0xCA401]  # CONTOH TESTNET
    pubs = [K.public_key_bytes(k) for k in privs]
    ws = witness_script(pubs)
    print("witnessScript :", ws.hex())
    print("Alamat 2-of-3 :", p2wsh_address_testnet(ws))
    r = spend({"txid": "22" * 32, "vout": 0, "value": 100_000}, ws, privs[:2],
              T.address_to_script(K.p2wpkh_address_testnet(pubs[0])), 300)
    print("Raw tx (2 dari 3 menandatangani):", r["hex"])
    print("Verifikasi:", verify_multisig_witness(r["tx"], ws, 100_000))
