import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from blockchain import Blockchain  # noqa: E402

D = 2  # kecil agar tes cepat


def buat():
    bc = Blockchain(D)
    bc.add_block("a")
    bc.add_block("b")
    return bc


def test_chain_baru_valid():
    assert buat().is_valid()


def test_ubah_data_tidak_valid():
    bc = buat()
    bc.chain[1].data = "dipalsukan"
    assert not bc.is_valid()


def test_ubah_previous_hash_tidak_valid():
    bc = buat()
    bc.chain[2].previous_hash = "f" * 64
    assert not bc.is_valid()


def test_ubah_data_lalu_mining_ulang_blok_itu_saja_tetap_gagal():
    bc = buat()
    bc.chain[1].data = "dipalsukan"
    bc.chain[1].mine(D)  # hash blok 1 berubah -> previous_hash blok 2 tak cocok
    assert not bc.is_valid()


def test_hash_memenuhi_difficulty():
    assert all(b.hash.startswith("0" * D) for b in buat().chain)


def test_print_chain():
    buf = io.StringIO()
    buat().print_chain(file=buf)
    assert "Genesis" in buf.getvalue() and len(buf.getvalue().splitlines()) == 5
