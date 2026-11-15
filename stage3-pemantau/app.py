"""Tahap 3: aplikasi web lokal (Flask) untuk memantau alamat testnet.

Jalankan: python app.py  -> buka http://127.0.0.1:5000  (hanya localhost)
"""
import os
import sys

from flask import Flask, render_template_string, request

sys.path.insert(0, os.path.dirname(__file__))
from explorer import EXPLORERS, Explorer, ExplorerError, InvalidAddress  # noqa: E402

PAGE = """<!doctype html><html lang="id"><meta charset="utf-8"><title>Bitcoin Lab - Pemantau Testnet</title>
<style>body{font-family:system-ui;max-width:860px;margin:2rem auto;padding:0 1rem}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:4px 8px;text-align:left;font-size:.9rem}
.err{color:#b00}code{word-break:break-all}small{color:#555}</style>
<h1>Pemantau Alamat Testnet</h1>
<p><small>Hanya TESTNET. Bukan saran keuangan.</small></p>
<form method="get"><input name="address" size="50" value="{{ address }}" placeholder="tb1... / m... / n...">
<select name="source">{% for k in sources %}<option {{ 'selected' if k==src }}>{{ k }}</option>{% endfor %}</select>
<button>Cari</button></form>
{% if error %}<p class="err">{{ error }}</p>{% endif %}
{% if s %}
<h2>Saldo: {{ s.balance }} sat ({{ '%.8f'|format(s.balance/1e8) }} tBTC)</h2>
<p><small>Terkonfirmasi: {{ s.balance_confirmed }} sat &middot; tinggi blok: {{ s.tip }} &middot; sumber: {{ s.source }}</small></p>
<h3>UTXO ({{ s.utxos|length }})</h3>
<table><tr><th>txid:vout</th><th>nilai (sat)</th><th>konfirmasi</th></tr>
{% for u in s.utxos %}<tr><td><code>{{ u.txid }}:{{ u.vout }}</code></td><td>{{ u.value }}</td><td>{{ u.confirmations }}</td></tr>{% endfor %}</table>
<h3>Riwayat ({{ s.history|length }})</h3>
<table><tr><th>txid</th><th>perubahan (sat)</th><th>konfirmasi</th></tr>
{% for t in s.history %}<tr><td><code>{{ t.txid }}</code></td><td>{{ '%+d'|format(t.net) }}</td><td>{{ t.confirmations }}</td></tr>{% endfor %}</table>
{% endif %}</html>"""


def create_app(explorer_factory=None):
    app = Flask(__name__)
    explorers = {}

    def get_explorer(name):
        if explorer_factory:
            return explorer_factory(name)
        if name not in explorers:  # satu instance per sumber -> cache dipakai bersama
            explorers[name] = Explorer(EXPLORERS[name])
        return explorers[name]

    @app.get("/")
    def index():
        address = request.args.get("address", "").strip()
        source = request.args.get("source", "mempool")
        if source not in EXPLORERS:
            source = "mempool"
        s = error = None
        status = 200
        if address:
            try:
                s = get_explorer(source).summary(address)
            except InvalidAddress as e:
                error, status = str(e), 400
            except ExplorerError as e:
                error, status = f"Explorer bermasalah: {e}", 502
        return render_template_string(PAGE, address=address, src=source, sources=list(EXPLORERS),
                                      s=s, error=error), status

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=False)
