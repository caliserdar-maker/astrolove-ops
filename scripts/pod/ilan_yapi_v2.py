#!/usr/bin/env python3
"""CSV-driven Etsy listing structure v2 writer (two or three variations).

The live listing and inventory are always fetched before a plan is built.  Dry
run never writes; write mode requires ``--confirm YAPI_V2``.
Aciklama PATCH'i varsayilan KAPALI (Serdar 27 Eyl: v3 aciklama pod-seo-v3 ile ayri yazilir);
yalniz ``--aciklama`` ile acilir. Plan yazmadan once docs/REFERANS_ILAN_CL.md fiyat tablosu ve
SKU v3 ile karsilastirilir; birebir degilse DUR.
"""
import re
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
from pod_sku import MAX_LEN, make_sku2, parse_sku  # noqa: E402

OUT = Path("out")
COLORS = "primary color"
FORMAT_ADI = "Digital File, Print or Framed?"
DIJITAL_RENK = "All 5 colors, Digital"  # Serdar 27 Eyl: dijitalde renk secimi yok; OAS: degerlerde parantez yasak
# Menu D (Serdar 27 Eyl): 2 menu; Menu 1 "Format & Color" (ozel property) 26 deger, Menu 2 Size.
MENU1_ADI = "Format & Color"
DIJITAL_D = "Digital File, All 5 Colors"
RENK_SIRA = ["Midnight Blue", "Deep Black", "Pure White", "Champagne Ivory", "Warm Parchment"]
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
    adlar = {name, FORMAT_ADI.lower()} if name == "format" else {name}
    return next((p for p in product.get("property_values", [])
                 if (p.get("property_name") or "").lower() in adlar), None)


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


def build_plan_v3(inventory, rows):
    """Yapi v3 (Serdar 27 Eyl, secenek A): Format x Primary color (5 canli renk + DIJITAL_RENK) x Size, tam kartezyen.
    Digital File yalniz DIJITAL_RENK ile, fiziksel formatlar yalniz 5 renkle acik (is_enabled). SKU RENK ICERMEZ
    (renk siparis varyasyonundan okunur, pod_sku.parse_tx). sku/price_on_property = [format, renk, boy] (a2, Serdar 27 Eyl)."""
    products = inventory["products"]
    colors = list(dict.fromkeys(value(p, COLORS) for p in products if value(p, COLORS) != DIJITAL_RENK))
    if len(colors) != 5 or not all(colors):
        raise ValueError(f"5 canli renk bekleniyordu: {colors}")
    sample = next((p for p in products if parse_sku(p.get("sku"))), None)
    if not sample:
        raise ValueError("canli standart SKU bulunamadi")
    pair = parse_sku(sample["sku"])[0]
    color_props = {value(p, COLORS): property_value(p, COLORS) for p in products if value(p, COLORS) in colors}
    size_prop = property_value(sample, "size")
    format_prop = next((property_value(p, "format") for p in products if property_value(p, "format")), None) \
        or {"property_id": 514, "property_name": FORMAT_ADI, "values": []}
    offering0 = sample["offerings"][0]
    renkler = colors + [DIJITAL_RENK]
    color_prop_id = color_props[colors[0]]["property_id"]
    planned = []
    for row in rows:
        dijital = row["tur"] == "digital"
        sku = (make_sku2(pair, row["boy"]) + "-DIGITAL") if dijital else make_sku2(pair, row["boy"], row["cerceve"] or None)
        if len(sku) > MAX_LEN:
            raise ValueError(f"SKU cok uzun: {sku}")
        for renk in renkler:
            cprop = copy_property(color_props[renk]) if renk in color_props else \
                {"property_id": color_props[colors[0]]["property_id"], "property_name": "Primary color", "values": [renk]}
            acik = bool(row["aktif"]) and (dijital == (renk == DIJITAL_RENK))
            planned.append({"sku": sku,
                            "property_values": [copy_property(format_prop, row["format"]), cprop,
                                                copy_property(size_prop, row["etiket"] or row["boy"])],
                            "offerings": [copy_offering(offering0, row["fiyat"], acik)]})
    result = {"products": planned,
              # Etsy (27 Eyl 400): 3 varyasyonda on_property yalniz 0, 1 ya da 3 id olabilir -> a2: uc menu birden
              "price_on_property": [format_prop["property_id"], color_prop_id, size_prop["property_id"]],
              "sku_on_property": [format_prop["property_id"], color_prop_id, size_prop["property_id"]]}
    for key in ("quantity_on_property", "readiness_state_on_property"):
        if inventory.get(key) is not None:
            result[key] = list(inventory[key])
    if len(planned) > 2500:
        raise ValueError(f"Etsy urun siniri 2500 asildi: {len(planned)}")
    return result


def menu1_degerleri(rows):
    formatlar = list(dict.fromkeys(r["format"] for r in sorted(rows, key=lambda r: int(r["sira"]))))
    return {f: ([DIJITAL_D] if f == "Digital File" else [f"{f}, {c}" for c in RENK_SIRA]) for f in formatlar}


def fmt_renk(p):
    """(format, renk): menu D'de 'Format & Color' degerinden, v3'te ayri menulerden. Dijital renk = DIJITAL_RENK."""
    pv = next((x for x in p.get("property_values", []) if (x.get("property_name") or "").lower() == MENU1_ADI.lower()), None)
    if pv:
        v = (pv.get("values") or [""])[0]
        if v == DIJITAL_D:
            return "Digital File", DIJITAL_RENK
        f, _, r = v.rpartition(", ")
        return f, r
    return value(p, "format"), value(p, COLORS)


def build_plan_d(inventory, rows):
    """Menu D: Format & Color (26) x Size (16) = 416 urun, hepsi acik. price/sku_on_property = [menu1, size].
    SKU renksiz (mevcut sema); ayni format+boyun 5 rengi ayni SKU'yu tasir, renk menu 1 degerinden okunur."""
    products = inventory.get("products") or []
    if not products:
        raise ValueError("canli envanter bos")
    canli = {value(p, COLORS) for p in products} - {""}
    if canli - set(RENK_SIRA) or len(canli) != 5:
        raise ValueError(f"canli renkler beklenen 5 renk degil: {sorted(canli)}")
    sample = next((p for p in products if parse_sku(p.get("sku"))), None)
    if not sample:
        raise ValueError("canli standart SKU bulunamadi")
    pair = parse_sku(sample["sku"])[0]
    size_prop = property_value(sample, "size")
    if not size_prop:
        raise ValueError("Size property bulunamadi")
    m1_id = 514 if size_prop["property_id"] != 514 else 513
    offering0 = sample["offerings"][0]
    rows = sorted(rows, key=lambda r: int(r["sira"]))
    planned = []
    for fmt, degerler in menu1_degerleri(rows).items():
        satirlar = [r for r in rows if r["format"] == fmt]
        for deger in degerler:
            for row in satirlar:
                dijital = row["tur"] == "digital"
                sku = (make_sku2(pair, row["boy"]) + "-DIGITAL") if dijital else make_sku2(pair, row["boy"], row["cerceve"] or None)
                planned.append({"sku": sku,
                                "property_values": [{"property_id": m1_id, "property_name": MENU1_ADI, "values": [deger]},
                                                    copy_property(size_prop, row["etiket"] or row["boy"])],
                                "offerings": [copy_offering(offering0, row["fiyat"], bool(row["aktif"]))]})
    ids = [m1_id, size_prop["property_id"]]
    result = {"products": planned, "price_on_property": ids, "sku_on_property": list(ids)}
    for key in ("quantity_on_property", "readiness_state_on_property"):
        kalan = [x for x in (inventory.get(key) or []) if x in ids]
        result[key] = kalan
    return result


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
        return build_plan_v3(inventory, rows)
    if mode == "3x":  # eski 3 varyasyon yolu (renk SKU icinde, 400 siniri); kullanilmiyor
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
            size = row["etiket"] if mode == "2" else (row["etiket"] or row["boy"])  # mod 3: canli boy etiketi korunur
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
                    # Canli ilanda Format yok: ikinci ozel property (514) yeni menu olarak acilir (Serdar 27 Eyl, rakip yapi).
                    format_prop = {"property_id": 514, "property_name": FORMAT_ADI, "values": []}
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
    if mode == "3":
        # SKU format x renk x boy'a gore degisir; Etsy bu durumda urun sinirini 400 yapar (325-400 arasi guvenli).
        result["sku_on_property"] = [format_prop["property_id"], color_prop["property_id"], size_prop["property_id"]]
        if len(planned) > 400:
            raise ValueError(f"Etsy urun siniri 400 asildi: {len(planned)}")
    return result


def signature(inventory):
    return sorted((*fmt_renk(p), value(p, "size"), p.get("sku") or "",
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


def referans_tablosu(path="docs/REFERANS_ILAN_CL.md"):
    """Fiyat tablosu (USD): {boy: (print, frame)}."""
    tablo, icinde = {}, False
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("## Fiyat tablosu"):
            icinde = True; continue
        if icinde and line.startswith("## "):
            break
        m = re.match(r"\|\s*([0-9A-Za-z]+)\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|", line) if icinde else None
        if m:
            tablo[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    return tablo


SKU3 = re.compile(r"^POD-[A-Z]{3}_[A-Z]{3}-([0-9]+x[0-9]+|A[0-9])(-DIGITAL|-F(GO|BK|WH|NA))?$")


def referans_kontrol(plan, tablo, dijital_fiyat=9.99):
    """Plan <-> REFERANS_ILAN_CL: fiyat tablosu, dijital 9.99, SKU v3 (renksiz), acik kurali. Hata listesi doner."""
    hatalar = []
    for p in plan["products"]:
        sku, fiyat = p.get("sku") or "", money(p["offerings"][0]["price"])
        fmt, renk = fmt_renk(p)
        m = SKU3.match(sku)
        if not m:
            hatalar.append(f"SKU v3 degil: {sku}"); continue
        boy, ek = m.group(1), m.group(2) or ""
        if boy not in tablo:
            hatalar.append(f"tabloda boy yok: {boy}"); continue
        bek = dijital_fiyat if ek == "-DIGITAL" else tablo[boy][1 if ek.startswith("-F") else 0]
        if abs(fiyat - bek) > 0.001:
            hatalar.append(f"fiyat {sku} {fmt}: {fiyat} != {bek}")
        if (fmt == "Digital File") != (ek == "-DIGITAL") or (ek.startswith("-F") != fmt.endswith("Frame")):
            hatalar.append(f"format/SKU uyusmaz: {fmt} {sku}")
        if p["offerings"][0]["is_enabled"] and ((fmt == "Digital File") != (renk == DIJITAL_RENK)):
            hatalar.append(f"acik kurali: {fmt} {renk}")
    return hatalar


def ozet(inventory, plan, state):
    def ac(inv): return sum(1 for p in inv.get("products") or [] if p["offerings"][0].get("is_enabled"))
    menu = {}
    idler = list(dict.fromkeys(pv["property_id"] for p in plan["products"] for pv in p["property_values"]))
    for i, pid in enumerate(idler, 1):
        menu[i] = list(dict.fromkeys(pv["values"][0] for p in plan["products"] for pv in p["property_values"]
                                     if pv["property_id"] == pid))
    ornek = {}
    for p in plan["products"]:
        m = SKU3.match(p.get("sku") or "")
        if m and m.group(1) in ("8x10", "16x20", "24x36") and p["offerings"][0]["is_enabled"]:
            ornek.setdefault(f'{m.group(1)} | {fmt_renk(p)[0]}', f'{money(p["offerings"][0]["price"])} {p["sku"]}')
    return {"state": state, "urun": [len(inventory.get("products") or []), len(plan["products"])],
            "acik": [ac(inventory), ac(plan)], "menu": menu, "ornek": dict(sorted(ornek.items()))}


def varyasyon_sayisi(plan):
    return len({pv["property_id"] for p in plan["products"] for pv in p["property_values"]})


def parantezsiz_oneri(plan):
    """Etsy parantezli degeri reddederse: yazmadan listelenecek oneri (Serdar karari bekler)."""
    return {v: re.sub(r"\s*\((.*?)\)", r" / \1", v).strip()
            for p in plan["products"] for pv in p["property_values"] for v in pv.get("values") or [] if "(" in v}


def d_varyasyon_gorselleri(readback, before_map):
    """Menu D: her '<format>, <renk>' degeri o rengin canli gorseline; dijital deger baglanmaz."""
    istek, gorulen = [], set()
    for p in readback.get("products") or []:
        pv = next((x for x in p["property_values"] if (x.get("property_name") or "").lower() == MENU1_ADI.lower()), None)
        if not pv or not pv.get("value_ids"):
            continue
        deger, vid = pv["values"][0], int(pv["value_ids"][0])
        renk = fmt_renk(p)[1]
        if renk in before_map and vid not in gorulen:
            gorulen.add(vid)
            istek.append({"property_id": pv["property_id"], "value_id": vid, "image_id": int(before_map[renk])})
    if len(istek) != 25:
        raise SystemExit(f"HATA: menu 1'de 25 renkli deger bekleniyordu, {len(istek)} bulundu. DUR.")
    return istek


def galeri(api, listing_id):
    r = api.get(f"/listings/{listing_id}/images") or {}
    return [(int(x["listing_image_id"]), int(x.get("rank") or 0)) for x in r.get("results", [])]


def videolar(api, listing_id):
    r = api.get(f"/listings/{listing_id}/videos", ok404=True) or {}
    return sorted(int(x["video_id"]) for x in r.get("results", []))


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
    p.add_argument("--aciklama", action="store_true",
                   help="aciklama PATCH'ini ac (varsayilan KAPALI; v3 aciklama pod-seo-v3 ile yazilir)")
    p.add_argument("--referans", default="docs/REFERANS_ILAN_CL.md")
    p.add_argument("--yapi", default="d", choices=("d", "v3"), help="d: 2 menu (Format & Color x Size); v3: 3 menu")
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
    if args.aciklama:
        size_block = Path("data/pod/aciklama_v2_boy_blok.txt").read_text(encoding="utf-8")
        digital_block = Path("data/pod/aciklama_v2_dijital_blok.txt").read_text(encoding="utf-8")
    tablo = referans_tablosu(args.referans)
    print(f"aciklama PATCH: {'ACIK' if args.aciklama else 'KAPALI'} | referans boy: {len(tablo)}")
    for index, listing_id in enumerate(ids, 1):
        # Mandatory live reads precede every plan; no stale PUT draft is accepted.
        listing = api.get(f"/listings/{listing_id}") or {}
        inventory = api.get(f"/listings/{listing_id}/inventory") or {}
        images = (api.get(f"/shops/{shop}/listings/{listing_id}/variation-images", ok404=True) or {}).get("results", [])
        backup = {"listing": listing, "inventory": inventory, "variation_images": images}
        (OUT / f"Y2_{listing_id}_ONCE.json").write_text(json.dumps(backup, ensure_ascii=False, indent=2))
        if listing.get("state") != "active":
            print(f"{listing_id}: state={listing.get('state')} (active degil) -> dokunulmadi"); continue
        plan = build_plan_d(inventory, config) if args.yapi == "d" else build_plan(inventory, config)
        description = (replace_description(listing.get("description", ""), size_block, digital_block)
                       if args.aciklama else listing.get("description", ""))
        write_diff(OUT / f"Y2_{listing_id}_DIFF.csv", inventory, plan)
        oz = ozet(inventory, plan, listing.get("state"))
        oz["referans_hata"] = referans_kontrol(plan, tablo)
        (OUT / f"Y2_{listing_id}_OZET.json").write_text(json.dumps(oz, ensure_ascii=False, indent=2))
        print(f"OZET {listing_id}: " + json.dumps(oz, ensure_ascii=False))
        if oz["referans_hata"]:
            raise SystemExit(f"HATA: plan REFERANS_ILAN_CL ile birebir degil ({len(oz['referans_hata'])}): "
                             f"{oz['referans_hata'][:5]}. DUR, yazilmadi.")
        already = signature(inventory) == signature(plan) and normalize(listing.get("description")) == normalize(description)
        if already: continue
        changed += 1
        if args.command == "yaz":
            if api.remaining is not None and int(api.remaining) < args.kota_alt: raise SystemExit("HATA: kota kapisi")
            before_map = pilot.v_renk_haritasi(inventory, images)
            if args.yapi == "d" and set(before_map) != set(RENK_SIRA):
                raise SystemExit(f"HATA: canli renk->gorsel eslemesi 5 renk degil: {sorted(before_map)}; yazilmadi. DUR.")
            personal = {k: listing.get(k) for k in PERSONALIZATION}
            sabit = {"title": listing.get("title"), "tags": list(listing.get("tags") or []),
                     "state": listing.get("state")}
            if not args.aciklama:
                sabit["description"] = normalize(listing.get("description"))
            galeri0, video0 = galeri(api, listing_id), videolar(api, listing_id)
            yol = f"/listings/{listing_id}/inventory"
            if varyasyon_sayisi(plan) == 3:  # menu D'de 2 menu: parametre gerekmez
                yol += "?max_variations_supported=3"   # OAS: varsayilan 2; 3 menu icin acikca istenir
            try:
                api.put_json(yol, plan)
            except SystemExit as hata:
                oneri = parantezsiz_oneri(plan)
                if "(" in str(hata) or "parenthes" in str(hata).lower():
                    print("PARANTEZ ONERISI (yazilmadi): " + json.dumps(oneri, ensure_ascii=False))
                raise SystemExit(f"HATA: envanter PUT reddedildi, ilan degismedi: {hata}. DUR.")
            readback = api.get(f"/listings/{listing_id}/inventory") or {}
            if signature(readback) != signature(plan): raise SystemExit("HATA: envanter geri okuma farkli")
            images2 = (api.get(f"/shops/{shop}/listings/{listing_id}/variation-images", ok404=True) or {}).get("results", [])
            if args.yapi == "d":
                istek = d_varyasyon_gorselleri(readback, before_map)
                api.post_json(f"/shops/{shop}/listings/{listing_id}/variation-images", {"variation_images": istek})
                images3 = (api.get(f"/shops/{shop}/listings/{listing_id}/variation-images", ok404=True) or {}).get("results", [])
                var = {(int(r["value_id"]), int(r["image_id"])) for r in images3}
                eksik = [x for x in istek if (int(x["value_id"]), int(x["image_id"])) not in var]
                if eksik:
                    raise SystemExit(f"HATA: menu 1 -> renk gorseli eslemesi eksik ({len(eksik)}/{len(istek)}). DUR.")
                print(f"varyasyon gorselleri: {len(istek)} menu 1 degeri -> 5 renk gorseli (dijital baglanmadi)")
            elif pilot.v_renk_haritasi(readback, images2) != before_map:
                by_color = {value(p, COLORS): property_value(p, COLORS) for p in readback["products"]}
                payload = [{"property_id": p["property_id"], "value_id": p["value_ids"][0], "image_id": int(image)}
                           for color, image in before_map.items() for p in [by_color[color]]]
                api.post_json(f"/shops/{shop}/listings/{listing_id}/variation-images", {"variation_images": payload})
                images3 = (api.get(f"/shops/{shop}/listings/{listing_id}/variation-images", ok404=True) or {}).get("results", [])
                if pilot.v_renk_haritasi(readback, images3) != before_map:
                    raise SystemExit("HATA: renk->gorsel eslesmesi onarilamadi")
            if args.aciklama:
                api.patch(f"/shops/{shop}/listings/{listing_id}", {"description": description})
            final = api.get(f"/listings/{listing_id}") or {}
            if normalize(final.get("description")) != normalize(description) or any(final.get(k) != v for k, v in personal.items()):
                raise SystemExit("HATA: aciklama/kisisellestirme geri okuma farkli")
            son = {"title": final.get("title"), "tags": list(final.get("tags") or []), "state": final.get("state")}
            if not args.aciklama:
                son["description"] = normalize(final.get("description"))
            fark = [k for k in sabit if sabit[k] != son[k]]
            if galeri(api, listing_id) != galeri0: fark.append("gorseller")
            if videolar(api, listing_id) != video0: fark.append("video")
            if fark:
                raise SystemExit(f"HATA: yazim sonrasi degismemesi gereken alanlar degisti: {fark}")
            print(f"GERI OKUMA {listing_id}: envanter=plan, renk-gorsel tamam, state={son['state']}, "
                  f"baslik/etiket/aciklama/{len(galeri0)} gorsel/{len(video0)} video degismedi")
        elapsed = time.monotonic()-started; remaining = elapsed/index*(len(ids)-index)
        print(f"ETA {index}/{len(ids)} %{index/len(ids)*100:.1f} gecen={elapsed:.0f}s kalan={remaining:.0f}s")
    if not changed: return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
