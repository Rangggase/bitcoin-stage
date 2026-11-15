# CATATAN (hal yang perlu Anda cek / keputusan konservatif)

1. **Tahap 1**: `stage1-blok\blockchain.py` yang disebut "sudah ada" tidak ditemukan (folder kosong), jadi saya membuatnya ulang dengan fitur sama + `print_chain()` + tes. Waktu mining di README adalah ukuran mesin pengembang; jalankan sendiri untuk difficulty 4/5/6.
2. **Jaringan**: dari lingkungan pengembangan, explorer testnet (mempool.space, blockstream.info) tidak bisa dijangkau (timeout/ditolak), sedangkan GitHub bisa. Tahap 3 dan jalur data nyata tahap 5 hanya diuji dengan mock/data contoh. Anda perlu menjalankan `python stage3-pemantau\explorer.py <alamat>` dan `analisis.py` tanpa `--synthetic`. Pastikan explorer yang dipakai masih melayani jaringan testnet yang Anda tuju (testnet3 vs testnet4 — cek dokumentasi resmi; ganti URL di `EXPLORERS`).
3. **Bitcoin Core tidak terpasang** dan pemasangan global tidak saya lakukan. Tahap 6 diuji dengan node tiruan (hash kriptografis nyata + vektor genesis regtest). Langkah pemasangan/menjalankan ada di `stage6-node\README.md`; Anda yang mengerjakan.
4. **Tahap 4**: transaksi tidak disiarkan. Untuk definition of done (terkonfirmasi) Anda harus mengambil coin faucet testnet, membuat tx dengan `buat_tx.py`, dan menyiarkan sendiri.
5. **Git**: repo lokal di `bitcoin-lab`; author commit diset per-perintah (`lab <lab@example.invalid>`), tanpa mengubah konfigurasi global. Tidak ada push/remote. Pertimbangkan `git config user.name/email` Anda sendiri.
6. **Wordlist BIP39** (`stage7-lanjutan\bip39_english.txt`) diambil dari paket `mnemonic` (hanya sebagai sumber data, diunduh ke folder sementara) dan checksum-nya cocok dengan daftar resmi BIP39 yang diuji di tes.
7. Eksekusi nyata Lightning (opsional) dan Taproot hanya dijelaskan, tidak diimplementasi.
8. `.gitignore` mengabaikan `*.csv`; ubah bila Anda ingin meng-commit data contoh.
