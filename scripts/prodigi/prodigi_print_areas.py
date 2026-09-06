#!/usr/bin/env python3
"""
Prodigi HPR 13 boyutun print-area pikselini API'den okur (salt okur) -> JSON.
GET /products/GLOBAL-HPR-<SIZE> -> variants[0].printAreaSizes.default {horizontalResolution, verticalResolution}.
Prodigi print-area degeri esastir (inc x 300'den sapma yalniz not olarak yazilir; 11x14 = 3307x4200).
Cikti: {"8x10": {"w": 2400, "h": 3000, "sku": "GLOBAL-HPR-8x10"}, ...}
Kullanim: prodigi_print_areas.py --out PRODIGI_HPR_PRINT_AREAS.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prodigi_pilot_quote import Api, load_key, log  # noqa: E402

SIZES = {"8x10": (8, 10), "A4": None, "11x14": (11, 14), "12x16": (12, 16), "A3": None, "12x18": (12, 18),
         "16x20": (16, 20), "16x24": (16, 24), "A2": None, "18x24": (18, 24), "20x30": (20, 30),
         "24x36": (24, 36), "30x40": (30, 40)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    api = Api(load_key())
    out, bad = {}, []
    for sz, inch in SIZES.items():
        sku = f"GLOBAL-HPR-{sz}"
        prod, err = api.product(sku)
        if prod is None:
            bad.append(f"{sku}: {err}"); continue
        var = (prod.get("variants") or [{}])[0]
        pas = (var.get("printAreaSizes") or {}).get("default") or {}
        w, h = int(pas.get("horizontalResolution") or 0), int(pas.get("verticalResolution") or 0)
        if w > h:                                   # portre: kisa kenar genislik
            w, h = h, w
        if not w or not h:
            bad.append(f"{sku}: printAreaSizes yok"); continue
        note = ""
        if inch and (w, h) != (inch[0] * 300, inch[1] * 300):
            # Prodigi print-area bazen inc x 300'den sapar (6 Eyl olcumu: 11x14 -> 3307x4200, 280 mm); API degeri esastir
            note = f"inc x 300 = {inch[0] * 300}x{inch[1] * 300}; API farkli, API kullanildi"
        out[sz] = {"w": w, "h": h, "sku": sku, "note": note}
        log(f"{sz:<6} {w}x{h} {note}")
    if bad:
        sys.exit("HATA: " + "; ".join(bad))
    Path(a.out).write_text(json.dumps(out, indent=1))
    log(f"yazildi: {a.out} ({len(out)} boyut)")


if __name__ == "__main__":
    main()
