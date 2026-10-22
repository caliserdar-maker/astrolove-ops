#!/usr/bin/env python3
"""Yayin oncesi trafik kaydi (14 Eki 2026; "Bizim Yilimiz" 78 ilani yayina girmeden once).
SALT OKUR: yalniz GET /v3/application/listings/batch (en fazla 100 id/istek). Ilan ve Ads ayari degismez.
Girdi: data/pod/pod78_ids.csv (listing_id, cift). Cikti: CSV (listing_id, cift, state, views, num_favorers, okuma_utc).
Not: Etsy 'views' gunde bir kez hesaplanir, anlik degildir. Anahtar/token hicbir dosyaya yazilmaz.
Kullanim: trafik_oncesi.py --ids data/pod/pod78_ids.csv --cikti _out/TRAFIK_ONCESI_20261014.csv"""
import argparse
import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", required=True)
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--beklenen", type=int, default=78)
    a = ap.parse_args()
    key, secret = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    if not key or not secret or not os.environ.get("TOKEN_FILE"):
        raise SystemExit("HATA: Etsy ortam degiskenleri eksik")
    mask(key)
    mask(secret)
    store = TokenStore(os.environ["TOKEN_FILE"], key, secret)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    girdi = list(csv.DictReader(open(a.ids, encoding="utf-8")))
    cift = {r["listing_id"].strip(): r["cift"].strip() for r in girdi}
    ids = list(cift)
    if len(ids) != a.beklenen or len(set(ids)) != len(ids):
        raise SystemExit(f"HATA: girdi {len(ids)} id (tekil {len(set(ids))}), beklenen {a.beklenen}")
    okuma = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    bulunan = {}
    for i in range(0, len(ids), 100):
        parca = ids[i:i + 100]
        yanit = api.get("/listings/batch", params={"listing_ids": ",".join(parca)}) or {}
        for l in yanit.get("results") or []:
            bulunan[str(l.get("listing_id"))] = l
    satirlar = []
    for lid in ids:
        l = bulunan.get(lid, {})
        satirlar.append({"listing_id": lid, "cift": cift[lid], "state": l.get("state", "BULUNAMADI"),
                         "views": l.get("views", ""), "num_favorers": l.get("num_favorers", ""), "okuma_utc": okuma})
    Path(a.cikti).parent.mkdir(parents=True, exist_ok=True)
    with open(a.cikti, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(satirlar[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(satirlar)
    say = lambda k: sum(int(r[k]) for r in satirlar if str(r[k]).isdigit())
    aktif_degil = [f"{r['listing_id']} {r['cift']} {r['state']}" for r in satirlar if r["state"] != "active"]
    log(f"SATIR {len(satirlar)} (bulunan {len(bulunan)}); toplam views {say('views')}; toplam num_favorers {say('num_favorers')}; "
        f"okuma {okuma}; Etsy GET cagrisi {api.calls}; kalan gunluk kota {api.remaining}")
    log(f"active OLMAYAN {len(aktif_degil)}" + "".join(f"\n  {x}" for x in aktif_degil))
    log("SONUC: " + ("PASS" if len(satirlar) == a.beklenen and len(bulunan) == a.beklenen else "FAIL") + "; Etsy yazma cagrisi 0")
    if len(bulunan) != a.beklenen:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
