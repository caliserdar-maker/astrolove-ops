#!/usr/bin/env python3
"""Pasif ilanlarin sure durumu + referans ilan gorseli (Serdar 22 Eki, BAG EDISYONLARI kontrol paketi madde 2-3). SALT OKUMA.

- GET /shops/{id}/listings state=inactive ve state=expired (sayfali). Her ilan: state, listing_type, tur (baslikta 'wallpaper'
  -> wallpaper, degilse dijital poster), ending_timestamp. Sinif: 'suresi_gecmis' (ending < simdi) / 'gecerli'.
  Etsy Help (How to Deactivate a Listing): deaktif ilanin 4 aylik suresi isler; suresi dolmus ilan yeniden acilirken 0,20 USD
  yenileme ister, dolmamis ilan ucretsiz acilir (ucret cumlesi: Etsy topluluk alintisi + 3. taraf; Help sayfasinda dogrulanmadi).
- --gorsel LID:RANK: o ilanin gorseli (getListingImages) tam cozunurlukte indirilir (Etsy CDN; API kotasi kullanmaz).
Kota tabani 10. Cikti: <out>/PASIF_SURE.json, PASIF_SURE.csv, GORSEL_<LID>_<RANK>.jpg; log'a yalniz sayi."""
import argparse
import csv
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.request
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

KOTA_TABAN = 10


def kota(api):
    if api.remaining is not None and int(api.remaining) < KOTA_TABAN:
        raise SystemExit(f"DUR: kota {api.remaining} < {KOTA_TABAN}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--gorsel", default="")
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    shop = os.environ["ETSY_SHOP_ID"]
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    simdi = dt.datetime.now(dt.timezone.utc)
    satir = []
    for durum in ("inactive", "expired"):
        off = 0
        while True:
            r = api.get(f"/shops/{shop}/listings", {"state": durum, "limit": 100, "offset": off}) or {}
            sayfa = r.get("results") or []
            for L in sayfa:
                end = L.get("ending_timestamp")
                e = dt.datetime.fromtimestamp(end, dt.timezone.utc) if end else None
                satir.append(dict(listing_id=L.get("listing_id"), state=L.get("state"), listing_type=L.get("listing_type"),
                                  tur="wallpaper" if "wallpaper" in (L.get("title") or "").lower() else "dijital_poster",
                                  ending=e.isoformat() if e else "", kalan_gun=round((e - simdi).total_seconds() / 86400, 1) if e else None,
                                  sinif=("suresi_gecmis" if e and e < simdi else "gecerli") if e else "bilinmiyor",
                                  state_ts=dt.datetime.fromtimestamp(L.get("state_timestamp") or 0, dt.timezone.utc).isoformat()))
            kota(api)
            off += len(sayfa)
            if not sayfa or off >= int(r.get("count") or 0):
                break
    say = Counter((x["state"], x["tur"], x["sinif"]) for x in satir)
    gecerli = [x["kalan_gun"] for x in satir if x["sinif"] == "gecerli"]
    oz = dict(toplam=len(satir), state=dict(Counter(x["state"] for x in satir)), tur=dict(Counter(x["tur"] for x in satir)),
              listing_type=dict(Counter(x["listing_type"] for x in satir)),
              sinif=dict(Counter(x["sinif"] for x in satir)), kirilim={" | ".join(k_): v for k_, v in say.items()},
              gecerli_kalan_gun_min=min(gecerli) if gecerli else None, gecerli_kalan_gun_max=max(gecerli) if gecerli else None,
              en_erken_bitis=min((x["ending"] for x in satir if x["ending"]), default=""),
              en_gec_bitis=max((x["ending"] for x in satir if x["ending"]), default=""),
              ucret_tahmini_usd=dict(ucretsiz_acilir=sum(1 for x in satir if x["sinif"] == "gecerli"),
                                     yenileme_020=sum(1 for x in satir if x["sinif"] == "suresi_gecmis"),
                                     toplam_usd=round(0.20 * sum(1 for x in satir if x["sinif"] == "suresi_gecmis"), 2)),
              olcum_utc=simdi.isoformat())
    (out / "PASIF_SURE.json").write_text(json.dumps(dict(ozet=oz, ilanlar=satir), ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "PASIF_SURE.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(satir[0]) if satir else ["listing_id"]); w.writeheader(); w.writerows(satir)
    print("PASIF_SURE", json.dumps(oz, ensure_ascii=False), flush=True)
    if a.gorsel:
        lid, rank = a.gorsel.split(":")
        imgs = (api.get(f"/listings/{lid}/images") or {}).get("results") or []
        kota(api)
        im = next((x for x in imgs if str(x.get("rank")) == rank), None)
        if not im:
            print(f"GORSEL {lid}#{rank}: bulunamadi (gorsel sayisi {len(imgs)})")
        else:
            p = out / f"GORSEL_{lid}_{rank}.jpg"
            with urllib.request.urlopen(urllib.request.Request(im["url_fullxfull"], headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
                p.write_bytes(r.read())
            print(f"GORSEL {lid}#{rank}: {im.get('full_width')}x{im.get('full_height')} | {p.stat().st_size} bayt | "
                  f"listing_image_id {im.get('listing_image_id')} | alt_text: {im.get('alt_text') or '(bos)'}")
    print(f"ETSY istek {api.calls} | kota {api.remaining}")


if __name__ == "__main__":
    main()
