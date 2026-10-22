#!/usr/bin/env python3
"""SALT OKUMA (Etsy'ye yazma YOK): verilen ilanlarin envanteri + ilan alanlari + kargo profili, karsilastirma tablosu.
Serdar 22 Eki: yil donumu ilanlarinda canli sayfada "This option is sold out" -> neden arastirmasi.
Cikti: <out>/ENVANTER_<id>.json (ham), <out>/KARSILASTIRMA.md (urun basina ozellik degerleri, quantity, is_enabled, price,
readiness; ilan quantity/state/profil/hazirlik; profil hedefleri). Log'a yalniz tablo (sir yok).
Kullanim: envanter_oku.py --ids 4595350971,4595373902,4595421558 --out OUT"""
import argparse
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

ILAN_ALAN = ("state", "quantity", "has_variations", "listing_type", "shipping_profile_id", "readiness_state_id",
             "processing_min", "processing_max", "is_personalizable", "personalization_is_required")


def para(p):
    return round(p["amount"] / p["divisor"], 2) if isinstance(p, dict) else p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api, shop = Etsy(store), os.environ["ETSY_SHOP_ID"]
    md, profiller = ["# ENVANTER KARSILASTIRMA (salt okuma)", ""], {}
    for lid in [x.strip() for x in a.ids.split(",") if x.strip()]:
        x = api.get(f"/listings/{lid}") or {}
        inv = api.get(f"/listings/{lid}/inventory") or {}
        vi = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
        (out / f"ENVANTER_{lid}.json").write_text(json.dumps({"ilan": x, "envanter": inv, "variation_images": vi}, ensure_ascii=False, indent=1),
                                                 encoding="utf-8")
        profiller.setdefault(x.get("shipping_profile_id"), [])
        md += [f"## {lid}", "", "ilan: " + ", ".join(f"{a_}={x.get(a_)}" for a_ in ILAN_ALAN),
               "on_property: " + ", ".join(f"{a_}={inv.get(a_)}" for a_ in ("price_on_property", "quantity_on_property", "sku_on_property",
                                                                              "readiness_state_on_property")),
               "", "| sku | ozellikler (property_id:deger[value_id]) | quantity | is_enabled | is_deleted | price | readiness |", "|---|---|---|---|---|---|---|"]
        for p in inv.get("products") or []:
            pv = " ; ".join(f"{v.get('property_id')}:{'/'.join(v.get('values') or [])}{v.get('value_ids')}" for v in p.get("property_values") or [])
            for o in p.get("offerings") or []:
                md.append(f"| {p.get('sku')} | {pv} | {o.get('quantity')} | {o.get('is_enabled')} | {o.get('is_deleted')} | "
                          f"{para(o.get('price'))} | {o.get('readiness_state_id')} |")
        md += [f"- urun {len(inv.get('products') or [])} | stil-gorsel bagi {len(vi)}", ""]
    for pid in profiller:
        sp = api.get(f"/shops/{shop}/shipping-profiles/{pid}", ok404=True) or {}
        hedef = sp.get("shipping_profile_destinations") or []
        md += [f"## kargo profili {pid}: {sp.get('title')}", f"- origin {sp.get('origin_country_iso')} | processing "
               f"{sp.get('min_processing_days')}-{sp.get('max_processing_days')} | hedef {len(hedef)}"]
        md += [f"  - {d.get('destination_country_iso') or d.get('destination_region')}: {para(d.get('primary_cost'))} "
               f"({d.get('min_delivery_days')}-{d.get('max_delivery_days')} gun)" for d in hedef]
        (out / f"PROFIL_{pid}.json").write_text(json.dumps(sp, ensure_ascii=False, indent=1), encoding="utf-8")
    md.append(f"\n- istek {api.calls} | kota {api.remaining}")
    (out / "KARSILASTIRMA.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
