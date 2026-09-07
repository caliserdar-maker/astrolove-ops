#!/usr/bin/env python3
"""
78 POD ilaninin TAM DENETIMI - SALT OKUR (Mo 7 Eyl 2026). Hicbir yazma cagrisi yoktur.

Her ilan icin 7 GET (listing, images, videos, inventory, translations/ru, variation-images, properties)
ve beklenenle karsilastirma. Beklenen kaynak:
  - sablon: docs/POD_LISTING_TEMPLATE.md + pod_listing_create (baslik/tag/aciklama/RU, SIZE etiketleri, SKU, fiyat)
  - sabitler: state=active, bolum/kargo/iade id'leri, who_made, when_made, auto-renew, adet 999, materyal
  - referans ilan (--ref-id, ARIES_LEO): ilan ozellikleri (Orientation/Framing/pieces/Material) haritasi
Rapor YALNIZ sapma tablosudur (listing_id, alan, beklenen, bulunan) + ozet. Kota --quota-min altina
inince durur, islenmeyen ilanlar raporlanir. Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
Kullanim: pod_audit.py --state STATE.csv --out OUT [--limit N] [--quota-min 400] [--ref-id 4570031205]
"""
import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from pod_inventory_update import sections  # noqa: E402
from pod_listing_create import (ATTRS, AUTO_RENEW, ED_NAME, EDITIONS, MATERIALS, QUANTITY, SIZE_LABEL,  # noqa: E402
                                SIZES, WHO_MADE, build_listing, build_ru, load_ru_template, read_prices)
from pod_listing_update import load_template  # noqa: E402
from pod_publish import RETURN_ID, SECTION_ID, SHIPPING_ID  # noqa: E402
from pod_sku import make_sku  # noqa: E402
from wp_listing_update import norm, tags_of  # noqa: E402

N_IMAGES, N_VIDEOS, N_TAGS, N_SECTIONS = 12, 1, 13, 9
COLOR_RANKS = {1, 9, 10, 11, 12}          # renk secenegine baglanan kareler (hero + 4 edisyon hero)
FIRST_PARA_MUST = "shipped unframed"      # ilk paragrafta bulunmali
# 7 Eyl geri alinan satir (PLEASE NOTE'taki "prints are sold unframed" MESRU, karistirilmaz)
FORBIDDEN_LINE = "Sold unframed — the frames in the photos"
FORBIDDEN_LINE_RU = "Продаётся без рамы — рамы на фото"


def read_state(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if (r.get("stage") or "") == "verified" and (r.get("listing_id") or "").isdigit():
                rows.append((r["pair"], r["listing_id"]))
    return sorted(rows)


def price_of(off):
    """Etsy offering price -> float (dict {amount,divisor} ya da duz sayi)."""
    p = (off or {}).get("price")
    if isinstance(p, dict):
        return round(float(p.get("amount") or 0) / float(p.get("divisor") or 100), 2)
    return round(float(p or 0), 2)


def prop_map(props):
    """properties cevabi -> {ozellik adi: 'deger1|deger2'}"""
    out = {}
    for p in props or []:
        out[(p.get("property_name") or str(p.get("property_id"))).strip()] = "|".join(str(v) for v in (p.get("values") or []))
    return out


def short(s, n=60):
    s = str(s).replace("\n", "\\n")
    return s if len(s) <= n else s[:n - 1] + "…"


def fetch(api, shop, lid):
    return {
        "L": api.get(f"/listings/{lid}") or {},
        "imgs": (api.get(f"/listings/{lid}/images", ok404=True) or {}).get("results") or [],
        "vids": (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or [],
        "inv": api.get(f"/listings/{lid}/inventory") or {},
        "ru": api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {},
        "vimg": (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or [],
        "props": (api.get(f"/shops/{shop}/listings/{lid}/properties", ok404=True) or {}).get("results") or [],
    }


def audit(pair, lid, data, prices, tpl, ru_tpl, ref_props, a):
    """-> sapma listesi [(listing_id, alan, beklenen, bulunan)]"""
    dev = []

    def add(alan, beklenen, bulunan):
        dev.append((lid, alan, short(beklenen), short(bulunan)))

    L, imgs, vids, inv = data["L"], data["imgs"], data["vids"], data["inv"]
    title, tags, desc, _ = build_listing(pair, tpl)
    ru_title, ru_tags, ru_desc, _ = build_ru(pair, ru_tpl)

    # --- ilan alanlari
    for alan, beklenen, bulunan in [
        ("state", "active", L.get("state")),
        ("shop_section_id", a.section_id, L.get("shop_section_id")),
        ("shipping_profile_id", a.shipping_profile_id, L.get("shipping_profile_id")),
        ("return_policy_id", a.return_policy_id, L.get("return_policy_id")),
        ("who_made", WHO_MADE, L.get("who_made")),
        ("when_made", "made_to_order", L.get("when_made")),
        ("should_auto_renew", AUTO_RENEW, bool(L.get("should_auto_renew"))),
        ("title", title, L.get("title")),
    ]:
        if bulunan != beklenen:
            add(alan, beklenen, bulunan)
    if tags_of(L) != tags:
        eksik = [t for t in tags if t not in tags_of(L)]
        add("etiket (EN)", f"{N_TAGS} etiket (sablon)", f"{len(tags_of(L))} etiket; eksik: {','.join(eksik) or '-'}")
    if sorted(str(m).strip() for m in (L.get("materials") or [])) != sorted(MATERIALS):
        add("materials", "; ".join(MATERIALS), "; ".join(L.get("materials") or []))
    if not (L.get("production_partner_ids") or L.get("production_partners")):
        add("production_partner", "Prodigi (dolu)", "bos")

    # --- aciklama
    got_desc = norm(L.get("description"))
    if got_desc != norm(desc):
        so, sn = sections(got_desc), sections(norm(desc))
        farkli = [k or "(giris)" for k in sn if so.get(k) != sn.get(k)] + [k or "(giris)" for k in so if k not in sn]
        add("aciklama", "sablonla ayni", "farkli bolum: " + ", ".join(farkli))
    n_sec = sum(1 for line in got_desc.split("\n") if line.startswith("✦ "))
    if n_sec != N_SECTIONS:
        add("aciklama bolum sayisi", N_SECTIONS, n_sec)
    if FORBIDDEN_LINE in got_desc:
        add("'Sold unframed' satiri", "yok", "VAR")
    if FIRST_PARA_MUST not in got_desc.split("\n\n")[0]:
        add("ilk paragraf", f"'{FIRST_PARA_MUST}' var", "yok")

    # --- RU katmani
    if data["ru"].get("title") != ru_title:
        add("RU baslik", ru_title, data["ru"].get("title") or "yok")
    got_ru = norm(data["ru"].get("description"))
    if got_ru != norm(ru_desc):
        so, sn = sections(got_ru), sections(norm(ru_desc))
        farkli = [k or "(giris)" for k in sn if so.get(k) != sn.get(k)] + [k or "(giris)" for k in so if k not in sn]
        add("RU aciklama", "sablonla ayni", ("yok" if not got_ru else "farkli bolum: " + ", ".join(farkli)))
    if FORBIDDEN_LINE_RU in got_ru:
        add("RU 'без рамы' satiri", "yok", "VAR")
    if len(data["ru"].get("tags") or []) != N_TAGS:
        add("etiket (RU)", N_TAGS, len(data["ru"].get("tags") or []))

    # --- medya
    ranks = sorted(i.get("rank") for i in imgs)
    if len(imgs) != N_IMAGES or ranks != list(range(1, N_IMAGES + 1)):
        add("gorsel", f"{N_IMAGES} (rank 1-{N_IMAGES})", f"{len(imgs)} (rank {ranks})")
    if len(vids) != N_VIDEOS:
        add("video", N_VIDEOS, len(vids))

    # --- envanter (65 varyant)
    exp = {make_sku(pair, ed, sz): (ED_NAME[ed], SIZE_LABEL[sz], prices[sz]) for ed in EDITIONS for sz in SIZES}
    got, kapali, adet_bad = {}, [], []
    for pr in inv.get("products") or []:
        vals = [v for pv in (pr.get("property_values") or []) for v in (pv.get("values") or [])]
        color = next((v for v in vals if v in ED_NAME.values()), None)
        size = next((v for v in vals if v in SIZE_LABEL.values()), None)
        off = (pr.get("offerings") or [{}])[0]
        got[pr.get("sku")] = (color, size, price_of(off))
        if not off.get("is_enabled", True):
            kapali.append(pr.get("sku"))
        if int(off.get("quantity") or 0) != QUANTITY:
            adet_bad.append(f"{pr.get('sku')}={off.get('quantity')}")
    if len(inv.get("products") or []) != len(exp):
        add("varyant sayisi", len(exp), len(inv.get("products") or []))
    yanlis = [k for k in exp if got.get(k) != exp[k]]
    if yanlis:
        k = yanlis[0]
        add("varyant SKU/etiket/fiyat", f"{len(exp)}/{len(exp)} dogru", f"{len(yanlis)} sapma, or. {k}: {exp[k]} -> {got.get(k, 'SKU yok')}")
    if kapali:
        add("varyant gorunurluk", "65 is_enabled", f"{len(kapali)} kapali: {','.join(kapali[:3])}")
    if adet_bad:
        add("varyant adedi", QUANTITY, f"{len(adet_bad)} sapma: {','.join(adet_bad[:3])}")

    # --- renk -> gorsel (5/5)
    by_id = {i.get("listing_image_id"): i.get("rank") for i in imgs}
    vmap = {v.get("value"): v.get("image_id") for v in data["vimg"]}
    bagli = {c: i for c, i in vmap.items() if c in ED_NAME.values() and i in by_id}
    if len(bagli) != len(EDITIONS) or {by_id[i] for i in bagli.values()} != COLOR_RANKS:
        add("renk->gorsel", f"{len(EDITIONS)}/{len(EDITIONS)} (rank {sorted(COLOR_RANKS)})",
            f"{len(bagli)}/{len(EDITIONS)} (rank {sorted(by_id[i] for i in bagli.values())})")

    # --- ilan ozellikleri (referans ilanla ayni)
    pm = prop_map(data["props"])
    if ref_props is not None:
        for k, v in ref_props.items():
            if pm.get(k) != v:
                add(f"ozellik {k}", v, pm.get(k) or "yok")
    else:                                   # referansin kendisi: ATTRS degerleri bulunmali
        vals = {v.lower() for s in pm.values() for v in s.split("|")}
        for k, v in ATTRS.items():
            if v.lower() not in vals:
                add(f"ozellik {k}", v, "yok (referans)")
    return dev


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--quota-min", type=int, default=400)
    ap.add_argument("--ref-id", default="4570031205", help="referans ilan (ozellik haritasi buradan)")
    ap.add_argument("--section-id", type=int, default=SECTION_ID)
    ap.add_argument("--shipping-profile-id", type=int, default=SHIPPING_ID)
    ap.add_argument("--return-policy-id", type=int, default=RETURN_ID)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows = read_state(a.state)
    if not rows:
        raise SystemExit(f"HATA: STATE'te verified ilan yok: {a.state}")
    if a.limit:
        rows = rows[:a.limit]
    prices, missing = read_prices()
    if missing:
        raise SystemExit(f"HATA: fiyat eksik: {missing}")
    tpl, ru_tpl = load_template(), load_ru_template()

    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    run(api, shop, rows, prices, tpl, ru_tpl, a, out)


def run(api, shop, rows, prices, tpl, ru_tpl, a, out):
    """Denetim dongusu (test edilebilirlik icin ayri)."""
    # referans once: ozellik haritasi
    ref = next((r for r in rows if r[1] == str(a.ref_id)), None)
    order = ([ref] + [r for r in rows if r is not ref]) if ref else list(rows)
    q0, dev, done, ref_props, t0, stopped = None, [], [], None, time.time(), None
    for n, (pair, lid) in enumerate(order, 1):
        try:
            rem = int(api.remaining) if api.remaining is not None else None
        except ValueError:
            rem = None
        if rem is not None and rem < a.quota_min:
            stopped = pair
            log(f"KOTA {rem} < {a.quota_min}: {pair} ve sonrasi denetlenmedi")
            break
        data = fetch(api, shop, lid)
        if q0 is None:
            q0 = api.remaining
        d = audit(pair, lid, data, prices, tpl, ru_tpl, ref_props, a)
        if ref and pair == ref[0] and ref_props is None:
            ref_props = prop_map(data["props"])
        dev += d
        done.append((pair, lid, len(d)))
        el = time.time() - t0
        log(f"[{n}/{len(order)}] {pair} {lid} {'UYUMLU' if not d else str(len(d)) + ' SAPMA: ' + ','.join(x[1] for x in d)}"
            f" | gecen {el:.0f}s kalan~{el / n * (len(order) - n):.0f}s %{100 * n // len(order)} | kota {api.remaining}")

    draft = [r for r in dev if r[1] == "state"]
    other = [r for r in dev if r[1] != "state"]
    sapan = sorted({r[0] for r in other})
    md = ["## POD tam denetim (SALT OKUR)", "",
          f"- Denetlenen {len(done)}/{len(rows)} ilan"
          + (f"; KOTA {api.remaining} < {a.quota_min}, {stopped} ve sonrasi denetlenmedi" if stopped else ""),
          f"- **{len(done) - len(sapan)}/{len(done)} uyumlu**" + (f"; {len(sapan)} ilanda {len(other)} sapma" if sapan else ""),
          f"- state=draft (bilinen, yayin onayi bekleyen): {len(draft)} ilan", ""]
    if other:
        md += ["| listing_id | alan | beklenen | bulunan |", "|---|---|---|---|"]
        md += [f"| {i} | {f} | {e} | {g} |" for i, f, e, g in other]
    else:
        md += ["Sapma yok (state disinda)."]
    if draft:
        md += ["", "Taslak ilanlar: " + ", ".join(r[0] for r in draft)]
    text = "\n".join(md)
    log(text)
    (out / "AUDIT_REPORT.md").write_text(text + "\n", encoding="utf-8")
    (out / "audit_result.json").write_text(json.dumps(
        {"listings": done, "deviations": dev, "quota": [q0, api.remaining]}, indent=1, ensure_ascii=False))
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")


if __name__ == "__main__":
    main()
