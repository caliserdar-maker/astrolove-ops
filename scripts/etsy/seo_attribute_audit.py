#!/usr/bin/env python3
"""Build a read-only category and attribute deviation report from a live snapshot.

The only Etsy calls are GET requests for the seller taxonomy tree and the
property definitions of taxonomy IDs already present in the snapshot.
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

FIELDS = [
    ("primary_color", ("Primary color", "Color", "Primary colour", "Colour")),
    ("material", ("Material multi", "Material")),
    ("framing", ("Framing",)),
    ("orientation", ("Orientation",)),
    ("number_of_pieces", ("Number of pieces included", "Number of pieces")),
    ("room", ("Room",)),
]

COLOR_BY_EDITION = {
    "Champagne Ivory": "Beige",
    "Warm Parchment": "Beige",
    "Deep Black": "Black",
    "Midnight Blue": "Blue",
    "Pure White": "White",
}


def taxonomy_rows(nodes, parents=()):
    rows = []
    for node in nodes or []:
        name = str(node.get("name") or "").strip()
        path = parents + ((name,) if name else ())
        node_id = node.get("id")
        if node_id is not None:
            rows.append({"taxonomy_id": str(node_id), "taxonomy_path": " > ".join(path)})
        rows.extend(taxonomy_rows(node.get("children") or [], path))
    return rows


def property_names(schema):
    return {
        str(item.get("display_name") or item.get("name") or item.get("property_name") or "").strip()
        for item in schema or []
        if str(item.get("display_name") or item.get("name") or item.get("property_name") or "").strip()
    }


def selected_value(props, aliases):
    wanted = {x.casefold() for x in aliases}
    for key, values in props.items():
        if key.casefold() in wanted:
            return " | ".join(str(x) for x in values)
    return ""


def supported(names, aliases):
    folded = {x.casefold() for x in names}
    return any(x.casefold() in folded for x in aliases)


def semantic_category_status(family, path, wallpaper_candidates):
    p = path.casefold()
    if not path:
        return "REVIEW_MISSING_TAXONOMY_PATH"
    if family == "POD baski":
        return "PASS" if ("print" in p or "gicl" in p) else "REVIEW_CATEGORY_SEMANTICS"
    if family == "Digital wall art":
        return "PASS" if ("digital" in p or "print" in p or "art" in p) else "REVIEW_CATEGORY_SEMANTICS"
    if family == "Digital wallpaper":
        if any(term in p for term in ("wallpaper", "phone", "screen", "background")):
            return "PASS"
        if "digital" in p:
            return "REVIEW_GENERIC_DIGITAL_CATEGORY"
        return "REVIEW_WALLPAPER_CATEGORY" if wallpaper_candidates else "REVIEW_NO_DEDICATED_CANDIDATE"
    return "REVIEW_UNKNOWN_FAMILY"


def value_check(row, props):
    issues = []
    family = row["product_family"]
    if family == "Digital wall art":
        expected = COLOR_BY_EDITION.get(row.get("edition") or "")
        actual = selected_value(props, FIELDS[0][1])
        if expected and actual != expected:
            issues.append(f"primary_color expected={expected} actual={actual or 'BLANK'}")
    elif family == "POD baski":
        checks = {
            "framing": ("Unframed", FIELDS[2][1]),
            "orientation": ("Vertical", FIELDS[3][1]),
            "number_of_pieces": ("1", FIELDS[4][1]),
        }
        for label, (expected, aliases) in checks.items():
            actual = selected_value(props, aliases)
            if actual != expected:
                issues.append(f"{label} expected={expected} actual={actual or 'BLANK'}")
        material = selected_value(props, FIELDS[1][1])
        if "paper" not in material.casefold():
            issues.append(f"material expected~Paper actual={material or 'BLANK'}")
    return issues


def run(api, snapshot_path, out_dir, expected_count=546):
    rows = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if len(rows) != expected_count or len({str(r.get('listing_id')) for r in rows}) != expected_count:
        raise SystemExit(f"HATA: snapshot kapsamı {len(rows)}; beklenen benzersiz {expected_count}")

    tree = api.get("/seller-taxonomy/nodes") or {}
    nodes = taxonomy_rows(tree.get("results") or [])
    path_by_id = {x["taxonomy_id"]: x["taxonomy_path"] for x in nodes}
    wallpaper_candidates = [
        x for x in nodes
        if re.search(r"wallpaper|phone|screen|desktop|digital background", x["taxonomy_path"], re.I)
    ]

    taxonomy_ids = sorted({str(r.get("taxonomy_id") or "") for r in rows if r.get("taxonomy_id")})
    schema_by_id = {}
    raw_schema_by_id = {}
    for taxonomy_id in taxonomy_ids:
        response = api.get(f"/seller-taxonomy/nodes/{taxonomy_id}/properties") or {}
        schema = response.get("results") or []
        raw_schema_by_id[taxonomy_id] = schema
        schema_by_id[taxonomy_id] = property_names(schema)

    audit_rows = []
    for row in rows:
        taxonomy_id = str(row.get("taxonomy_id") or "")
        path = path_by_id.get(taxonomy_id, "")
        schema_names = schema_by_id.get(taxonomy_id, set())
        props = json.loads(row.get("properties_json") or "{}")
        field_status = {}
        for field, aliases in FIELDS:
            value = selected_value(props, aliases)
            if value:
                field_status[field] = f"SET: {value}"
            elif supported(schema_names, aliases):
                field_status[field] = "SUPPORTED_BLANK"
            else:
                field_status[field] = "NOT_SUPPORTED"

        category_status = semantic_category_status(row["product_family"], path, wallpaper_candidates)
        issues = value_check(row, props)
        supported_blanks = [k for k, v in field_status.items() if v == "SUPPORTED_BLANK"]
        if issues:
            overall = "ERROR_VALUE_MISMATCH"
        elif category_status != "PASS" or supported_blanks:
            overall = "REVIEW"
        else:
            overall = "PASS"
        audit_rows.append({
            "listing_id": str(row["listing_id"]),
            "product_family": row["product_family"],
            "zodiac_pair": row.get("zodiac_pair") or "",
            "edition": row.get("edition") or "",
            "taxonomy_id": taxonomy_id,
            "taxonomy_path": path,
            "category_status": category_status,
            **field_status,
            "value_issues": " | ".join(issues),
            "overall_status": overall,
            "url": row.get("url") or "",
        })

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "seo_attribute_deviation_546.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(audit_rows[0]))
        writer.writeheader()
        writer.writerows(audit_rows)

    family_status = defaultdict(Counter)
    for row in audit_rows:
        family_status[row["product_family"]][row["overall_status"]] += 1
    summary = [
        "# AstroLove kategori ve nitelik sapma raporu",
        "",
        f"- Oluşturma (UTC): **{datetime.now(timezone.utc).isoformat()}**",
        f"- Kaynak snapshot: **{len(rows)}/{expected_count} benzersiz aktif ilan**",
        "- Etsy yöntemi: **yalnız GET**",
        f"- Taxonomy API çağrısı: **{api.calls}**",
        "- Etsy yazma işlemi: **0**",
        "",
        "## Sonuç",
        "",
    ]
    for family in sorted(family_status):
        counts = family_status[family]
        summary.append(f"- {family}: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    summary += ["", "## Taxonomy yolları", ""]
    for taxonomy_id in taxonomy_ids:
        summary.append(f"- {taxonomy_id}: {path_by_id.get(taxonomy_id) or 'PATH_NOT_RESOLVED'}")
    summary += ["", "## Wallpaper aday taxonomy yolları", ""]
    if wallpaper_candidates:
        summary.extend(f"- {x['taxonomy_id']}: {x['taxonomy_path']}" for x in wallpaper_candidates)
    else:
        summary.append("- Etsy seller taxonomy ağacında doğrudan wallpaper/phone/screen adayı bulunamadı.")
    summary += [
        "",
        "## Yorumlama kuralı",
        "",
        "- NOT_SUPPORTED: Bu taxonomy alanı sunmuyor; boşluk hata değildir.",
        "- SUPPORTED_BLANK: Alan taxonomy tarafından sunuluyor fakat ilanda seçilmemiş; inceleme gerekir.",
        "- REVIEW: Otomatik canlı düzeltme önerisi değildir; kategori anlamı veya boş desteklenen alan insan kararı gerektirir.",
        "- ERROR_VALUE_MISMATCH: Ürün ailesinin kilitli gerçeğiyle canlı değer uyuşmuyor.",
    ]
    (out_dir / "seo_attribute_deviation_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    (out_dir / "taxonomy_reference.json").write_text(json.dumps({
        "taxonomy_paths": path_by_id,
        "used_taxonomy_ids": taxonomy_ids,
        "property_schemas": raw_schema_by_id,
        "wallpaper_candidates": wallpaper_candidates,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "active_listings": len(rows),
        "unique_listing_ids": len({r["listing_id"] for r in audit_rows}),
        "etsy_write_calls": 0,
        "etsy_get_calls": api.calls,
        "status_counts": {family: dict(counts) for family, counts in family_status.items()},
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return audit_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expected-count", type=int, default=546)
    args = parser.parse_args()
    key = os.environ.get("ETSY_API_KEY", "")
    secret = os.environ.get("ETSY_SHARED_SECRET", "")
    if not key or not secret or not os.environ.get("TOKEN_FILE"):
        raise SystemExit("HATA: Etsy ortam değişkenleri eksik")
    mask(key)
    mask(secret)
    store = TokenStore(os.environ["TOKEN_FILE"], key, secret)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    rows = run(api, Path(args.snapshot), Path(args.out), args.expected_count)
    log(f"SONUC: {len(rows)}/546; Etsy yazma çağrısı 0")


if __name__ == "__main__":
    main()
