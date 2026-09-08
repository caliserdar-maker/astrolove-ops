#!/usr/bin/env python3
"""
SALT OKUR: Pure White (PW) dijital ilanlarinin RU cevirisi icin kaynak tespiti (Mo 8 Eyl 2026).

Verilen cift(ler) icin dijital ilanlarin 5 edisyonunu baslikla eslestirir; secilen edisyonlarin
CANLI metinlerini oldugu gibi yazdirir: EN baslik/aciklama/etiketler + RU baslik/aciklama/etiketler.
Hicbir yazma yapmaz. Amac: token donusumunu (edisyon adi, renk ifadeleri) gercek metinden turetmek.

Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
Kullanim: pw_ru_probe.py --pairs ARIES_LEO,AQUARIUS_AQUARIUS [--editions "Champagne Ivory,Pure White"]
"""
import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from pod_listing_create import DIGITAL_ORDER  # noqa: E402
from xsell_links import pair_rx, shop_listings  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pairs", required=True, help="virgullu cift listesi (ARIES_LEO,...)")
    ap.add_argument("--editions", default="Champagne Ivory,Pure White,Midnight Blue")
    a = ap.parse_args()
    pairs = [p.strip().upper() for p in a.pairs.split(",") if p.strip()]
    eds = [e.strip() for e in a.editions.split(",") if e.strip()]
    for e in eds:
        if e not in DIGITAL_ORDER:
            raise SystemExit(f"bilinmeyen edisyon: {e} (gecerli: {DIGITAL_ORDER})")

    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]
    listings = shop_listings(api, shop)
    log(f"aktif ilan: {len(listings)} | kota {api.remaining}")

    for pair in pairs:
        rx = pair_rx(pair)
        aday = [x for x in listings if rx.search(x["title"]) and not re.search(r"wallpaper", x["title"], re.I)]
        print(f"\n===== {pair}: {len(aday)} aday ilan =====")
        for x in sorted(aday, key=lambda y: y["title"]):
            print(f"- {x['listing_id']} | {x['title']}")
        for ed in eds:
            hits = [x for x in aday if ed.lower() in x["title"].lower()]
            if len(hits) != 1:
                print(f"\n### {pair} / {ed}: {len(hits)} aday - ATLANDI")
                continue
            lid = hits[0]["listing_id"]
            L = api.get(f"/listings/{lid}") or {}
            t = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True)
            print(f"\n### {pair} / {ed} - ilan {lid} (state={L.get('state')})")
            print(f"----- EN baslik -----\n{L.get('title')}")
            print(f"----- EN etiketler ({len(L.get('tags') or [])}) -----\n{L.get('tags')}")
            print(f"----- EN aciklama ({len(L.get('description') or '')} karakter) -----\n{L.get('description')}\n----- EN son -----")
            if t is None:
                print("----- RU: ceviri yok (404) -----")
            else:
                print(f"----- RU baslik -----\n{t.get('title')}")
                print(f"----- RU etiketler ({len(t.get('tags') or [])}) -----\n{t.get('tags')}")
                print(f"----- RU aciklama ({len(t.get('description') or '')} karakter) -----\n{t.get('description')}\n----- RU son -----")
    log(f"kota sonra: {api.remaining}")


if __name__ == "__main__":
    main()
