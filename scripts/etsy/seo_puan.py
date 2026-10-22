#!/usr/bin/env python3
"""0018 ham ilan JSON'unu cevrimdisi SEO puanina donusturur.

Kullanim: seo_puan.py Girdi.json SEO_PUAN.csv OZET.md
Bu arac yalniz yerel dosya okur ve sonuc dosyalarini yazar.
"""
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

from alt_metin_kontrol import BURCLAR, cifti_ayir

WEIGHTS = {"ilk40": 20, "long_tail": 15, "ortusme": 15, "aciklama": 15,
           "kannibalizasyon": 20, "cesitlilik": 15}
STOP = {"a", "an", "and", "for", "in", "of", "the", "to", "with"}
PRODUCT = {"art", "print", "poster"}


def words(value):
    return re.findall(r"[a-z0-9]+", str(value).lower())


def unpack(payload):
    """0018 listesi ile Etsy'nin ``results`` zarfindan gelen ham veriyi kabul eder."""
    if isinstance(payload, dict):
        payload = payload.get("results", payload.get("listings", []))
    if not isinstance(payload, list):
        raise ValueError("JSON kok degeri liste veya results/listings iceren sozluk olmali")
    out = []
    for item in payload:
        listing = item.get("listing") if isinstance(item, dict) else None
        listing = listing if isinstance(listing, dict) else item
        if not isinstance(listing, dict):
            continue
        pair = str(item.get("pair") or item.get("cift") or listing.get("pair") or "")
        out.append((str(listing.get("listing_id") or item.get("listing_id") or ""), pair, listing))
    return out


def signs(pair, title):
    try:
        return cifti_ayir(pair)
    except ValueError:
        found = [sign for sign in BURCLAR if re.search(rf"\b{sign}\b", title, re.I)]
        return found[:2]


def has_keyword(text, zodiac):
    token = set(words(text))
    return bool(PRODUCT & token) and bool(zodiac) and all(s.lower() in token for s in set(zodiac))


def suggestions(failed, zodiac):
    pair = " and ".join(zodiac) if zodiac else "Your Zodiac Pair"
    pool = {
        "ilk40": f"Start the title with {pair} Zodiac Wall Art",
        "long_tail": f"Add the tag {pair} Couple Gift",
        "ortusme": "Reuse the strongest title phrase as a relevant tag",
        "aciklama": f"Open the description with {pair} Zodiac Wall Art for couples",
        "kannibalizasyon": "Give this title a distinct recipient or occasion focus",
        "cesitlilik": f"Replace a repeated tag with {pair} Astrology Decor",
    }
    ordered = list(failed) + [key for key in WEIGHTS if key not in failed]
    return [pool[key] for key in ordered[:3]]


def score_rows(records):
    prepared = []
    tag_counts = Counter()
    title_counts = Counter()
    for listing_id, pair, listing in records:
        title = str(listing.get("title") or "").strip()
        tags = [str(tag).strip() for tag in listing.get("tags") or [] if str(tag).strip()]
        description = str(listing.get("description") or "")
        prepared.append((listing_id, pair, title, tags, description))
        tag_counts.update(tag.lower() for tag in set(tags))
        title_counts[" ".join(words(title))] += 1
    top_tags = [(tag, count) for tag, count in tag_counts.most_common(30) if count > 1]
    common = {tag for tag, _ in top_tags}
    rows = []
    for listing_id, pair, title, tags, description in prepared:
        zodiac = signs(pair, title)
        first_paragraph = re.split(r"\n\s*\n", description.strip(), maxsplit=1)[0]
        title_terms = {w for w in words(title) if w not in STOP}
        tag_terms = {w for tag in tags for w in words(tag) if w not in STOP}
        long_tail = sum(len(words(tag)) >= 2 for tag in tags) / len(tags) if tags else 0
        overlap = len(title_terms & tag_terms) / len(title_terms) if title_terms else 0
        diversity = sum(tag.lower() not in common for tag in tags) / len(tags) if tags else 0
        checks = {
            "ilk40": has_keyword(title[:40], zodiac),
            "long_tail": long_tail >= 0.70,
            "ortusme": overlap >= 0.50,
            "aciklama": has_keyword(first_paragraph, zodiac),
            "kannibalizasyon": title_counts[" ".join(words(title))] == 1,
            "cesitlilik": diversity >= 0.50,
        }
        values = {"ilk40": float(checks["ilk40"]), "long_tail": long_tail,
                  "ortusme": min(1.0, overlap / 0.50), "aciklama": float(checks["aciklama"]),
                  "kannibalizasyon": float(checks["kannibalizasyon"]), "cesitlilik": diversity}
        score = round(sum(WEIGHTS[key] * values[key] for key in WEIGHTS))
        failed = [key for key, passed in checks.items() if not passed]
        advice = suggestions(failed, zodiac)
        rows.append({"ilan_id": listing_id, "cift": pair, "puan": score,
                     **{key: "PASS" if value else "FAIL" for key, value in checks.items()},
                     "long_tail_orani": f"{long_tail:.2f}", "baslik_etiket_ortusmesi": f"{overlap:.2f}",
                     "oneriler": " | ".join(advice)})
    return rows, top_tags


def audit(input_json, output_csv, output_md):
    records = unpack(json.loads(Path(input_json).read_text(encoding="utf-8")))
    rows, top_tags = score_rows(records)
    fields = ["ilan_id", "cift", "puan", *WEIGHTS, "long_tail_orani", "baslik_etiket_ortusmesi", "oneriler"]
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    average = sum(row["puan"] for row in rows) / len(rows) if rows else 0
    failures = Counter(key for row in rows for key in WEIGHTS if row[key] == "FAIL")
    lines = ["# SEO Puan Ozeti", "", f"Ilan sayisi: {len(rows)}", f"Ortalama puan: {average:.1f}", "",
             "## Kural FAIL sayilari"]
    lines += [f"* {key}: {failures[key]}" for key in WEIGHTS]
    lines += ["", "## En cok tekrar eden etiketler"]
    lines += [f"* {tag}: {count}" for tag, count in top_tags] or ["* Tekrar eden etiket yok"]
    Path(output_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", type=Path)
    parser.add_argument("output_csv", type=Path, nargs="?", default=Path("SEO_PUAN.csv"))
    parser.add_argument("output_md", type=Path, nargs="?", default=Path("OZET.md"))
    args = parser.parse_args(argv)
    audit(args.input_json, args.output_csv, args.output_md)


if __name__ == "__main__":
    main()
