#!/usr/bin/env python3
"""
POD (Prodigi poster) YENI ILAN olusturma: createDraftListing + 10 gorsel +
Color(5) x Size(13) = 65 varyant + renk secenegine edisyon 01 karesi - 6 Eyl 2026.

Kaynaklar:
  - baslik/tag/aciklama: docs/POD_LISTING_TEMPLATE.md (+ TITLE sablonu asagida)
  - 13 boyut fiyati: scripts/etsy/pod_prices.csv (size,price; USD, tum edisyonlarda ayni); bos fiyat -> apply reddedilir
  - gorseller: <images>/<PAIR>/<ED>/NN_*.jpg (Drive TEMP/POD_GALLERY/<PAIR>, 78 cift)
  - API'den okunur (tahmin yok): kargo profili, bolum, production partner (Prodigi),
    iade politikasi, taxonomy (Prints > Giclee), varyasyon property id'leri.

Kullanim:
  pod_listing_create.py --pairs ARIES_LEO --images IMG --state STATE.csv --out OUT --dry-run
  pod_listing_create.py --pairs ARIES_LEO --images IMG --state STATE.csv --out OUT --apply   # ONAY SONRASI
  --pairs A_B,C_D | --pairs-file dosya (satir basina cift) ; --limit N (0 = hepsi)

Dry-run HICBIR yazma cagrisi yapmaz: kesif tablosu + ilan basina payload JSON.
Apply: kargo profili / bolum yoksa olusturur; ilan basina asama asama STATE'e yazar
(resume); kota 400 altinda yeni ilana baslamaz. Ortam: ETSY_API_KEY,
ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE, GITHUB_STEP_SUMMARY (istege bagli).
"""
import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from pod_listing_update import SIGNS, build as build_text, load_template  # noqa: E402
from wp_listing_update import norm, tags_of, validate  # noqa: E402

HERE = Path(__file__).resolve().parent
PRICES_CSV = HERE / "pod_prices.csv"
MAX_TITLE = 140
QUOTA_MIN = 400
QUANTITY = 999
MAX_IMAGES = 10

TITLE = "{S1} and {S2} Zodiac Wall Art, Couple Compatibility Giclée Print, Unframed Fine Art Poster, Gift for Couples"
EDITIONS = ["MIDNIGHT_BLUE", "DEEP_BLACK", "WARM_PARCHMENT", "CHAMPAGNE_IVORY", "PURE_WHITE"]
ED_NAME = {"MIDNIGHT_BLUE": "Midnight Blue", "DEEP_BLACK": "Deep Black", "WARM_PARCHMENT": "Warm Parchment",
           "CHAMPAGNE_IVORY": "Champagne Ivory", "PURE_WHITE": "Pure White"}
SIZES = ["8x10", "A4", "11x14", "12x16", "A3", "12x18", "16x20", "16x24", "A2", "18x24", "20x30", "24x36", "30x40"]
SIZE_LABEL = {"8x10": "8x10 in (20.3×25.4 cm)", "A4": "A4 (21×29.7 cm)", "11x14": "11x14 in (27.9×35.6 cm)",
              "12x16": "12x16 in (30.5×40.6 cm)", "A3": "A3 (29.7×42 cm)", "12x18": "12x18 in (30.5×45.7 cm)",
              "16x20": "16x20 in (40.6×50.8 cm)", "16x24": "16x24 in (40.6×61 cm)", "A2": "A2 (41.9×59.4 cm)",
              "18x24": "18x24 in (45.7×61 cm)", "20x30": "20x30 in (50.8×76.2 cm)", "24x36": "24x36 in (61×91.4 cm)",
              "30x40": "30x40 in (76.2×101.6 cm)"}       # Mo, 6 Eyl: sira kucukten buyuge, tum edisyonlarda ayni fiyat
MATERIALS = ["Hahnemuhle Photo Rag 308 gsm cotton paper", "archival pigment ink"]

SHIPPING_TITLE = "POD Prints – Free Shipping"
SECTION_TITLE = "Zodiac Fine Art Prints"
PARTNER_NAME = "prodigi"
TAXONOMY_PATH = ["prints", "giclée"]           # ust dugum adi 'Prints', yaprak 'Giclée' (giclee de kabul)

# 10 gorsel/ilan siniri: ana edisyonun 6 karesi + diger 4 edisyonun 01 karesi (renk secenegine baglanir)
DEFAULT_FRAMES = "01,02,03,05,08,10"
STAGES = ["created", "images", "inventory", "variation_images", "verified"]


# ------------------------------------------------------------------ girdi
def read_prices(path=PRICES_CSV):
    prices, missing = {}, []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            s = (r.get("size") or "").strip()
            v = (r.get("price") or r.get("price_usd") or "").strip()
            if not s:
                continue
            if not v:
                missing.append(s)
                continue
            prices[s] = round(float(v), 2)
    for s in SIZES:
        if s not in prices and s not in missing:
            missing.append(s)
    return prices, missing


def find_frame(img_root, pair, ed, no):
    d = Path(img_root) / pair / ed
    hits = sorted(d.glob(f"{no}_*.jpg")) if d.exists() else []
    return hits[0] if hits else None


def image_plan(img_root, pair, primary, frames):
    """[(rank, edisyon, dosya|None, renk_karesi_mi)] - en fazla 10."""
    plan, rank = [], 1
    for no in frames:
        plan.append((rank, primary, find_frame(img_root, pair, primary, no), no == "01")); rank += 1
    for ed in EDITIONS:
        if ed == primary:
            continue
        plan.append((rank, ed, find_frame(img_root, pair, ed, "01"), True)); rank += 1
    if len(plan) > MAX_IMAGES:
        raise SystemExit(f"HATA: gorsel plani {len(plan)} > {MAX_IMAGES}")
    return plan


def build_listing(pair, desc_tpl):
    s1, s2 = pair.split("_", 1)
    S1, S2 = s1.capitalize(), s2.capitalize()
    tags, desc, note = build_text(pair, desc_tpl)
    title = TITLE.format(S1=S1, S2=S2)
    issue = validate(title, tags)
    if issue:
        raise SystemExit(f"HATA: {pair}: {issue}")
    return title, tags, desc, note


def inventory_body(pair, prices, color_pid, size_pid, color_name, size_name):
    products = []
    for ed in EDITIONS:
        for sz in SIZES:
            products.append({
                "sku": f"POD-{pair}-{ed}-{sz}",
                "property_values": [
                    {"property_id": color_pid, "property_name": color_name, "values": [ED_NAME[ed]]},
                    {"property_id": size_pid, "property_name": size_name, "values": [SIZE_LABEL[sz]]},
                ],
                "offerings": [{"price": prices.get(sz, 0), "quantity": QUANTITY, "is_enabled": True}],
            })
    return {"products": products, "price_on_property": [size_pid], "quantity_on_property": [],
            "sku_on_property": [color_pid, size_pid]}


# ------------------------------------------------------------------ kesif (salt okur)
def _walk(nodes, path, out):
    for n in nodes or []:
        p = path + [(n.get("name") or "")]
        out.append((n.get("id"), p))
        _walk(n.get("children") or [], p, out)


def find_taxonomy(tree):
    flat = []
    _walk(tree.get("results") or [], [], flat)
    want_parent, want_leaf = TAXONOMY_PATH
    leafs = {"giclée", "giclee", "giclée prints", "giclee prints"}
    hits = [(i, p) for i, p in flat if p and p[-1].lower() in leafs and any(want_parent == x.lower() for x in p[:-1])]
    if not hits:
        hits = [(i, p) for i, p in flat if p and p[-1].lower() in leafs]
    return hits


def discover(api, shop, return_policy_id=""):
    d = {}
    sp = (api.get(f"/shops/{shop}/shipping-profiles") or {}).get("results") or []
    d["shipping_profiles"] = [(x.get("shipping_profile_id"), x.get("title")) for x in sp]
    d["shipping_profile_id"] = next((x.get("shipping_profile_id") for x in sp if (x.get("title") or "").strip().lower() == SHIPPING_TITLE.lower()), None)
    sec = (api.get(f"/shops/{shop}/sections") or {}).get("results") or []
    d["sections"] = [(x.get("shop_section_id"), x.get("title")) for x in sec]
    d["shop_section_id"] = next((x.get("shop_section_id") for x in sec if (x.get("title") or "").strip().lower() == SECTION_TITLE.lower()), None)
    pp = (api.get(f"/shops/{shop}/production-partners") or {}).get("results") or []
    d["partners"] = [(x.get("production_partner_id"), x.get("partner_name"), x.get("location")) for x in pp]
    d["production_partner_id"] = next((x.get("production_partner_id") for x in pp if PARTNER_NAME in (x.get("partner_name") or "").lower()), None)
    rp = (api.get(f"/shops/{shop}/policies/return") or {}).get("results") or []
    d["return_policies"] = [(x.get("return_policy_id"), x.get("accepts_returns"), x.get("accepts_exchanges"), x.get("return_deadline")) for x in rp]
    if return_policy_id:
        d["return_policy_id"] = int(return_policy_id)
    else:
        d["return_policy_id"] = rp[0].get("return_policy_id") if len(rp) == 1 else None
    d["return_policy_spec"] = None
    tax = find_taxonomy(api.get("/seller-taxonomy/nodes") or {})
    d["taxonomy_hits"] = [(i, " > ".join(p)) for i, p in tax]
    d["taxonomy_id"] = tax[0][0] if len(tax) == 1 else None
    d["color_pid"] = d["size_pid"] = d["color_name"] = d["size_name"] = None
    if d["taxonomy_id"]:
        props = (api.get(f"/seller-taxonomy/nodes/{d['taxonomy_id']}/properties") or {}).get("results") or []
        d["properties"] = [(p.get("property_id"), p.get("name"), p.get("supports_variations")) for p in props]
        for p in props:
            nm = (p.get("name") or "").lower()
            if p.get("supports_variations") and "color" in nm and d["color_pid"] is None:
                d["color_pid"], d["color_name"] = p.get("property_id"), p.get("name")
            if p.get("supports_variations") and nm.startswith("size") and d["size_pid"] is None:
                d["size_pid"], d["size_name"] = p.get("property_id"), p.get("name")
        if d["size_pid"] is None:
            # Giclee (121) taxonomy'sinde Size ozelligi yok (6 Eyl kesfi); Etsy panelindeki gibi
            # ozel varyasyon Custom1 (513) "Size" etiketiyle kullanilir.
            cust = next((p for p in props if p.get("supports_variations") and (p.get("name") or "").lower() == "custom1"), None)
            if cust:
                d["size_pid"], d["size_name"] = cust.get("property_id"), "Size"
                d["size_note"] = f"taxonomy'de Size yok; Custom1 ({cust.get('property_id')}) 'Size' olarak kullanilir"
    return d


def parse_rp_spec(spec):
    """'returns=1,exchanges=1,deadline=30' -> createShopReturnPolicy govdesi (yalniz Mo'nun verdigi degerler)."""
    if not spec:
        return None
    kv = dict(x.split("=", 1) for x in spec.split(",") if "=" in x)
    try:
        body = {"accepts_returns": kv["returns"].strip().lower() in ("1", "true", "yes"),
                "accepts_exchanges": kv["exchanges"].strip().lower() in ("1", "true", "yes")}
        if body["accepts_returns"] or body["accepts_exchanges"]:
            body["return_deadline"] = int(kv["deadline"])
    except (KeyError, ValueError) as e:
        raise SystemExit(f"HATA: --return-policy-spec bicimi: returns=1,exchanges=1,deadline=30 ({e})")
    return body


def ensure_return_policy(api, shop, d):
    if d["return_policy_id"]:
        return d["return_policy_id"]
    if not d.get("return_policy_spec"):
        raise SystemExit("HATA: iade politikasi yok ve --return-policy-spec verilmedi")
    r = api.post(f"/shops/{shop}/policies/return", d["return_policy_spec"])
    d["return_policy_id"] = r.get("return_policy_id")
    log(f"  iade politikasi olusturuldu: {d['return_policy_id']} {d['return_policy_spec']}")
    return d["return_policy_id"]


def discovery_issues(d):
    iss = []
    if d["production_partner_id"] is None:
        iss.append("Prodigi production partner yok (Etsy panelinden eklenmeli)")
    if d["return_policy_id"] is None and not d.get("return_policy_spec"):
        iss.append(f"iade politikasi yok/secilemedi ({len(d['return_policies'])} adet; --return-policy-id ya da --return-policy-spec ver)")
    if d["taxonomy_id"] is None:
        iss.append(f"taxonomy Prints > Giclee tek eslesme yok: {d['taxonomy_hits']}")
    if d["color_pid"] is None or d["size_pid"] is None:
        iss.append("varyasyon property (color/size) bulunamadi")
    return iss


# ------------------------------------------------------------------ durum
def read_state(path):
    st = {}
    p = Path(path)
    if p.exists():
        with open(p, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                st[r["pair"]] = r
    return st


def write_state(path, st):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    cols = ["pair", "listing_id", "stage", "ts_utc", "note"]
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for k in sorted(st):
            w.writerow({c: st[k].get(c, "") for c in cols})


def set_stage(st, path, pair, lid, stage, note=""):
    st[pair] = dict(pair=pair, listing_id=str(lid or ""), stage=stage,
                    ts_utc=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), note=note)
    write_state(path, st)
    log(f"  STATE {pair}: {stage} {lid or ''} {note}")


# ------------------------------------------------------------------ apply adimlari
def quota_ok(api, qmin=QUOTA_MIN):
    if api.remaining is None:
        return True
    try:
        return int(api.remaining) >= qmin
    except ValueError:
        return True


def ensure_shipping(api, shop, d, proc_min, proc_max):
    if d["shipping_profile_id"]:
        return d["shipping_profile_id"]
    body = {"title": SHIPPING_TITLE, "origin_country_iso": "US", "primary_cost": 0, "secondary_cost": 0,
            "min_processing_time": proc_min, "max_processing_time": proc_max,
            "processing_time_unit": "business_days", "destination_region": "none"}
    r = api.post(f"/shops/{shop}/shipping-profiles", body)
    d["shipping_profile_id"] = r.get("shipping_profile_id")
    log(f"  kargo profili olusturuldu: {d['shipping_profile_id']}")
    return d["shipping_profile_id"]


def ensure_section(api, shop, d):
    if d["shop_section_id"]:
        return d["shop_section_id"]
    r = api.post(f"/shops/{shop}/sections", {"title": SECTION_TITLE})
    d["shop_section_id"] = r.get("shop_section_id")
    log(f"  bolum olusturuldu: {d['shop_section_id']}")
    return d["shop_section_id"]


def listing_body(title, desc, tags, d, base_price):
    return {"quantity": QUANTITY, "title": title, "description": desc, "price": base_price,
            "who_made": "someone_else", "when_made": "made_to_order", "taxonomy_id": d["taxonomy_id"],
            "shipping_profile_id": d["shipping_profile_id"], "return_policy_id": d["return_policy_id"],
            "shop_section_id": d["shop_section_id"], "tags": ",".join(tags), "materials": ",".join(MATERIALS),
            "production_partner_ids": str(d["production_partner_id"]), "type": "physical", "is_supply": "false"}


def create_pair(api, shop, pair, d, prices, img_root, primary, frames, st, state_path, out_dir):
    title, tags, desc, note = build_listing(pair, load_template())
    plan = image_plan(img_root, pair, primary, frames)
    missing_img = [f"{ed}/{rk:02d}" for rk, ed, p, _ in plan if p is None]
    if missing_img:
        raise SystemExit(f"HATA: {pair}: eksik gorsel {missing_img}")
    row = st.get(pair, {})
    lid = row.get("listing_id") or ""
    stage = row.get("stage") or ""
    base_price = prices[SIZES[0]]

    if not lid:
        r = api.post(f"/shops/{shop}/listings", listing_body(title, desc, tags, d, base_price))
        lid = r.get("listing_id")
        if not lid:
            raise SystemExit(f"HATA: {pair}: createDraftListing cevabinda listing_id yok")
        set_stage(st, state_path, pair, lid, "created")
        stage = "created"

    if STAGES.index(stage) < STAGES.index("images"):
        have = {i.get("rank") for i in ((api.get(f"/listings/{lid}/images", ok404=True) or {}).get("results") or [])}
        for rk, ed, p, _ in plan:
            if rk in have:
                continue
            with open(p, "rb") as fh:
                api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (p.name, fh, "image/jpeg")},
                              data={"rank": str(rk)})
        set_stage(st, state_path, pair, lid, "images")
        stage = "images"

    if STAGES.index(stage) < STAGES.index("inventory"):
        api.put_json(f"/listings/{lid}/inventory", inventory_body(pair, prices, d["color_pid"], d["size_pid"], d["color_name"], d["size_name"]))
        set_stage(st, state_path, pair, lid, "inventory")
        stage = "inventory"

    if STAGES.index(stage) < STAGES.index("variation_images"):
        inv = api.get(f"/listings/{lid}/inventory") or {}
        value_ids = {}
        for pr in inv.get("products") or []:
            for pv in pr.get("property_values") or []:
                if pv.get("property_id") == d["color_pid"] and pv.get("value_ids") and pv.get("values"):
                    value_ids[pv["values"][0]] = pv["value_ids"][0]
        imgs = (api.get(f"/listings/{lid}/images") or {}).get("results") or []
        by_rank = {i.get("rank"): i.get("listing_image_id") for i in imgs}
        vi = []
        for rk, ed, p, is_color in plan:
            if is_color and ED_NAME[ed] in value_ids and rk in by_rank:
                vi.append({"property_id": d["color_pid"], "value_id": value_ids[ED_NAME[ed]], "image_id": by_rank[rk]})
        if len(vi) != len(EDITIONS):
            raise SystemExit(f"HATA: {pair}: renk-gorsel eslemesi {len(vi)}/{len(EDITIONS)} (value_ids {value_ids}, ranks {sorted(by_rank)})")
        api.put_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
        set_stage(st, state_path, pair, lid, "variation_images")
        stage = "variation_images"

    # geri okuma
    L = api.get(f"/listings/{lid}") or {}
    imgs = (api.get(f"/listings/{lid}/images") or {}).get("results") or []
    inv = api.get(f"/listings/{lid}/inventory") or {}
    vimg = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
    checks = {"state_draft": L.get("state") == "draft", "title": L.get("title") == title,
              "tags": tags_of(L) == tags, "desc": norm(L.get("description")) == norm(desc),
              "images": len(imgs) == len(plan), "products": len(inv.get("products") or []) == len(EDITIONS) * len(SIZES),
              "variation_images": len(vimg) == len(EDITIONS), "partner": bool(L.get("production_partner_ids") or L.get("production_partners"))}
    ok = all(checks.values())
    set_stage(st, state_path, pair, lid, "verified" if ok else stage, "PASS" if ok else "FAIL " + ",".join(k for k, v in checks.items() if not v))
    (Path(out_dir) / f"{pair}_readback.json").write_text(json.dumps({"listing": L, "checks": checks, "n_images": len(imgs),
                                                                     "n_products": len(inv.get("products") or []), "variation_images": vimg}, indent=1, ensure_ascii=False))
    return lid, ok, checks


# ------------------------------------------------------------------ ana
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pairs", default="", help="virgullu cift listesi, or. ARIES_LEO,CANCER_LIBRA")
    ap.add_argument("--pairs-file", default="", help="satir basina bir cift")
    ap.add_argument("--limit", type=int, default=0, help="en fazla N cift (0 = hepsi)")
    ap.add_argument("--images", required=True, help="<images>/<PAIR>/<ED>/NN_*.jpg")
    ap.add_argument("--state", required=True, help="cift,listing_id,stage CSV (resume)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--prices", default=str(PRICES_CSV))
    ap.add_argument("--primary", default="MIDNIGHT_BLUE", choices=EDITIONS)
    ap.add_argument("--frames", default=DEFAULT_FRAMES, help="ana edisyondan alinacak kareler")
    ap.add_argument("--return-policy-id", default="")
    ap.add_argument("--return-policy-spec", default="", help="magazada iade politikasi yoksa apply'da olusturulur: returns=1,exchanges=1,deadline=30")
    ap.add_argument("--quota-min", type=int, default=QUOTA_MIN, help="bu degerin altinda yazma yok (varsayilan 400)")
    ap.add_argument("--processing-min", type=int, default=3)
    ap.add_argument("--processing-max", type=int, default=5)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    pairs = [p.strip().upper() for p in a.pairs.split(",") if p.strip()]
    if a.pairs_file:
        pairs += [l.strip().upper() for l in Path(a.pairs_file).read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    pairs = list(dict.fromkeys(pairs))
    if not pairs:
        raise SystemExit("HATA: --pairs veya --pairs-file gerekli")
    for p in pairs:
        s = p.split("_")
        if len(s) != 2 or any(x.capitalize() not in SIGNS for x in s):
            raise SystemExit(f"HATA: gecersiz cift {p}")
    out_dir = Path(a.out); out_dir.mkdir(parents=True, exist_ok=True)
    frames = [f.strip() for f in a.frames.split(",") if f.strip()]
    prices, missing = read_prices(a.prices)
    st = read_state(a.state)
    todo = [p for p in pairs if (st.get(p) or {}).get("stage") != "verified"]
    if a.limit:
        todo = todo[:a.limit]
    log(f"ciftler: {len(pairs)} istendi, {len(todo)} islenecek (verified atlanir); fiyat eksik: {missing or 'yok'}")

    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    d = discover(api, shop, a.return_policy_id)
    if not d["return_policy_id"] and a.return_policy_spec:
        d["return_policy_spec"] = parse_rp_spec(a.return_policy_spec)
    iss = discovery_issues(d)
    md = [f"## Kesif (kota {api.remaining})", "",
          f"- kargo profili '{SHIPPING_TITLE}': {d['shipping_profile_id'] or 'YOK -> apply olusturur'} | mevcut: {d['shipping_profiles']}",
          f"- bolum '{SECTION_TITLE}': {d['shop_section_id'] or 'YOK -> apply olusturur'} | mevcut: {d['sections']}",
          f"- production partner Prodigi: {d['production_partner_id']} | mevcut: {d['partners']}",
          f"- iade politikasi: {d['return_policy_id'] or ('YOK -> apply olusturur ' + str(d['return_policy_spec']) if d['return_policy_spec'] else 'YOK')} | mevcut: {d['return_policies']}",
          f"- taxonomy: {d['taxonomy_id']} | eslesme: {d['taxonomy_hits']}",
          f"- varyasyon property: color {d['color_pid']} ({d['color_name']}), size {d['size_pid']} ({d['size_name']}) {d.get('size_note', '')}",
          f"- fiyat: {len(prices)}/13 dolu; eksik: {missing or 'yok'}",
          f"- kesif sorunlari: {iss or 'yok'}", ""]
    (out_dir / "discovery.json").write_text(json.dumps(d, indent=1, ensure_ascii=False, default=str))

    rows = []
    if a.dry_run:
        for pair in todo:
            title, tags, desc, note = build_listing(pair, load_template())
            plan = image_plan(a.images, pair, a.primary, frames)
            miss_img = [f"{ed}/{frames[i] if i < len(frames) else '01'}" for i, (rk, ed, p, _) in enumerate(plan) if p is None]
            body = listing_body(title, desc, tags, d, prices.get(SIZES[0], 0))
            inv = inventory_body(pair, prices, d["color_pid"], d["size_pid"], d["color_name"], d["size_name"])
            (out_dir / f"{pair}_payload.json").write_text(json.dumps(
                {"listing": body, "images": [(rk, ed, str(p) if p else None, c) for rk, ed, p, c in plan], "inventory": inv},
                indent=1, ensure_ascii=False))
            status = "HAZIR" if not (missing or miss_img or iss) else "EKSIK: " + "; ".join(
                ([f"fiyat {missing}"] if missing else []) + ([f"gorsel {miss_img}"] if miss_img else []) + iss)
            rows.append(dict(pair=pair, title_len=len(title), n_tags=len(tags), desc_len=len(desc), n_images=len(plan),
                             n_products=len(inv["products"]), pair_tag_note=note, status=status))
            log(f"[dry-run] {pair}: baslik {len(title)} | gorsel {len(plan)} | varyant {len(inv['products'])} | {status}")
        md.append("| cift | baslik | tag | aciklama | gorsel | varyant | durum |\n|---|---|---|---|---|---|---|")
        md += [f"| {r['pair']} | {r['title_len']} | {r['n_tags']} | {r['desc_len']} | {r['n_images']} | {r['n_products']} | {r['status']} |" for r in rows]
        md.append("\nDRY-RUN: yazma yok. Payload: <out>/<PAIR>_payload.json")
    else:
        if missing or iss:
            raise SystemExit(f"HATA: apply icin eksik: fiyat {missing}; kesif {iss}")
        if not quota_ok(api, a.quota_min):
            raise SystemExit(f"HATA: kota {api.remaining} < {a.quota_min}; yazma yok")
        ensure_shipping(api, shop, d, a.processing_min, a.processing_max)
        ensure_section(api, shop, d)
        ensure_return_policy(api, shop, d)
        t0 = time.time()
        for n, pair in enumerate(todo, 1):
            if not quota_ok(api, a.quota_min):
                log(f"KOTA {api.remaining} < {a.quota_min}: {pair} ve sonrasi islenmedi (resume ile devam)")
                break
            lid, ok, checks = create_pair(api, shop, pair, d, prices, a.images, a.primary, frames, st, a.state, out_dir)
            rows.append(dict(pair=pair, listing_id=lid, status="PASS" if ok else "FAIL", checks=checks))
            el = time.time() - t0
            log(f"[{n}/{len(todo)}] {pair} {lid} {'PASS' if ok else 'FAIL ' + str(checks)} | gecen {el:.0f}s kalan~{el / n * (len(todo) - n):.0f}s | kota {api.remaining}")
        md.append("| cift | listing_id | durum |\n|---|---|---|")
        md += [f"| {r['pair']} | {r['listing_id']} | {r['status']} |" for r in rows]
    text = "\n".join(md)
    log(text)
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    if a.apply and any(r["status"] != "PASS" for r in rows):
        raise SystemExit("FAIL: en az bir ilan PASS degil")


if __name__ == "__main__":
    main()
