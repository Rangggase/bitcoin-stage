# Tahap 4 — Transaksi (TESTNET, tanpa broadcast)

> `tx.py` **tidak punya** kode broadcast. Program hanya menghasilkan raw hex; **Anda yang menyiarkan** sendiri ke testnet setelah memeriksanya.

## Konsep kunci
- **Struktur**: `version | [marker 00, flag 01] | n_input | input… | n_output | output… | [witness…] | locktime`.
- **Input** = referensi ke output lama: `txid` (disimpan *little-endian* di byte, ditulis terbalik di explorer) + `vout` + `scriptSig` (kosong di SegWit) + `sequence` (`0xFFFFFFFD` = boleh RBF).
- **Output** = `value` (satoshi, 8 byte LE) + `scriptPubKey`. P2PKH: `76a914<hash160>88ac`. P2WPKH: `0014<hash160>`.
- **Fee** = total input − total output (tidak ditulis di transaksi!). Dihitung dari **vsize** = ceil(weight/4); byte witness dihitung 1/4 → SegWit lebih murah. Fee rate = sat/vB.
- **Sighash**: tanda tangan ECDSA atas ringkasan *seluruh transaksi* (BIP143 untuk SegWit: hash prevouts, sequences, outputs, nilai input yang dibelanjakan, dst.) dengan `SIGHASH_ALL`. Karena itu mengubah satu output (mis. jumlah) membuat tanda tangan tidak valid — penyiar tidak bisa mengalihkan dana. (Tes: `test_tanda_tangan_valid_dan_terikat_isi_tx`.)
- **Legacy vs SegWit**: legacy menaruh tanda tangan di `scriptSig` (ikut dalam txid → rentan *malleability*); SegWit menaruhnya di *witness* (di luar txid, diskon bobot).
- **Faucet**: situs/layanan yang mengirim sedikit coin testnet gratis ke alamat Anda dari dompet miliknya, karena coin testnet tidak bernilai. Cari "bitcoin testnet faucet" (testnet3/testnet4 — verifikasi jaringan mana yang dipakai explorer & faucet agar cocok). **Hanya masukkan alamat testnet Anda; jangan pernah menyerahkan kunci privat apa pun, dan jangan memakai kunci dompet utama.** Faucet tidak pernah butuh kunci Anda.

## Pemilihan UTXO & change
Greedy terbesar-dulu sampai `Σinput ≥ target + fee`. Fee diestimasi konservatif (68 vB/input P2WPKH). Jika kembalian < 294 sat (batas debu), tidak dibuat output change; sisanya menjadi fee tambahan. Dana kurang → `InsufficientFunds`.

## Cara menjalankan
```powershell
cd D:\new another projecte\bitcoin-lab
.\.venv\Scripts\Activate.ps1
pytest stage4-transaksi -q
python stage4-transaksi\buat_tx.py demo          # UTXO palsu + kunci contoh
python stage4-transaksi\buat_tx.py decode <hex>
```
Untuk dana faucet milik Anda: simpan WIF **testnet** (`c...`) di `secrets\testnet.wif` (folder ini di-.gitignore), simpan UTXO (`[{"txid","vout","value"}]`) dari tahap 3 ke `utxo.json`, lalu `buat_tx.py buat ...` (lihat docstring). Dompet harus P2WPKH (`tb1q…`) dari kunci tersebut.

## Latihan (Anda kerjakan)
Jalankan `demo`, lalu jelaskan tiap field output `decode`: version, marker/flag, input (txid, vout, sequence), dua output + change, witness (tanda tangan + kunci publik), locktime. Verifikasi dengan `bitcoin-cli -testnet decoderawtransaction` (tahap 6) atau decoder explorer. Setelah siap, siarkan transaksi testnet **Anda sendiri** dan tunggu konfirmasi.

## Keputusan teknis
- Hanya input P2WPKH (kunci terkompresi); output ke P2PKH/P2WPKH. P2TR/P2WSH ditunda ke tahap 7.
- Vektor resmi BIP143 dipakai untuk membuktikan sighash benar.
- Definition of done "disiarkan & terkonfirmasi" adalah langkah **Anda** (saya dilarang menyiarkan).

## Definition of done
12 tes lulus (fee, change, dana kurang, sighash BIP143) dan Anda dapat menjelaskan setiap field raw transaction.
