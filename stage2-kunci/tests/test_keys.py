import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import keys  # noqa: E402

FIXED = 1  # CONTOH TESTNET: kunci privat tetap & publik diketahui semua orang


def test_pubkey_deterministik():
    assert keys.public_key_bytes(FIXED) == keys.public_key_bytes(FIXED)


def test_kunci_1_adalah_titik_G():
    assert keys.public_key_point(1) == keys.G


def test_G_ada_di_kurva():
    x, y = keys.G
    assert (y * y - x ** 3 - 7) % keys.P == 0


def test_urutan_G_adalah_N():
    assert keys.point_mul(keys.N) is None


def test_kompresi_dan_non_kompresi():
    assert len(keys.public_key_bytes(FIXED, True)) == 33
    u = keys.public_key_bytes(FIXED, False)
    assert len(u) == 65 and u[0] == 4
    assert keys._parse_pubkey(keys.public_key_bytes(FIXED)) == keys._parse_pubkey(u)


def test_cocok_dengan_coincurve():
    coincurve = pytest.importorskip("coincurve")
    for _ in range(5):
        k = keys.generate_private_key()
        pk = coincurve.PrivateKey(k.to_bytes(32, "big"))
        assert keys.public_key_bytes(k) == pk.public_key.format(compressed=True)
        msg = b"x" * 32
        sig = keys.sign_hash(k, msg)
        assert coincurve.PublicKey(keys.public_key_bytes(k)).verify(keys.der_encode(sig), msg, hasher=None)


def test_alamat_p2pkh_testnet():
    for _ in range(5):
        a = keys.p2pkh_address_testnet(keys.public_key_bytes(keys.generate_private_key()))
        assert a[0] in "mn"
    assert keys.p2pkh_address_testnet(keys.public_key_bytes(FIXED)) == "mrCDrCybB6J1vRfbwM5hemdJz73FwDBC8r"


def test_alamat_p2wpkh_vektor_bip173():
    pub = bytes.fromhex("0279BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798")
    assert keys.p2wpkh_address_testnet(pub) == "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx"
    assert keys.p2wpkh_address_testnet(keys.public_key_bytes(keys.generate_private_key())).startswith("tb1")


def test_bech32_roundtrip():
    pub = keys.public_key_bytes(keys.generate_private_key())
    addr = keys.p2wpkh_address_testnet(pub)
    assert keys.bech32_decode_segwit(addr) == ("tb", 0, keys.hash160(pub))


def test_wif_roundtrip_dan_vektor():
    assert keys.to_wif_testnet(FIXED) == "cMahea7zqjxrtgAbB7LSGbcQUr1uX1ojuat9jZodMN87JcbXMTcA"
    assert keys.from_wif(keys.to_wif_testnet(FIXED)) == (FIXED, True)


def test_base58_checksum_salah_ditolak():
    s = keys.to_wif_testnet(FIXED)
    bad = s[:-1] + ("1" if s[-1] != "1" else "2")
    with pytest.raises(ValueError):
        keys.base58check_decode(bad)


def test_ripemd160_vektor_dan_fallback():
    assert keys._ripemd160_pure(b"abc").hex() == "8eb208f7e05d987a9b044a8e98c6b087f15a0bfc"
    assert keys._ripemd160_pure(b"").hex() == "9c1185a5c5e9fc54612808977ee8f548b2258d31"
    assert keys.ripemd160(b"hello") == keys._ripemd160_pure(b"hello")


def test_tanda_tangan_valid_dan_diubah():
    k = keys.generate_private_key()
    pub = keys.public_key_bytes(k)
    sig = keys.sign_message(k, "halo")
    assert keys.verify_message(pub, "halo", sig)
    assert not keys.verify_message(pub, "halo!", sig)  # pesan diubah
    rusak = bytearray(sig)
    rusak[10] ^= 1
    assert not keys.verify_message(pub, "halo", bytes(rusak))  # tanda tangan diubah
    assert not keys.verify_message(keys.public_key_bytes(keys.generate_private_key()), "halo", sig)


def test_rfc6979_deterministik():
    assert keys.sign_message(FIXED, "a") == keys.sign_message(FIXED, "a")


def test_kunci_di_luar_rentang():
    with pytest.raises(ValueError):
        keys.public_key_point(0)
    with pytest.raises(ValueError):
        keys.public_key_point(keys.N)
