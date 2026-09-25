#!/usr/bin/env python3
"""Tek Prodigi siparisini SALT OKUMA ile bul (GOREV 0005): GET /orders/{id} + GET /orders?top=N listesinde
merchantReference / id eslesmesi. POST/iptal YOK. Alici (ad/adres/e-posta) YAZILMAZ; yalniz id, referans,
tarih, durum, issues kodlari, branding alan adlari, ucret toplamlari.
Kullanim: prodigi_siparis_oku.py <order_id> <merchantReference> [top]"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def ozet(o):
    st = o.get("status") or {}
    br = o.get("branding") or {}
    return {"id": o.get("id"), "merchantReference": o.get("merchantReference"), "created": o.get("created"),
            "lastUpdated": o.get("lastUpdated"), "stage": st.get("stage"), "details": st.get("details"),
            "issues": [f"{i.get('errorCode')}:{str(i.get('description') or '')[:160]}" for i in st.get("issues") or []],
            "branding_alanlari": {k: sorted((v or {}).keys()) if isinstance(v, dict) else type(v).__name__ for k, v in br.items()},
            "iptal_edilebilir": ((o.get("actions") or {}).get("cancel") or {}).get("isAvailable"),
            "charges": [{"toplam": (c.get("totalCost") or {}).get("amount"), "para": (c.get("totalCost") or {}).get("currency"),
                         "fatura_no_var": bool(c.get("prodigiInvoiceNumber"))} for c in o.get("charges") or []],
            "kalem": [{"sku": i.get("sku"), "status": i.get("status")} for i in o.get("items") or []]}


def main():
    from prodigi_pilot_quote import Api, load_key
    oid, ref = sys.argv[1], sys.argv[2]
    top = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    api = Api(load_key())
    r = api._call("GET", f"/orders/{oid}")
    try:
        d = r.json()
    except ValueError:
        d = {}
    print(f"GET /orders/{oid}: HTTP {r.status_code} outcome={d.get('outcome')} traceParent={d.get('traceParent', '')}", flush=True)
    if (d or {}).get("order"):
        print("  " + json.dumps(ozet(d["order"]), ensure_ascii=False), flush=True)
    r = api._call("GET", f"/orders?top={top}")
    L = (r.json() or {}).get("orders") or [] if r.status_code == 200 else []
    print(f"GET /orders?top={top}: HTTP {r.status_code}, {len(L)} siparis", flush=True)
    for o in L:
        eslesme = o.get("id") == oid or o.get("merchantReference") == ref
        print(f"  {'>>' if eslesme else '  '} {o.get('id')} | ref {'(test)' if str(o.get('merchantReference','')).startswith('guvenli-test') else '-'} "
              f"| {str(o.get('created') or '')[:19]} | {(o.get('status') or {}).get('stage')}", flush=True)
        if eslesme:
            print("     " + json.dumps(ozet(o), ensure_ascii=False), flush=True)
    for q in (f"/orders?merchantReference={ref}", f"/orders?top=10&merchantReference={ref}"):
        r = api._call("GET", q)
        try:
            n = len((r.json() or {}).get("orders") or [])
        except ValueError:
            n = "?"
        print(f"GET {q.split('?')[0]}?merchantReference=<ref>: HTTP {r.status_code}, {n} siparis", flush=True)


if __name__ == "__main__":
    main()
