#!/usr/bin/env python3
"""Eski sade kupa taslagi 4607523667'yi SIL (Serdar 2 Kas onayi, Merkez 2 Kas gece madde 3). Yalniz bu tek ilan.

Iki asama (is akisi asamalar arasinda yedegi Drive'a yazar ve dogrular):
  --asama oku : GET listing + GET inventory; ham JSON'u OUT/YEDEK_4607523667.json'a yazar; kosullari denetler; silme yok.
  --asama sil : yeniden GET listing + inventory (kosullar ayni); kota >= 10 ise TEK deleteListing; sonra 404 dogrulamasi.
Kosullar (hepsi): listing_id ve shop_id dogru; state "draft"; baslik ve SKU kumesi 1 Kas okumasi
(Drive TEMP/SADE_TASLAK_G/20261101_160821/SABLON_4607523667.json) ile birebir. Biri tutmazsa DUR, silme yok.
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE, OUT. Cikti: OUT/SIL_4607523667_<asama>.json
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import API, KOTA_SINIRI, Etsy, TokenStore, mask  # noqa: E402

SIL = 4607523667
BASLIK = ("Aries Gifts, Personalized Aries Zodiac Mug with Name or Date, Custom Coffee Mug, "
          "Astrology Birthday Gift for Her or Him")
SKULAR = frozenset(f"KUPA-TAURUS_VIRGO-{n:02d}-{oz}" for n in range(1, 9) for oz in (11, 15))


class Kilit(Etsy):
    """GET serbest; tek izinli yazma sil(): DELETE /listings/SIL. Kota < KOTA_SINIRI -> DUR."""

    def _call(self, method, path, **kw):
        if method != "GET":
            raise SystemExit(f"YASAK yazma: {method} {path}")
        return super()._call(method, path, **kw)

    def sil(self, lid):
        if lid != SIL:
            raise SystemExit(f"YASAK: yalniz {SIL} silinir, istenen {lid}")
        if self.remaining is None or int(self.remaining) < KOTA_SINIRI:
            raise SystemExit(f"DUR: kota {self.remaining} < {KOTA_SINIRI}")
        self.calls += 1
        r = requests.delete(API + f"/listings/{SIL}", headers=self._headers(), timeout=60)
        self.remaining = r.headers.get("x-remaining-today", self.remaining)
        return r.status_code, r.text[:300]

    def post(self, *a, **k):
        raise SystemExit("YASAK: POST")

    def put(self, *a, **k):
        raise SystemExit("YASAK: PUT")

    def patch(self, *a, **k):
        raise SystemExit("YASAK: PATCH")

    def delete(self, *a, **k):
        raise SystemExit("YASAK: DELETE (yalniz sil())")

    def post_json(self, *a, **k):
        raise SystemExit("YASAK: POST json")

    def put_json(self, *a, **k):
        raise SystemExit("YASAK: PUT json")

    def post_file(self, *a, **k):
        raise SystemExit("YASAK: POST file")


def denetle(L, inv, shop):
    """-> (ozet, hatalar). hatalar bos degilse silme yok."""
    skular = sorted({p.get("sku") for p in (inv or {}).get("products") or []})
    oz = dict(listing_id=L.get("listing_id"), shop_id=L.get("shop_id"), state=L.get("state"), title=L.get("title"),
              sku=skular, listing_skus=sorted(L.get("skus") or []))
    h = []
    if L.get("listing_id") != SIL:
        h.append(f"listing_id {L.get('listing_id')}")
    if str(L.get("shop_id")) != str(shop):
        h.append(f"shop_id {L.get('shop_id')}")
    if L.get("state") != "draft":
        h.append(f"state {L.get('state')!r} (draft degil)")
    if L.get("title") != BASLIK:
        h.append(f"baslik farkli: {L.get('title')!r}")
    if set(skular) != SKULAR:
        h.append(f"SKU kumesi farkli ({len(skular)} sku; eksik {sorted(SKULAR - set(skular))[:4]}, fazla {sorted(set(skular) - SKULAR)[:4]})")
    return oz, h


def calistir(api, shop, out, asama, bekle=5):
    R = dict(sil=SIL, asama=asama)
    yol = out / f"SIL_{SIL}_{asama}.json"

    def kaydet():
        yol.write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str), encoding="utf-8")

    def dur(neden):
        R["sonuc"] = f"DUR: {neden}"; kaydet()
        raise SystemExit(R["sonuc"])

    L = api.get(f"/listings/{SIL}", ok404=True)
    if not L:
        dur(f"{SIL} okunamadi (404); silme yok")
    inv = api.get(f"/listings/{SIL}/inventory", ok404=True)
    if asama == "oku":
        (out / f"YEDEK_{SIL}.json").write_text(json.dumps(dict(okuma_zamani=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                                               listing=L, inventory=inv), indent=1, ensure_ascii=False),
                                               encoding="utf-8")
    R["once"], hata = denetle(L, inv, shop)
    R["kota_once"] = api.remaining
    print(f"once: state {R['once']['state']} | baslik esit {R['once']['title'] == BASLIK} | sku {len(R['once']['sku'])} | "
          f"kota {api.remaining}", flush=True)
    if hata:
        dur("; ".join(hata))
    if asama == "oku":
        R["sonuc"] = "KOSUL PASS (silme yok)"; kaydet()
        print(f"::notice::SIL {SIL} oku: {R['sonuc']} | istek {api.calls} | kota {api.remaining}", flush=True)
        return R
    kaydet()
    kod, metin = api.sil(SIL)
    R["delete"] = dict(status=kod, metin=metin, kota=api.remaining)
    print(f"deleteListing {SIL} -> {kod}", flush=True)
    kaydet()
    if kod not in (200, 204):
        dur(f"deleteListing {kod}: {metin}")
    L2 = "okunmadi"
    for i in range(4):                     # silme birkac saniyede yansiyabilir
        L2 = api.get(f"/listings/{SIL}", ok404=True)
        if L2 is None:
            break
        time.sleep(bekle * (i + 1))
    R["sonra"] = dict(okunamiyor_404=L2 is None, state=(L2 or {}).get("state") if isinstance(L2, dict) else None,
                      kota=api.remaining, cagri=api.calls)
    R["sonuc"] = "PASS" if L2 is None else f"FAIL: silme sonrasi hala okunuyor (state {R['sonra']['state']})"
    kaydet()
    print(f"::notice::SIL {SIL}: delete {kod} | {R['sonuc']} | istek {api.calls} | kota {api.remaining}", flush=True)
    if L2 is not None:
        raise SystemExit(R["sonuc"])
    return R


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--asama", required=True, choices=["oku", "sil"])
    a = ap.parse_args(argv)
    out = Path(os.environ.get("OUT", "_out")); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    calistir(Kilit(store), os.environ["ETSY_SHOP_ID"], out, a.asama)


if __name__ == "__main__":
    main()
