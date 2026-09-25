#!/usr/bin/env python3
"""Prodigi iptal ucu + 'actions' alani DOGRULAMA (SALT OKUMA). Siparis iptal EDILMEZ, POST yok.
1) Resmi API dokumani (prodigi.com/print-api/docs/reference) indirilir; cancel / actions bolumleri alintilanir.
2) Tamamlanmis bir kanal siparisinde GET /orders/{id} (ust alanlar, 'actions' var mi) ve GET /orders/{id}/actions.
Cikti: <out>/PRODIGI_IPTAL_DOK.md"""
import html, json, re, sys
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etsy"))
import order_router as R

out = Path(sys.argv[1] if len(sys.argv) > 1 else "_out/dok"); out.mkdir(parents=True, exist_ok=True)
OID = sys.argv[2] if len(sys.argv) > 2 else "ord_72470448809534464"      # Complete kanal siparisi
md = ["# Prodigi iptal ucu dogrulamasi (salt okuma)", ""]
r = requests.get("https://www.prodigi.com/print-api/docs/reference/", timeout=60)
md.append(f"## 1. Dokuman: https://www.prodigi.com/print-api/docs/reference/ (HTTP {r.status_code}, {len(r.text)} bayt)")
metin = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", r.text)))
metin = re.sub(r"[ \t\r\f\v]+", " ", metin)
metin = re.sub(r"\n\s*\n+", "\n", metin)
for anahtar in (r"/actions/cancel", r"isAvailable", r"Get actions", r"Cancel an order", r"CancelOrder|cancel order", r"salesChannel"):
    bulunan = [m.start() for m in re.finditer(anahtar, metin, re.I)]
    md += ["", f"### '{anahtar}': {len(bulunan)} yer"]
    for b in bulunan[:4]:
        md += ["```", metin[max(0, b - 500): b + 900].strip(), "```"]
p = R.Prodigi(R.load_prodigi_key("live"), "live")
st, d = p.get_order(OID)
o = d.get("order") or {}
md += ["", f"## 2. GET /orders/{OID} -> HTTP {st}", f"- order ust alanlari: {sorted(o.keys())}",
       f"- 'actions' alani siparis govdesinde var mi: {'actions' in o} -> {json.dumps(o.get('actions'))[:300]}",
       f"- status.stage: {(o.get('status') or {}).get('stage')}"]
st2, d2 = p.call("GET", f"/orders/{OID}/actions")
md += ["", f"## 3. GET /orders/{OID}/actions -> HTTP {st2}", "```json", json.dumps(d2, indent=1)[:2000], "```"]
(out / "PRODIGI_IPTAL_DOK.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(md)[:6000])
