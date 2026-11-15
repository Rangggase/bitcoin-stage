# Tahap 6 — Node sendiri (Bitcoin Core regtest) dan indeks data

## Konsep kunci
- **Full node**: mengunduh dan *memvalidasi sendiri* semua blok/transaksi (tanda tangan, aturan konsensus, double-spend) — tidak percaya pada explorer. **regtest** = chain pribadi lokal: Anda menambang blok sesuai kemauan (difficulty minimum), cocok untuk eksperimen.
- **JSON-RPC**: Bitcoin Core membuka HTTP di `127.0.0.1:18443` (regtest); autentikasi HTTP Basic (`rpcuser`/`rpcpassword`). Jangan pernah membuka `rpcbind` ke jaringan publik.
- **Header blok (80 byte)**: `version` (4), `previousblockhash` (32), `merkleroot` (32), `time` (4), `bits` (4, target difficulty terkompresi), `nonce` (4). **Hash blok = SHA256d(header)** — persis ide tahap 1, hanya format biner & double-SHA. Hash blok *tidak disimpan* di header; dihitung ulang.
- **Merkle root**: pohon hash txid (dipasangkan, level ganjil menduplikasi elemen terakhir). Mengubah satu transaksi mengubah merkle root → mengubah hash blok. Memungkinkan bukti "tx ada di blok" ringkas (SPV).
- **Indexing**: node hanya menyimpan data dalam format yang efisien untuk validasi; kueri seperti "blok mana berisi tx X" butuh indeks sendiri (di sini SQLite; `txindex=1` untuk `getrawtransaction` bebas blok).

## Isi folder
- `indexer.py` — klien RPC (stdlib), `parse_block` (menghitung ulang hash & merkle root dan membandingkan dengan node), `sync`, `verify_against_node`. **Menolak chain `main`.**
- `bitcoin.conf.contoh` — konfigurasi regtest.
- `tests/` — 9 tes dengan node tiruan; termasuk hash blok genesis regtest yang dihitung sendiri.

## Memasang & menjalankan node (Windows, langkah untuk ANDA)
Saya tidak memasang perangkat lunak global. Lakukan sendiri:
1. Unduh **Bitcoin Core resmi untuk Windows** dari https://bitcoincore.org/en/download/ dan **verifikasi checksum/tanda tangan** sesuai petunjuk di sana. Pasang (mis. `C:\Program Files\Bitcoin`). Cek versi terbaru di situs resmi.
2. Buat folder data dan konfigurasi:
```powershell
mkdir $env:APPDATA\Bitcoin -Force
Copy-Item D:\new` another` projecte\bitcoin-lab\stage6-node\bitcoin.conf.contoh $env:APPDATA\Bitcoin\bitcoin.conf
notepad $env:APPDATA\Bitcoin\bitcoin.conf     # ganti rpcpassword dengan teks acak panjang
```
3. Jalankan node (jendela PowerShell terpisah) dan buat blok:
```powershell
$bin = "C:\Program Files\Bitcoin\daemon"
& "$bin\bitcoind.exe" -regtest -daemon
& "$bin\bitcoin-cli.exe" -regtest createwallet lab
$addr = & "$bin\bitcoin-cli.exe" -regtest -rpcwallet=lab getnewaddress
& "$bin\bitcoin-cli.exe" -regtest generatetoaddress 101 $addr     # 101: coinbase baru bisa dibelanjakan setelah 100 blok
& "$bin\bitcoin-cli.exe" -regtest getblockchaininfo
```
(Biasanya `bitcoin-cli.exe` ada di `...\Bitcoin\bin` pada paket installer; sesuaikan path.)
4. Indeks dan bandingkan:
```powershell
cd D:\new another projecte\bitcoin-lab\stage6-node
..\.venv\Scripts\Activate.ps1
$env:BTC_RPC_PASSWORD = "password-yang-sama-dengan-bitcoin.conf"
python indexer.py
& "$bin\bitcoin-cli.exe" -regtest generatetoaddress 3 $addr; python indexer.py     # tambah blok, indeks ikut
& "$bin\bitcoin-cli.exe" -regtest stop
```
(Pada WSL2/Linux, perintah sama dengan `bitcoind -regtest`.) `bitcoin.conf` ada di `.gitignore`, jadi password tidak ikut ter-commit.

## Latihan (Anda kerjakan)
Bandingkan `bitcoin-cli -regtest getblock <hash> 1` dengan blok tahap 1: field mana yang sama konsepnya (previous hash, nonce, timestamp, hash), mana yang baru (merkleroot, bits, version, ukuran/weight, banyak tx), dan mengapa Bitcoin hanya mengikat *header* ke PoW sedangkan data transaksi diikat lewat merkle root. Tambahan: jelaskan fungsi `bits` terhadap target (`0x207fffff` = hampir semua hash lolos → regtest cepat).

## Keputusan teknis & catatan
- Bitcoin Core **belum terpasang** di mesin ini, jadi `generatetoaddress` nyata & pencocokan dengan node asli **belum dijalankan**; logika diverifikasi dengan node tiruan yang memakai hash kriptografis sungguhan + vektor genesis regtest. Mohon jalankan langkah di atas dan laporkan jika RPC berbeda.
- Autentikasi RPC memakai user/password (sederhana untuk regtest). Untuk penggunaan lebih serius, pakai `rpcauth` atau cookie file (`.cookie` di datadir).
- Reorg ditangani sederhana (bandingkan hash per tinggi); cukup untuk regtest.

## Definition of done
9 tes lulus; setelah Anda menjalankan node, `python indexer.py` harus mencetak `Ketidakcocokan: tidak ada`, dan Anda bisa menjelaskan tiap field header.
