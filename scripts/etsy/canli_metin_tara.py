#!/usr/bin/env python3
"""Canli POD ilan metinlerini salt okunur Etsy batch API ile denetle.

Kullanim:
  canli_metin_tara.py etsy METIN_78.csv canli_metin.json
  canli_metin_tara.py denetle canli_metin.json CANLI_METIN.csv CANLI_METIN_OZET.json
"""
import csv
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import API, mask  # noqa: E402
from pod_listing_create import MESSAGE_INSTRUCTION, SHIPPING_TITLE, TITLE, personalization_questions  # noqa: E402

FORBIDDEN = {
    "oba_free": re.compile(r"\bOBA[ -]?free\b", re.I),
    "bright_white": re.compile(r"\bbright white\b", re.I),
    "lifetime_years": re.compile(r"\b\d{2,3}\s*(?:-|to)\s*\d{2,3}\s+years?\b", re.I),
    "12_colour": re.compile(r"\b12[ -]colou?r\b", re.I),
}
ENGLISH_TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 &'/-]*$")


def read_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for row in rows:
        listing_id = (row.get("ilan_id") or row.get("listing_id") or "").strip()
        pair = (row.get("cift") or row.get("pair") or "").strip()
        if listing_id:
            out.append({"listing_id": listing_id, "pair": pair})
    if not out:
        raise SystemExit("HATA: listede ilan_id/listing_id bulunamadi")
    return out


def fetch(input_csv, output_json):
    """Yalniz x-api-key kullanir; OAuth token okumaz ve Etsy'ye yazmaz."""
    rows = read_rows(input_csv)
    key, secret = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    if not key or not secret:
        raise SystemExit("HATA: ETSY_API_KEY/ETSY_SHARED_SECRET eksik")
    mask(key); mask(secret)
    session = requests.Session()
    session.headers["x-api-key"] = f"{key}:{secret}"
    found = {}
    calls = 0
    for start in range(0, len(rows), 100):
        ids = [r["listing_id"] for r in rows[start:start + 100]]
        response = session.get(API + "/listings/batch", params={
            "listing_ids": ",".join(ids), "includes": "personalization"
        }, timeout=60)
        calls += 1
        response.raise_for_status()
        for listing in (response.json() or {}).get("results") or []:
            found[str(listing.get("listing_id"))] = listing
    payload = [{"listing_id": r["listing_id"], "pair": r["pair"], "listing": found.get(r["listing_id"])} for r in rows]
    Path(output_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"etsy: {len(found)}/{len(rows)} ilan, {calls} batch cagrisi", flush=True)


def _questions(listing):
    questions = listing.get("personalization_questions")
    if not isinstance(questions, list) and isinstance(listing.get("personalization"), dict):
        questions = listing["personalization"].get("personalization_questions")
    return questions if isinstance(questions, list) else []


def audit_one(listing_id, pair, listing):
    failures = []
    if not isinstance(listing, dict):
        return {"ilan_id": listing_id, "cift": pair, "durum": "FAIL", "neden": "api_missing", "kurallar": "api_missing"}
    try:
        a, b = pair.replace(" + ", "_").replace(" ", "_").upper().split("_", 1)
        expected_title = TITLE.format(S1=a.capitalize(), S2=b.capitalize())
        expected_questions = personalization_questions(f"{a}_{b}")
    except (ValueError, KeyError):
        return {"ilan_id": listing_id, "cift": pair, "durum": "FAIL", "neden": "pair_invalid", "kurallar": "pair_invalid"}

    if listing.get("title") != expected_title:
        failures.append("title_schema")
    description = listing.get("description") or ""
    for name, pattern in FORBIDDEN.items():
        if pattern.search(description):
            failures.append(name)
    dash_text = description.replace(SHIPPING_TITLE, "")
    if "–" in dash_text or "—" in dash_text:
        failures.append("long_dash")
    if re.search(r"\bHahnemuhle\b", description, re.I):
        failures.append("hahnemuhle_spelling")

    tags = listing.get("tags") or []
    if len(tags) != 13:
        failures.append("tag_count")
    if any(len(str(tag)) > 20 for tag in tags):
        failures.append("tag_length")
    if any(not ENGLISH_TAG.fullmatch(str(tag)) for tag in tags):
        failures.append("tag_english")

    questions = _questions(listing)
    if len(questions) != 3 or any(q.get("instruction") != expected_questions[i]["instruction"] for i, q in enumerate(questions)):
        failures.append("personalization_instruction")
    expected_labels = [q["question_text"] for q in expected_questions]
    if [q.get("question_text") for q in questions] != expected_labels:
        failures.append("personalization_labels")
    unique = list(dict.fromkeys(failures))
    return {"ilan_id": listing_id, "cift": pair, "durum": "FAIL" if unique else "PASS",
            "neden": ";".join(unique) if unique else "-", "kurallar": ";".join(unique)}


def audit(input_json, output_csv, summary_json):
    payload = json.loads(Path(input_json).read_text(encoding="utf-8"))
    rows = [audit_one(str(item.get("listing_id", "")), item.get("pair", ""), item.get("listing")) for item in payload]
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["ilan_id", "cift", "durum", "neden"])
        writer.writeheader(); writer.writerows({k: row[k] for k in writer.fieldnames} for row in rows)
    counts = Counter(rule for row in rows for rule in row["kurallar"].split(";") if rule)
    passed = sum(row["durum"] == "PASS" for row in rows)
    summary = {"pass": passed, "total": len(rows), "fail": len(rows) - passed, "rule_fail_counts": dict(sorted(counts.items()))}
    Path(summary_json).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OZET {passed}/{len(rows)} PASS; kural FAIL {json.dumps(summary['rule_fail_counts'], ensure_ascii=False)}")
    return rows, summary


def main(argv=None):
    argv = argv or sys.argv[1:]
    if len(argv) == 3 and argv[0] == "etsy":
        fetch(argv[1], argv[2])
    elif len(argv) == 4 and argv[0] == "denetle":
        audit(argv[1], argv[2], argv[3])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
