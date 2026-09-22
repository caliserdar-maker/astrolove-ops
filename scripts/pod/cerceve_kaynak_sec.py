#!/usr/bin/env python3
"""Mockup kaynaklarini OLCEREK secer (tahmin yok).

poster: oranı 4:5'e (h/w = 1.25) en yakin dosya.
oda   : en KOYU kare (ortalama parlaklik en dusuk) = "koyu oda sahnesi".
Cikti: <out> dosyasina iki satir (poster yolu, oda yolu).
"""
import argparse
import pathlib
import sys

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poster-kok", required=True)
    ap.add_argument("--oda-kok", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    adaylar = []
    for p in sorted(pathlib.Path(a.poster_kok).rglob("*.jpg")):
        with Image.open(p) as im:
            w, h = im.size
        adaylar.append((abs(h / w - 1.25), p, f"{w}x{h}", round(h / w, 4)))
    if not adaylar:
        raise SystemExit("DUR: poster bulunamadi")
    adaylar.sort()
    for fark, p, boy, oran in adaylar[:6]:
        print(f"poster aday: {p.name} ({p.parent.name}) {boy} oran {oran} | 4:5 farki {fark:.4f}")
    if adaylar[0][0] > 0.02:
        raise SystemExit(f"DUR: 4:5 poster yok (en yakin oran {adaylar[0][3]})")
    poster = adaylar[0][1]

    odalar = []
    for p in sorted(pathlib.Path(a.oda_kok).rglob("*")):
        if p.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        with Image.open(p) as im:
            k = np.asarray(im.convert("L").resize((96, 96), Image.BILINEAR), dtype=np.float32)
        odalar.append((float(k.mean()), p))
    if not odalar:
        raise SystemExit("DUR: oda karesi bulunamadi")
    odalar.sort()
    for parlaklik, p in odalar[:6]:
        print(f"oda aday: {p.name} ortalama parlaklik {parlaklik:.1f}")
    oda = odalar[0][1]
    pathlib.Path(a.out).write_text(f"{poster}\n{oda}\n", encoding="utf-8")
    print(f"SECILEN poster={poster} oda={oda}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
