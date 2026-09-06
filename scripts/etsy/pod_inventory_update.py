#!/usr/bin/env python3
"""
POD ilani envanter guncellemesi: Size degerlerine oran etiketi (EK 1, Mo 6 Eyl 2026).

Mevcut envanter GET ile okunur; her urunun SKU / fiyat / adet / is_enabled / readiness_state_id
BIREBIR korunur, yalniz Size property degeri yeni etikete cevrilir
("18x24 in (45.7×61 cm) · 3:4", A4/A3/A2 icin "· A-series"). Tek updateListingInventory (PUT).
Dry-run: eski -> yeni tablo, yazma yok. Apply: PUT + geri okuma (65/65 SKU + fiyat + etiket).
Kota < --quota-min ise yazma yok (rapor). Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
Kullanim: pod_inventory_update.py --listing-id 4570031205 --out OUT --dry-run|--apply [--quota-min 400]
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from pod_listing_create import SIZE_LABEL, SIZES  # noqa: E402

# eski etiket (oransiz) -> boyut anahtari; yeni etiket SIZE_LABEL (oranli)
OLD_LABEL = {"8x10": "8x10 in (20.3×25.4 cm)", "A4": "A4 (21×29.7 cm)", "11x14": "11x14 in (27.9×35.6 cm)",
             "12x16": "12x16 in (30.5×40.6 cm)", "A3": "A3 (29.7×42 cm)", "12x18": "12x18 in (30.5×45.7 cm)",
             "16x20": "16x20 in (40.6×50.8 cm)", "16x24": "16x24 in (40.6×61 cm)", "A2": "A2 (41.9×59.4 cm)",
             "18x24": "18x24 in (45.7×61 cm)", "20x30": "20x30 in (50.8×76.2 cm)", "24x36": "24x36 in (61×91.4 cm)",
             "30x40": "30x40 in (76.2×101.6 cm)"}
KEY_OF = {v: k for k, v in OLD_LABEL.items()}
KEY_OF.update({v: k for k, v in SIZE_LABEL.items()})          # zaten yeni etiketliyse ayni kalir


def money(p):
    if isinstance(p, dict):
        return round(float(p.get("amount") or 0) / float(p.get("divisor") or 100), 2)
    return round(float(p or 0), 2)


def convert(inv):
    """Mevcut envanter -> PUT govdesi + (sku, eski etiket, yeni etiket, fiyat) satirlari."""
    products, rows = [], []
    for pr in inv.get("products") or []:
        pvs, old_lbl, new_lbl = [], None, None
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
        products.append({"sku": pr.get("sku"), "property_values": pvs, "offerings": offs})
        rows.append((pr.get("sku"), old_lbl, new_lbl, offs[0]["price"] if offs else None, offs[0]["quantity"] if offs else None))
    body = {"products": products, "price_on_property": inv.get("price_on_property") or [],
            "quantity_on_property": inv.get("quantity_on_property") or [], "sku_on_property": inv.get("sku_on_property") or []}
    return body, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--listing-id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--quota-min", type=int, default=400)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    lid = a.listing_id
    inv = api.get(f"/listings/{lid}/inventory") or {}
    quota_before = api.remaining
    body, rows = convert(inv)
    changed = [r for r in rows if r[1] != r[2]]
    md = [f"## Envanter Size etiketi ({'APPLY' if a.apply else 'DRY-RUN'}) — ilan {lid} | kota once {quota_before}", "",
          f"- urun: {len(rows)}; degisen etiket: {len(changed)}; SKU/fiyat/adet/gorunurluk korunur", "",
          "| sku | eski | yeni | fiyat | adet |", "|---|---|---|---|---|"]
    md += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |" for r in rows]
    (out / "inventory_before.json").write_text(json.dumps(inv, indent=1, ensure_ascii=False))
    (out / "inventory_put.json").write_text(json.dumps(body, indent=1, ensure_ascii=False))
    status = "DRY-RUN"
    if a.apply:
        if not changed:
            status = "DEGISIM_YOK"
        else:
            try:
                rem = int(quota_before or 0)
            except ValueError:
                rem = 0
            if quota_before is not None and rem < a.quota_min:
                status = f"KOTA({rem}<{a.quota_min}) yazma yok"
            else:
                api.put_json(f"/listings/{lid}/inventory", body)
                back = api.get(f"/listings/{lid}/inventory") or {}
                want = {r[0]: (r[2], r[3]) for r in rows}
                got = {}
                for pr in back.get("products") or []:
                    lbl = next((pv["values"][0] for pv in pr.get("property_values") or [] if (pv.get("property_name") or "").lower() == "size" and pv.get("values")), None)
                    got[pr.get("sku")] = (lbl, money((pr.get("offerings") or [{}])[0].get("price")))
                ok = [s for s in want if got.get(s) == want[s]]
                bad = [(s, want[s], got.get(s)) for s in want if got.get(s) != want[s]]
                status = f"PASS {len(ok)}/{len(want)}" if not bad else f"FAIL {len(ok)}/{len(want)}: {bad[:5]}"
                (out / "inventory_after.json").write_text(json.dumps(back, indent=1, ensure_ascii=False))
    md += ["", f"**Durum: {status}** | kota sonra {api.remaining}"]
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
