#!/usr/bin/env python3
"""
TEK ILANI YAYINA AL (ETSY'YE YAZAR) - 5 Eyl 2026 Mo gorevi (Cancer_Libra).

Once salt okur on-kontrol: state, galeri gorseli sayisi (6) ve rank sirasi,
dijital dosya sayisi (5) ve adlari, video 0. Kosul saglanmazsa YAZMAZ, FAIL.
Sonra updateListing (PATCH state=active) ve kararli geri okuma
(iki ardisik okuma state=active). Fiyat/metin/medya/dosyaya DOKUNMAZ.
Varsayilan DRY-RUN; yazma icin --apply gerekir.
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from wp_mockup_common import EDITIONS, GALLERY_ORDER  # noqa: E402
from wp_verify_all import PDF_NAME  # noqa: E402


def hazir_mi(listing, imgs, files, vids, pair):
    """On-kontrol. Donus: (ok, detay)."""
    det = []
    st = listing.get("state")
    if st == "active":
        det.append("zaten active")
    elif st not in ("inactive", "edit", "draft"):
        det.append(f"beklenmeyen state {st}")
    if len(imgs) != len(GALLERY_ORDER):
        det.append(f"gorsel {len(imgs)} != {len(GALLERY_ORDER)}")
    ranks = [i.get("rank") for i in imgs]
    if ranks != sorted(ranks):
        det.append(f"rank sirasi bozuk {ranks}")
    adlar = sorted(str(f.get("filename") or "") for f in files)
    bekl = sorted([f"AstroLove_{pair}_{e}.zip" for e in EDITIONS] + [PDF_NAME])
    if adlar != bekl:
        det.append(f"dosyalar {adlar} != {bekl}")
    if vids:
        det.append(f"video {len(vids)} (0 beklenir)")
    return (not det), "; ".join(det)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listing-id", required=True)
    ap.add_argument("--pair", required=True)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    lid = a.listing_id

    L = api.get(f"/listings/{lid}", ok404=True) or api.get(f"/shops/{shop}/listings/{lid}", ok404=True) or {}
    imgs = sorted((api.get(f"/listings/{lid}/images", ok404=True) or {}).get("results", []), key=lambda x: x.get("rank") or 0)
    files = (api.get(f"/shops/{shop}/listings/{lid}/files", ok404=True) or {}).get("results", [])
    vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results", [])
    log(f"once: state {L.get('state')} | gorsel {len(imgs)} rank {[i.get('rank') for i in imgs]} | "
        f"dosya {len(files)} | video {len(vids)} | fiyat {L.get('price')} | kota {api.remaining}")
    ok, det = hazir_mi(L, imgs, files, vids, a.pair)
    if not ok:
        log(f"ON-KONTROL FAIL: {det} -> YAZILMADI")
        return 1
    if not a.apply:
        log("DRY-RUN: on-kontrol PASS, state=active yazilacakti")
        return 0
    log("PATCH state=active ...")
    api.patch(f"/shops/{shop}/listings/{lid}", {"state": "active"})
    prev = None
    for _ in range(4):
        time.sleep(10)
        cur = (api.get(f"/listings/{lid}", ok404=True) or {}).get("state")
        log(f"  geri okuma: state {cur}")
        if cur == "active" and prev == "active":
            break
        prev = cur
    L2 = api.get(f"/listings/{lid}", ok404=True) or {}
    imgs2 = (api.get(f"/listings/{lid}/images", ok404=True) or {}).get("results", [])
    files2 = (api.get(f"/shops/{shop}/listings/{lid}/files", ok404=True) or {}).get("results", [])
    sonuc = L2.get("state") == "active" and len(imgs2) == len(imgs) and len(files2) == len(files)
    log(f"sonra: state {L2.get('state')} | gorsel {len(imgs2)} | dosya {len(files2)} | url {L2.get('url')} | kota {api.remaining}")
    log(f"SONUC {'PASS' if sonuc else 'FAIL'}")
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write(f"## yayina alma {a.pair} {lid}: {'PASS' if sonuc else 'FAIL'} - state {L2.get('state')}, "
                     f"gorsel {len(imgs2)}, dosya {len(files2)}, {L2.get('url')}\n")
    return 0 if sonuc else 1


if __name__ == "__main__":
    sys.exit(main())
