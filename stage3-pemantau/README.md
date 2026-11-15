# Tahap 3 — Pemantau saldo dan transaksi (TESTNET)

## Konsep kunci
- **UTXO vs akun**: Bitcoin tidak punya "saldo" di database. Yang ada adalah kumpulan *output yang belum dibelanjakan* (UTXO), mirip uang kertas/koin: satu UTXO dibelanjakan **utuh**, sisanya kembali sebagai output *change*. Alasannya: tiap UTXO bisa divalidasi independen (paralel), mencegah *replay*, dan lebih privat (alamat baru per change). **Saldo = jumlah nilai semua UTXO milik alamat/dompet.**
- **Konfirmasi**: transaksi di mempool = 0 konfirmasi. Setelah masuk blok = 1; tiap blok baru menambah 1. Rumus: `tip_height - block_height + 1`. Makin dalam, makin sulit dibatalkan (reorg).
- **Perubahan bersih per transaksi** (riwayat): `output ke alamat − input dari alamat`.
- **API Esplora** (mempool.space & Blockstream): `/address/{a}/utxo`, `/address/{a}/txs`, `/blocks/tip/height`. Data eksternal = *tidak tepercaya*: alamat divalidasi ketat (regex, hanya testnet — mainnet ditolak) sebelum masuk ke URL; respons dibaca lewat `json.loads`, bukan `eval`.
- **Ketahanan**: timeout 10 dtk, retry dengan backoff eksponensial untuk 429/5xx (menghormati `Retry-After`), cache TTL 30 dtk agar tidak membebani API (rate limit).

## Struktur
- `explorer.py` — klien API, validasi alamat, `TTLCache`, `Explorer.summary()`, `compare_explorers()`.
- `app.py` — Flask di `http://127.0.0.1:5000` (hanya localhost).
- `tests/` — 11 tes dengan data tiruan; tidak butuh internet.

## Cara menjalankan
```powershell
cd D:\new another projecte\bitcoin-lab
.\.venv\Scripts\Activate.ps1
pytest stage3-pemantau -q
python stage3-pemantau\app.py        # lalu buka http://127.0.0.1:5000
python stage3-pemantau\explorer.py mrCDrCybB6J1vRfbwM5hemdJz73FwDBC8r   # latihan bandingkan 2 explorer
```

## Latihan (Anda kerjakan)
Jalankan perintah terakhir untuk beberapa alamat testnet. Bandingkan saldo, jumlah UTXO, dan tinggi blok antar-explorer. Perbedaan kecil lazim: node berbeda belum sinkron (tip beda 1 blok), mempool berbeda (transaksi 0-konfirmasi), atau API memotong riwayat (Esplora hanya menampilkan 25 transaksi pertama per halaman — `/txs/chain/{last_txid}` untuk halaman berikut).

## Keputusan teknis & catatan
- Pakai `urllib` (stdlib) bukan `requests`; Flask dipakai hanya untuk web (butuh server + templating).
- Lingkungan pengembangan otomatis saya tidak bisa menjangkau internet (timeout), jadi pemanggilan API **asli belum diuji** — hanya lewat mock. Mohon Anda jalankan latihan di atas dan laporkan bila ada beda format respons (lihat `CATATAN.md`).
- Riwayat dibatasi halaman pertama (25 tx).

## Definition of done
11 tes lulus; aplikasi lokal menampilkan saldo, UTXO, riwayat (**perlu Anda cek dengan internet**).
