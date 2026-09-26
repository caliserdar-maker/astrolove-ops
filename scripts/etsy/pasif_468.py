#!/usr/bin/env python3
"""GOREV_0021 md.3: pasife alinacak 468 ilanin KURU KOSU listesi (SALT OKUR).

Etsy'ye YAZMA YOK - yalniz GET. Musteri verisi yazilmaz/loglanmaz: makbuzlardan
yalniz ilan basina ADET ve acik/kapali durum sayilir.
Kapsam: 390 dijital poster + 78 wallpaper (Serdar karari 26 Eyl; POD ilanlari kalir).
Cikti: PASIF_468.csv (listing_id, tur, cift, state, siparis_90g, favori, acik_siparis)
       + PASIF_468_OZET.json (QC: sayilar, KALAN listesiyle capraz kontrol, PASS/FAIL).
"""
import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from envanter_raporu import burclar, siniflandir  # noqa: E402

STATES = ("active", "inactive", "draft", "expired", "sold_out")
KAPALI = {"completed", "canceled", "cancelled", "fully refunded"}
TUR = {"Dijital poster": "dijital", "Duvar kagidi": "wallpaper"}


def ilanlar(api, shop, state, max_pages=12):
    out, offset = [], 0
    for _ in range(max_pages):
        r = api.get(f"/shops/{shop}/listings", params={"state": state, "limit": 100,
                                                        "offset": offset}, ok404=True) or {}
        res = r.get("results") or []
        out += res
        if len(res) < 100:
            break
        offset += 100
    return out


def makbuzlar(api, shop, gun=90, max_pages=10):
    """Ilan basina 90 gunluk siparis adedi + acik (teslim bekleyen) siparis sayisi."""
    esik = int(time.time()) - gun * 86400
    say, acik, offset, n = defaultdict(int), defaultdict(int), 0, 0
    for _ in range(max_pages):
        try:
            r = api.get(f"/shops/{shop}/receipts",
                        params={"limit": 100, "offset": offset, "min_created": esik}) or {}
        except SystemExit as ex:
            return None, None, f"makbuz okunamadi: {str(ex)[:100]}"
        res = r.get("results") or []
        for rc in res:
            n += 1
            durum = str(rc.get("status") or "").strip().lower()
            for tr in rc.get("transactions") or []:
                lid = str(tr.get("listing_id") or "")
                if not lid:
                    continue
                say[lid] += int(tr.get("quantity") or 1)
                if durum not in KAPALI and not rc.get("is_shipped"):
                    acik[lid] += 1
        if len(res) < 100:
            return say, acik, f"tam ({n} makbuz, {gun} gun)"
        offset += 100
    return say, acik, f"{max_pages} sayfa siniri ({n} makbuz)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kalan", required=True, help="DIJITAL_78_KALAN_ILANLAR.csv (390 capraz kontrol)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    shop = os.environ["ETSY_SHOP_ID"]; mask(shop)
    store = TokenStore(os.environ.get("TOKEN_FILE", "_work/ETSY_TOKEN.json"), k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    satir, tum = [], {}
    for st in STATES:
        for L in ilanlar(api, shop, st):
            tum[str(L["listing_id"])] = (st, L)
    log(f"ilan okundu: {len(tum)} (state {STATES}), cagri {api.calls}, kota {api.remaining}")
    say, acik, mnot = makbuzlar(api, shop)
    log(f"makbuz: {mnot}")
    for lid, (st, L) in sorted(tum.items()):
        tur = TUR.get(siniflandir(L))
        if not tur:
            continue                                   # POD ve digerleri KALIR
        b = burclar(L.get("title") or "")
        satir.append({"listing_id": lid, "tur": tur, "cift": "_".join(x.upper() for x in b),
                      "state": st, "siparis_90g": (say or {}).get(lid, 0) if say is not None else "",
                      "favori": L.get("num_favorers"),
                      "acik_siparis": ("EVET" if (acik or {}).get(lid) else "hayir")
                      if acik is not None else "OKUNAMADI"})
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    with open(out / "PASIF_468.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(satir[0].keys()) if satir else ["listing_id"])
        w.writeheader(); w.writerows(satir)

    kalan = set()
    with open(a.kalan, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            kalan.add(r["keep_listing_id"].strip())
            kalan.update(x.strip() for x in r["deactivate_ids"].split(";") if x.strip())
    dij = {r["listing_id"] for r in satir if r["tur"] == "dijital"}
    wp = [r for r in satir if r["tur"] == "wallpaper"]
    oz = {"toplam": len(satir), "dijital": len(dij), "wallpaper": len(wp),
          "state": {st: sum(1 for r in satir if r["state"] == st) for st in STATES},
          "kalan390_bulunan": len(kalan & dij), "kalan390_eksik": sorted(kalan - dij)[:20],
          "dijital_kalan_disi": sorted(dij - kalan)[:20],
          "acik_siparisli": [r["listing_id"] for r in satir if r["acik_siparis"] == "EVET"],
          "siparis_90g_toplam": sum(int(r["siparis_90g"] or 0) for r in satir),
          "makbuz": mnot, "etsy_cagri": api.calls, "etsy_yazma": 0}
    oz["SONUC"] = "PASS" if (oz["toplam"] == 468 and oz["dijital"] == 390 and oz["wallpaper"] == 78
                             and oz["kalan390_bulunan"] == 390 and acik is not None) else "FAIL"
    (out / "PASIF_468_OZET.json").write_text(json.dumps(oz, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in oz.items()}, ensure_ascii=False))
    return 0 if oz["SONUC"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
