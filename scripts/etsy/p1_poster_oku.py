#!/usr/bin/env python3
"""SALT OKUMA (Etsy'ye yazim YOK; yalniz GET). P1 envanteri (Serdar 4 Kas P1 "A"; Merkez gorev P1_POSTER_YANITSIZ 1. asama).
- 78 poster (data/pod/pod78_ids.csv): GET /listings/{id}, GET /listings/{id}/inventory, RU tekil GET
  (beyan_marka_yaz.ru_tekil: /shops/{shop}/listings/{id}/translations/ru) -> HAM/<id>.json. Ilan basina hata yakalanir
  ("okunamadi"); kota SystemExit'i yakalanmaz (kosu durur, kalan ilanlar OZET'te).
- Tum aktif ilanlar (/shops/{shop}/listings/active, 100'luk): yalniz EN aciklamada onizleme sozu SAYIMI -> AKTIF_SAYIM.csv
  (ilan, grup, sayilar; metin yazilmaz).
Kota: baslangic kapisi kalan >= 78 x 3 + KOTA_SINIRI; ilan basina api.kota_kapisi + kalan < 3 + KOTA_SINIRI ise DUR
(poster_metin_yaz.py kota_kapisi deseni); her istekte etsy_common sert taban.
Import: yalniz main'deki modüller (etsy_common, beyan_marka_yaz). Kullanim: p1_poster_oku.py --out OUT"""
import argparse
import csv
import html
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import etsy_common as E  # noqa: E402
from beyan_marka_yaz import ru_tekil  # noqa: E402

KOK = pathlib.Path(__file__).resolve().parents[2]
ISTEK_ILAN = 3                     # GET ilan + GET envanter + GET RU tekil
SOZ = {"genel": re.compile(r"If we don.t hear from you within 24 hours of receiving the preview"),
       "go_ahead": re.compile(r"we go ahead with the design as shown"),
       "eski": re.compile(r"we print the design as shown")}


class SaltOku(E.Etsy):
    """Yalniz GET; her yazma cagrisi kosuyu durdurur."""

    def _call(self, method, path, **kw):
        if method != "GET":
            raise SystemExit(f"YASAK (salt okuma): {method} {path}")
        return super()._call(method, path, **kw)

    def post_file(self, path, *a, **k):   # etsy_common.post_file _call'u atlar; inceleme 4 Kas D-11
        raise SystemExit(f"YASAK (salt okuma): POST(file) {path}")


def idler(ad):
    return [r["listing_id"].strip() for r in csv.DictReader(open(KOK / "data" / "pod" / ad, encoding="utf-8-sig"))]


def kota(api, lid, kalan_istek=ISTEK_ILAN):
    api.kota_kapisi(f"ilan {lid}")
    if api.remaining is not None and int(api.remaining) < kalan_istek + E.KOTA_SINIRI:
        raise SystemExit(f"DUR: kota: ilan {lid} kalan {api.remaining} < {kalan_istek} + {E.KOTA_SINIRI}")


HTTP_RX = re.compile(r"^HATA: GET \S+ -> (\d{3}):")


def ilan_hatasi(e):
    """etsy_common._call 2xx disinda SystemExit atar. Yalniz 404 ve 5xx (3 denemeden sonra) ilan basina 'okunamadi';
    kota / 429 / 401 / 403 / YASAK -> None (kosu durur). Inceleme 4 Kas D-2."""
    m = HTTP_RX.match(str(e))
    if m and (m.group(1) == "404" or m.group(1).startswith("5")):
        return f"HTTP {m.group(1)}"
    return None


def sayim(t):
    return {k: len(rx.findall(t or "")) for k, rx in SOZ.items()}


def calis(api, shop, out, poster, yd, oz):
    """oz: cagiranin sozlugu (SystemExit'te de OZET.json'a yazilir)."""
    (out / "HAM").mkdir(parents=True, exist_ok=True)
    oz.update(ilan=len(poster), okunan=0, okunamadi=[], ru_yok=[], islenmedi=list(poster), istek=0)
    try:
        # 1) tum aktif ilanlar: yalniz sayim
        satir, off, n0 = [], 0, None
        while True:
            j = api.get(f"/shops/{shop}/listings/active", params={"limit": 100, "offset": off}) or {}
            oz["istek"] += 1
            if n0 is None:
                n0 = int(j.get("count") or 0)
                tah = len(poster) * ISTEK_ILAN + (n0 // 100)
                oz["tahmin_istek"] = tah + 1
                if api.remaining is None or int(api.remaining) < tah + E.KOTA_SINIRI:
                    raise SystemExit(f"DUR: baslangic kota kapisi: kalan {api.remaining} < {tah} + {E.KOTA_SINIRI}")
            for x in j.get("results") or []:
                lid = str(x["listing_id"]); s = sayim(html.unescape(x.get("description") or ""))
                grup = "poster78" if lid in poster else ("yd78" if lid in yd else ("kupa" if re.search(r"\bmug\b", x.get("title") or "", re.I) else "diger"))
                satir.append(dict(listing_id=lid, grup=grup, **s))
            if len(j.get("results") or []) < 100:
                break
            off += 100
        with open(out / "AKTIF_SAYIM.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["listing_id", "grup", *SOZ], lineterminator="\n"); w.writeheader(); w.writerows(satir)
        oz["aktif"] = len(satir)
        # 2) 78 poster: ham okuma
        for i, lid in enumerate(poster):
            try:
                kota(api, lid)
            except SystemExit:
                oz["islenmedi"] = poster[i:]
                raise
            kayit = dict(listing_id=lid)
            try:
                x = api.get(f"/listings/{lid}") or {}; oz["istek"] += 1
                inv = api.get(f"/listings/{lid}/inventory") or {}; oz["istek"] += 1
                ru = ru_tekil(api, shop, lid); oz["istek"] += 1
                kayit.update(listing={k: x.get(k) for k in ("listing_id", "state", "title", "description", "tags", "materials",
                                                              "last_modified_timestamp")},
                             inventory=inv, ru={k: (ru or {}).get(k) for k in ("title", "description", "tags")} if ru else None,
                             ru_durum="var" if ru else "yok")
                if not ru:
                    oz["ru_yok"].append(lid)
                oz["okunan"] += 1
            except SystemExit as e:
                h = ilan_hatasi(e)
                if h is None:
                    oz["islenmedi"] = poster[i:]
                    raise
                kayit.update(ru_durum="okunamadi", hata=h)   # yalniz durum kodu (govde yazilmaz)
                oz["okunamadi"].append(lid)
            except Exception as e:   # ag istisnasi: okunamadi (metin yazilmaz)
                kayit.update(ru_durum="okunamadi", hata=type(e).__name__)
                oz["okunamadi"].append(lid)
            (out / "HAM" / f"{lid}.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
            oz["islenmedi"] = poster[i + 1:]
            print(f"[{i + 1}/{len(poster)}] {lid} {kayit.get('ru_durum')} | kota {api.remaining}", flush=True)
    finally:
        oz["kota_son"] = api.remaining


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    E.mask(k); E.mask(s)
    store = E.TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    oz = {}
    try:
        calis(SaltOku(store), os.environ["ETSY_SHOP_ID"], out, idler("pod78_ids.csv"), set(idler("yd78_ids.csv")), oz)
    finally:
        (out / "OZET.json").write_text(json.dumps(oz, indent=1), encoding="utf-8")
    print("P1 OKUMA:", json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in oz.items()}), flush=True)


if __name__ == "__main__":
    main()
