"""Tahap 7a: BIP39 (mnemonic) + BIP32 (kunci hierarkis) + BIP84 testnet (m/84'/1'/0'/0/0).

HANYA TESTNET / UNTUK BELAJAR. Mnemonic yang Anda buat dengan modul ini jangan dipakai untuk dana nyata.
"""
import hashlib
import hmac
import os
import secrets
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "stage2-kunci"))
import keys  # noqa: E402

with open(os.path.join(os.path.dirname(__file__), "bip39_english.txt"), encoding="utf-8") as _f:
    WORDLIST = _f.read().split()
assert len(WORDLIST) == 2048

HARDENED = 0x80000000
TPRV_VERSION = bytes.fromhex("04358394")  # testnet extended private key
TPUB_VERSION = bytes.fromhex("043587CF")


# ---------- BIP39 ----------
def entropy_to_mnemonic(entropy: bytes) -> str:
    if len(entropy) not in (16, 20, 24, 28, 32):
        raise ValueError("entropy harus 16-32 byte (kelipatan 4)")
    cs_bits = len(entropy) * 8 // 32
    bits = bin(int.from_bytes(entropy, "big"))[2:].zfill(len(entropy) * 8)
    bits += bin(hashlib.sha256(entropy).digest()[0])[2:].zfill(8)[:cs_bits]
    return " ".join(WORDLIST[int(bits[i:i + 11], 2)] for i in range(0, len(bits), 11))


def generate_mnemonic(words: int = 12) -> str:
    return entropy_to_mnemonic(secrets.token_bytes({12: 16, 15: 20, 18: 24, 21: 28, 24: 32}[words]))


def mnemonic_is_valid(mnemonic: str) -> bool:
    words = mnemonic.split()
    if len(words) not in (12, 15, 18, 21, 24) or any(w not in WORDLIST for w in words):
        return False
    bits = "".join(bin(WORDLIST.index(w))[2:].zfill(11) for w in words)
    cs_len = len(bits) // 33
    ent, cs = bits[:-cs_len], bits[-cs_len:]
    entropy = int(ent, 2).to_bytes(len(ent) // 8, "big")
    return bin(hashlib.sha256(entropy).digest()[0])[2:].zfill(8)[:cs_len] == cs


def mnemonic_to_seed(mnemonic: str, passphrase: str = "") -> bytes:
    m = unicodedata.normalize("NFKD", mnemonic)
    salt = unicodedata.normalize("NFKD", "mnemonic" + passphrase)
    return hashlib.pbkdf2_hmac("sha512", m.encode(), salt.encode(), 2048)


# ---------- BIP32 ----------
class ExtKey:
    def __init__(self, key: int, chain: bytes, depth=0, parent_fp=b"\0\0\0\0", index=0):
        self.key, self.chain, self.depth, self.parent_fp, self.index = key, chain, depth, parent_fp, index

    @property
    def pub(self) -> bytes:
        return keys.public_key_bytes(self.key)

    @property
    def fingerprint(self) -> bytes:
        return keys.hash160(self.pub)[:4]

    def child(self, i: int) -> "ExtKey":
        data = (b"\x00" + self.key.to_bytes(32, "big") if i >= HARDENED else self.pub) + i.to_bytes(4, "big")
        I = hmac.new(self.chain, data, hashlib.sha512).digest()
        il = int.from_bytes(I[:32], "big")
        child = (il + self.key) % keys.N
        if il >= keys.N or child == 0:
            raise ValueError("indeks tidak valid, coba indeks berikutnya")
        return ExtKey(child, I[32:], self.depth + 1, self.fingerprint, i)

    def derive(self, path: str) -> "ExtKey":
        node = self
        parts = path.split("/")
        if parts[0] != "m":
            raise ValueError("path harus diawali 'm'")
        for p in parts[1:]:
            hard = p.endswith(("'", "h"))
            node = node.child(int(p.rstrip("'h")) + (HARDENED if hard else 0))
        return node

    def serialize_private(self, version: bytes = TPRV_VERSION) -> str:
        raw = (version + bytes([self.depth]) + self.parent_fp + self.index.to_bytes(4, "big") + self.chain
               + b"\x00" + self.key.to_bytes(32, "big"))
        return keys.base58check_encode(raw)

    def serialize_public(self, version: bytes = TPUB_VERSION) -> str:
        raw = version + bytes([self.depth]) + self.parent_fp + self.index.to_bytes(4, "big") + self.chain + self.pub
        return keys.base58check_encode(raw)


def master_from_seed(seed: bytes) -> ExtKey:
    I = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
    return ExtKey(int.from_bytes(I[:32], "big"), I[32:])


def bip84_testnet_address(mnemonic: str, account=0, change=0, index=0, passphrase=""):
    """Alamat P2WPKH testnet di m/84'/1'/account'/change/index (coin type 1 = semua testnet)."""
    root = master_from_seed(mnemonic_to_seed(mnemonic, passphrase))
    node = root.derive(f"m/84'/1'/{account}'/{change}/{index}")
    return keys.p2wpkh_address_testnet(node.pub), node


if __name__ == "__main__":
    m = generate_mnemonic(12)
    addr, node = bip84_testnet_address(m)
    print("CONTOH TESTNET - jangan dipakai untuk dana nyata\nMnemonic :", m)
    print("Jalur    : m/84'/1'/0'/0/0\nAlamat   :", addr)
