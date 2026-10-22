#!/usr/bin/env python3
"""Build the pinned 546-listing factual-correction plan from the audited snapshot."""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

OLD_HEADER = "PREFER IT READY TO HANG?"
NEW_HEADER = "PREFER A PRINTED VERSION?"
ABBR = {"aqu", "ari", "can", "cap", "gem", "lib", "pis", "sag", "sco", "tau", "vir"}


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def norm(value):
    return "\n".join((value or "").replace("\r\n", "\n").splitlines()).strip()


def replace_tags(row, tags):
    family = row["product_family"]
    pair = row["zodiac_pair"]
    out = []
    for tag in tags:
        words = set(re.findall(r"[a-z]+", tag.casefold()))
        if family == "Digital wallpaper" and tag.casefold() == "zodiac compatibility":
            new = "digital wallpaper"
        elif family == "POD baski" and tag.casefold() == "compatibility print":
            new = "fine art print"
        elif words & ABBR:
            if tag.casefold().endswith("gift"):
                new = "couple gift"
            elif tag.casefold().endswith("zodiac"):
                signs = pair.split("_")
                new = f"{signs[0].title()} zodiac" if len(set(signs)) == 1 else "zodiac couple"
            elif family == "Digital wall art" and tag.casefold() == "capricorn sag art":
                new = "zodiac couple"
            else:
                raise ValueError(f"{row['listing_id']}: bilinmeyen kisaltmali etiket: {tag}")
        else:
            new = tag
        out.append(new.casefold())
    return out


def build(rows, source_sha):
    plan = []
    for row in rows:
        old_desc = norm(row["current_description"])
        if row["product_family"] == "Digital wall art":
            if old_desc.count(OLD_HEADER) != 1:
                raise ValueError(f"{row['listing_id']}: aciklama basligi sayisi 1 degil")
            new_desc = old_desc.replace(OLD_HEADER, NEW_HEADER, 1)
        else:
            new_desc = old_desc
        old_tags = [x.strip().casefold() for x in row["current_tags"].split(" | ") if x.strip()]
        new_tags = replace_tags(row, old_tags)
        if len(old_tags) != 13 or len(new_tags) != 13:
            raise ValueError(f"{row['listing_id']}: etiket sayisi 13 degil")
        if len(set(new_tags)) != 13 or any(len(x) > 20 for x in new_tags):
            raise ValueError(f"{row['listing_id']}: hedef etiket QC FAIL: {new_tags}")
        title = norm(row["current_title"])
        plan.append({
            "listing_id": row["listing_id"],
            "product_family": row["product_family"],
            "zodiac_pair": row["zodiac_pair"],
            "title_sha256": digest(title),
            "description_before_sha256": digest(old_desc),
            "description_after_sha256": digest(new_desc),
            "description_replace": OLD_HEADER if old_desc != new_desc else "",
            "tags_before": old_tags,
            "tags_after": new_tags,
        })
    plan.sort(key=lambda x: int(x["listing_id"]))
    stats = {
        "listings": len(plan),
        "description_changes": sum(x["description_before_sha256"] != x["description_after_sha256"] for x in plan),
        "tag_listing_changes": sum(x["tags_before"] != x["tags_after"] for x in plan),
        "wallpaper_false_compatibility": sum(x["product_family"] == "Digital wallpaper" and x["tags_before"] != x["tags_after"] for x in plan),
        "pod_false_compatibility": sum(x["product_family"] == "POD baski" and x["tags_before"] != x["tags_after"] for x in plan),
        "abbreviation_listings": sum(any(set(re.findall(r"[a-z]+", t)) & ABBR for t in x["tags_before"]) for x in plan),
    }
    expected = {"listings": 546, "description_changes": 390, "tag_listing_changes": 161,
                "wallpaper_false_compatibility": 78, "pod_false_compatibility": 78,
                "abbreviation_listings": 24}
    if stats != expected:
        raise ValueError(f"plan sayimlari uyusmuyor: {stats} != {expected}")
    return {"schema": 1, "source_sha256": source_sha, "stats": stats, "rows": plan}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit-csv", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    source = Path(args.audit_csv)
    source_bytes = source.read_bytes()
    with source.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    payload = build(rows, hashlib.sha256(source_bytes).hexdigest())
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(payload["stats"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
