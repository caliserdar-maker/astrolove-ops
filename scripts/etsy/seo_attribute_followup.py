#!/usr/bin/env python3
"""78 wallpaper taxonomy/property takip denetimi. Yalniz Etsy GET kullanir."""
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

TAXONOMY_ID = 2078
SECTION_ID = 60120017
EXPECTED = 78


def walk(nodes, parents=None):
    parents = parents or []
    for node in nodes or []:
        name = str(node.get("name") or "")
        path = parents + [name]
        yield int(node.get("id") or 0), path
        yield from walk(node.get("children") or [], path)


def prop_map(results):
    out = {}
    for p in results or []:
        name = str(p.get("name") or p.get("property_name") or p.get("property_id"))
        values = [str(v.get("name") or "") for v in (p.get("possible_values") or [])]
        out[name] = {
            "property_id": p.get("property_id"),
            "supports_variations": bool(p.get("supports_variations")),
            "possible_values": values,
        }
    return out


def main():
    out_dir = Path(os.environ.get("OUT_DIR", "_out"))
    out_dir.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("ETSY_API_KEY", "")
    secret = os.environ.get("ETSY_SHARED_SECRET", "")
    shop = os.environ["ETSY_SHOP_ID"]
    mask(key)
    mask(secret)
    store = TokenStore(os.environ["TOKEN_FILE"], key, secret)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    tree = api.get("/seller-taxonomy/nodes") or {}
    paths = dict(walk(tree.get("results") or []))
    taxonomy_path = paths.get(TAXONOMY_ID, [])
    taxonomy_props = prop_map(
        (api.get(f"/seller-taxonomy/nodes/{TAXONOMY_ID}/properties") or {}).get("results") or []
    )

    listings = []
    offset = 0
    while True:
        page = api.get(
            f"/shops/{shop}/listings",
            params={"state": "active", "limit": 100, "offset": offset},
        ) or {}
        got = page.get("results") or []
        listings.extend(got)
        if len(got) < 100:
            break
        offset += 100

    wallpapers = [
        x for x in listings
        if int(x.get("shop_section_id") or 0) == SECTION_ID
    ]
    rows = []
    schemas = Counter()
    failures = []
    for listing in wallpapers:
        lid = str(listing.get("listing_id") or "")
        # Shop listing collection omits the `type` field. Read the full listing
        # before validating download/physical type; this remains GET-only.
        full = api.get(f"/listings/{lid}") or {}
        props = (api.get(f"/shops/{shop}/listings/{lid}/properties", ok404=True) or {}).get("results") or []
        names = sorted(str(p.get("property_name") or p.get("name") or p.get("property_id")) for p in props)
        schema = " | ".join(names) if names else "(empty)"
        schemas[schema] += 1
        core = {
            "taxonomy": int(full.get("taxonomy_id") or listing.get("taxonomy_id") or 0) == TAXONOMY_ID,
            "section": int(full.get("shop_section_id") or listing.get("shop_section_id") or 0) == SECTION_ID,
            "type": full.get("type") == "download",
            "state": full.get("state") == "active",
        }
        if not all(core.values()):
            failures.append({"listing_id": lid, "core": core})
        rows.append({
            "listing_id": lid,
            "taxonomy_id": full.get("taxonomy_id") or listing.get("taxonomy_id"),
            "shop_section_id": full.get("shop_section_id") or listing.get("shop_section_id"),
            "type": full.get("type"),
            "state": full.get("state"),
            "properties": names,
            "schema": schema,
            "core_pass": all(core.values()),
        })

    status = "PASS" if len(wallpapers) == EXPECTED and not failures and taxonomy_path else "FAIL"
    result = {
        "status": status,
        "mode": "READ_ONLY_GET",
        "etsy_writes": 0,
        "expected_wallpapers": EXPECTED,
        "wallpaper_count": len(wallpapers),
        "taxonomy_id": TAXONOMY_ID,
        "taxonomy_path": taxonomy_path,
        "taxonomy_properties": taxonomy_props,
        "listing_property_schemas": dict(schemas),
        "core_failures": failures,
        "rows": rows,
        "remaining_quota": api.remaining,
        "decision": (
            "NO_CONFIRMED_ERROR; ATTRIBUTE_OPPORTUNITY_REQUIRES_RELEVANCE_DECISION"
            if status == "PASS" else "STOP_REVIEW"
        ),
    }
    (out_dir / "wallpaper_taxonomy_property_audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        "# Wallpaper taxonomy/property salt-okur denetimi",
        "",
        f"- Durum: **{status}**",
        f"- Etsy yazma: **0**",
        f"- Wallpaper: **{len(wallpapers)}/{EXPECTED}**",
        f"- Taxonomy: **{TAXONOMY_ID}** — {' > '.join(taxonomy_path) or 'YOL BULUNAMADI'}",
        f"- Desteklenen property sayisi: **{len(taxonomy_props)}**",
        f"- Canli property semalari: **{dict(schemas)}**",
        f"- Core sapma: **{len(failures)}**",
        f"- Kota kalan: **{api.remaining}**",
        "",
        "Bos property degeri otomatik hata sayilmadi; yalniz taxonomy destegi ve urun ilgisiyle karar verilecek.",
    ]
    (out_dir / "wallpaper_taxonomy_property_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
