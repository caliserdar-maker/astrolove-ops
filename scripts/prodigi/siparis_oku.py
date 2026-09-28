#!/usr/bin/env python3
"""Prodigi siparis durumu, SALT OKUMA (yalniz GET; siparis/iptal/guncelleme YOK).
Verilen siparis + ayni receipt'e ait diger siparisler (yeniden basim dahil; merchantReference ya da kalem referansi
receipt'i iceren, ya da son --gun gun icinde acilan): asama, ayrinti, sorunlar, kalem SKU, asset (Drive id / host,
durum) ve kullanilabilir eylemler (GET /orders/{id}/actions). Alici/adres YAZILMAZ; receipt yalniz son 4 hane.
Kullanim: siparis_oku.py --oid ord_... --out OUT.json [--env live] [--gun 14]
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etsy"))
import order_router as R  # noqa: E402


def asset_ozet(url):
    u = urlparse(url or "")
    fid = (parse_qs(u.query).get("id") or [""])[0] or (re.findall(r"/d/([\w-]+)", u.path) or [""])[0]
    return f"drive:{fid}" if "google" in u.netloc and fid else (u.netloc or "-")


def ozet(o, eylem, rid):
    s = o.get("status") or {}
    maske = lambda t: str(t or "").replace(rid, "..." + rid[-4:]) if rid else str(t or "")
    return {"id": o.get("id"), "created": o.get("created"), "lastUpdated": o.get("lastUpdated"),
            "merchantReference": maske(o.get("merchantReference")), "stage": s.get("stage"), "details": s.get("details"),
            "issues": [{"kod": i.get("errorCode"), "aciklama": str(i.get("description") or "")[:160]} for i in s.get("issues") or []],
            "kargo": o.get("shippingMethod"),
            "kalem": [{"sku": k.get("sku"), "adet": k.get("copies"), "ref": maske(k.get("merchantReference")), "durum": k.get("status"),
                       "asset": [{"alan": a.get("printArea"), "kaynak": asset_ozet(a.get("url")), "durum": a.get("status"),
                                  "md5": a.get("md5Hash")} for a in k.get("assets") or []]} for k in o.get("items") or []],
            "sevkiyat": [{"durum": sp.get("status"), "tarih": sp.get("dispatchDate"), "tasiyici": (sp.get("carrier") or {}).get("name")}
                         for sp in o.get("shipments") or []],
            "eylemler": eylem}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oid", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--env", default="live"); ap.add_argument("--gun", type=int, default=14)
    a = ap.parse_args()
    p = R.Prodigi(R.load_prodigi_key(a.env), a.env)
    st, d = p.get_order(a.oid)
    if st != 200:
        sys.exit(f"HATA: GET /orders/{a.oid} HTTP {st}")
    ana = d.get("order") or {}
    mr = str(ana.get("merchantReference") or "")
    rid = next((x for x in re.split(r"[-_]", mr) if x.isdigit() and len(x) >= 8), "")
    sinir = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - a.gun * 86400))
    secilen = {ana.get("id"): ana}
    for o in p.siparisler(100):
        refs = [str(o.get("merchantReference") or "")] + [str(k.get("merchantReference") or "") for k in o.get("items") or []]
        if (rid and any(rid in r for r in refs)) or str(o.get("created") or "") >= sinir:
            secilen.setdefault(o.get("id"), o)
    sonuc = []
    for oid, o in secilen.items():
        st2, d2 = p.get_order(oid)
        o = d2.get("order") or o if st2 == 200 else o
        st3, d3 = p.call("GET", f"/orders/{oid}/actions")
        eylem = {k: (v or {}).get("isAvailable") for k, v in (d3 or {}).items() if isinstance(v, dict)} if st3 == 200 else f"HTTP {st3}"
        z = ozet(o, eylem, rid)
        z["receipt_eslesme"] = bool(rid) and any(rid in str(x) for x in [o.get("merchantReference")] + [k.get("merchantReference") for k in o.get("items") or []])
        sonuc.append(z)
    sonuc.sort(key=lambda z: str(z.get("created") or ""))
    Path(a.out).write_text(json.dumps({"ana": a.oid, "receipt_son4": rid[-4:], "siparisler": sonuc}, indent=1, ensure_ascii=False))
    for z in sonuc:
        print(f"{z['id']} | {z['created']} | {z['merchantReference']} | eslesme {z['receipt_eslesme']} | {z['stage']} | "
              f"{json.dumps(z['details'])} | issues {len(z['issues'])} | "
              + "; ".join(f"{k['sku']}x{k['adet']} {k['durum']} [" + ", ".join(f"{x['kaynak']} {x['durum']}" for x in k['asset']) + "]"
                          for k in z["kalem"]) + f" | eylemler {json.dumps(z['eylemler'])}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
