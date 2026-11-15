"""CLI tahap 4. TIDAK menyiarkan transaksi; hanya mencetak raw hex untuk Anda periksa.

  python buat_tx.py demo
      Contoh dengan UTXO PALSU dan kunci contoh (aman, tanpa jaringan).
  python buat_tx.py buat --wif ..\\secrets\\testnet.wif --utxo-json utxo.json --ke ALAMAT:SAT [--ke ...] --change ALAMAT --fee-rate 2
      Memakai kunci TESTNET milik Anda dari file di folder secrets\\ (di-.gitignore).
  python buat_tx.py decode <hex>
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import tx as T  # noqa: E402

K = T.keys


def tampil(r):
    print(f"txid      : {r['txid']}\nfee       : {r['fee']} sat   change: {r['change']} sat   vsize: {r['vsize']} vB")
    print(f"raw hex   : {r['hex']}\n")
    print(json.dumps(T.decode_tx(r["hex"]), indent=2))
    print("\nBELUM disiarkan. Periksa dengan `bitcoin-cli -testnet decoderawtransaction <hex>` lalu siarkan sendiri "
          "(mis. lewat halaman 'broadcast' explorer TESTNET) bila yakin.")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo")
    b = sub.add_parser("buat")
    b.add_argument("--wif", required=True)
    b.add_argument("--utxo-json", required=True)
    b.add_argument("--ke", action="append", required=True, help="ALAMAT:SATOSHI")
    b.add_argument("--change", required=True)
    b.add_argument("--fee-rate", type=float, default=2.0)
    d = sub.add_parser("decode")
    d.add_argument("hex")
    a = p.parse_args()

    if a.cmd == "demo":
        print("DEMO: kunci contoh & UTXO palsu (bukan dana nyata)\n")
        priv = 0xC0FFEE
        mine = K.p2wpkh_address_testnet(K.public_key_bytes(priv))
        utxos = [{"txid": "11" * 32, "vout": 0, "value": 100_000}]
        outs = [(K.p2pkh_address_testnet(K.public_key_bytes(7)), 30_000),
                (K.p2wpkh_address_testnet(K.public_key_bytes(9)), 20_000)]
        tampil(T.build_signed_tx(priv, utxos, outs, mine, fee_rate=2))
    elif a.cmd == "buat":
        with open(a.wif) as f:
            priv, comp = K.from_wif(f.read().strip())  # menolak WIF non-testnet
        if not comp:
            sys.exit("Kunci harus terkompresi untuk P2WPKH.")
        with open(a.utxo_json) as f:
            utxos = json.load(f)
        outs = [(x.rsplit(":", 1)[0], int(x.rsplit(":", 1)[1])) for x in a.ke]
        tampil(T.build_signed_tx(priv, utxos, outs, a.change, a.fee_rate))
    else:
        print(json.dumps(T.decode_tx(a.hex), indent=2))


if __name__ == "__main__":
    main()
