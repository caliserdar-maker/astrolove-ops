#!/usr/bin/env python3
"""CSV-driven Etsy listing structure v2 writer (two or three variations).

The live listing and inventory are always fetched before a plan is built.  Dry
run never writes; write mode requires ``--confirm YAPI_V2``.
"""
import argparse
import csv
import html
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "etsy")]
import pod_pilot_15 as pilot  # noqa: E402
from pod_sku import MAX_LEN, parse_sku  # noqa: E402

OUT = Path("out")
COLORS = "primary color"
PERSONALIZATION = ("is_personalizable", "personalization_is_required",
                   "personalization_char_count_max", "personalization_instructions")
CSV_FIELDS = {"mod", "sira", "etiket", "format", "tur", "boy", "cerceve",
              "fiyat", "sku_ek", "aktif"}


def money(value):
    if isinstance(value, dict):
        return round(float(value.get("amount", 0)) / float(value.get("divisor", 100)), 2)
    return round(float(value), 2)


def normalize(text):
    return html.unescape(text or "").replace("\r\n", "\n").strip()


def property_value(product, name):
    return next((p for p in product.get("property_values", [])
                 if (p.get("property_name") or "").lower() == name), None)


def value(product, name):
    prop = property_value(product, name)
    return ((prop or {}).get("values") or [""])[0]


def copy_property(prop, new_value=None):
    result = {"property_id": prop.get("property_id"),
              "values": [new_value] if new_value is not None else list(prop.get("values") or [])}
    for key in ("property_name", "scale_id"):
        if prop.get(key) is not None:
            result[key] = prop[key]
    if new_value is None and prop.get("value_ids"):
        result["value_ids"] = list(prop["value_ids"])
    return result


def copy_offering(offering, price, enabled):
    result = {"price": price, "quantity": offering.get("quantity"), "is_enabled": enabled}
    if offering.get("readiness_state_id") is not None:
        result["readiness_state_id"] = offering["readiness_state_id"]
    return result


def load_config(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or []) != CSV_FIELDS:
            raise ValueError(f"CSV basligi tam olarak {','.join(CSV_FIELDS)} alanlarini icermeli")
        rows = list(reader)
    modes = {row["mod"] for row in rows}
    if not modes or not modes <= {"2", "3"}:
        raise ValueError("mod yalniz 2 veya 3 olabilir")
    for row in rows:
        row["fiyat"] = round(float(row["fiyat"]), 2)
        row["aktif"] = row["aktif"] == "1"
        if row["mod"] == "2" and not row["etiket"]:
            raise ValueError("mod=2 satirinda etiket zorunlu")
        if row["mod"] == "3" and not row["format"]:
            raise ValueError("mod=3 satirinda format zorunlu")
    return rows


def sku_for(base_sku, row):
    parsed = parse_sku(base_sku)
    if not parsed:
        # Re-plans can start from a digital/framed product; keep stable prefix.
        parts = (base_sku or "").split("-")
        if len(parts) < 4:
            raise ValueError(f"SKU cozulemedi: {base_sku}")
        prefix = "-".join(parts[:3])
    else:
        pair, edition, _ = parsed
        from pod_sku import ED2, SIGN3
        a, b = pair.split("_", 1)
        prefix = f"POD-{SIGN3[a]}_{SIGN3[b]}-{ED2[edition]}"
    suffix = row["sku_ek"].strip()  # boy yazimi canli SKU ile ayni kalir (8x10, A4)
    sku = f"{prefix}-{suffix}"
    if len(sku) > MAX_LEN:
        raise ValueError(f"SKU cok uzun: {sku}")
    return sku


def build_plan(inventory, config):
    """Build solely from a freshly supplied live inventory snapshot."""
    products = inventory.get("products") or []
    if not products:
        raise ValueError("canli envanter bos")
    modes = {row["mod"] for row in config}
    if len(modes) != 1:
        raise ValueError("CSV tek bir mod icermeli")
    mode = modes.pop()
    rows = sorted(config, key=lambda r: int(r["sira"]))
    if mode == "3":
        # Etsy expects the full Cartesian product.  CSV-listed combinations
        # carry their configured state; absent combinations are explicit,
        # disabled products rather than silently disappearing.
        formats = list(dict.fromkeys(r["format"] for r in rows))
        sizes = list(dict.fromkeys(r["boy"] for r in rows))
        configured = {(r["format"], r["boy"]): r for r in rows}
        expanded = []
        for fmt in formats:
            template = next(r for r in rows if r["format"] == fmt)
            for size in sizes:
                if (fmt, size) in configured:
                    expanded.append(configured[(fmt, size)])
                    continue
                suffix = ("DIGITAL-" + size if template["tur"] == "digital" else
                          size + (f"-F{template['cerceve']}" if template["cerceve"] else ""))
                expanded.append(dict(template, boy=size, sku_ek=suffix, aktif=False))
        rows = expanded
    colors = list(dict.fromkeys(value(p, COLORS) for p in products))
    if not all(colors):
        raise ValueError("Primary color bulunamadi")

    # Preserve each color's live quantity/readiness and use a parseable live SKU.
    exemplars = {}
    existing = {}
    for product in products:
        color = value(product, COLORS)
        if color and color not in exemplars and parse_sku(product.get("sku")):
            exemplars[color] = product
        existing[(color, value(product, "size"), value(product, "format"))] = product
    if set(exemplars) != set(colors):
        raise ValueError("her renk icin standart canli SKU bulunamadi")

    planned = []
    for color in colors:
        sample = exemplars[color]
        color_prop = property_value(sample, COLORS)
        size_prop = property_value(sample, "size")
        if not size_prop:
            raise ValueError("Size property bulunamadi")
        format_prop = property_value(sample, "format")
        for row in rows:
            size = row["etiket"] if mode == "2" else row["boy"]
            fmt = "" if mode == "2" else row["format"]
            matched = existing.get((color, size, fmt))
            old = matched or sample
            offering = (old.get("offerings") or sample.get("offerings"))[0]
            props = [copy_property(color_prop), copy_property(size_prop, size)]
            if mode == "3":
                if not format_prop:
                    # Etsy custom property id used by the live listing must exist.
                    format_prop = next((property_value(p, "format") for p in products
                                        if property_value(p, "format")), None)
                if not format_prop:
                    raise ValueError("mod=3 icin canli Format property bulunamadi")
                props.insert(0, copy_property(format_prop, fmt))
            planned.append({"sku": old.get("sku") if matched else sku_for(sample.get("sku"), row),
                            "property_values": props,
                            "offerings": [copy_offering(offering, row["fiyat"],
                                                         bool(offering.get("is_enabled")) if matched else row["aktif"])]})
    result = {"products": planned}
    for key in ("quantity_on_property", "sku_on_property", "readiness_state_on_property"):
        if inventory.get(key) is not None:
            result[key] = list(inventory[key])
    result["price_on_property"] = ([format_prop["property_id"], size_prop["property_id"]]
                                   if mode == "3" else [size_prop["property_id"]])
    return result


def signature(inventory):
    return sorted((value(p, "format"), value(p, COLORS), value(p, "size"), p.get("sku") or "",
                   money(p["offerings"][0]["price"]), p["offerings"][0].get("quantity"),
                   bool(p["offerings"][0].get("is_enabled")),
                   p["offerings"][0].get("readiness_state_id"))
                  for p in inventory.get("products") or [])


def replace_description(description, size_block, digital_block):
    lines = html.unescape(description or "").replace("\r\n", "\n").split("\n")
    block_heading = size_block.strip().splitlines()[0].strip()
    start = next((i for i, line in enumerate(lines)
                  if line.strip().lstrip("✦").strip().upper().startswith("16 SIZES")
                  or line.strip() == block_heading), None)
    if start is None:
        raise ValueError("aciklamada 16 SIZES bolumu bulunamadi")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip().startswith("✦")), len(lines))
    replacement = size_block.strip().splitlines()
    updated = lines[:start] + replacement + lines[end:]
    if normalize(digital_block) not in normalize("\n".join(updated)):
        updated += ["", *digital_block.strip().splitlines()]
    return "\n".join(updated).strip()


def write_diff(path, before, after):
    old = set(signature(before)); new = set(signature(after))
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle); writer.writerow(["durum", "format", "renk", "boy", "sku", "fiyat", "adet", "enabled"])
        for state, item in [("SILINDI", x) for x in sorted(old-new)] + [("YENI", x) for x in sorted(new-old)]:
            writer.writerow([state, *item[:7]])


def parser():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("kuru", "yaz")); p.add_argument("ilan")
    p.add_argument("--confirm"); p.add_argument("--yalniz", default=""); p.add_argument("--kota-alt", type=int, default=400)
    p.add_argument("--csv", default="data/pod/yapi_v2.csv")
    p.add_argument("--ilan-csv", default="", help="78 POD ilan listesi (ilan_id/listing_id sutunu); hepsi icin zorunlu")
    return p


def main(argv=None, api=None):
    args = parser().parse_args(argv)
    if args.command == "yaz" and args.confirm != "YAPI_V2":
        raise SystemExit("HATA: yaz icin --confirm YAPI_V2 gerekir")
    config = load_config(args.csv)
    if api is None:
        from etsy_common import Etsy, TokenStore, mask
        key, secret = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
        mask(key); mask(secret); store = TokenStore(os.environ["TOKEN_FILE"], key, secret)
        if store.needs_refresh(): store.refresh()
        api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]
    if args.ilan == "hepsi":
        # Magazada pasife alinmayi bekleyen dijital ilanlar olabilir: liste Drive'daki 78 POD dosyasindan gelir.
        if not args.ilan_csv: raise SystemExit("HATA: hepsi icin --ilan-csv gerekir")
        with open(args.ilan_csv, encoding="utf-8-sig") as fh:
            ids = [str(r.get("ilan_id") or r.get("listing_id") or "").strip() for r in csv.DictReader(fh)]
        ids = list(dict.fromkeys(x for x in ids + ["4570143815"] if x))
        if len(ids) != 78: raise SystemExit(f"HATA: 78 POD ilani bekleniyordu, {len(ids)} bulundu")
    else: ids = [args.ilan]
    only = {x.strip() for x in args.yalniz.split(",") if x.strip()}
    if only: ids = [x for x in ids if x in only]
    OUT.mkdir(exist_ok=True); started = time.monotonic(); changed = 0
    size_block = Path("data/pod/aciklama_v2_boy_blok.txt").read_text(encoding="utf-8")
    digital_block = Path("data/pod/aciklama_v2_dijital_blok.txt").read_text(encoding="utf-8")
    for index, listing_id in enumerate(ids, 1):
        # Mandatory live reads precede every plan; no stale PUT draft is accepted.
        listing = api.get(f"/listings/{listing_id}") or {}
        inventory = api.get(f"/listings/{listing_id}/inventory") or {}
        images = (api.get(f"/shops/{shop}/listings/{listing_id}/variation-images", ok404=True) or {}).get("results", [])
        backup = {"listing": listing, "inventory": inventory, "variation_images": images}
        (OUT / f"Y2_{listing_id}_ONCE.json").write_text(json.dumps(backup, ensure_ascii=False, indent=2))
        if listing.get("state") != "active": continue
        plan = build_plan(inventory, config)
        description = replace_description(listing.get("description", ""), size_block, digital_block)
        write_diff(OUT / f"Y2_{listing_id}_DIFF.csv", inventory, plan)
        already = signature(inventory) == signature(plan) and normalize(listing.get("description")) == normalize(description)
        if already: continue
        changed += 1
        if args.command == "yaz":
            if api.remaining is not None and int(api.remaining) < args.kota_alt: raise SystemExit("HATA: kota kapisi")
            before_map = pilot.v_renk_haritasi(inventory, images)
            personal = {k: listing.get(k) for k in PERSONALIZATION}
            api.put_json(f"/listings/{listing_id}/inventory", plan)
            readback = api.get(f"/listings/{listing_id}/inventory") or {}
            if signature(readback) != signature(plan): raise SystemExit("HATA: envanter geri okuma farkli")
            images2 = (api.get(f"/shops/{shop}/listings/{listing_id}/variation-images", ok404=True) or {}).get("results", [])
            if pilot.v_renk_haritasi(readback, images2) != before_map:
                by_color = {value(p, COLORS): property_value(p, COLORS) for p in readback["products"]}
                payload = [{"property_id": p["property_id"], "value_id": p["value_ids"][0], "image_id": int(image)}
                           for color, image in before_map.items() for p in [by_color[color]]]
                api.post_json(f"/shops/{shop}/listings/{listing_id}/variation-images", {"variation_images": payload})
                images3 = (api.get(f"/shops/{shop}/listings/{listing_id}/variation-images", ok404=True) or {}).get("results", [])
                if pilot.v_renk_haritasi(readback, images3) != before_map:
                    raise SystemExit("HATA: renk->gorsel eslesmesi onarilamadi")
            api.patch(f"/shops/{shop}/listings/{listing_id}", {"description": description})
            final = api.get(f"/listings/{listing_id}") or {}
            if normalize(final.get("description")) != normalize(description) or any(final.get(k) != v for k, v in personal.items()):
                raise SystemExit("HATA: aciklama/kisisellestirme geri okuma farkli")
        elapsed = time.monotonic()-started; remaining = elapsed/index*(len(ids)-index)
        print(f"ETA {index}/{len(ids)} %{index/len(ids)*100:.1f} gecen={elapsed:.0f}s kalan={remaining:.0f}s")
    if not changed: return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
