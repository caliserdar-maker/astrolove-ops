#!/usr/bin/env python3
"""BIZIM YILIMIZ: CANCER_LIBRA taslak HAZIRLIGI (14 Eki 2026, Takip gorevi). ILAN ACMA YOK, PATCH YOK, canli ilana yazma YOK.

Tek yazma: magaza bolumu "1st Anniversary Gifts" (Serdar onayli) - yalniz yoksa ve bolum sayisi < 20 ise POST /shops/{shop}/sections.
Geri kalan her sey GET (+ Etsy OAS dosyasi, statik). Cikti: <out>/BY_TASLAK_HAZIRLIK.json + .md + PAYLOAD_*.json (GONDERILMEZ).

Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE, CSV (BIZIM_YILIMIZ_78_ILAN_METIN.csv), OUT
"""
import csv
import json
import os
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

REF_LISTING = 4570143815          # canli CANCER_LIBRA (referans; yalniz okunur)
PAIR = "CANCER_LIBRA"
SECTION_TITLE = "1st Anniversary Gifts"
SECTION_MAX = 20
OAS = "https://www.etsy.com/openapi/generated/oas/3.0.0.json"
STYLES = ["Starlit", "Timeless", "First Page", "Layers", "Botanical"]
FORMATS = [("Printable card 5x7", 5.00, "CARD5X7"), ("Digital file 8x10", 9.00, "DIGI8X10"), ("Print 8x10", 29.00, "PRINT8X10")]
SECTION_RE = re.compile(r"^/shops/\d+/sections$")


class SadeceBolum(Etsy):
    """Yazma kilidi: yalniz POST /shops/{shop}/sections. Diger her yazma cagrisi programi durdurur."""
    def patch(self, *a, **k):
        raise SystemExit("YASAK: PATCH")

    def put(self, *a, **k):
        raise SystemExit("YASAK: PUT")

    def put_json(self, *a, **k):
        raise SystemExit("YASAK: PUT")

    def post_json(self, *a, **k):
        raise SystemExit("YASAK: POST json")

    def delete(self, *a, **k):
        raise SystemExit("YASAK: DELETE")

    def post_file(self, *a, **k):
        raise SystemExit("YASAK: dosya yukleme")

    def post(self, path, data):
        if not SECTION_RE.match(path):
            raise SystemExit(f"YASAK: POST {path}")
        return super().post(path, data)


def oas_ozet():
    """Etsy OAS (statik dosya): kisisellestirme sorulari semasi + reklam/ads uclari var mi."""
    d = requests.get(OAS, timeout=120).json()
    paths = d.get("paths", {})
    S = d.get("components", {}).get("schemas", {})
    pers = {}
    for p, ops in paths.items():
        if "personaliz" in p.lower():
            for m, op in ops.items():
                if not isinstance(op, dict):
                    continue
                body = (((op.get("requestBody") or {}).get("content") or {}))
                pers[f"{m.upper()} {p}"] = dict(operationId=op.get("operationId"), summary=(op.get("summary") or "")[:200],
                                               description=(op.get("description") or "")[:600], body=json.dumps(body)[:5000])
    sema = {k: json.dumps(v)[:2500] for k, v in S.items() if "ersonaliz" in k}
    ads = sorted({p for p in paths if re.search(r"(^|/)(ads?|advert\w*|promot\w*|marketing)(/|$)", p.lower())})
    listing_ads = {}
    for k, v in S.items():
        if k.lower().endswith("shoplisting") or k == "ShopListing":
            for f in (v.get("properties") or {}):
                if re.search(r"ad|promot|market", f.lower()):
                    listing_ads[f] = (v["properties"][f].get("description") or "")[:200]
    return dict(personalization_uclari=pers, personalization_semalari=sema, ads_uclari=ads, listing_ads_alanlari=listing_ads,
                oas_surum=d.get("info", {}).get("version"))


def main():
    out = Path(os.environ.get("OUT", "_out")); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = SadeceBolum(store)
    shop = os.environ["ETSY_SHOP_ID"]
    R = {}

    # 1) bolum
    secs = (api.get(f"/shops/{shop}/sections") or {}).get("results") or []
    R["bolumler_once"] = [(x.get("shop_section_id"), x.get("title"), x.get("active_listing_count")) for x in secs]
    var = [x for x in secs if (x.get("title") or "").strip().lower() == SECTION_TITLE.lower()]
    if var:
        R["bolum"] = dict(id=var[0]["shop_section_id"], durum="zaten vardi, acilmadi")
    elif len(secs) >= SECTION_MAX:
        R["bolum"] = dict(id=None, durum=f"ACILMADI: bolum sayisi {len(secs)} >= {SECTION_MAX}")
    else:
        r = api.post(f"/shops/{shop}/sections", {"title": SECTION_TITLE}) or {}
        secs2 = (api.get(f"/shops/{shop}/sections") or {}).get("results") or []
        yeni = [x for x in secs2 if (x.get("title") or "").strip().lower() == SECTION_TITLE.lower()]
        R["bolum"] = dict(id=(yeni[0]["shop_section_id"] if yeni else r.get("shop_section_id")), durum="acildi",
                          dogrulama=bool(yeni), bolum_sayisi_sonra=len(secs2))

    # 2) referans ilan (salt okuma)
    L = api.get(f"/listings/{REF_LISTING}") or {}
    alan = ["listing_id", "state", "title", "shop_section_id", "shipping_profile_id", "return_policy_id", "taxonomy_id", "listing_type",
            "who_made", "when_made", "is_supply", "should_auto_renew", "is_personalizable", "personalization_is_required",
            "personalization_char_count_max", "personalization_instructions", "materials", "style", "processing_min", "processing_max",
            "production_partners", "is_customizable", "has_variations", "quantity", "item_weight", "item_dimensions_unit", "language"]
    R["referans_ilan"] = {a: L.get(a) for a in alan}
    props = (api.get(f"/shops/{shop}/listings/{REF_LISTING}/properties", ok404=True) or {}).get("results") or []
    R["nitelikler"] = [dict(property_id=p.get("property_id"), ad=p.get("property_name"), degerler=p.get("values"),
                            value_ids=p.get("value_ids"), scale_id=p.get("scale_id")) for p in props]
    inv = api.get(f"/listings/{REF_LISTING}/inventory") or {}
    prods = inv.get("products") or []
    rs = sorted({o.get("readiness_state_id") for p in prods for o in (p.get("offerings") or []) if o.get("readiness_state_id")})
    R["envanter"] = dict(urun_sayisi=len(prods), price_on_property=inv.get("price_on_property"), sku_on_property=inv.get("sku_on_property"),
                         quantity_on_property=inv.get("quantity_on_property"), readiness_state_ids=rs,
                         ozellikler=sorted({(v.get("property_id"), v.get("property_name")) for p in prods for v in (p.get("property_values") or [])}))
    rsd = (api.get(f"/shops/{shop}/readiness-state-definitions") or {}).get("results") or []
    R["hazirlik_durumlari"] = [dict(id=x.get("readiness_state_id"), durum=x.get("readiness_state"), min_gun=x.get("min_processing_days"),
                                    max_gun=x.get("max_processing_days"), birim=x.get("processing_days_display_label")) for x in rsd]
    if L.get("shipping_profile_id"):
        sp = api.get(f"/shops/{shop}/shipping-profiles/{L['shipping_profile_id']}", ok404=True) or {}
        R["kargo_profili"] = dict(id=sp.get("shipping_profile_id"), ad=sp.get("title"), cikis_ulke=sp.get("origin_country_iso"),
                                  min_islem=sp.get("min_processing_days"), max_islem=sp.get("max_processing_days"),
                                  hedefler=[(d.get("destination_country_iso") or d.get("destination_region"), d.get("primary_cost", {}).get("amount") if isinstance(d.get("primary_cost"), dict) else d.get("primary_cost"),
                                             d.get("min_delivery_days"), d.get("max_delivery_days"), d.get("shipping_carrier_id")) for d in (sp.get("shipping_profile_destinations") or [])],
                                  ust_secenekler=len(sp.get("shipping_profile_upgrades") or []))
    if L.get("return_policy_id"):
        rp = api.get(f"/shops/{shop}/policies/return/{L['return_policy_id']}", ok404=True) or {}
        R["iade_politikasi"] = {a: rp.get(a) for a in ("return_policy_id", "accepts_returns", "accepts_exchanges", "return_deadline")}
    pp = (api.get(f"/shops/{shop}/production-partners", ok404=True) or {}).get("results") or []
    R["uretim_ortaklari"] = [(x.get("production_partner_id"), x.get("partner_name"), x.get("location")) for x in pp]
    R["referans_kisisellestirme"] = api.get(f"/listings/{REF_LISTING}/personalization", ok404=True)   # OAS: getListingPersonalization
    bl = (api.get("/listings/batch", params={"listing_ids": str(REF_LISTING), "includes": "personalization"}, ok404=True) or {}).get("results") or [{}]
    R["referans_kisisellestirme_batch"] = {k_: v for k_, v in bl[0].items() if "ersonaliz" in k_}
    tx = api.get(f"/seller-taxonomy/nodes/{L.get('taxonomy_id')}/properties", ok404=True) if L.get("taxonomy_id") else None
    R["kategori_ozellikleri"] = [(p.get("property_id"), p.get("name"), p.get("supports_variations"), p.get("is_required"))
                                 for p in ((tx or {}).get("results") or [])]

    # 3-4) OAS: kisisellestirme semasi + reklam uclari
    try:
        R["oas"] = oas_ozet()
    except Exception as e:  # OAS erisilemezse rapora yazilir
        R["oas"] = dict(hata=str(e)[:300])

    # 5) PAYLOAD (GONDERILMEZ)
    row = next(r for r in csv.DictReader(open(os.environ["CSV"], encoding="utf-8")) if r["cift"] == PAIR)
    tags = [row[f"etiket_{i}"] for i in range(1, 14)]
    rsid = rs[0] if len(rs) == 1 else None
    create = dict(quantity=999, title=row["baslik"], description=row["aciklama"], price=5.00, who_made=L.get("who_made"),
                  when_made=L.get("when_made"), taxonomy_id=L.get("taxonomy_id"), shipping_profile_id=L.get("shipping_profile_id"),
                  return_policy_id=L.get("return_policy_id"), shop_section_id=R["bolum"].get("id"), readiness_state_id=rsid,
                  tags=",".join(tags), type="physical", is_supply="false", should_auto_renew="true",
                  is_personalizable="true", personalization_is_required="true",
                  production_partner_ids=",".join(str(x.get("production_partner_id")) for x in (L.get("production_partners") or [])) or None,
                  materials="ACIK SORU (canli ilandaki Hahnemuhle ifadesi yeni ilanda kullanilmaz)")
    # OAS 3.0.0: POST /shops/{shop}/listings/{id}/personalization (updateListingPersonalization); question_type enum
    # text_input|dropdown|unlabeled_upload|labeled_upload; "Currently, only a single question with type 'text_input' is supported";
    # question_text 1..45 karakter; dropdown'da instructions yok. Bu yuzden: 1 dropdown (Top line) + 1 text_input (diger 4 bilgi).
    pers = dict(personalization_questions=[
        dict(question_text="Top line", question_type="dropdown", required=True,
             options=[dict(label="Paper Anniversary"), dict(label="Our First Year")]),
        dict(question_text="Names, date and optional line", question_type="text_input", required=True, max_allowed_characters=100,
             instructions="Please write on separate lines: 1) Name under Cancer (max 11 letters) 2) Name under Libra (max 11 letters) "
                          "3) Special date, e.g. 14 June 2025 4) Optional short line, max 20 characters, replaces Year One")])
    pers_alternatif_5_alan = dict(not_="OAS'a gore REDDEDILIR (tek text_input); yalniz karsilastirma icin", personalization_questions=[
        dict(question_text=q, question_type="text_input", required=r, max_allowed_characters=m)
        for q, r, m in (("Name under Cancer", True, 11), ("Name under Libra", True, 11), ("Special date", True, 20),
                        ("Top line", True, 20), ("Short line (optional)", False, 20))])
    prodsP = []
    for st in STYLES:
        for fm, pr, kod in FORMATS:
            prodsP.append(dict(sku=f"BY-CAN_LIB-{st.replace(' ', '').upper()[:6]}-{kod}",
                               property_values=[dict(property_id=513, property_name="Style", values=[st]),
                                                dict(property_id=514, property_name="Format", values=[fm])],
                               offerings=[dict(price=pr, quantity=999, is_enabled=True, readiness_state_id=rsid)]))
    inventory = dict(products=prodsP, price_on_property=[514], quantity_on_property=[], sku_on_property=[513, 514])
    gorseller = ["01_Cover_A.jpg", "02_Shared_Symbol_A.jpg", "03_Five_Styles_A.jpg", "04_Personalization_A.jpg", "05_Starlit_Timeless_A.jpg",
                 "06_FirstPage_Botanical_A.jpg", "07_Layers_Material_A.jpg", "08_Formats_A.jpg", "09_Size_Gift_Scene_A.jpg", "10_Free_Preview_A.jpg"]
    for n, b in (("PAYLOAD_1_createDraftListing.json", create), ("PAYLOAD_2_personalization_POST.json", pers), ("PAYLOAD_2b_5alan_REDDEDILIR.json", pers_alternatif_5_alan),
                 ("PAYLOAD_3_inventory.json", inventory), ("PAYLOAD_4_gorseller.json", dict(sira=gorseller, kaynak="Drive TEMP/BIZIM_YILIMIZ_78_20261014_v2/CANCER_LIBRA/galeri"))):
        json.dump(b, open(out / n, "w"), indent=1, ensure_ascii=False)
    R["payload_ozet"] = dict(baslik_uzunluk=len(row["baslik"]), etiket=len(tags), urun=len(prodsP), fiyatlar={f: p for f, p, _ in FORMATS},
                             readiness_state_id=rsid, shop_section_id=R["bolum"].get("id"),
                             sku_max_uzunluk=max(len(p["sku"]) for p in prodsP))
    R["kota_kalan"] = api.remaining
    R["cagri"] = api.calls
    json.dump(R, open(out / "BY_TASLAK_HAZIRLIK.json", "w"), indent=1, ensure_ascii=False, default=str)
    print(json.dumps({k_: R[k_] for k_ in ("bolum", "payload_ozet", "kota_kalan", "cagri")}, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
