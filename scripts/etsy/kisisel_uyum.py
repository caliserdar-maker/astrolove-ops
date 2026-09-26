#!/usr/bin/env python3
"""Tum aktif Etsy ilanlarini kisisel siparis modeline gore salt-okur denetle."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402
from pod_listing_create import personalization_questions  # noqa: E402

INSTANT_RX = re.compile(r"\b(?:instant(?:ly)?\s+download|instant\s+digital\s+download|download\s+immediately|immediate\s+download)\b", re.I)
DELIVERY_RX = re.compile(r"\b(?:within|in)\s+\d+(?:\s*[-–]\s*\d+)?\s+(?:hours?|business\s+days?|days?)\b", re.I)
CSV_FIELDS = ["ilan_id", "baslik", "tur", "durum", "neden", "dosya_adlari",
              "teslim_suresi_ifadesi", "islem_suresi"]


def _questions(listing):
    questions = listing.get("personalization_questions")
    if not isinstance(questions, list) and isinstance(listing.get("personalization"), dict):
        questions = listing["personalization"].get("personalization_questions")
    return questions if isinstance(questions, list) else []


def _question_issues(listing):
    expected = personalization_questions("ARIES_LEO")
    questions = _questions(listing)
    issues = []
    if len(questions) != 3:
        return ["kisisellestirme_soru_sayisi"]
    if any(q.get("required") is not True for q in questions):
        issues.append("kisisellestirme_zorunlu")
    if [q.get("max_allowed_characters") for q in questions] != [11, 11, 35]:
        issues.append("kisisellestirme_karakter_siniri")
    if [q.get("instruction") for q in questions] != [q["instruction"] for q in expected]:
        issues.append("kisisellestirme_talimati")
    labels = [str(q.get("question_text") or "").casefold() for q in questions]
    if not (all("name" in label for label in labels[:2]) and "message" in labels[2]):
        issues.append("kisisellestirme_soru_metni")
    return issues


def _processing(listing):
    pairs = (("processing_min", "processing_max"), ("processing_min_days", "processing_max_days"))
    for low, high in pairs:
        if listing.get(low) is not None and listing.get(high) is not None:
            return f"{listing[low]}-{listing[high]}"
    profile = listing.get("shipping_profile") or {}
    if isinstance(profile, dict):
        low, high = profile.get("processing_min"), profile.get("processing_max")
        if low is not None and high is not None:
            return f"{low}-{high}"
    return ""


def audit_one(listing, files=None):
    files = files or []
    issues = []
    if listing.get("is_personalizable") is not True:
        issues.append("kisisellestirme_kapali")
    issues.extend(_question_issues(listing))
    listing_type = str(listing.get("type") or listing.get("listing_type") or "")
    names = [str(item.get("filename") or item.get("name") or "") for item in files]
    if listing_type == "download" and files:
        issues.append("anlik_indirme_dosyasi")
    description = str(listing.get("description") or "")
    if INSTANT_RX.search(description):
        issues.append("anlik_teslim_ifadesi")
    delivery = bool(DELIVERY_RX.search(description))
    processing = _processing(listing)
    if not processing:
        issues.append("islem_suresi_yok")
    issues = list(dict.fromkeys(issues))
    return {"ilan_id": str(listing.get("listing_id") or ""), "baslik": str(listing.get("title") or ""),
            "tur": listing_type, "durum": "FAIL" if issues else "PASS",
            "neden": ";".join(issues) or "-", "dosya_adlari": "|".join(names),
            "teslim_suresi_ifadesi": "VAR" if delivery else "YOK", "islem_suresi": processing or "YOK"}


def audit(payload, output, summary):
    rows = [audit_one(item["listing"], item.get("files")) for item in payload]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader(); writer.writerows(rows)
    counts = Counter(reason for row in rows for reason in row["neden"].split(";") if reason != "-")
    result = {"toplam": len(rows), "pass": sum(r["durum"] == "PASS" for r in rows),
              "fail": sum(r["durum"] == "FAIL" for r in rows), "kural_hatalari": dict(sorted(counts.items())),
              "teslim_suresi_ifadesi_yok": sum(r["teslim_suresi_ifadesi"] == "YOK" for r in rows)}
    summary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OZET {result['pass']}/{result['toplam']} PASS; {result['fail']} FAIL")
    return rows


def fetch(api, shop):
    listings, offset = [], 0
    while True:
        page = api.get(f"/shops/{shop}/listings/active", params={"limit": 100, "offset": offset,
                                                                    "includes": "personalization,shipping_profile"}) or {}
        batch = page.get("results") or []
        listings.extend(batch)
        if len(batch) < 100:
            break
        offset += 100
    payload = []
    for listing in listings:
        files = []
        if str(listing.get("type") or listing.get("listing_type") or "") == "download":
            response = api.get(f"/shops/{shop}/listings/{listing['listing_id']}/files") or {}
            files = response.get("results") or []
        payload.append({"listing": listing, "files": files})
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Agsiz sentetik JSON")
    parser.add_argument("--out", type=Path, default=Path("TEMP/KISISEL_UYUM.csv"))
    parser.add_argument("--summary", type=Path, default=Path("TEMP/KISISEL_UYUM_OZET.json"))
    args = parser.parse_args(argv)
    if args.input:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        key, secret = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
        mask(key); mask(secret)
        store = TokenStore(os.environ["TOKEN_FILE"], key, secret)
        if store.needs_refresh():
            store.refresh()
        payload = fetch(Etsy(store), os.environ["ETSY_SHOP_ID"])
    rows = audit(payload, args.out, args.summary)
    return 1 if any(row["durum"] == "FAIL" for row in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
