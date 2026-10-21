#!/usr/bin/env python3
"""SALT OKUMA (Etsy'ye yazma YOK): tum aktif ilanlarin baslik, etiket, aciklama ve bolumu (Serdar 22 Eki, burc gift taramasi).
GET /shops/{shop}/listings?state=active (100'luk sayfalar) + GET /shops/{shop}/sections. Kota tabani 10 (CLAUDE.md).
Cikti: <out>/AKTIF_METIN.json [{listing_id, bolum, title, tags, description}], <out>/OZET.json. Sir/kimlik yazilmaz.
Kullanim: aktif_metin_oku.py --out OUT"""
import argparse
import html
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

KOTA_TABAN = 10


def kota(api):
    if api.remaining is not None and int(api.remaining) < KOTA_TABAN:
        raise SystemExit(f"DUR: kota {api.remaining} < {KOTA_TABAN}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="_out")
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api, shop = Etsy(store), os.environ["ETSY_SHOP_ID"]
    bolum = {x.get("shop_section_id"): x.get("title") for x in (api.get(f"/shops/{shop}/sections") or {}).get("results") or []}
    kota(api)
    ilanlar, ofs, toplam = [], 0, None
    while True:
        d = api.get(f"/shops/{shop}/listings", params={"state": "active", "limit": 100, "offset": ofs}) or {}
        kota(api)
        toplam = d.get("count", toplam)
        r = d.get("results") or []
        for x in r:
            ilanlar.append({"listing_id": x.get("listing_id"), "bolum": bolum.get(x.get("shop_section_id"), ""),
                            "title": html.unescape(x.get("title") or ""), "tags": x.get("tags") or [],
                            "description": html.unescape(x.get("description") or "").replace("\r\n", "\n")})
        ofs += len(r)
        if not r or ofs >= (toplam or 0):
            break
    (out / "AKTIF_METIN.json").write_text(json.dumps(ilanlar, ensure_ascii=False, indent=1), encoding="utf-8")
    say = {}
    for x in ilanlar:
        say[x["bolum"]] = say.get(x["bolum"], 0) + 1
    oz = {"etsy_count": toplam, "okunan": len(ilanlar), "tekil": len({x["listing_id"] for x in ilanlar}), "bolum": say,
          "istek": api.calls, "kota_kalan": api.remaining}
    (out / "OZET.json").write_text(json.dumps(oz, ensure_ascii=False, indent=1), encoding="utf-8")
    print("OZET", json.dumps(oz, ensure_ascii=False))
    if oz["okunan"] != toplam or oz["tekil"] != oz["okunan"]:
        raise SystemExit("DUR: okunan sayi Etsy count ile ayni degil ya da tekrar var")


if __name__ == "__main__":
    main()
