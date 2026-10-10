#!/usr/bin/env python3
"""Etsy organik arama incelemesi icin 78 aktif ilanin SALT OKUR dokumu (10 Eki 2026, etsy-arama oturumu).

Yalniz ``Etsy.get``. Ilan, reklam, magaza ayari degistirmez.
Okunan: aktif ilanlar (baslik, 13 etiket, kategori, malzeme, stil, kisisellestirme, goruntulenme, favori),
her ilanin nitelikleri, kategori agaci adi, kategorinin doldurulabilir nitelikleri, magaza bolumleri.
Cikti: canli_78.csv / canli_78.json / kategori_nitelik.json / ozet.md
"""
import argparse
import csv
import html
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from seo_live_snapshot import list_active, property_map, zodiac_pair  # noqa: E402


def taxonomy_paths(nodes):
    out = {}

    def walk(items, prefix):
        for n in items or []:
            path = prefix + [n.get("name") or str(n.get("id"))]
            out[n.get("id")] = " > ".join(path)
            walk(n.get("children"), path)

    walk(nodes, [])
    return out


def ts(value):
    try:
        return datetime.fromtimestamp(int(value), timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return ""


def build_row(listing, props_raw, tax_names, sections):
    title = html.unescape(listing.get("title") or "")
    props = property_map(props_raw)
    tags = [html.unescape(str(x)) for x in (listing.get("tags") or [])]
    return {
        "listing_id": str(listing.get("listing_id") or ""),
        "zodiac_pair": zodiac_pair(title),
        "title": title,
        "title_len": len(title),
        "tags": " | ".join(tags),
        "tag_count": len(tags),
        "taxonomy_id": listing.get("taxonomy_id") or "",
        "taxonomy_path": tax_names.get(listing.get("taxonomy_id"), ""),
        "materials": " | ".join(html.unescape(str(x)) for x in (listing.get("materials") or [])),
        "style": " | ".join(html.unescape(str(x)) for x in (listing.get("style") or [])),
        "shop_section": sections.get(listing.get("shop_section_id"), str(listing.get("shop_section_id") or "")),
        "listing_type": listing.get("listing_type") or "",
        "who_made": listing.get("who_made") or "",
        "when_made": listing.get("when_made") or "",
        "is_personalizable": listing.get("is_personalizable"),
        "personalization_is_required": listing.get("personalization_is_required"),
        "personalization_instructions": html.unescape(listing.get("personalization_instructions") or ""),
        "has_variations": listing.get("has_variations"),
        "views": listing.get("views"),
        "num_favorers": listing.get("num_favorers"),
        "featured_rank": listing.get("featured_rank"),
        "created": ts(listing.get("original_creation_timestamp") or listing.get("created_timestamp")),
        "state_since": ts(listing.get("state_timestamp")),
        "last_modified": ts(listing.get("last_modified_timestamp") or listing.get("updated_timestamp")),
        "url": listing.get("url") or "",
        "description_first300": html.unescape(listing.get("description") or "")[:300],
        "description_len": len(listing.get("description") or ""),
        "property_count": len(props),
        "properties_json": json.dumps(props, ensure_ascii=False, sort_keys=True),
    }


def run(api, shop, out, expected):
    out.mkdir(parents=True, exist_ok=True)
    listings = list_active(api, shop)
    log(f"aktif ilan {len(listings)} | kota {api.remaining}")
    tree = (api.get("/seller-taxonomy/nodes") or {}).get("results") or []
    tax_names = taxonomy_paths(tree)
    sec = (api.get(f"/shops/{shop}/sections") or {}).get("results") or []
    sections = {s.get("shop_section_id"): s.get("title") or "" for s in sec}
    tax_props = {}
    for tid in sorted({x.get("taxonomy_id") for x in listings if x.get("taxonomy_id")}):
        res = (api.get(f"/seller-taxonomy/nodes/{tid}/properties", ok404=True) or {}).get("results") or []
        tax_props[str(tid)] = {
            "path": tax_names.get(tid, ""),
            "properties": [
                {"name": p.get("name") or p.get("display_name"), "required": p.get("is_required"),
                 "multi": p.get("is_multivalued"),
                 "values": [v.get("name") for v in (p.get("possible_values") or [])][:80]}
                for p in res
            ],
        }
    rows = []
    for i, listing in enumerate(listings, 1):
        lid = listing.get("listing_id")
        props = (api.get(f"/shops/{shop}/listings/{lid}/properties", ok404=True) or {}).get("results") or []
        rows.append(build_row(listing, props, tax_names, sections))
        if i % 20 == 0 or i == len(listings):
            log(f"ilerleme {i}/{len(listings)} ({100 * i // len(listings)}%) | kota {api.remaining}")
    rows.sort(key=lambda r: (r["zodiac_pair"], r["listing_id"]))
    with (out / "canli_78.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (out / "canli_78.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "kategori_nitelik.json").write_text(json.dumps(tax_props, ensure_ascii=False, indent=1) + "\n",
                                               encoding="utf-8")
    pnames = Counter()
    for r in rows:
        pnames.update(json.loads(r["properties_json"]).keys())
    status = "PASS" if len(rows) == expected else "COUNT_MISMATCH"
    lines = [
        "# Etsy arama incelemesi: canli 78 ilan (salt okur)",
        f"- Durum: {status} ({len(rows)} / beklenen {expected})",
        f"- API: yalniz GET, {api.calls} cagri, kota {api.remaining}",
        f"- Kategori: {dict(Counter(r['taxonomy_path'] for r in rows))}",
        f"- Bolum: {dict(Counter(r['shop_section'] for r in rows))}",
        f"- Etiket sayisi dagilimi: {dict(Counter(r['tag_count'] for r in rows))}",
        f"- Malzeme dolu: {sum(bool(r['materials']) for r in rows)} | Stil dolu: {sum(bool(r['style']) for r in rows)}",
        f"- Kisisellestirilebilir: {sum(bool(r['is_personalizable']) for r in rows)}",
        f"- Nitelik adlari: {dict(pnames)}",
    ]
    (out / "ozet.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--expected-count", type=int, default=78)
    a = ap.parse_args()
    key, secret, shop = (os.environ.get(k, "") for k in ("ETSY_API_KEY", "ETSY_SHARED_SECRET", "ETSY_SHOP_ID"))
    if not key or not secret or not shop or not os.environ.get("TOKEN_FILE"):
        raise SystemExit("HATA: Etsy ortam degiskenleri eksik")
    mask(key)
    mask(secret)
    store = TokenStore(os.environ["TOKEN_FILE"], key, secret)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    status = run(api, shop, Path(a.out), a.expected_count)
    log(f"SONUC: {status}; Etsy yazma cagrisi 0")


if __name__ == "__main__":
    main()
