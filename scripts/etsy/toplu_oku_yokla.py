#!/usr/bin/env python3
"""Etsy toplu okuma YOKLAMASI (Serdar 31 Eki 1a, istek azaltma madde 3-4). YALNIZ GET; yazma yok.
Amac: getListingsByListingIds (GET /listings/batch?listing_ids=..&includes=..) ve toplu envanter okumasinin GERCEK yanit seklini olcmek
(developer.etsy.com bu oturumdan okunamadi; ayristirici tahminle degil olculen yanitla yazilir). Ayni ilanlar ilan basina uclardan da
okunur (galeri, video, kisisellestirme, ceviri, envanter) ve alan alan karsilastirilir.
Cikti --out: YOKLAMA.json (her istek: yol, parametre, durum, ust anahtarlar, ilk sonucun anahtar agaci; ham yanit), KIYAS.json
(toplu == tekil mi, alan bazinda). Kullanim: toplu_oku_yokla.py --ilan 4598525642,4570143815 --out _out"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore  # noqa: E402

INCLUDES = "Images,Videos,Personalization,Translations,Inventory"
ENV_YOLLAR = ("/listings/batch/inventory", "/listings/inventory")


def agac(x, d=0):
    """anahtar agaci (deger yok): sekil olcumu"""
    if d > 4:
        return "..."
    if isinstance(x, dict):
        return {k: agac(v, d + 1) for k, v in sorted(x.items())}
    if isinstance(x, list):
        return [agac(x[0], d + 1)] if x else []
    return type(x).__name__


def dene(api, yol, params):
    try:
        y = api.get(yol, params=params, ok404=True)
        return dict(yol=yol, params=params, durum="200" if y is not None else "404", ust=sorted(y) if isinstance(y, dict) else None,
                    ilk=agac(((y or {}).get("results") or [None])[0]) if isinstance(y, dict) else None, ham=y)
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
    api.get(f"/shops/{os.environ.get('ETSY_SHOP_ID', '39729443')}")
    api.kota_kapisi("yoklama")
    c0 = api.calls
    Y = [dene(api, "/listings/batch", {"listing_ids": ",".join(ids), "includes": INCLUDES}),
         dene(api, "/listings/batch", {"listing_ids": ",".join(ids), "includes": "Images,Videos,Translations"})]
    for yol in ENV_YOLLAR:
        Y.append(dene(api, yol, {"listing_ids": ",".join(ids)}))
    tekil = {}
    for i in ids:
        tekil[i] = dict(images=dene(api, f"/listings/{i}/images", None), videos=dene(api, f"/listings/{i}/videos", None),
                        personalization=dene(api, f"/listings/{i}/personalization", None),
                        ru=dene(api, f"/listings/{i}/translations/ru", None), inventory=dene(api, f"/listings/{i}/inventory", None))
    toplu = {str(x.get("listing_id")): x for x in ((Y[0].get("ham") or {}).get("results") or [])}
    K = {}
    for i in ids:
        t = toplu.get(i) or {}
        K[i] = {k: (sorted(t) if k == "_anahtarlar" else None) for k in ("_anahtarlar",)}
        for alan, tek, cek in (("images", tekil[i]["images"], lambda h: [(x.get("listing_image_id"), x.get("rank"), x.get("alt_text")) for x in (h or {}).get("results") or []]),
                               ("videos", tekil[i]["videos"], lambda h: [x.get("video_id") for x in (h or {}).get("results") or []])):
            tb = t.get(alan) if alan in t else t.get(alan.capitalize())
            K[i][alan] = dict(toplu_var=tb is not None, esit=(cek({"results": tb}) == cek(tek.get("ham"))) if tb is not None else None)
        K[i]["personalization_anahtar"] = [k for k in t if "personal" in k.lower()]
        K[i]["translations_anahtar"] = [k for k in t if "translation" in k.lower()]
        K[i]["inventory_anahtar"] = [k for k in t if "inventory" in k.lower()]
    (out / "YOKLAMA.json").write_text(json.dumps(dict(istek=api.calls - c0, kota=api.remaining, toplu=Y, tekil=tekil), indent=1, ensure_ascii=False))
    (out / "KIYAS.json").write_text(json.dumps(K, indent=1, ensure_ascii=False))
    for y in Y:
        print(y["yol"], y["params"].get("includes", ""), "->", y["durum"], y.get("ust"), (y.get("hata") or "")[:160])
    print(json.dumps(K, ensure_ascii=False)[:1500])
    print(f"istek {api.calls - c0} | kota {api.remaining}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
