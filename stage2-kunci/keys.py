"""Tahap 2: kunci privat/publik, alamat testnet, WIF, dan tanda tangan ECDSA.

Implementasi secp256k1 ditulis manual UNTUK BELAJAR (bukan konstan-waktu, jangan
dipakai mengamankan dana nyata). Tes membandingkannya dengan `coincurve`.
HANYA TESTNET.
"""
import hashlib
import hmac
import secrets

# ---- Parameter kurva secp256k1: y^2 = x^3 + 7 (mod P) ----
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (
    0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
    0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
)
TESTNET_P2PKH = 0x6F
TESTNET_WIF = 0xEF
TESTNET_HRP = "tb"


# ---- Aritmetika titik (None = titik di tak hingga) ----
def point_add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    (x1, y1), (x2, y2) = a, b
    if x1 == x2 and (y1 + y2) % P == 0:
        return None
    if a == b:
        lam = 3 * x1 * x1 * pow(2 * y1, -1, P) % P
    else:
        lam = (y2 - y1) * pow(x2 - x1, -1, P) % P
    x3 = (lam * lam - x1 - x2) % P
    return x3, (lam * (x1 - x3) - y1) % P


def point_mul(k, pt=G):
    """Perkalian skalar (double-and-add)."""
    result, addend = None, pt
    while k:
        if k & 1:
            result = point_add(result, addend)
        addend = point_add(addend, addend)
        k >>= 1
    return result


# ---- Kunci ----
def generate_private_key() -> int:
    """Angka acak aman secara kriptografis di rentang [1, N-1]."""
    while True:
        k = secrets.randbelow(N)
        if k >= 1:
            return k


def public_key_point(priv: int):
    if not 1 <= priv < N:
        raise ValueError("kunci privat di luar rentang [1, N-1]")
    return point_mul(priv)


def public_key_bytes(priv: int, compressed: bool = True) -> bytes:
    x, y = public_key_point(priv)
    if compressed:
        return bytes([2 + (y & 1)]) + x.to_bytes(32, "big")
    return b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big")


# ---- Hash ----
def sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def hash256(b: bytes) -> bytes:
    return sha256(sha256(b))


def ripemd160(b: bytes) -> bytes:
    try:
        return hashlib.new("ripemd160", b).digest()
    except ValueError:  # OpenSSL 3 tanpa legacy provider
        return _ripemd160_pure(b)


def hash160(b: bytes) -> bytes:
    return ripemd160(sha256(b))


def _ripemd160_pure(data: bytes) -> bytes:
    """RIPEMD-160 murni Python sebagai cadangan jika hashlib tidak menyediakannya."""
    M = 0xFFFFFFFF

    def rol(x, n):
        return ((x << n) | (x >> (32 - n))) & M

    r1 = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 7, 4, 13, 1, 10, 6, 15, 3, 12, 0, 9, 5, 2, 14, 11, 8,
          3, 10, 14, 4, 9, 15, 8, 1, 2, 7, 0, 6, 13, 11, 5, 12, 1, 9, 11, 10, 0, 8, 12, 4, 13, 3, 7, 15, 14, 5, 6, 2,
          4, 0, 5, 9, 7, 12, 2, 10, 14, 1, 3, 8, 11, 6, 15, 13]
    r2 = [5, 14, 7, 0, 9, 2, 11, 4, 13, 6, 15, 8, 1, 10, 3, 12, 6, 11, 3, 7, 0, 13, 5, 10, 14, 15, 8, 12, 4, 9, 1, 2,
          15, 5, 1, 3, 7, 14, 6, 9, 11, 8, 12, 2, 10, 0, 4, 13, 8, 6, 4, 1, 3, 11, 15, 0, 5, 12, 2, 13, 9, 7, 10, 14,
          12, 15, 10, 4, 1, 5, 8, 7, 6, 2, 13, 14, 0, 3, 9, 11]
    s1 = [11, 14, 15, 12, 5, 8, 7, 9, 11, 13, 14, 15, 6, 7, 9, 8, 7, 6, 8, 13, 11, 9, 7, 15, 7, 12, 15, 9, 11, 7, 13, 12,
          11, 13, 6, 7, 14, 9, 13, 15, 14, 8, 13, 6, 5, 12, 7, 5, 11, 12, 14, 15, 14, 15, 9, 8, 9, 14, 5, 6, 8, 6, 5, 12,
          9, 15, 5, 11, 6, 8, 13, 12, 5, 12, 13, 14, 11, 8, 5, 6]
    s2 = [8, 9, 9, 11, 13, 15, 15, 5, 7, 7, 8, 11, 14, 14, 12, 6, 9, 13, 15, 7, 12, 8, 9, 11, 7, 7, 12, 7, 6, 15, 13, 11,
          9, 7, 15, 11, 8, 6, 6, 14, 12, 13, 5, 14, 13, 13, 7, 5, 15, 5, 8, 11, 14, 14, 6, 14, 6, 9, 12, 9, 12, 5, 15, 8,
          8, 5, 12, 9, 12, 5, 14, 6, 8, 13, 6, 5, 15, 13, 11, 11]
    k1 = [0, 0x5A827999, 0x6ED9EBA1, 0x8F1BBCDC, 0xA953FD4E]
    k2 = [0x50A28BE6, 0x5C4DD124, 0x6D703EF3, 0x7A6D76E9, 0]
    fs = [lambda x, y, z: x ^ y ^ z,
          lambda x, y, z: (x & y) | (~x & M & z),
          lambda x, y, z: (x | (~y & M)) ^ z,
          lambda x, y, z: (x & z) | (y & ~z & M),
          lambda x, y, z: x ^ (y | (~z & M))]
    msg = data + b"\x80"
    msg += b"\x00" * ((56 - len(msg)) % 64) + (len(data) * 8).to_bytes(8, "little")
    h = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0]
    for off in range(0, len(msg), 64):
        X = [int.from_bytes(msg[off + i * 4:off + i * 4 + 4], "little") for i in range(16)]
        a1, b1, c1, d1, e1 = h
        a2, b2, c2, d2, e2 = h
        for j in range(80):
            r = j // 16
            t = (rol((a1 + fs[r](b1, c1, d1) + X[r1[j]] + k1[r]) & M, s1[j]) + e1) & M
            a1, e1, d1, c1, b1 = e1, d1, rol(c1, 10), b1, t
            t = (rol((a2 + fs[4 - r](b2, c2, d2) + X[r2[j]] + k2[r]) & M, s2[j]) + e2) & M
            a2, e2, d2, c2, b2 = e2, d2, rol(c2, 10), b2, t
        t = (h[1] + c1 + d2) & M
        h = [t, (h[2] + d1 + e2) & M, (h[3] + e1 + a2) & M, (h[4] + a1 + b2) & M, (h[0] + b1 + c2) & M]
    return b"".join(x.to_bytes(4, "little") for x in h)


# ---- Base58Check ----
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def base58check_encode(payload: bytes) -> str:
    data = payload + hash256(payload)[:4]
    n = int.from_bytes(data, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = B58[r] + out
    pad = len(data) - len(data.lstrip(b"\x00"))
    return "1" * pad + out


def base58check_decode(s: str) -> bytes:
    n = 0
    for ch in s:
        n = n * 58 + B58.index(ch)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    raw = b"\x00" * (len(s) - len(s.lstrip("1"))) + raw
    payload, checksum = raw[:-4], raw[-4:]
    if hash256(payload)[:4] != checksum:
        raise ValueError("checksum Base58Check salah")
    return payload


def to_wif_testnet(priv: int, compressed: bool = True) -> str:
    payload = bytes([TESTNET_WIF]) + priv.to_bytes(32, "big") + (b"\x01" if compressed else b"")
    return base58check_encode(payload)


def from_wif(wif: str):
    payload = base58check_decode(wif)
    if payload[0] != TESTNET_WIF:
        raise ValueError("bukan WIF testnet")
    compressed = len(payload) == 34 and payload[-1] == 1
    return int.from_bytes(payload[1:33], "big"), compressed


def p2pkh_address_testnet(pubkey: bytes) -> str:
    return base58check_encode(bytes([TESTNET_P2PKH]) + hash160(pubkey))


# ---- Bech32 (BIP173, untuk witness v0) ----
CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _polymod(values):
    gen = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ v
        for i in range(5):
            chk ^= gen[i] if (b >> i) & 1 else 0
    return chk


def _hrp_expand(hrp):
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def _convertbits(data, frm, to, pad=True):
    acc = bits = 0
    ret = []
    maxv = (1 << to) - 1
    for v in data:
        acc = (acc << frm) | v
        bits += frm
        while bits >= to:
            bits -= to
            ret.append((acc >> bits) & maxv)
    if pad and bits:
        ret.append((acc << (to - bits)) & maxv)
    return ret


def bech32_encode_segwit(hrp: str, witver: int, program: bytes) -> str:
    data = [witver] + _convertbits(program, 8, 5)
    const = 1  # Bech32 (v0); v1+/Taproot memakai Bech32m (0x2bc830a3)
    pm = _polymod(_hrp_expand(hrp) + data + [0] * 6) ^ const
    checksum = [(pm >> 5 * (5 - i)) & 31 for i in range(6)]
    return hrp + "1" + "".join(CHARSET[d] for d in data + checksum)


def bech32_decode_segwit(addr: str):
    """Mengembalikan (hrp, witver, program) untuk alamat witness v0, atau melempar ValueError."""
    addr = addr.lower()
    pos = addr.rfind("1")
    hrp, rest = addr[:pos], addr[pos + 1:]
    data = [CHARSET.index(c) for c in rest]
    if _polymod(_hrp_expand(hrp) + data) != 1:
        raise ValueError("checksum Bech32 salah")
    prog = bytes(_convertbits(data[1:-6], 5, 8, pad=False))
    return hrp, data[0], prog


def p2wpkh_address_testnet(pubkey: bytes) -> str:
    if len(pubkey) != 33:
        raise ValueError("P2WPKH wajib memakai kunci publik terkompresi")
    return bech32_encode_segwit(TESTNET_HRP, 0, hash160(pubkey))


# ---- ECDSA (nonce deterministik RFC 6979) ----
def _rfc6979_k(priv: int, h: bytes) -> int:
    x = priv.to_bytes(32, "big")
    h1 = (int.from_bytes(h, "big") % N).to_bytes(32, "big")
    v, k = b"\x01" * 32, b"\x00" * 32
    k = hmac.new(k, v + b"\x00" + x + h1, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    k = hmac.new(k, v + b"\x01" + x + h1, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    while True:
        v = hmac.new(k, v, hashlib.sha256).digest()
        cand = int.from_bytes(v, "big")
        if 1 <= cand < N:
            return cand
        k = hmac.new(k, v + b"\x00", hashlib.sha256).digest()
        v = hmac.new(k, v, hashlib.sha256).digest()


def sign_hash(priv: int, h: bytes):
    """Tanda tangan (r, s) atas hash 32 byte, dengan low-S (aturan standar Bitcoin)."""
    z = int.from_bytes(h, "big")
    k = _rfc6979_k(priv, h)
    r = point_mul(k)[0] % N
    s = pow(k, -1, N) * (z + r * priv) % N
    if s > N // 2:
        s = N - s
    return r, s


def _parse_pubkey(pub: bytes):
    if len(pub) == 33 and pub[0] in (2, 3):
        x = int.from_bytes(pub[1:], "big")
        y2 = (pow(x, 3, P) + 7) % P
        y = pow(y2, (P + 1) // 4, P)
        if y * y % P != y2:
            raise ValueError("titik tidak ada di kurva")
        if (y & 1) != (pub[0] & 1):
            y = P - y
        return x, y
    if len(pub) == 65 and pub[0] == 4:
        x, y = int.from_bytes(pub[1:33], "big"), int.from_bytes(pub[33:], "big")
        if (y * y - x ** 3 - 7) % P:
            raise ValueError("titik tidak ada di kurva")
        return x, y
    raise ValueError("format kunci publik tidak dikenal")


def verify_hash(pubkey: bytes, h: bytes, sig) -> bool:
    r, s = sig
    if not (1 <= r < N and 1 <= s < N):
        return False
    try:
        pt = _parse_pubkey(pubkey)
    except ValueError:
        return False
    z = int.from_bytes(h, "big")
    w = pow(s, -1, N)
    pt2 = point_add(point_mul(z * w % N), point_mul(r * w % N, pt))
    return pt2 is not None and pt2[0] % N == r


def der_encode(sig) -> bytes:
    def enc(i):
        b = i.to_bytes((i.bit_length() + 7) // 8 or 1, "big")
        return (b"\x00" + b) if b[0] & 0x80 else b

    r, s = enc(sig[0]), enc(sig[1])
    body = b"\x02" + bytes([len(r)]) + r + b"\x02" + bytes([len(s)]) + s
    return b"\x30" + bytes([len(body)]) + body


def der_decode(der: bytes):
    if der[0] != 0x30 or der[1] != len(der) - 2 or der[2] != 2:
        raise ValueError("DER tidak valid")
    lr = der[3]
    r = int.from_bytes(der[4:4 + lr], "big")
    ls = der[5 + lr]
    s = int.from_bytes(der[6 + lr:6 + lr + ls], "big")
    return r, s


def sign_message(priv: int, message: str) -> bytes:
    """Tanda tangan DER atas SHA256d(pesan). (Bukan format 'signmessage' Bitcoin Core.)"""
    return der_encode(sign_hash(priv, hash256(message.encode())))


def verify_message(pubkey: bytes, message: str, der_sig: bytes) -> bool:
    try:
        return verify_hash(pubkey, hash256(message.encode()), der_decode(der_sig))
    except (ValueError, IndexError):
        return False


if __name__ == "__main__":
    print("CONTOH TESTNET SAJA - jangan dipakai untuk dana nyata\n")
    priv = generate_private_key()
    pub = public_key_bytes(priv)
    print("WIF testnet :", to_wif_testnet(priv))
    print("Pub (33 B)  :", pub.hex())
    print("P2PKH       :", p2pkh_address_testnet(pub))
    print("P2WPKH      :", p2wpkh_address_testnet(pub))
    sig = sign_message(priv, "halo bitcoin lab")
    print("Tanda tangan:", sig.hex())
    print("Verifikasi  :", verify_message(pub, "halo bitcoin lab", sig))
