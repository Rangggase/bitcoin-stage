# CATATAN (hal yang perlu Anda cek / keputusan konservatif)

1. **Tahap 1**: file `stage1-blok\blockchain.py` yang disebut "sudah ada" tidak ditemukan di folder (kosong), jadi saya membuatnya ulang dengan fitur yang sama + `print_chain()` + tes.
2. **Jaringan**: dari lingkungan otomatis saya, akses ke mempool.space timeout. Tahap 3 diuji dengan mock saja. Anda perlu menjalankan `python stage3-pemantau\explorer.py <alamat>` dan `app.py` sendiri.
3. **Git**: repo lokal dibuat di `bitcoin-lab`. Author commit diset sementara `lab <lab@example.invalid>` (tanpa mengubah konfigurasi global). Tidak ada push.
