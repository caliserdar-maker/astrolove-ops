#!/usr/bin/env python3
"""Etsy toplu okuma YOKLAMASI (Serdar 31 Eki 1a, istek azaltma madde 3-4). YALNIZ GET, EN FAZLA 3 ISTEK:
  1. GET /shops/{shop} (kota okumasi; kalan < KOTA_YOKLAMA (50, Merkez 31 Eki) ise baska istek yok, DUR)
  2. GET /listings/batch?listing_ids=..&includes=Images,Videos,Personalization,Translations (getListingsByListingIds; Merkez 31 Eki,
     Etsy dokumani: en fazla 100 ilan; Inventory / Shipping bu uctan kaldirildi)
  3. GET /listings/batch/inventory?listing_ids=.. (en fazla 100 ilan, listings_r)
Amac: yanit SEKLINI gercek veriden olcmek (ayristirici tahminle yazilmaz). Cikti --out: YOKLAMA.json (her istek: yol, parametre, durum,
ust anahtarlar, ilk sonucun anahtar agaci, ham yanit). Kullanim: toplu_oku_yokla.py --ilan 4598525642,4570143815 --out _out"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore  # noqa: E402

INCLUDES = "Images,Videos,Personalization,Translations"
KOTA_YOKLAMA = 50


def agac(x, d=0):
    """anahtar agaci (deger yok): sekil olcumu"""
    if d > 5:
        return "..."
    if isinstance(x, dict):
        return {k: agac(v, d + 1) for k, v in sorted(x.items())}
    if isinstance(x, list):
        return [agac(x[0], d + 1)] if x else []
    return type(x).__name__


def dene(api, yol, params):
    try:
        y = api.get(yol, params=params, ok404=True)
        sonuc = (y or {}).get("results") if isinstance(y, dict) else None
        return dict(yol=yol, params=params, durum="200" if y is not None else "404", ust=sorted(y) if isinstance(y, dict) else None,
                    n_sonuc=len(sonuc) if isinstance(sonuc, list) else None, ilk=agac((sonuc or [None])[0]) if sonuc else agac(y), ham=y)
    except SystemExit as e:
        return dict(yol=yol, params=params, durum="HATA", hata=str(e.code)[:400])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ilan", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    ids = [x.strip() for x in a.ilan.split(",") if x.strip()]
    if not ids or len(ids) > 5 or not all(x.isdigit() for x in ids):
        raise SystemExit("DUR: --ilan 1-5 rakam kimlik")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    api = Etsy(TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")))
    c0 = api.calls
    api.get(f"/shops/{os.environ.get('ETSY_SHOP_ID') or '39729443'}")
    if api.remaining is None or int(api.remaining) < KOTA_YOKLAMA:
        raise SystemExit(f"DUR: kota {api.remaining} < {KOTA_YOKLAMA} (Merkez 31 Eki); yoklama yapilmadi")
    Y = [dene(api, "/listings/batch", {"listing_ids": ",".join(ids), "includes": INCLUDES}),
         dene(api, "/listings/batch/inventory", {"listing_ids": ",".join(ids)})]
    (out / "YOKLAMA.json").write_text(json.dumps(dict(istek=api.calls - c0, kota=api.remaining, ilanlar=ids, toplu=Y), indent=1,
                                                  ensure_ascii=False))
    for y in Y:
        print(y["yol"], y["params"].get("includes", ""), "->", y["durum"], "n", y.get("n_sonuc"), y.get("ust"), (y.get("hata") or "")[:200])
        print("  ilk:", json.dumps(y.get("ilk"), ensure_ascii=False)[:1500])
    print(f"istek {api.calls - c0} | kota {api.remaining}")
    return 0 if all(y["durum"] == "200" for y in Y) else 1


if __name__ == "__main__":
    sys.exit(main())
