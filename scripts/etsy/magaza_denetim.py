#!/usr/bin/env python3
"""Magazadaki aktif ve taslak Etsy ilanlarini salt okunur denetle."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alt_metin_kontrol import BURCLAR, denetle as alt_metin_denetle  # noqa: E402
from etsy_common import Etsy, TokenStore  # noqa: E402

YASAK = {
    "OBA-free": re.compile(r"\bOBA[\s-]*free\b", re.I),
    "bright white": re.compile(r"\bbright\s+white\b", re.I),
    "omur yili": re.compile(r"\b\d{2,3}\s*(?:-|to)\s*\d{2,3}\s+years?\b", re.I),
    "12-colour": re.compile(r"\b12[\s-]*colou?r\b", re.I),
}
ANLIK_TESLIM = re.compile(
    r"\b(?:instant|immediate)\s+(?:download|delivery)\b|"
    r"\b(?:aninda|anlık|anlik)\s+(?:indirme|indir|teslim)\b",
    re.I,
)
OZEL = "%:&+"


def _sonuclar(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return value
    return value.get("results") or [] if isinstance(value, dict) else []


def ilan_turu(listing: dict[str, Any]) -> str:
    if str(listing.get("type") or "").lower() == "download":
        return "dijital"
    text = " ".join(
        [
            str(listing.get("title") or ""),
            str(listing.get("description") or ""),
            " ".join(map(str, listing.get("materials") or [])),
        ]
    ).casefold()
    pod_terms = ("hahnem", "fine art paper", "giclée", "giclee", "unframed")
    return "pod" if any(term in text for term in pod_terms) else "fiziksel"


def _kelimeler(text: str) -> list[str]:
    return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+", text.casefold())


def _fiyat(listing: dict[str, Any]) -> float:
    value = listing.get("price")
    if isinstance(value, dict):
        try:
            return float(value.get("amount", 0)) / (float(value.get("divisor", 100)) or 100)
        except (TypeError, ValueError):
            return 0
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0


def _processing(listing: dict[str, Any]) -> tuple[Any, Any]:
    shipping = listing.get("shipping") or {}
    return (
        listing.get("processing_min")
        or shipping.get("min_processing_days")
        or shipping.get("min_processing_time"),
        listing.get("processing_max")
        or shipping.get("max_processing_days")
        or shipping.get("max_processing_time"),
    )


def denetle_ilan(listing: dict[str, Any]) -> list[dict[str, str]]:
    """Bir ilan icin her kurali ayri satir olarak dondurur."""
    lid, tur = str(listing.get("listing_id") or ""), ilan_turu(listing)
    rows: list[dict[str, str]] = []

    def add(kural: str, ok: bool, value: Any) -> None:
        rows.append(
            {
                "ilan": lid,
                "tur": tur,
                "kural": kural,
                "durum": "PASS" if ok else "FAIL",
                "deger": str(value)[:500],
            }
        )

    title = str(listing.get("title") or "").strip()
    words = _kelimeler(title)
    dup = sorted(word for word, count in Counter(words).items() if count > 1)
    caps = re.findall(r"\b[A-ZÀ-ÖØ-Þ]{2,}\b", title)
    add("baslik_uzunluk", bool(title) and len(title) <= 140, len(title))
    add("baslik_tekrar", bool(title) and not dup, ", ".join(dup) or "-")
    special = {char: title.count(char) for char in OZEL if title.count(char) > 1}
    add("baslik_ozel_karakter", not special, json.dumps(special, ensure_ascii=False) if special else "-")
    add("baslik_all_caps", not caps, ", ".join(caps) or "-")

    tags = [str(item).strip() for item in listing.get("tags") or []]
    folded = [tag.casefold() for tag in tags]
    repeated = sorted(tag for tag, count in Counter(folded).items() if count > 1)
    exact = sum(tag in set(words) for tag in folded)
    add("etiket_sayisi", len(tags) == 13, len(tags))
    add("etiket_uzunluk", all(tag and len(tag) <= 20 for tag in tags), max(map(len, tags), default=0))
    add("etiket_tekrar", not repeated, ", ".join(repeated) or "-")
    add("etiket_baslik_birebir", True, exact)  # Esik yok; yalniz olcum.

    desc = str(listing.get("description") or "").strip()
    lead_words = set(_kelimeler(desc[:160]))
    keywords = {
        word
        for word in set(words) | {word for tag in tags for word in _kelimeler(tag)}
        if len(word) > 2 and not word.isdigit()
    }
    forbidden = [name for name, pattern in YASAK.items() if pattern.search(desc)]
    add("aciklama_bos", bool(desc), len(desc))
    add("aciklama_ilk160_anahtar", bool(lead_words & keywords), ", ".join(sorted(lead_words & keywords)[:10]) or "-")
    add("aciklama_yasak_ifade", not forbidden, ", ".join(forbidden) or "-")
    add("aciklama_tire", "—" not in desc and "–" not in desc, "var" if "—" in desc or "–" in desc else "-")
    add("hahnemuhle_yazimi", not re.search(r"\bHahnemuhle\b", desc, re.I), "Hahnemuhle" if re.search(r"\bHahnemuhle\b", desc, re.I) else "-")
    instant = ANLIK_TESLIM.search(desc)
    add("anlik_teslim_ifadesi", instant is None, instant.group(0) if instant else "-")

    materials = listing.get("materials") or []
    add("materials", bool(materials) if tur != "dijital" else True, len(materials))
    add("who_made", listing.get("who_made") == "i_did", listing.get("who_made"))
    add("when_made", listing.get("when_made") == "made_to_order", listing.get("when_made"))
    add("is_supply", listing.get("is_supply") is False, listing.get("is_supply"))
    add("is_personalizable", listing.get("is_personalizable") is True, listing.get("is_personalizable"))
    add("section", bool(listing.get("shop_section_id")), listing.get("shop_section_id"))

    images = _sonuclar(listing.get("images") or listing.get("Images"))
    videos = _sonuclar(listing.get("videos") or listing.get("Videos"))
    add("gorsel_sayisi", len(images) >= (13 if tur == "pod" else 10), len(images))
    add("video", bool(videos), len(videos))
    pair = [sign for sign in BURCLAR if re.search(rf"\b{sign}\b", title, re.I)]
    alt_map = {str(image.get("rank") or index + 1): image.get("alt_text") for index, image in enumerate(images)}
    if len(pair) >= 2 and alt_map:
        alt_result = alt_metin_denetle(alt_map, "_".join(pair[:2]))
        alt_ok = all(status == "PASS" for _, status, _ in alt_result)
        alt_value = "; ".join(f"{rank}:{','.join(errors)}" for rank, status, errors in alt_result if status == "FAIL")
    else:
        alt_ok = bool(images) and all(isinstance(image.get("alt_text"), str) and image["alt_text"].strip() for image in images)
        alt_value = "tum dolu" if alt_ok else "eksik"
    add("alt_metin", alt_ok, alt_value)
    price = _fiyat(listing)
    add("fiyat", price > 0, price)
    if tur == "pod":
        pmin, pmax = _processing(listing)
        add("shipping_profile", bool(listing.get("shipping_profile_id")), listing.get("shipping_profile_id"))
        add("processing_3_5", pmin == 3 and pmax == 5, f"{pmin}-{pmax}")
    if tur == "dijital":
        add("dijital_type", listing.get("type") == "download", listing.get("type"))
        files = _sonuclar(listing.get("files") or listing.get("Files"))
        add("dijital_dosya_yok", not files, len(files))
    return rows


def denetle(listings: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows = [row for listing in listings for row in denetle_ilan(listing)]
    taxonomies: dict[str, set[Any]] = defaultdict(set)
    for listing in listings:
        taxonomies[ilan_turu(listing)].add(listing.get("taxonomy_id"))
    for listing in listings:
        tur = ilan_turu(listing)
        values = taxonomies[tur]
        rows.append(
            {
                "ilan": str(listing.get("listing_id") or ""),
                "tur": tur,
                "kural": "taxonomy_tutarlilik",
                "durum": "PASS" if len(values) == 1 and None not in values else "FAIL",
                "deger": str(listing.get("taxonomy_id")),
            }
        )
    return rows


def getir(api: Etsy, shop: str) -> list[dict[str, Any]]:
    ids: list[str] = []
    for state in ("active", "draft"):
        offset = 0
        while True:
            page = _sonuclar(api.get(f"/shops/{shop}/listings", params={"state": state, "limit": 100, "offset": offset}) or {})
            ids.extend(str(item["listing_id"]) for item in page if item.get("listing_id"))
            if len(page) < 100:
                break
            offset += 100
    listings: list[dict[str, Any]] = []
    for start in range(0, len(ids), 100):
        result = api.get(
            "/listings/batch",
            params={"listing_ids": ",".join(ids[start : start + 100]), "includes": "Images,Videos,Inventory,Shipping"},
        ) or {}
        listings.extend(_sonuclar(result))
    for listing in listings:
        if ilan_turu(listing) == "dijital":
            result = api.get(f"/listings/{listing['listing_id']}/files", ok404=True)
            listing["files"] = _sonuclar(result or {})
    return listings


def yaz(rows: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ilan", "tur", "kural", "durum", "deger"])
        writer.writeheader()
        writer.writerows(rows)
    fails = Counter(row["kural"] for row in rows if row["durum"] == "FAIL")
    bad = Counter(row["ilan"] for row in rows if row["durum"] == "FAIL")
    print("KURAL FAIL: " + json.dumps(dict(fails.most_common()), ensure_ascii=False))
    print("ILK 20 KOTU ILAN: " + json.dumps(bad.most_common(20), ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Agsiz sentetik Etsy JSON")
    parser.add_argument("--output", type=Path, default=Path("TEMP/MAGAZA_DENETIM.csv"))
    parser.add_argument("--raw-output", type=Path, help="Donusum planinda kullanilacak ham ilan JSON'u")
    args = parser.parse_args(argv)
    if args.input:
        listings = _sonuclar(json.loads(args.input.read_text(encoding="utf-8")))
    else:
        key, secret, shop = (os.environ.get(name, "") for name in ("ETSY_API_KEY", "ETSY_SHARED_SECRET", "ETSY_SHOP_ID"))
        if not key or not secret or not shop:
            raise SystemExit("HATA: ETSY_API_KEY/ETSY_SHARED_SECRET/ETSY_SHOP_ID eksik")
        store = TokenStore(os.environ.get("TOKEN_FILE", "ETSY_TOKEN.json"), key, secret)
        if store.needs_refresh():
            store.refresh()
        listings = getir(Etsy(store), shop)
    if args.raw_output:
        args.raw_output.parent.mkdir(parents=True, exist_ok=True)
        args.raw_output.write_text(
            json.dumps({"results": listings}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    rows = denetle(listings)
    yaz(rows, args.output)
    return 1 if any(row["durum"] == "FAIL" for row in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
