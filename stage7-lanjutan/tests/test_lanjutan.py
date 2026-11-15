import hashlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import hd  # noqa: E402
import multisig as M  # noqa: E402

K = hd.keys
VEC = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"  # vektor uji publik


def test_wordlist_resmi():
    # dinormalisasi ke LF agar lulus walau Git Windows mengubah akhir baris (autocrlf)
    teks = "
".join(hd.WORDLIST) + "
"
    assert hashlib.sha256(teks.encode()).hexdigest() == "2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda"


def test_bip39_vektor():
    assert hd.entropy_to_mnemonic(bytes(16)) == VEC
    assert hd.entropy_to_mnemonic(bytes.fromhex("7f" * 16)) == (
        "legal winner thank year wave sausage worth useful legal winner thank yellow")
    assert hd.entropy_to_mnemonic(bytes([0xFF] * 32)).endswith("zoo vote")


def test_bip39_validasi_checksum():
    assert hd.mnemonic_is_valid(VEC)
    assert not hd.mnemonic_is_valid(VEC.replace("about", "abandon"))  # checksum salah
    assert not hd.mnemonic_is_valid("foo " + VEC[8:])
    assert hd.mnemonic_is_valid(hd.generate_mnemonic(12)) and hd.mnemonic_is_valid(hd.generate_mnemonic(24))


def test_seed_pbkdf2_dan_passphrase():
    s = hd.mnemonic_to_seed(VEC, "TREZOR")
    assert len(s) == 64 and s.hex().startswith("c55257c360c07c72")  # vektor Trezor
    assert hd.mnemonic_to_seed(VEC) != s


def test_bip32_vektor_1():
    seed = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
    m = hd.master_from_seed(seed)
    mainnet = bytes.fromhex("0488ADE4"), bytes.fromhex("0488B21E")
    assert m.serialize_private(mainnet[0]) == ("xprv9s21ZrQH143K3QTDL4LXw2F7HEK3wJUD2nW2nRk4stbPy6cq3jPPqjiChkVvvNKm"
                                               "PGJxWUtg6LnF5kejMRNNU3TGtRBeJgk33yuGBxrMPHi")
    assert m.serialize_public(mainnet[1]) == ("xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjq"
                                              "JoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8")
    c = m.derive("m/0'")
    assert c.serialize_private(mainnet[0]) == ("xprv9uHRZZhk6KAJC1avXpDAp4MDc3sQKNxDiPvvkX8Br5ngLNv1TxvUxt4cV1rGL5hj"
                                               "6KCesnDYUhd7oWgT11eZG7XnxHrnYeSvkzY7d2bhkJ7")


def test_derivasi_hardened_dan_publik_tak_bisa_mundur():
    m = hd.master_from_seed(bytes(32))
    assert m.derive("m/0'/1").key == m.child(hd.HARDENED).child(1).key
    assert m.derive("m/1").pub != m.derive("m/0'").pub


def test_bip84_testnet_alamat():
    addr, node = hd.bip84_testnet_address(VEC)
    assert addr.startswith("tb1q") and node.depth == 5
    assert hd.bip84_testnet_address(VEC)[0] == addr  # deterministik
    assert hd.bip84_testnet_address(VEC, index=1)[0] != addr
    assert node.serialize_private().startswith("tprv")


def test_multisig_alamat_vektor_bip173_dan_urutan_kunci():
    ws_hash = bytes.fromhex("1863143c14c5166804bd19203356da136c985678cd4d27a1b8c6329604903262")
    assert K.bech32_encode_segwit("tb", 0, ws_hash) == "tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7"
    pubs = [K.public_key_bytes(k) for k in (11, 22, 33)]
    assert M.witness_script(pubs) == M.witness_script(pubs[::-1])  # BIP67: urutan input tak berpengaruh
    assert M.p2wsh_address_testnet(M.witness_script(pubs)).startswith("tb1q") and len(
        M.p2wsh_address_testnet(M.witness_script(pubs))) == 62


PRIVS = [0xA11CE, 0xB0B, 0xCA401]
PUBS = [K.public_key_bytes(k) for k in PRIVS]
WS = M.witness_script(PUBS)
UTXO = {"txid": "22" * 32, "vout": 0, "value": 100_000}
DEST = M.T.address_to_script(K.p2wpkh_address_testnet(PUBS[0]))


@pytest.mark.parametrize("pair", [(0, 1), (0, 2), (1, 2)])
def test_dua_dari_tiga_cukup(pair):
    r = M.spend(UTXO, WS, [PRIVS[i] for i in pair], DEST, 300)
    assert M.verify_multisig_witness(r["tx"], WS, 100_000)


def test_satu_tanda_tangan_tidak_cukup():
    with pytest.raises(ValueError):
        M.spend(UTXO, WS, PRIVS[:1], DEST, 300)


def test_ubah_output_membatalkan_tanda_tangan():
    r = M.spend(UTXO, WS, PRIVS[:2], DEST, 300)
    tx = r["tx"]
    tx["vout"][0]["value"] += 1  # sighash berubah -> tanda tangan lama tak berlaku
    assert not M.verify_multisig_witness(tx, WS, 100_000)


def test_kunci_asing_ditolak():
    with pytest.raises(ValueError):
        M.spend(UTXO, WS, [PRIVS[0], 999], DEST, 300)
