# Tahap 1 — Blok, hash, dan Proof of Work

## Tujuan
Memahami bagaimana blok saling terkait lewat hash dan mengapa mengubah data lama membuat rantai tidak valid.

## Konsep kunci
- **SHA-256**: deterministik (input sama → hash sama), satu arah (tak bisa dibalik), dan sensitif (ubah 1 karakter → hash berubah total, *avalanche effect*).
- **Blok**: `index, timestamp, data, previous_hash, nonce, hash`. Hash dihitung dari semua field lain.
- **Proof of Work**: cari `nonce` sampai hash diawali N nol (difficulty). Tidak ada jalan pintas — hanya coba-coba, tapi verifikasinya hanya 1 kali hash.
- **Validasi**: (1) hash cocok dengan isi, (2) memenuhi difficulty, (3) `previous_hash` = hash blok sebelumnya.
- **Anti-pemalsuan**: mengubah blok k mengubah hash-nya → `previous_hash` blok k+1 tak cocok → penyerang harus menambang ulang blok k dan *semua* blok sesudahnya, lebih cepat dari jaringan jujur.

## Cara menjalankan (PowerShell)
```powershell
cd D:\new another projecte\bitcoin-lab
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # jika diblokir: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned (Anda yang menjalankan)
pip install -r requirements.txt
cd stage1-blok
python blockchain.py          # difficulty 4
python blockchain.py 5        # difficulty lain
pytest -q
```

## Membaca output
Tiap baris "Blok N ditambang" menampilkan nonce yang ditemukan, awal hash (diawali nol sesuai difficulty), dan waktu. Tabel menunjukkan rantai; kolom *Prev hash* blok k selalu sama dengan *Hash* blok k-1. Baris terakhir membuktikan `is_valid()` berubah menjadi `False` setelah data blok 1 diubah.

## Hasil eksperimen difficulty (mesin pengembang, 1 blok, angka bervariasi karena acak)
| Difficulty | Nonce rata-rata teoretis | Waktu terukur |
|---|---|---|
| 4 | 16^4 = 65.536 | ~0,5–0,7 dtk |
| 5 | 16^5 ≈ 1,05 juta | ~3–33 dtk |
| 6 | 16^6 ≈ 16,8 juta | ~70–124 dtk |

**Mengapa eksponensial?** Tiap digit hex menambah syarat 1 dari 16 kemungkinan; peluang sukses per percobaan = 16^-d, jadi rata-rata percobaan = 16^d. Menambah 1 nol = ×16 kerja. Waktu per blok bervariasi besar (distribusi geometrik), jadi ukur beberapa kali dan ambil rata-rata. *Latihan Anda:* jalankan di mesin Anda dan isi tabel sendiri.

## Keputusan teknis
- `timestamp` blok genesis di-set 0 agar deterministik.
- JSON dengan `sort_keys=True` agar serialisasi stabil (hash tidak bergantung urutan key).
- Tes memakai difficulty 2 agar cepat.

## Definition of done
`pytest` lulus (6 tes) dan Anda dapat menjelaskan dengan kata sendiri mengapa rantai tidak bisa diubah diam-diam.
