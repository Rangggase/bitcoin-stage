# Bitcoin Lab

Project belajar Bitcoin bertahap (Python, Windows/PowerShell). **Hanya testnet/regtest** — tidak pernah mainnet, tidak ada dana nyata. Analisis harga di tahap 5 adalah latihan teknis, **bukan saran keuangan**.

## Peta tahap
| Tahap | Folder | Isi | Tes |
|---|---|---|---|
| 1 | `stage1-blok` | Blok, SHA-256, proof of work, validasi rantai | 6 |
| 2 | `stage2-kunci` | secp256k1 manual, WIF, P2PKH/P2WPKH testnet, ECDSA | 15 |
| 3 | `stage3-pemantau` | Klien explorer testnet, UTXO/saldo, web Flask lokal | 11 |
| 4 | `stage4-transaksi` | Raw tx P2WPKH, fee, change, BIP143 (tanpa broadcast) | 12 |
| 5 | `stage5-analisis` | Data harga → SQLite, log return, volatilitas, grafik | 10 |
| 6 | `stage6-node` | RPC Bitcoin Core regtest, parser blok, indeks SQLite | 9 |
| 7 | `stage7-lanjutan` | BIP39/32/84 dan multisig P2WSH 2-of-3 (+ Taproot/Lightning konsep) | 14 |

Baca README tiap folder (konsep + latihan). Ringkasan akhir: `RINGKASAN.md`. Hal yang perlu Anda cek: `CATATAN.md`.

## Menjalankan (PowerShell)
```powershell
cd "D:\new another projecte\bitcoin-lab"
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # bila diblokir: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned (Anda yang menjalankan)
pip install -r requirements.txt
pytest -q                        # semua tes (tanpa internet)
python stage1-blok\blockchain.py
python stage2-kunci\keys.py
python stage3-pemantau\app.py    # http://127.0.0.1:5000
python stage4-transaksi\buat_tx.py demo
python stage5-analisis\analisis.py --synthetic
python stage7-lanjutan\hd.py
```

## Catatan keamanan
- **PERINGATAN:** kode kriptografi di repo ini ditulis untuk belajar (tidak konstan-waktu, tidak diaudit). **Jangan dipakai untuk mengamankan dana nyata.**
- Kunci/mnemonic dalam contoh adalah **contoh testnet**; jangan dipakai untuk dana nyata. Kunci milik Anda (testnet) simpan di `secrets\` (di-.gitignore).
- Kode kriptografi di sini untuk belajar, bukan produksi (tidak konstan-waktu).
- Transaksi tidak pernah disiarkan oleh kode ini; Anda yang menyiarkan ke testnet setelah memeriksa hex.
- `bitcoin.conf`, `*.sqlite`, `data\`, `secrets\`, `.env` diabaikan Git. Periksa `git status` sebelum push apa pun ke GitHub.
