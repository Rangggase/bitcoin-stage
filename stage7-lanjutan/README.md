# Tahap 7 — Materi lanjutan (dipilih: BIP39/BIP32/BIP84 dan multisig P2WSH 2-of-3)

> Semua TESTNET. Mnemonic `abandon … about` adalah vektor uji publik; **jangan** dipakai untuk dana. Mnemonic dari `hd.py` hanya untuk belajar.

## A. BIP39 + BIP32 + BIP84 (`hd.py`)
- **BIP39**: entropi 128–256 bit + checksum (bit awal SHA-256 entropi) dipecah per 11 bit → indeks kata dari daftar 2048 kata. 12 kata = 128 bit entropi + 4 bit checksum. Checksum menangkap salah ketik, bukan menambah keamanan. **Seed** = `PBKDF2-HMAC-SHA512(mnemonic, "mnemonic"+passphrase, 2048 iterasi)` → 64 byte. Passphrase menghasilkan dompet berbeda total ("kata ke-25").
- **BIP32**: `HMAC-SHA512("Bitcoin seed", seed)` → kunci master + chain code. Anak: `HMAC(chain, data||index)`, `anak = (IL + induk) mod N`. Indeks ≥ 2³¹ = *hardened* (pakai kunci privat induk; xpub induk tak bisa menurunkan anak hardened maupun membocorkan induk). Satu seed → pohon tak terbatas kunci.
- **BIP84**: `m / 84' / coin' / account' / change / index`; coin `1'` = semua testnet; `change` 0 = penerimaan, 1 = kembalian. Menghasilkan P2WPKH (`tb1q…`).
- Wordlist `bip39_english.txt` diambil dari repo resmi BIP (checksum SHA-256 diuji). Diverifikasi vektor BIP39 (entropi nol, 7f.., ff..), PBKDF2 "TREZOR", dan vektor 1 BIP32 resmi.

## B. Multisig P2WSH 2-of-3 (`multisig.py`)
- **witnessScript** = `OP_2 <pk1><pk2><pk3> OP_3 OP_CHECKMULTISIG`; kunci diurutkan (BIP67) agar alamat sama siapa pun yang menyusun. **Alamat** = Bech32(`tb`, v0, `SHA256(witnessScript)`) → 62 karakter (program 32 byte, vs 42 untuk P2WPKH).
- **Belanja**: witness = `[kosong, sig_A, sig_B, witnessScript]`. Item kosong wajib (bug off-by-one `OP_CHECKMULTISIG`); tanda tangan harus **berurutan sesuai urutan kunci** di script. Sighash BIP143 memakai `witnessScript` sebagai scriptCode. Tiap penanda tangan boleh menandatangani sendiri-sendiri di mesin berbeda (kunci privat tak pernah berkumpul) — di dunia nyata dikoordinasikan lewat PSBT (BIP174), yang tidak diimplementasi di sini.
- Tes: tiga kombinasi 2-dari-3 valid, 1 tanda tangan ditolak, kunci asing ditolak, perubahan output membatalkan tanda tangan, vektor alamat P2WSH testnet BIP173.

## C. Dijelaskan (tidak diimplementasi)
- **Taproot/Schnorr (BIP340/341)**: tanda tangan Schnorr 64 byte atas kunci publik 32 byte (x-only); linear sehingga kunci/tanda tangan dapat *diagregasi* (MuSig2): multisig tampak seperti satu tanda tangan biasa → privasi + hemat ruang. Alamat `tb1p…` (witness v1, Bech32m). Skrip kompleks disembunyikan dalam pohon Merkle (MAST) dan hanya cabang yang dipakai yang dibuka.
- **Lightning**: dua pihak mengunci dana di output multisig 2-of-2 (*funding*), lalu bertukar transaksi *commitment* bertanda tangan di luar rantai; saldo berubah tanpa transaksi on-chain. **HTLC** (hash time-locked contract) meneruskan pembayaran lintas hop: bayar jika penerima mengungkap *preimage* hash sebelum timeout. Lightning di atas Bitcoin karena penyelesaian sengketa (penutupan channel) selalu bisa dipaksakan on-chain. Eksekusi nyata butuh node LN (mis. LND/Core Lightning) di testnet — opsional.

## Cara menjalankan
```powershell
cd D:\new another projecte\bitcoin-lab
.\.venv\Scripts\Activate.ps1
pytest stage7-lanjutan -q
python stage7-lanjutan\hd.py
python stage7-lanjutan\multisig.py
```

## Batasan implementasi
Aritmetika kurva tidak konstan-waktu; tanpa PSBT; multisig hanya P2WSH murni (bukan P2SH-P2WSH/Taproot); hanya satu input; pendanaan alamat multisig di testnet & broadcast dilakukan manual oleh Anda. Lihat `..\RINGKASAN.md`.

## Definition of done
14 tes lulus (BIP39/32/84 + multisig). Modul menghasilkan alamat/raw tx testnet; **belum diuji di jaringan** (tidak ada broadcast oleh saya).
