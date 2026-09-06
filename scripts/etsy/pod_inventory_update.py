#!/usr/bin/env python3
"""
POD ilani duzenlemesi (Mo 6 Eyl 2026, Aries-Leo 4570031205 yayinda):

  IS 1  Size etiketleri v3 + SIRA (tek updateListingInventory): SKU / fiyat / adet / is_enabled /
        readiness_state_id BIREBIR korunur; yalniz Size degeri SIZE_LABEL'a cevrilir ve urunler
        oran gruplari sirasina (4:5, 3:4, 2:3, 11:14, A-series) dizilir. Geri okuma 65/65 + sira.
  IS 2  Aciklama: yalniz "✦ 13 SIZES" blogu degisir (EN updateListing PATCH, RU translations/ru PUT);
        diger bolumler birebir ayni degilse YAZMA YOK (FAIL).
  IS 3  Renk -> gorsel (variation-images GET); beklenenden farkliysa POST ile duzeltilir, raporlanir.
Dry-run: yalniz tablolar/diff. Kota < --quota-min ise yazma yok.
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
Kullanim: pod_inventory_update.py --listing-id 4570031205 --pair ARIES_LEO --out OUT --dry-run|--apply
          [--quota-min 400] [--ru-dict dict/ru_RU] [--expect-images "Midnight Blue=8484286094,..."]
"""
import argparse
import difflib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from pod_listing_create import ED_NAME, SIZE_LABEL, SIZES, build_listing, build_ru, load_ru_template, spellcheck_ru  # noqa: E402
from pod_listing_update import load_template  # noqa: E402
from wp_listing_update import norm, tags_of  # noqa: E402

# eski etiketler -> boyut anahtari (v1 oransiz, v2 EK 1 oran sonda); yeni etiket SIZE_LABEL (v3)
_V1 = {"8x10": "8x10 in (20.3×25.4 cm)", "A4": "A4 (21×29.7 cm)", "11x14": "11x14 in (27.9×35.6 cm)",
       "12x16": "12x16 in (30.5×40.6 cm)", "A3": "A3 (29.7×42 cm)", "12x18": "12x18 in (30.5×45.7 cm)",
       "16x20": "16x20 in (40.6×50.8 cm)", "16x24": "16x24 in (40.6×61 cm)", "A2": "A2 (41.9×59.4 cm)",
       "18x24": "18x24 in (45.7×61 cm)", "20x30": "20x30 in (50.8×76.2 cm)", "24x36": "24x36 in (61×91.4 cm)",
       "30x40": "30x40 in (76.2×101.6 cm)"}
_RATIO = {"8x10": "4:5", "16x20": "4:5", "12x16": "3:4", "18x24": "3:4", "30x40": "3:4", "12x18": "2:3", "16x24": "2:3",
          "20x30": "2:3", "24x36": "2:3", "11x14": "11:14", "A4": "A-series", "A3": "A-series", "A2": "A-series"}
KEY_OF = {v: k for k, v in _V1.items()}
KEY_OF.update({f"{v} · {_RATIO[k]}": k for k, v in _V1.items()})      # v2 (EK 1)
KEY_OF.update({v: k for k, v in SIZE_LABEL.items()})                    # v3 (zaten yeni ise ayni kalir)
SIZE_IDX = {k: i for i, k in enumerate(SIZES)}
# Mo 6 Eyl (11. kosu geri okumasi): renk -> image_id
EXPECT_IMAGES = {"Midnight Blue": 8484286094, "Deep Black": 8532185767, "Warm Parchment": 8532185855,
                 "Champagne Ivory": 8484286904, "Pure White": 8484287028}
SEC_EN, SEC_RU = "✦ 13 SIZES", "✦ 13 РАЗМЕРОВ"


def money(p):
    if isinstance(p, dict):
        return round(float(p.get("amount") or 0) / float(p.get("divisor") or 100), 2)
    return round(float(p or 0), 2)


def size_of(pr):
    for pv in pr.get("property_values") or []:
        if (pv.get("property_name") or "").lower() == "size" and pv.get("values"):
            return pv["values"][0]
    return None


def color_of(pr):
    for pv in pr.get("property_values") or []:
        if (pv.get("property_name") or "").lower() != "size" and pv.get("values"):
            return pv["values"][0]
    return None


def convert(inv):
    """Mevcut envanter -> PUT govdesi (yeni etiket + yeni sira) + (sku, eski, yeni, fiyat, adet) satirlari."""
    items = []
    color_order = []
    for pos, pr in enumerate(inv.get("products") or []):
        pvs, old_lbl, new_lbl, key = [], None, None, None
        for pv in pr.get("property_values") or []:
            vals = list(pv.get("values") or [])
            name = (pv.get("property_name") or "")
            if name.lower() == "size" and vals:
                key = KEY_OF.get(vals[0])
                if key is None:
                    raise SystemExit(f"HATA: Size degeri taninmadi: {vals[0]!r} (sku {pr.get('sku')})")
                old_lbl, new_lbl = vals[0], SIZE_LABEL[key]
                vals = [new_lbl]
            pvs.append({"property_id": pv.get("property_id"), "property_name": name, "values": vals})
        offs = []
        for o in pr.get("offerings") or []:
            off = {"price": money(o.get("price")), "quantity": o.get("quantity"), "is_enabled": bool(o.get("is_enabled"))}
            if o.get("readiness_state_id"):
                off["readiness_state_id"] = o["readiness_state_id"]
            offs.append(off)
        col = color_of(pr)
        if col not in color_order:
            color_order.append(col)
        items.append((color_order.index(col), SIZE_IDX.get(key, 99), pos,
                      {"sku": pr.get("sku"), "property_values": pvs, "offerings": offs},
                      (pr.get("sku"), old_lbl, new_lbl, offs[0]["price"] if offs else None, offs[0]["quantity"] if offs else None)))
    items.sort(key=lambda t: t[:3])             # renk (mevcut sira) -> yeni boyut sirasi
    products = [t[3] for t in items]
    rows = [t[4] for t in items]
    body = {"products": products, "price_on_property": inv.get("price_on_property") or [],
            "quantity_on_property": inv.get("quantity_on_property") or [], "sku_on_property": inv.get("sku_on_property") or []}
    return body, rows


def size_order(inv):
    """Envanterde Size degerlerinin ilk gorunme sirasi (Etsy menu sirasi)."""
    seen = []
    for pr in inv.get("products") or []:
        v = size_of(pr)
        if v and v not in seen:
            seen.append(v)
    return seen


def sections(desc):
    """Aciklama -> {'baslik': govde}; ilk parca (giris) anahtari ''. Bolumler '✦ ' satiriyla baslar."""
    out, key, buf = {}, "", []
    for line in norm(desc).split("\n"):
        if line.startswith("✦ "):
            out[key] = "\n".join(buf).strip(); key, buf = line, []
        else:
            buf.append(line)
    out[key] = "\n".join(buf).strip()
    return out


def desc_diff(old, new, sec_prefix):
    """(yalniz_sizes_bolumu_degisti, diff_metni). Bolum basliklari da eslesmeli (SIZES basligi haric)."""
    so, sn = sections(old), sections(new)
    ko = [k for k in so if not k.startswith(sec_prefix)]
    kn = [k for k in sn if not k.startswith(sec_prefix)]
    other_same = ko == kn and all(so[k] == sn[k] for k in ko)
    o_key = next((k for k in so if k.startswith(sec_prefix)), None)
    n_key = next((k for k in sn if k.startswith(sec_prefix)), None)
    o_txt = (o_key + "\n" + so[o_key]) if o_key else ""
    n_txt = (n_key + "\n" + sn[n_key]) if n_key else ""
    diff = "\n".join(difflib.unified_diff(o_txt.split("\n"), n_txt.split("\n"), "eski", "yeni", lineterm="", n=0))
    return other_same and n_key is not None, diff


def parse_expect(s):
    out = {}
    for part in (s or "").split(","):
        if "=" in part:
            k, v = part.split("=", 1); out[k.strip()] = int(v.strip())
    return out or dict(EXPECT_IMAGES)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--listing-id", required=True)
    ap.add_argument("--pair", default="ARIES_LEO")
    ap.add_argument("--out", required=True)
    ap.add_argument("--quota-min", type=int, default=400)
    ap.add_argument("--ru-dict", default="", help="Hunspell ru_RU (spylls) yolu; bos = RU yazim denetimi yok")
    ap.add_argument("--expect-images", default="", help="'Renk=image_id,...' (bos = script sabiti)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    pair = a.pair.upper()
    expect = parse_expect(a.expect_images)

    # sablondan yeni metinler
    title, tags, new_desc, _ = build_listing(pair, load_template())
    ru_title, ru_tags, new_ru, _ = build_ru(pair, load_ru_template())
    if a.ru_dict:
        spellcheck_ru(a.ru_dict, [ru_title, new_ru, " ".join(ru_tags)])

    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    lid = a.listing_id
    mode = "APPLY" if a.apply else "DRY-RUN"
    fails = []

    # ---- IS 1: envanter
    inv = api.get(f"/listings/{lid}/inventory") or {}
    quota_before = api.remaining
    body, rows = convert(inv)
    changed = [r for r in rows if r[1] != r[2]]
    want_order = [SIZE_LABEL[k] for k in SIZES]
    md = [f"## POD ilan duzenlemesi ({mode}) — ilan {lid} {pair} | kota once {quota_before}", "",
          "### IS 1 Size etiketleri (eski -> yeni) + sira", "",
          f"- urun: {len(rows)}; degisen etiket: {len(changed)}; SKU/fiyat/adet/gorunurluk korunur",
          f"- mevcut Size sirasi: {size_order(inv)}", f"- hedef Size sirasi: {want_order}", "",
          "| sku | eski | yeni | fiyat | adet |", "|---|---|---|---|---|"]
    md += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |" for r in rows]
    (out / "inventory_before.json").write_text(json.dumps(inv, indent=1, ensure_ascii=False))
    (out / "inventory_put.json").write_text(json.dumps(body, indent=1, ensure_ascii=False))

    # ---- IS 2: aciklama (EN + RU)
    L = api.get(f"/listings/{lid}") or {}
    old_desc = L.get("description") or ""
    en_ok, en_diff = desc_diff(old_desc, new_desc, SEC_EN)
    tru = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
    old_ru = tru.get("description") or ""
    ru_ok, ru_diff = desc_diff(old_ru, new_ru, SEC_RU)
    en_same = norm(old_desc) == norm(new_desc)
    ru_same = norm(old_ru) == norm(new_ru)
    md += ["", "### IS 2 Aciklama diff (yalniz SIZES blogu)", "",
           f"- EN: {'degisim yok' if en_same else ('yalniz SIZES blogu degisiyor -> PATCH' if en_ok else 'FAIL: SIZES disinda fark var, yazma yok')}",
           "```diff", en_diff or "(fark yok)", "```",
           f"- RU: {'degisim yok' if ru_same else ('yalniz SIZES blogu degisiyor -> PUT' if ru_ok else 'FAIL: SIZES disinda fark var / ceviri yok, yazma yok')}",
           "```diff", ru_diff or "(fark yok)", "```",
           f"- RU baslik/tag korunur: baslik {'ayni' if tru.get('title') == ru_title else 'FARKLI'}, tag {'ayni' if tags_of(tru) == ru_tags else 'FARKLI'}"]
    if not en_same and not en_ok:
        fails.append("EN aciklama SIZES disinda fark")
    if not ru_same and not ru_ok:
        fails.append("RU aciklama SIZES disinda fark")

    # ---- IS 3: renk -> gorsel
    vimg = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
    got = {v.get("value"): v.get("image_id") for v in vimg}
    md += ["", "### IS 3 Renk -> gorsel", "", "| renk | beklenen | okunan | sonuc |", "|---|---|---|---|"]
    md += [f"| {c} | {expect[c]} | {got.get(c)} | {'PASS' if got.get(c) == expect[c] else 'FARK -> POST'} |" for c in expect]

    status = mode
    if a.apply:
        try:
            rem = int(quota_before or 0)
        except ValueError:
            rem = 0
        if fails:
            status = "FAIL " + "; ".join(fails)
        elif quota_before is not None and rem < a.quota_min:
            status = f"KOTA({rem}<{a.quota_min}) yazma yok"
        else:
            res = []
            # IS 1
            api.put_json(f"/listings/{lid}/inventory", body)
            back = api.get(f"/listings/{lid}/inventory") or {}
            want = {r[0]: (r[2], r[3], r[4]) for r in rows}
            got_inv = {pr.get("sku"): (size_of(pr), money((pr.get("offerings") or [{}])[0].get("price")), (pr.get("offerings") or [{}])[0].get("quantity"))
                       for pr in back.get("products") or []}
            bad = [(s, want[s], got_inv.get(s)) for s in want if got_inv.get(s) != want[s]]
            order_ok = size_order(back) == want_order
            res.append(f"envanter {len(want) - len(bad)}/{len(want)}" + ("" if not bad else f" FAIL {bad[:5]}") + f"; sira {'PASS' if order_ok else 'FAIL ' + str(size_order(back))}")
            if bad or not order_ok:
                fails.append("envanter")
            (out / "inventory_after.json").write_text(json.dumps(back, indent=1, ensure_ascii=False))
            # IS 2
            if not en_same:
                api.patch(f"/shops/{shop}/listings/{lid}", {"description": new_desc})
            if not ru_same:
                tpath = f"/shops/{shop}/listings/{lid}/translations/ru"
                tbody = {"title": ru_title, "description": new_ru, "tags": ",".join(ru_tags)}
                (api.put if tru else api.post)(tpath, tbody)
            L2 = api.get(f"/listings/{lid}") or {}
            tru2 = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
            en_back = norm(L2.get("description")) == norm(new_desc)
            ru_back = norm(tru2.get("description")) == norm(new_ru) and tru2.get("title") == ru_title
            res.append(f"aciklama EN {'PASS' if en_back else 'FAIL'}, RU {'PASS' if ru_back else 'FAIL'}; state {L2.get('state')}")
            if not (en_back and ru_back):
                fails.append("aciklama")
            # IS 3: envanter PUT'u renk deger id'lerini yenileyebilir (EK 1 sonrasi 4 renk bagsiz kaldi) -> PUT SONRASI yeniden oku
            vimg2 = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
            got2 = {v.get("value"): v.get("image_id") for v in vimg2}
            if any(got2.get(c) != expect[c] for c in expect):
                vid_of, pid = {}, None
                for pr in back.get("products") or []:            # deger id'leri PUT sonrasi envanterden
                    for pv in pr.get("property_values") or []:
                        if (pv.get("property_name") or "").lower() != "size" and pv.get("values"):
                            pid = pid or pv.get("property_id"); vid_of.setdefault(pv["values"][0], (pv.get("value_ids") or [None])[0])
                missing = [c for c in expect if vid_of.get(c) is None]
                if pid is None or missing:
                    fails.append(f"renk->gorsel value_id yok {missing}")
                else:
                    api.post_json(f"/shops/{shop}/listings/{lid}/variation-images",
                                  {"variation_images": [{"property_id": pid, "value_id": vid_of[c], "image_id": expect[c]} for c in expect]})
                    vimg3 = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
                    got3 = {v.get("value"): v.get("image_id") for v in vimg3}
                    n_ok = sum(1 for c in expect if got3.get(c) == expect[c])
                    res.append(f"renk->gorsel POST ile duzeltildi {n_ok}/{len(expect)} {'PASS' if n_ok == len(expect) else 'FAIL ' + str(got3)}")
                    if n_ok != len(expect):
                        fails.append("renk->gorsel")
            else:
                res.append(f"renk->gorsel {len(expect)}/{len(expect)} PASS (PUT sonrasi degisim yok)")
            status = ("PASS" if not fails else "FAIL") + " | " + " | ".join(res)
    md += ["", f"**Durum: {status}** | kota once {quota_before} / sonra {api.remaining}"]
    text = "\n".join(md)
    log(text)
    (out / "INVENTORY_REPORT.md").write_text(text + "\n", encoding="utf-8")
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    if status.startswith("FAIL") or status.startswith("KOTA"):
        sys.exit(1)


if __name__ == "__main__":
    main()
