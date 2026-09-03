#!/usr/bin/env python3
"""
GECE ZINCIRI asama f: 78 ilanin SON DOGRULAMASI (SALT OKUR).

Her ilan ID ile tek tek sorgulanir; beklenen:
  - 6 galeri gorseli, rank 1..6 kesintisiz, her biri 3000x2250
  - 1 video (video_state active/processing)
  - 5 dijital dosya: 4 edisyon ZIP + HOW_TO_SET_YOUR_WALLPAPER.pdf (ad eslesmesi)
  - baslik sablonu (WP_LISTING_TEMPLATE.md), fiyat 3.99 USD, bolum 60120017
  - state (beklenen: pilot active, digerleri draft)
Cikti: CSV (ilan basina bir satir + FAIL nedeni) + job summary ozeti.
Etsy'ye hicbir yazma yok; tek yazma OAuth token yenilemesi (dosyaya geri yazilir).

Kullanim:
  wp_verify_all.py --state WA_WP_DRAFTS_STATE.csv --out verify_all.csv \\
      [--pairs ...] [--limit N] [--expect-video false]
"""
import argparse
import csv
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from wp_mockup_common import EDITIONS  # noqa: E402

PILOT_PAIR = "Cancer_Libra"
N_IMAGES = 6
IMG_W, IMG_H = 3000, 2250
PRICE = "3.99"
SECTION = 60120017
PDF_NAME = "HOW_TO_SET_YOUR_WALLPAPER.pdf"
TITLE_TPL = ("{Sign1} {Sign2} Matching Couple Wallpaper, 4 Colors, "
             "Phone Tablet Desktop Watch, Zodiac Digital Download")
TOKEN_REFRESH_S = 40 * 60


def money(obj):
    try:
        return f"{int(obj['amount']) / int(obj['divisor']):.2f}"
    except (TypeError, KeyError, ZeroDivisionError):
        return ""


def read_state(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for raw in csv.reader(fh):
            if len(raw) >= 2 and raw[1].strip().isdigit():
                rows.append((raw[0].strip(), raw[1].strip()))
    return rows


def check(api, shop, pair, lid, expect_video):
    issues = []
    listing = api.get(f"/listings/{lid}", ok404=True)
    if not listing:
        listing = api.get(f"/shops/{shop}/listings/{lid}", ok404=True)
    if not listing:
        return dict(pair=pair, listing_id=lid, ok=False, detail="ilan okunamadi")
    imgs = sorted((api.get(f"/listings/{lid}/images", ok404=True) or {}).get("results", []),
                  key=lambda x: x.get("rank", 0))
    vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results", [])
    files = (api.get(f"/shops/{shop}/listings/{lid}/files", ok404=True) or {}).get("results", [])
    inv = api.get(f"/listings/{lid}/inventory", ok404=True) or {}
    if len(imgs) != N_IMAGES:
        issues.append(f"gorsel {len(imgs)}")
    else:
        if [i.get("rank") for i in imgs] != list(range(1, N_IMAGES + 1)):
            issues.append("rank sirasi " + ",".join(str(i.get("rank")) for i in imgs))
        bad = [f"{i.get('full_width')}x{i.get('full_height')}" for i in imgs
               if (i.get("full_width"), i.get("full_height")) != (IMG_W, IMG_H)]
        if bad:
            issues.append("gorsel olcu " + ";".join(bad))
    if expect_video and len(vids) != 1:
        issues.append(f"video {len(vids)}")
    names = sorted(f.get("filename", "") for f in files)
    want = sorted([f"AstroLove_{pair}_{ed}.zip" for ed in EDITIONS] + [PDF_NAME])
    if names != want:
        issues.append(f"dosya {len(files)}: {','.join(names)[:80]}")
    s1, s2 = pair.split("_", 1)
    want_title = TITLE_TPL.format(Sign1=s1.capitalize(), Sign2=s2.capitalize())
    if (listing.get("title") or "").strip() != want_title:
        issues.append("baslik")
    price = money(listing.get("price"))
    try:
        price = price or money(inv["products"][0]["offerings"][0]["price"])
    except (KeyError, IndexError, TypeError):
        pass
    if price != PRICE:
        issues.append(f"fiyat {price}")
    if int(listing.get("shop_section_id") or 0) != SECTION:
        issues.append(f"bolum {listing.get('shop_section_id')}")
    want_state = "active" if pair == PILOT_PAIR else "draft"
    if listing.get("state") != want_state:
        issues.append(f"state {listing.get('state')} (beklenen {want_state})")
    return dict(pair=pair, listing_id=lid, state=listing.get("state"), images=len(imgs), videos=len(vids),
                files=len(files), price=price, section=listing.get("shop_section_id"),
                ok=not issues, detail="; ".join(issues))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pairs", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--expect-video", default="true")
    a = ap.parse_args()
    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    rows = read_state(a.state)
    if a.pairs:
        want = {p.strip() for p in a.pairs.split(",") if p.strip()}
        rows = [r for r in rows if r[0] in want]
    if a.limit:
        rows = rows[:a.limit]
    expect_video = a.expect_video.lower() == "true"
    log(f"{len(rows)} ilan dogrulanacak (video beklenen: {expect_video})")
    out = []
    t0 = time.time(); last_token = time.time()
    for i, (pair, lid) in enumerate(rows):
        if time.time() - last_token > TOKEN_REFRESH_S:
            store.refresh(); last_token = time.time()
        r = check(api, shop, pair, lid, expect_video)
        out.append(r)
        el = time.time() - t0
        log(f"[{i + 1}/{len(rows)}] {pair} {lid}: {'PASS' if r['ok'] else 'FAIL ' + r['detail']} | "
            f"gecen {el / 60:.1f} dk kalan {el / (i + 1) * (len(rows) - i - 1) / 60:.1f} dk | kota {api.remaining}")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["pair", "listing_id", "state", "images", "videos", "files", "price", "section", "sonuc", "detay"])
        for r in out:
            w.writerow([r.get("pair"), r.get("listing_id"), r.get("state"), r.get("images"), r.get("videos"),
                        r.get("files"), r.get("price"), r.get("section"), "PASS" if r["ok"] else "FAIL", r.get("detail", "")])
    n_ok = sum(1 for r in out if r["ok"])
    fails = [r["pair"] for r in out if not r["ok"]]
    log(f"SONUC asama f: {n_ok}/{len(out)} PASS" + (f" | FAIL: {','.join(fails)}" if fails else "")
        + f" | api cagri {api.calls} | kalan kota {api.remaining} | {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC")
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write(f"## son dogrulama: {n_ok}/{len(out)} PASS\n\n" + (f"FAIL: {', '.join(fails)}\n" if fails else "")
                     + f"- kalan kota: {api.remaining}\n")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
