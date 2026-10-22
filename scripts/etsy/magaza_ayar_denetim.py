#!/usr/bin/env python3
"""Etsy magaza ayarlarini salt okunur olarak indirir ve cevrimdisi denetler.

Canli: ``magaza_ayar_denetim.py etsy SNAPSHOT.json``
Cevrimdisi: ``magaza_ayar_denetim.py denetle SNAPSHOT.json RAPOR.csv ONERI.txt``
"""
import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from canli_metin_tara import FORBIDDEN  # noqa: E402
from etsy_common import Etsy, TokenStore, mask  # noqa: E402
from pod_listing_create import PARTNER_NAME  # noqa: E402

POD_PROFILE_ID = 314711751541
TEXT_FIELDS = ("title", "announcement", "about")


def _results(value):
    return (value or {}).get("results") or []


def fetch_pagewise(api, path, limit=100):
    rows, offset = [], 0
    while True:
        page = api.get(path, {"limit": limit, "offset": offset}) or {}
        got = _results(page)
        rows.extend(got)
        if len(got) < limit:
            return rows
        offset += limit


def fetch(output):
    """Yalniz GET yapar; OAuth yenilenirse TokenStore .updated olusturur."""
    key, secret = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(key); mask(secret)
    store = TokenStore(os.environ["TOKEN_FILE"], key, secret)
    if store.needs_refresh():
        store.refresh()
    api, shop = Etsy(store), os.environ["ETSY_SHOP_ID"]
    listings = fetch_pagewise(api, f"/shops/{shop}/listings", 100)
    profiles = fetch_pagewise(api, f"/shops/{shop}/shipping-profiles", 100)
    # Liste yaniti destinasyon/upgrade ayrintilarini vermeyebilir.
    detailed_profiles = []
    for profile in profiles:
        pid = profile["shipping_profile_id"]
        detail = api.get(f"/shops/{shop}/shipping-profiles/{pid}") or profile
        detail["shipping_profile_upgrades"] = _results(
            api.get(f"/shops/{shop}/shipping-profiles/{pid}/upgrades", ok404=True)
        )
        detailed_profiles.append(detail)
    profiles = detailed_profiles
    payload = {
        "shop": api.get(f"/shops/{shop}") or {},
        "sections": fetch_pagewise(api, f"/shops/{shop}/sections", 100),
        "shipping_profiles": profiles,
        "return_policies": fetch_pagewise(api, f"/shops/{shop}/policies/return", 100),
        "production_partners": fetch_pagewise(api, f"/shops/{shop}/production-partners", 100),
        "listings": listings,
    }
    Path(output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot: {len(listings)} ilan, {len(profiles)} kargo profili, {api.calls} GET")


def _add(rows, area, object_id, rule, ok, detail, suggestion):
    rows.append({"alan": area, "nesne_id": str(object_id or "-"), "kural": rule,
                 "durum": "PASS" if ok else "FAIL", "ayrinti": detail,
                 "duzeltme_onerisi": "-" if ok else suggestion})


def audit(data):
    rows = []
    listings = data.get("listings") or []
    profiles = data.get("shipping_profiles") or []
    profile_by_id = {str(p.get("shipping_profile_id")): p for p in profiles}
    used_profiles = {str(x.get("shipping_profile_id")) for x in listings if x.get("shipping_profile_id")}
    for pid in sorted(used_profiles):
        _add(rows, "kargo", pid, "ilan_profili_var", pid in profile_by_id,
             "profil bulundu" if pid in profile_by_id else "ilanin profili listede yok",
             "Ilandaki kargo profilini mevcut bir profile baglayin.")
    for pid, profile in profile_by_id.items():
        lo, hi = profile.get("min_processing_days"), profile.get("max_processing_days")
        valid = lo is not None and hi is not None and isinstance(lo, int) and isinstance(hi, int) and 0 <= lo <= hi
        _add(rows, "kargo", pid, "processing_min_max", valid, f"min={lo}, max={hi}",
             "Profilde processing min/max degerlerini gecerli ve sirali girin.")
        destinations = profile.get("shipping_profile_destinations") or []
        details = [{"ulke": d.get("destination_country_iso"), "bolge": d.get("destination_region"),
                    "ucretsiz": d.get("primary_cost", {}).get("amount") in (0, "0", "0.00"),
                    "upgrade": d.get("shipping_upgrade_id") or d.get("upgrades") or []}
                   for d in destinations]
        details.append({"profil_upgradeleri": profile.get("shipping_profile_upgrades") or []})
        _add(rows, "kargo", pid, "hedefler_ve_ucretler", bool(destinations),
             json.dumps(details, ensure_ascii=False, sort_keys=True),
             "Profile en az bir ulke/bolge hedefi ve kargo ucreti ekleyin.")
    _add(rows, "kargo", POD_PROFILE_ID, "pod_profili_var", str(POD_PROFILE_ID) in profile_by_id,
         "bilinen POD profili bulundu" if str(POD_PROFILE_ID) in profile_by_id else "bilinen POD profili yok",
         f"POD ilanlari icin {POD_PROFILE_ID} profilini geri yukleyin veya eslemeyi duzeltin.")

    sections = data.get("sections") or []
    counts = {str(s.get("shop_section_id")): 0 for s in sections}
    for listing in listings:
        sid = listing.get("shop_section_id")
        if sid is not None and str(sid) in counts:
            counts[str(sid)] += 1
        _add(rows, "bolum", listing.get("listing_id"), "ilan_bolumu_var", sid is not None,
             f"section={sid}", "Ilani uygun magaza bolumune atayin.")
    seen = set()
    for section in sections:
        sid, title = str(section.get("shop_section_id")), (section.get("title") or "")
        norm = re.sub(r"\s+", " ", title).strip().casefold()
        spelling_ok = bool(title) and title == title.strip() and "  " not in title and not re.search(r"[–—]", title) and norm not in seen
        _add(rows, "bolum", sid, "bolum_adi", spelling_ok, title or "bos ad",
             "Bolum adindaki bosluk/tire/yinelenen yazim sorununu duzeltin.")
        seen.add(norm)
        _add(rows, "bolum", sid, "bolumde_ilan_var", counts.get(sid, 0) > 0,
             f"ilan={counts.get(sid, 0)}", "Bos bolumu kaldirin veya uygun ilanlari bu bolume atayin.")

    policies = data.get("return_policies") or []
    compatible = {str(p.get("return_policy_id")) for p in policies
                  if p.get("accepts_returns") is False and p.get("accepts_exchanges") is False}
    _add(rows, "iade", "magaza", "pod_iade_politikasi", bool(compatible),
         f"uyumlu={','.join(sorted(compatible)) or '-'}",
         "POD icin iade ve degisim kabul etmeyen politikayi tanimlayin; hasarli urunu 7 gunde ucretsiz yeniden basin.")
    for listing in listings:
        if str(listing.get("shipping_profile_id")) == str(POD_PROFILE_ID):
            rid = str(listing.get("return_policy_id") or "")
            _add(rows, "iade", listing.get("listing_id"), "pod_ilan_iade", rid in compatible,
                 f"policy={rid or '-'}", "POD ilanini no returns/no exchanges politikasina baglayin.")

    partners = data.get("production_partners") or []
    prodigi_ids = {str(p.get("production_partner_id")) for p in partners
                   if PARTNER_NAME in (p.get("partner_name") or "").casefold()}
    _add(rows, "partner", "magaza", "prodigi_var", bool(prodigi_ids),
         f"Prodigi={','.join(sorted(prodigi_ids)) or '-'}", "Magazaya Prodigi production partner ekleyin.")
    for listing in listings:
        if str(listing.get("shipping_profile_id")) != str(POD_PROFILE_ID):
            continue
        assigned = listing.get("production_partner_ids") or [p.get("production_partner_id") for p in listing.get("production_partners") or []]
        assigned = {str(x) for x in assigned}
        _add(rows, "partner", listing.get("listing_id"), "pod_prodigi_atamasi", bool(assigned & prodigi_ids),
             f"partner={','.join(sorted(assigned)) or '-'}", "POD ilanina Prodigi production partner atayin.")

    shop = data.get("shop") or {}
    for field in TEXT_FIELDS:
        value = shop.get(field) or shop.get(f"shop_{field}") or ""
        failures = (["bos"] if not value.strip() else []) + (["uzun_orta_tire"] if re.search(r"[–—]", value) else [])
        failures += [name for name, pattern in FORBIDDEN.items() if pattern.search(value)]
        _add(rows, "magaza_metni", field, "metin_kurallari", not failures,
             ";".join(failures) or "uygun", "Metni doldurun; uzun/orta tireleri ve yasakli ifadeleri kaldirin.")
    return rows


def write_reports(rows, csv_path, suggestions_path):
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    fields = ["alan", "nesne_id", "kural", "durum", "ayrinti", "duzeltme_onerisi"]
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    failures = [r for r in rows if r["durum"] == "FAIL"]
    lines = [f"- [{r['alan']}/{r['nesne_id']}] {r['kural']}: {r['duzeltme_onerisi']}" for r in failures]
    Path(suggestions_path).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(f"SONUC: {len(rows)-len(failures)}/{len(rows)} PASS, {len(failures)} FAIL")
    return 1 if failures else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    live = sub.add_parser("etsy"); live.add_argument("snapshot")
    offline = sub.add_parser("denetle"); offline.add_argument("snapshot"); offline.add_argument("csv"); offline.add_argument("oneriler")
    args = ap.parse_args(argv)
    if args.command == "etsy":
        fetch(args.snapshot); return 0
    data = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    return write_reports(audit(data), args.csv, args.oneriler)


if __name__ == "__main__":
    raise SystemExit(main())
