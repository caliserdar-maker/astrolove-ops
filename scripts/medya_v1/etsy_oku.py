#!/usr/bin/env python3
"""medya-v1: Etsy SALT OKUR dokum (24 Eyl 2026).

1) Magazadaki tum ilanlarda (her state) basliginda Cancer ve Libra gecenleri
   listeler: id, state, tur, bolum, SKU'lar, foto/video sayisi.
2) REF_ID ve LIVE_ID icin tam dokum (listing, images+alt_text, videos,
   inventory, bolum adi) + tum gorselleri (fullxfull) ve videoyu indirir.

Yalniz GET. Etsy'ye yazan hicbir cagri yoktur (patch/put/post engelli).
Tek yan etki: token yenilenirse ETSY_TOKEN.json guncellenir (workflow geri yazar).
"""
import json
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etsy"))
from etsy_common import Etsy, TokenStore, log  # noqa: E402

OUT = Path(os.environ.get("OUT_DIR", "_out/etsy"))
REF_ID = int(os.environ.get("REF_ID", "4570143815"))
LIVE_ID = int(os.environ.get("LIVE_ID", "4570110121"))
STATES = ("active", "draft", "inactive", "expired", "sold_out")


class ReadOnly(Etsy):
    def _call(self, method, path, **kw):
        if method != "GET":
            raise SystemExit(f"HATA: salt okur istemci {method} {path} reddetti.")
        return super()._call(method, path, **kw)


def eta(i, n, t0, what):
    el = time.time() - t0
    rem = el / i * (n - i) if i else 0
    log(f"  [{i}/{n}] %{100*i/n:.0f} gecen {el:.0f}s kalan ~{rem:.0f}s  {what}")


def all_listings(api, shop):
    rows = []
    for st in STATES:
        off = 0
        while True:
            p = api.get(f"/shops/{shop}/listings",
                        params={"state": st, "limit": 100, "offset": off}) or {}
            res = p.get("results", [])
            rows += res
            off += 100
            if off >= int(p.get("count", 0)) or not res:
                break
        log(f"state={st}: toplam simdiye kadar {len(rows)}")
    return rows


def dump(api, shop, lid, sections, tag):
    d = OUT / f"{tag}_{lid}"
    d.mkdir(parents=True, exist_ok=True)
    listing = api.get(f"/listings/{lid}", ok404=True)
    if listing is None:
        for st in STATES:
            p = api.get(f"/shops/{shop}/listings", params={"state": st, "limit": 100}) or {}
            for it in p.get("results", []):
                if int(it["listing_id"]) == lid:
                    listing = it
    images = api.get(f"/listings/{lid}/images", ok404=True) or \
        api.get(f"/shops/{shop}/listings/{lid}/images", ok404=True) or {}
    videos = api.get(f"/listings/{lid}/videos", ok404=True) or {}
    inv = api.get(f"/listings/{lid}/inventory", ok404=True) or {}
    pers = api.get(f"/listings/{lid}/personalization", ok404=True)
    full = {"listing": listing, "images": images, "videos": videos, "inventory": inv,
            "personalization": pers,
            "section_title": sections.get(listing.get("shop_section_id"))}
    (d / "listing_full.json").write_text(json.dumps(full, indent=2, ensure_ascii=False))
    imgs = sorted(images.get("results", []), key=lambda x: x.get("rank", 0))
    vids = videos.get("results", [])
    jobs = [(f"{im['rank']:02d}_{im['listing_image_id']}.jpg", im["url_fullxfull"]) for im in imgs]
    jobs += [(f"video_{v['video_id']}.mp4", v["video_url"]) for v in vids]
    t0 = time.time()
    for i, (name, url) in enumerate(jobs, 1):
        r = requests.get(url, timeout=180)
        r.raise_for_status()
        (d / name).write_bytes(r.content)
        eta(i, len(jobs), t0, f"{tag} {name} {len(r.content)//1024} KB")
    # ozet
    prods = inv.get("products", [])
    sizes = []
    for p in prods:
        vals = " / ".join(f"{pv.get('property_name')}={','.join(pv.get('values', []))}"
                          for pv in p.get("property_values", []))
        sizes.append((p.get("sku"), vals, p["offerings"][0]["price"]["amount"] /
                      p["offerings"][0]["price"]["divisor"] if p.get("offerings") else None))
    summ = {
        "listing_id": lid, "state": listing.get("state"), "title": listing.get("title"),
        "listing_type": listing.get("listing_type"), "is_digital": listing.get("is_digital"),
        "shop_section_id": listing.get("shop_section_id"),
        "section_title": sections.get(listing.get("shop_section_id")),
        "is_personalizable": listing.get("is_personalizable"),
        "personalization_is_required": listing.get("personalization_is_required"),
        "personalization_char_count_max": listing.get("personalization_char_count_max"),
        "personalization_instructions": listing.get("personalization_instructions"),
        "tags": listing.get("tags"), "num_images": len(imgs), "num_videos": len(vids),
        "image_dims": [f"{im.get('full_width')}x{im.get('full_height')}" for im in imgs],
        "alt_texts": [im.get("alt_text") for im in imgs],
        "num_products": len(prods), "skus": sorted({s for s, _, _ in sizes if s}),
        "variants": sizes,
    }
    (d / "summary.json").write_text(json.dumps(summ, indent=2, ensure_ascii=False))
    log(json.dumps({k: summ[k] for k in summ if k not in ("variants", "alt_texts")},
                   ensure_ascii=False))
    for s in sizes:
        log(f"    varyant: {s}")
    return summ


def main():
    store = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                       os.environ.get("ETSY_SHARED_SECRET"))
    if store.needs_refresh():
        store.refresh()
    api = ReadOnly(store)
    shop = os.environ["ETSY_SHOP_ID"]
    OUT.mkdir(parents=True, exist_ok=True)
    sec = api.get(f"/shops/{shop}/sections") or {}
    sections = {s["shop_section_id"]: s["title"] for s in sec.get("results", [])}
    rows = all_listings(api, shop)
    cl = [r for r in rows if "cancer" in (r.get("title") or "").lower()
          and "libra" in (r.get("title") or "").lower()]
    log(f"\n=== Basliginda Cancer+Libra gecen ilanlar: {len(cl)} (toplam {len(rows)}) ===")
    table = []
    for r in cl:
        row = {"listing_id": r["listing_id"], "state": r.get("state"),
               "listing_type": r.get("listing_type"), "is_digital": r.get("is_digital"),
               "section": sections.get(r.get("shop_section_id")), "sku": r.get("skus") or r.get("sku"),
               "title": r.get("title")}
        table.append(row)
        log(json.dumps(row, ensure_ascii=False))
    (OUT / "cancer_libra_listings.json").write_text(json.dumps(table, indent=2, ensure_ascii=False))
    (OUT / "sections.json").write_text(json.dumps(sections, indent=2, ensure_ascii=False))
    log("\n=== REFERANS ===")
    dump(api, shop, REF_ID, sections, "REF")
    log("\n=== KOVA-KOVA CANLI ===")
    dump(api, shop, LIVE_ID, sections, "LIVE")
    # Referans adaylari: Cancer+Libra fiziksel ilanlarin SKU'lari
    log("\n=== Cancer+Libra adaylarinin SKU kontrolu ===")
    for r in cl:
        if r["listing_id"] in (REF_ID,):
            continue
        inv = api.get(f"/listings/{r['listing_id']}/inventory", ok404=True) or {}
        skus = sorted({p.get("sku") for p in inv.get("products", []) if p.get("sku")})
        log(f"  {r['listing_id']} state={r.get('state')} tur={r.get('listing_type')} "
            f"sku_ornek={skus[:3]} sku_sayisi={len(skus)}")
    log(f"Etsy cagri sayisi: {api.calls}, kalan kota: {api.remaining}")


if __name__ == "__main__":
    main()
