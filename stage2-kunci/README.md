# Tahap 2 — Kunci privat, kunci publik, dan alamat (TESTNET)

> Semua contoh di sini adalah **contoh testnet**. Kunci privat `1` diketahui semua orang — jangan pernah dipakai untuk dana nyata. Program `keys.py` hanya menghasilkan kunci/alamat testnet (`m`/`n`, `tb1`, WIF `c...`).

## Konsep kunci
- **Kunci privat**: angka acak 256-bit di rentang `[1, N-1]`. Siapa pun yang tahu angka ini mengendalikan dana. Keacakan wajib berasal dari CSPRNG (`secrets`, bukan `random`) — kunci yang bisa ditebak = dana hilang.
- **secp256k1**: kurva `y² = x³ + 7 (mod p)`. Bitcoin memilihnya karena parameternya tanpa konstanta "misterius" (kecurigaan backdoor pada kurva NIST) dan efisien dihitung.
- **Kunci publik** = `k·G`: titik `G` ditambahkan ke dirinya `k` kali. Maju mudah, mundur (mencari `k` dari titik) = *discrete logarithm problem*, mustahil secara praktis.
- **Terkompresi (33 B)** = `02/03 + x` (prefiks menyatakan paritas y; y dihitung ulang dari persamaan kurva). **Tidak terkompresi (65 B)** = `04 + x + y`. Terkompresi lebih hemat dan wajib untuk SegWit.
- **Hash160** = `RIPEMD160(SHA256(pubkey))` → 20 byte. Alamat tidak membuka kunci publik sampai dana dibelanjakan, dan lebih pendek.
- **Encoding**: WIF (Base58Check; testnet prefiks `0xEF`, akhiran `01` bila terkompresi); P2PKH testnet = Base58Check(`0x6F` + hash160) → diawali `m`/`n`; P2WPKH = Bech32(`tb`, witness v0, hash160) → `tb1q...`.
- **P2PKH / P2WPKH / P2TR**: P2PKH = legacy; P2WPKH = SegWit v0 (fee lebih murah karena tanda tangan di witness); P2TR = Taproot (witness v1, kunci Schnorr 32 byte, Bech32m, `tb1p...`).
- **ECDSA**: tanda tangan `(r, s)` membuktikan penanda tangan tahu `k` tanpa membukanya, karena verifikasi hanya memakai kunci publik. Nonce dibuat deterministik (RFC 6979) — nonce yang dipakai ulang/bias membocorkan kunci privat. `s` dinormalisasi *low-S*.

## Keputusan teknis
- **Dipilih: implementasi manual** (mode belajar mandiri) untuk `secp256k1`, Base58Check, Bech32, RFC6979, ECDSA, dan RIPEMD160 cadangan murni Python. **`coincurve` dipakai hanya di tes** sebagai pembanding silang (binding libsecp256k1; wheel Windows tersedia, tanpa compiler). Trade-off: manual = transparan tapi lambat & tidak tahan *side-channel*; coincurve = cepat & aman, tetapi menyembunyikan matematikanya.
- **RIPEMD160**: dicek di Python 3.13.9 Windows — `hashlib` mendukungnya. Jika di mesin Anda `hashlib.new("ripemd160")` gagal (OpenSSL 3), `keys.ripemd160` otomatis memakai implementasi murni (dites dengan vektor standar).
- Pesan ditandatangani sebagai DER atas `SHA256d(pesan)` — **bukan** format `signmessage` Bitcoin Core.

## Cara menjalankan
```powershell
cd D:\new another projecte\bitcoin-lab
.\.venv\Scripts\Activate.ps1
python stage2-kunci\keys.py
pytest stage2-kunci -q
```

## Latihan (Anda kerjakan)
Kunci tetap `1` → alamat testnet `mrCDrCybB6J1vRfbwM5hemdJz73FwDBC8r` (P2PKH, terkompresi). Cari alamat itu di explorer testnet (mis. mempool.space/testnet) — **tanpa mengirim dana apa pun** — dan cocokkan. Lalu hitung alamat P2WPKH dari kunci yang sama dan jelaskan mengapa berbeda dari P2PKH padahal kunci publiknya sama.

## Definition of done
15 tes lulus (termasuk vektor BIP173, vektor WIF, perbandingan dengan coincurve) dan Anda bisa menjelaskan: kunci privat = rahasia (angka), kunci publik = titik di kurva turunan satu arah dari privat, alamat = hash kunci publik yang di-encode.
