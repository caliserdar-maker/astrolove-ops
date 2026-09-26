#!/usr/bin/env python3
"""Aktif Etsy ilan gorsellerini salt okunur denetler.

Canli kip yalniz Etsy GET ve CDN GET kullanir. ``--input`` kipi sentetik/ag
gerektirmeyen testler icin Etsy ``includes=images`` bicimindeki JSON'u okur.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import cv2
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageOps
from scipy.fft import dctn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alt_metin_kontrol import BURCLAR  # noqa: E402
from etsy_common import APIKeyStore, Etsy  # noqa: E402

MIN_SIDE = 2000
MIN_BYTES = 100_000
RATIO_TOLERANCE = 0.02
PHASH_DISTANCE = 4
FIELDS = ["ilan_id", "baslik", "sira", "durum", "neden", "genislik",
          "yukseklik", "bayt", "oran", "laplace", "phash"]


def _results(value):
    if isinstance(value, list):
        return value
    return value.get("results", []) if isinstance(value, dict) else []


def pair_from_title(title):
    """Baslikta gecen ilk iki essiz burcu beklenen cift kabul eder."""
    found = []
    for sign in BURCLAR:
        if re.search(rf"\b{sign}\b", title or "", re.I):
            found.append(sign)
    return found[:2] if len(found) >= 2 else []


def fetch_live():
    """Aktif ilanlari ve gorsel URL'lerini GET ile toplar; yazma yapmaz."""
    store = APIKeyStore(os.environ.get("ETSY_API_KEY", ""),
                        os.environ.get("ETSY_SHARED_SECRET", ""))
    api, shop, out, offset = Etsy(store), os.environ["ETSY_SHOP_ID"], [], 0
    while True:
        body = api.get(f"/shops/{shop}/listings/active", params={
            "limit": 100, "offset": offset, "includes": "images"
        }) or {}
        batch = _results(body)
        out.extend(batch)
        if len(batch) < 100:
            break
        offset += 100
    return out


def download(url, timeout=90):
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content


def phash(gray):
    small = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(float)
    low = dctn(small, norm="ortho")[:8, :8]
    bits = low > np.median(low[1:])
    return f"{sum(int(v) << i for i, v in enumerate(bits.flat)):016x}"


def hamming(left, right):
    return (int(left, 16) ^ int(right, 16)).bit_count()


def ocr_signs(image):
    """Tesseract yoksa/okuyamazsa bos kume dondurur (BELIRSIZ)."""
    enlarged = ImageOps.autocontrast(image.convert("L")).resize(
        (image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
    try:
        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            enlarged.save(tmp.name)
            result = subprocess.run(
                ["tesseract", tmp.name, "stdout", "--psm", "11", "-l", "eng"],
                capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return set()
    text = result.stdout
    return {sign for sign in BURCLAR if re.search(rf"\b{sign}\b", text, re.I)}


def inspect_image(data):
    image = Image.open(io.BytesIO(data)).convert("RGB")
    arr = np.asarray(image)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    return {
        "image": image, "width": image.width, "height": image.height,
        "bytes": len(data), "ratio": image.width / image.height,
        "laplace": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
        "flat": float(gray.std()) < 2.0, "phash": phash(gray),
    }


def audit(listings, loader=download):
    """Indirme + tum kurallari uygular; sonuc satirlari ve resimleri dondurur."""
    jobs, errors, started = [], {}, time.monotonic()
    for listing in listings:
        lid = str(listing.get("listing_id", ""))
        images = sorted(_results(listing.get("images") or listing.get("Images")),
                        key=lambda item: item.get("rank") or 0)
        for image in images:
            jobs.append((lid, listing.get("title", ""), image.get("rank") or 0,
                         image.get("url_fullxfull") or ""))
    loaded = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        pending = {pool.submit(loader, url): (lid, title, rank, url) for lid, title, rank, url in jobs}
        for done, future in enumerate(as_completed(pending), 1):
            lid, title, rank, url = pending[future]
            try:
                loaded[(lid, rank)] = (title, inspect_image(future.result()))
            except Exception as exc:  # HTTP, Pillow ve bozuk girdi ilan FAIL'idir
                errors[(lid, rank)] = (title, f"indir/ac: {type(exc).__name__}")
            elapsed = max(time.monotonic() - started, .001)
            eta = (len(jobs) - done) / (done / elapsed)
            print(f"gorsel {done}/{len(jobs)} ETA {eta:.0f}s", flush=True)

    values = [entry[1]["laplace"] for entry in loaded.values()]
    median = float(np.median(values)) if values else 0.0
    mad = float(np.median(np.abs(np.asarray(values) - median))) if values else 0.0
    blur_limit = max(0.0, median - 5 * mad)
    reasons = {key: [] for key in loaded}
    by_listing = {}
    for (lid, rank), (_, item) in loaded.items():
        by_listing.setdefault(lid, []).append((rank, item))
        if min(item["width"], item["height"]) < MIN_SIDE: reasons[(lid, rank)].append("cozunurluk")
        if item["bytes"] < MIN_BYTES: reasons[(lid, rank)].append("dosya_boyutu")
        if item["flat"]: reasons[(lid, rank)].append("bos_tek_renk")
        if item["laplace"] < blur_limit: reasons[(lid, rank)].append("bulanik")
    for lid, items in by_listing.items():
        ratios = [item["ratio"] for _, item in items]
        target = float(np.median(ratios))
        for rank, item in items:
            if abs(item["ratio"] - target) > RATIO_TOLERANCE:
                reasons[(lid, rank)].append("oran_tutarsiz")
        for pos, (rank, item) in enumerate(items):
            if any(hamming(item["phash"], other["phash"]) <= PHASH_DISTANCE
                   for _, other in items[:pos]):
                reasons[(lid, rank)].append("ilan_ici_tekrar")
    covers = [(lid, rank, item) for lid, items in by_listing.items()
              for rank, item in items if rank == 1]
    for lid, rank, item in covers:
        if any(other_lid != lid and hamming(item["phash"], other["phash"]) <= PHASH_DISTANCE
               for other_lid, _, other in covers):
            reasons[(lid, rank)].append("ilanlar_arasi_ayni_kapak")

    rows = []
    for key, (title, item) in loaded.items():
        lid, rank = key
        why = reasons[key]
        status = "FAIL" if why else "PASS"
        if rank == 1:
            expected, seen = set(pair_from_title(title)), ocr_signs(item["image"])
            if expected and seen and seen != expected:
                why.append("ocr_yanlis_cift"); status = "FAIL"
            elif not expected or not seen:
                why.append("ocr_okunamadi"); status = "BELIRSIZ" if status == "PASS" else status
        rows.append({"ilan_id": lid, "baslik": title, "sira": rank, "durum": status,
                     "neden": ";".join(why) or "-", "genislik": item["width"],
                     "yukseklik": item["height"], "bayt": item["bytes"],
                     "oran": f'{item["ratio"]:.5f}', "laplace": f'{item["laplace"]:.2f}',
                     "phash": item["phash"]})
    for (lid, rank), (title, why) in errors.items():
        rows.append({"ilan_id": lid, "baslik": title, "sira": rank, "durum": "FAIL", "neden": why,
                     "genislik": "", "yukseklik": "", "bayt": "", "oran": "", "laplace": "", "phash": ""})
    return sorted(rows, key=lambda row: (row["ilan_id"], int(row["sira"]))), loaded


def write_outputs(rows, loaded, csv_path, contact_path):
    csv_path, contact_path = Path(csv_path), Path(contact_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS); writer.writeheader(); writer.writerows(rows)
    failed = [row for row in rows if row["durum"] == "FAIL" and (row["ilan_id"], row["sira"]) in loaded]
    if not failed:
        return
    thumb, label = 180, 42
    sheet = Image.new("RGB", (thumb * 4, (thumb + label) * ((len(failed) + 3) // 4)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, row in enumerate(failed):
        image = loaded[(row["ilan_id"], row["sira"])][1]["image"].copy()
        image.thumbnail((thumb, thumb))
        x, y = index % 4 * thumb, index // 4 * (thumb + label)
        sheet.paste(image, (x + (thumb-image.width)//2, y))
        draw.text((x + 3, y + thumb), f'{row["ilan_id"]} #{row["sira"]}\n{row["neden"][:25]}', fill="black")
    contact_path.parent.mkdir(parents=True, exist_ok=True); sheet.save(contact_path, quality=80)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="ag kullanmadan listing JSON")
    parser.add_argument("--output", default="TEMP/GORSEL_DENETIM.csv")
    parser.add_argument("--contact", default="TEMP/GORSEL_DENETIM_FAIL.jpg")
    args = parser.parse_args(argv)
    listings = _results(json.loads(args.input.read_text(encoding="utf-8"))) if args.input else fetch_live()
    rows, loaded = audit(listings)
    write_outputs(rows, loaded, args.output, args.contact)
    fails = sum(row["durum"] == "FAIL" for row in rows)
    print(f"OZET {len(rows)} gorsel; {fails} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
