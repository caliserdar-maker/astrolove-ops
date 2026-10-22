#!/usr/bin/env python3
"""SALT OKUMA (Etsy'ye yazma YOK) - Serdar karari 25 Eyl, 26 Eyl 07:30 isi.
 (1) Tek ilan: getListing + getListingFiles -> type, when_made, is_made_to_order (varsa), state, dosya sayisi.
 (2) 78 POD ilani (Drive TEMP/YAYILIM_78/METIN_78.csv ilan_id): getListingsByListingIds (100'luk parti) ->
     who_made, when_made, shipping_profile_id, processing_min/max, production_partners (API veriyorsa);
     magaza production partner listesi; kullanilan her kargo profili icin getShopShippingProfile (+destinations):
     acik ulkeler, processing min/max.
 Cikti: out/POD_URETIM_KARGO_API.csv + out/POD_KARGO_ULKELER.csv -> Drive DIJITAL_78.
 Kota tabani: x-remaining-today < 230 olursa DUR.
Kullanim: pod_uretim_kargo_oku.py <tek_ilan_id> <metin78_csv>"""
import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

KOTA_TABAN = 230
OUT = Path("out")


def kota_ok(api, adim):
    try:
        kalan = int(api.remaining) if api.remaining is not None else None
    except ValueError:
        kalan = None
    print(f"  kota: {kalan} ({adim}, cagri {api.calls})", flush=True)
    if kalan is not None and kalan < KOTA_TABAN:
        print(f"::warning::DUR: kota {kalan} < {KOTA_TABAN} ({adim})", flush=True)
        sys.exit(2)


def main():
    tek, metin78 = sys.argv[1], sys.argv[2]
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]
    OUT.mkdir(exist_ok=True)

    # (1) tek ilan
    print(f"== (1) ilan {tek} (salt okuma)", flush=True)
    L = api.get(f"/listings/{tek}", ok404=True) or {}
    F = api.get(f"/shops/{shop}/listings/{tek}/files", ok404=True) or {}
    print("  " + json.dumps({"listing_id": L.get("listing_id"), "type": L.get("type"), "when_made": L.get("when_made"),
                             "is_made_to_order": L.get("is_made_to_order", "ALAN YOK"), "state": L.get("state"),
                             "who_made": L.get("who_made"), "dosya_sayisi": F.get("count", len(F.get("results") or []))},
                            ensure_ascii=False), flush=True)
    kota_ok(api, "tek ilan")

    # (2) 78 POD
    ids = [r["ilan_id"] for r in csv.DictReader(open(metin78, encoding="utf-8")) if r.get("ilan_id")]
    print(f"== (2) {len(ids)} POD ilani (getListingsByListingIds)", flush=True)
    ilanlar = []
    for i in range(0, len(ids), 100):
        d = api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100])}) or {}
        ilanlar += d.get("results") or []
        kota_ok(api, f"batch {i // 100 + 1}")
    bulunan = {str(x.get("listing_id")) for x in ilanlar}
    eksik = [x for x in ids if x not in bulunan]
    pp = api.get(f"/shops/{shop}/production-partners", ok404=True) or {}
    pp_list = [{"id": p.get("production_partner_id"), "ad": p.get("partner_name"), "yer": p.get("location")}
               for p in pp.get("results") or []]
    print(f"  magaza production partner: {json.dumps(pp_list, ensure_ascii=False)}", flush=True)
    profiller = sorted({str(x.get("shipping_profile_id")) for x in ilanlar if x.get("shipping_profile_id")})
    prof = {}
    for pid in profiller:
        prof[pid] = api.get(f"/shops/{shop}/shipping-profiles/{pid}", ok404=True) or {}
        kota_ok(api, f"profil {pid}")

    with open(OUT / "POD_URETIM_KARGO_API.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["ilan_id", "state", "who_made", "when_made", "is_made_to_order", "shipping_profile_id", "profil_adi",
                    "processing_min", "processing_max", "processing_birim", "production_partners"])
        for x in ilanlar:
            p = prof.get(str(x.get("shipping_profile_id"))) or {}
            w.writerow([x.get("listing_id"), x.get("state"), x.get("who_made"), x.get("when_made"),
                        x.get("is_made_to_order", ""), x.get("shipping_profile_id"), p.get("title", ""),
                        x.get("processing_min", p.get("min_processing_days")), x.get("processing_max", p.get("max_processing_days")),
                        p.get("processing_days_display_label", ""),
                        ";".join(str(y.get("production_partner_id")) for y in x.get("production_partners") or [])
                        if "production_partners" in x else "API VERMIYOR"])
    with open(OUT / "POD_KARGO_ULKELER.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["shipping_profile_id", "profil_adi", "origin", "destination_country_iso", "destination_region",
                    "primary_cost", "secondary_cost", "shipping_carrier_id", "mail_class", "min_delivery_days",
                    "max_delivery_days", "min_processing_days", "max_processing_days"])
        for pid, p in prof.items():
            for d in p.get("shipping_profile_destinations") or []:
                w.writerow([pid, p.get("title"), p.get("origin_country_iso"), d.get("destination_country_iso"),
                            d.get("destination_region"), (d.get("primary_cost") or {}).get("amount"),
                            (d.get("secondary_cost") or {}).get("amount"), d.get("shipping_carrier_id"),
                            d.get("mail_class"), d.get("min_delivery_days"), d.get("max_delivery_days"),
                            p.get("min_processing_days"), p.get("max_processing_days")])

    def say(alan):
        c = {}
        for x in ilanlar:
            c[str(x.get(alan))] = c.get(str(x.get(alan)), 0) + 1
        return c
    print("OZET " + json.dumps({
        "ilan": len(ilanlar), "eksik": eksik, "state": say("state"), "who_made": say("who_made"), "when_made": say("when_made"),
        "profil": {pid: {"ad": prof[pid].get("title"), "ilan": sum(1 for x in ilanlar if str(x.get("shipping_profile_id")) == pid),
                         "processing": [prof[pid].get("min_processing_days"), prof[pid].get("max_processing_days")],
                         "ulke": sorted({d.get("destination_country_iso") or d.get("destination_region")
                                         for d in prof[pid].get("shipping_profile_destinations") or []})}
                   for pid in prof},
        "production_partners_alani": sum(1 for x in ilanlar if "production_partners" in x),
        "cagri": api.calls, "kota_son": api.remaining}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
