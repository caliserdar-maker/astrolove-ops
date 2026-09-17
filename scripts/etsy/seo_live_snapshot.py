#!/usr/bin/env python3
"""AstroLove SEO icin tum aktif Etsy ilanlarini ve niteliklerini SALT OKUR alir.

Yalniz ``Etsy.get`` kullanir. Etsy'de ilan, reklam veya magaza ayari degistirmez.
Cikti: ``seo_live_snapshot.csv/json``, ``seo_live_summary.md`` ve ``manifest.json``.
"""
import argparse
import csv
import hashlib
import html
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_RX = re.compile(r"(?<![A-Za-z])(" + "|".join(SIGNS) + r")(?![A-Za-z])", re.I)
EDITIONS = ["Champagne Ivory", "Pure White", "Warm Parchment", "Midnight Blue", "Deep Black"]


def family(listing):
    title = listing.get("title") or ""
    if listing.get("listing_type") == "physical":
        return "POD baski"
    if re.search(r"wallpaper", title, re.I):
        return "Digital wallpaper"
    if listing.get("listing_type") == "download":
        return "Digital wall art"
    return f"Diger ({listing.get('listing_type') or 'bilinmiyor'})"


def zodiac_pair(title):
    signs = [m.group(1).upper() for m in SIGN_RX.finditer(title or "")][:2]
    return "_".join(sorted(signs)) if len(signs) == 2 else ""


def edition(title, product_family):
    for name in EDITIONS:
        if re.search(re.escape(name), title or "", re.I):
            return name
    if product_family == "Digital wallpaper":
        return "4 renk (tek ilan)"
    if product_family == "POD baski":
        return "5 renk (varyasyon)"
    return ""


def property_map(properties):
    out = {}
    for prop in properties or []:
        name = (prop.get("property_name") or str(prop.get("property_id") or "")).strip()
        values = [html.unescape(str(v)).strip() for v in (prop.get("values") or []) if str(v).strip()]
        out[name] = values
    return out


def find_property(props, *names):
    wanted = {x.casefold() for x in names}
    for key, values in props.items():
        if key.casefold() in wanted:
            return " | ".join(values)
    return ""


def list_active(api, shop, max_pages=12):
    rows, offset = [], 0
    for _ in range(max_pages):
        response = api.get(
            f"/shops/{shop}/listings",
            params={"state": "active", "limit": 100, "offset": offset},
        ) or {}
        page = response.get("results") or []
        rows.extend(page)
        if len(page) < 100:
            return rows
        offset += 100
    raise SystemExit(f"HATA: aktif ilan sayfalama {max_pages} sayfada bitmedi")


def remaining_int(api):
    try:
        return int(api.remaining)
    except (TypeError, ValueError):
        return None


def build_row(listing, properties):
    title = html.unescape(listing.get("title") or "")
    product_family = family(listing)
    props = property_map(properties)
    return {
        "listing_id": str(listing.get("listing_id") or ""),
        "product_family": product_family,
        "zodiac_pair": zodiac_pair(title),
        "edition": edition(title, product_family),
        "title": title,
        "description": html.unescape(listing.get("description") or ""),
        "tags": " | ".join(html.unescape(str(x)) for x in (listing.get("tags") or [])),
        "tag_count": len(listing.get("tags") or []),
        "taxonomy_id": listing.get("taxonomy_id") or "",
        "shop_section_id": listing.get("shop_section_id") or "",
        "listing_type": listing.get("listing_type") or "",
        "state": listing.get("state") or "",
        "url": listing.get("url") or "",
        "property_count": len(props),
        "primary_color": find_property(props, "Primary color", "Color", "Primary colour", "Colour"),
        "secondary_color": find_property(props, "Secondary color", "Secondary colour"),
        "orientation": find_property(props, "Orientation"),
        "room": find_property(props, "Room"),
        "style": find_property(props, "Style"),
        "subject": find_property(props, "Subject"),
        "occasion": find_property(props, "Occasion"),
        "recipient": find_property(props, "Recipient"),
        "material_attribute": find_property(props, "Material"),
        "properties_json": json.dumps(props, ensure_ascii=False, sort_keys=True),
    }


def write_outputs(rows, out, expected_count, api, quota_start):
    out.mkdir(parents=True, exist_ok=True)
    rows.sort(key=lambda r: (r["product_family"], r["zodiac_pair"], r["edition"], r["listing_id"]))
    fields = list(rows[0]) if rows else []
    with (out / "seo_live_snapshot.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    json_text = json.dumps(rows, ensure_ascii=False, indent=1)
    (out / "seo_live_snapshot.json").write_text(json_text + "\n", encoding="utf-8")
    digest = hashlib.sha256(json_text.encode("utf-8")).hexdigest()

    families = Counter(r["product_family"] for r in rows)
    property_names = Counter()
    for row in rows:
        property_names.update(json.loads(row["properties_json"]).keys())
    missing_color = Counter(
        r["product_family"] for r in rows if not r["primary_color"] and not r["secondary_color"]
    )
    missing_pair = sum(not r["zodiac_pair"] for r in rows)
    bad_tags = sum(r["tag_count"] != 13 for r in rows)
    status = "PASS" if len(rows) == expected_count else "COUNT_MISMATCH"
    summary = [
        "# AstroLove canlı Etsy SEO snapshot",
        "",
        f"- Durum: **{status}**",
        f"- Aktif ilan: **{len(rows)}** (beklenen {expected_count})",
        f"- API yöntemi: **yalnız GET**",
        f"- API çağrısı: **{api.calls}**",
        f"- Kota: **{quota_start} -> {api.remaining}**",
        f"- SHA-256: `{digest}`",
        f"- Çözülemeyen burç çifti: **{missing_pair}**",
        f"- 13 olmayan etiket seti: **{bad_tags}**",
        "",
        "## Ürün ailesi",
        "",
    ]
    summary.extend(f"- {key}: {value}" for key, value in sorted(families.items()))
    summary += ["", "## Renk niteliği boş olan ilanlar", ""]
    if missing_color:
        summary.extend(f"- {key}: {value}" for key, value in sorted(missing_color.items()))
    else:
        summary.append("- Yok")
    summary += ["", "## Canlı property adları", ""]
    summary.extend(f"- {key}: {value}" for key, value in property_names.most_common())
    (out / "seo_live_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "active_listings": len(rows),
        "expected_listings": expected_count,
        "families": dict(families),
        "api_calls": api.calls,
        "quota_start": quota_start,
        "quota_end": api.remaining,
        "sha256": digest,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return status


def run(api, shop, out, expected_count=546, quota_buffer=60):
    listings = list_active(api, shop)
    quota_start = api.remaining
    remaining = remaining_int(api)
    required = len(listings) + quota_buffer
    if remaining is not None and remaining < required:
        raise SystemExit(
            f"HATA: kota {remaining}; {len(listings)} property GET + {quota_buffer} tampon icin yetersiz. "
            "Property taramasi baslatilmadi."
        )
    rows = []
    for index, listing in enumerate(listings, 1):
        remaining = remaining_int(api)
        if remaining is not None and remaining <= quota_buffer:
            raise SystemExit(f"HATA: kota tamponu {quota_buffer}'a indi; {index - 1}/{len(listings)} okundu")
        listing_id = listing.get("listing_id")
        response = api.get(f"/shops/{shop}/listings/{listing_id}/properties", ok404=True) or {}
        rows.append(build_row(listing, response.get("results") or []))
        if index % 50 == 0 or index == len(listings):
            log(f"property ilerleme {index}/{len(listings)} | kota {api.remaining}")
    return write_outputs(rows, out, expected_count, api, quota_start)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--expected-count", type=int, default=546)
    parser.add_argument("--quota-buffer", type=int, default=60)
    args = parser.parse_args()
    key = os.environ.get("ETSY_API_KEY", "")
    secret = os.environ.get("ETSY_SHARED_SECRET", "")
    shop = os.environ.get("ETSY_SHOP_ID", "")
    if not key or not secret or not shop or not os.environ.get("TOKEN_FILE"):
        raise SystemExit("HATA: Etsy ortam degiskenleri eksik")
    mask(key)
    mask(secret)
    store = TokenStore(os.environ["TOKEN_FILE"], key, secret)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    status = run(api, shop, Path(args.out), args.expected_count, args.quota_buffer)
    log(f"SONUC: {status}; Etsy yazma cagrisi 0")
    if status != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
