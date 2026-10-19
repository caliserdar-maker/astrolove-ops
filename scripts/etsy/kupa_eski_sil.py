#!/usr/bin/env python3
"""KUPA: eski 7 stil CANCER_LIBRA taslagi 4597843405'i SIL (Serdar onayi 19 Eki 2026). Yalniz bu tek ilan.

1) Oku: 4597843405 state "draft" ve baslik BASLIK degilse DUR (silme yok). 4598525642 "draft" degilse DUR.
2) Tek deneme deleteListing (DELETE /listings/4597843405). Baska hicbir yazma cagrisi yok (Kilit her seyi durdurur).
3) Dogrula: 4597843405 okunamiyor (404) ve 4598525642 hala "draft".
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE, OUT. Cikti: OUT/KUPA_ESKI_SIL.json
Kota tabani 10: x-remaining-today < 10 ise DUR.
"""
import json
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import API, Etsy, TokenStore, mask  # noqa: E402

SIL = 4597843405
KORU = 4598525642
BASLIK = "Cancer and Libra Personalized Mug, Zodiac Symbols with Names, Gift for Couples"
KOTA_MIN = 10


class Kilit(Etsy):
    """GET serbest; tek izinli yazma sil() ile DELETE /listings/SIL. Kota < 10 -> DUR."""

    def _call(self, method, path, **kw):
        if method != "GET":
            raise SystemExit(f"YASAK yazma: {method} {path}")
        r = super()._call(method, path, **kw)
        self.kota()
        return r

    def kota(self):
        try:
            if self.remaining is not None and int(self.remaining) < KOTA_MIN:
                raise SystemExit(f"DUR: kota {self.remaining} < {KOTA_MIN}")
        except ValueError:
            pass

    def sil(self, lid):
        """deleteListing: TEK deneme. (status, metin)."""
        if lid != SIL:
            raise SystemExit(f"YASAK: yalniz {SIL} silinir, istenen {lid}")
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


def calistir(api, shop, out, bekle=5):
    R = {"sil": SIL, "koru": KORU}

    def kaydet():
        json.dump(R, open(out / "KUPA_ESKI_SIL.json", "w"), indent=1, ensure_ascii=False, default=str)

    def dur(neden):
        R["sonuc"] = f"DUR: {neden}"; kaydet()
        raise SystemExit(R["sonuc"])

    # 1) silmeden once oku
    L = api.get(f"/listings/{SIL}", ok404=True)
    K = api.get(f"/listings/{KORU}", ok404=True)
    R["once"] = dict(sil=L and dict(listing_id=L.get("listing_id"), state=L.get("state"), title=L.get("title"), shop_id=L.get("shop_id")),
                     koru=K and dict(listing_id=K.get("listing_id"), state=K.get("state"), title=K.get("title")), kota=api.remaining)
    print(f"once: {R['once']}", flush=True)
    if not L:
        dur(f"{SIL} okunamadi (404); silme yok")
    if L.get("listing_id") != SIL or str(L.get("shop_id")) != str(shop):
        dur(f"{SIL} kimlik/magaza uyumsuz {L.get('listing_id')} {L.get('shop_id')}")
    if L.get("state") != "draft":
        dur(f"{SIL} state {L.get('state')!r} (draft degil); silme yok")
    if L.get("title") != BASLIK:
        dur(f"{SIL} baslik farkli {L.get('title')!r}; silme yok")
    if not K or K.get("state") != "draft":
        dur(f"{KORU} draft degil ({K and K.get('state')}); silme yok")
    kaydet()

    # 2) tek deleteListing
    kod, metin = api.sil(SIL)
    R["delete"] = dict(status=kod, metin=metin, kota=api.remaining)
    print(f"deleteListing {SIL} -> {kod}", flush=True)
    kaydet()
    if kod not in (200, 204):
        dur(f"deleteListing {kod}: {metin}")

    # 3) dogrula
    for i in range(4):                     # silme birkac saniyede yansiyabilir
        L2 = api.get(f"/listings/{SIL}", ok404=True)
        if L2 is None:
            break
        time.sleep(bekle * (i + 1))
    K2 = api.get(f"/listings/{KORU}", ok404=True)
    R["kontrol"] = {f"{SIL} okunamiyor (404)": L2 is None,
                    f"{KORU} hala draft": bool(K2) and K2.get("state") == "draft"}
    R["sonra"] = dict(sil=L2 and dict(state=L2.get("state")), koru=K2 and dict(state=K2.get("state")), kota=api.remaining, cagri=api.calls)
    kotu = [k for k, v in R["kontrol"].items() if not v]
    R["sonuc"] = "PASS" if not kotu else f"FAIL {kotu}"
    kaydet()
    print(f"::warning::ESKI SIL {SIL}: delete {kod} | {R['sonuc']} | {KORU} state={K2 and K2.get('state')} | kota {api.remaining}")
    if kotu:
        raise SystemExit(R["sonuc"])
    return R


def main():
    out = Path(os.environ.get("OUT", "_out")); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    calistir(Kilit(store), os.environ["ETSY_SHOP_ID"], out)


if __name__ == "__main__":
    main()
