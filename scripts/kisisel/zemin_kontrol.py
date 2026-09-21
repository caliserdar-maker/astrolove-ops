"""Canva kopyasindan cikarilan zeminleri mevcut zeminle karsilastirir.

Kapi (Mo, 21 Eyl 2026): ortalama fark <= 1.5. Karsilastirma poster
genisligi 2400 px'e normalize edilmis uzayda yapilir; mevcut zemin
ORAN_SABITLERI.json'daki kilitli hiza (olcek, dx, dy) ile yerlestirilir,
yeni zemin dogrudan sayfa render'i oldugu icin yalniz olceklenir.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

NORM_W = 2400
KAPI = 1.5
SABIT = Path(__file__).with_name("ORAN_SABITLERI.json")


def norm(im, h=None):
    k = NORM_W / im.width
    return im.convert("RGB").resize(
        (NORM_W, h if h else int(round(im.height * k))), Image.LANCZOS)


def eski_zemin(bg_im, oran, yukseklik):
    """pilot12.fark_haritasi ile ayni yerlestirme."""
    h = json.loads(SABIT.read_text(encoding="utf-8"))["oranlar"][oran]["bg_hizasi_kilit"]
    s, dx, dy = h["olcek"], h["dx"], h["dy"]
    w = int(round(NORM_W * s))
    b = bg_im.convert("RGB").resize(
        (w, int(round(bg_im.height * w / bg_im.width))), Image.LANCZOS)
    bx = max(0, min((w - NORM_W) // 2 + dx, b.width - NORM_W))
    y0 = max(0, min((b.height - yukseklik) // 2 + dy, b.height - yukseklik))
    return b.crop((bx, y0, bx + NORM_W, y0 + yukseklik))


def karsilastir(yeni_yol, eski_yol, oran):
    yeni = norm(Image.open(yeni_yol))
    eski = eski_zemin(Image.open(eski_yol), oran, yeni.height)
    a = np.asarray(yeni).astype(np.float32)
    b = np.asarray(eski).astype(np.float32)
    d = np.abs(a - b).max(axis=2)
    return {"oran": oran, "olcu": f"{yeni.width}x{yeni.height}",
            "ort": round(float(d.mean()), 3),
            "medyan": round(float(np.median(d)), 3),
            "p99": round(float(np.percentile(d, 99)), 1),
            "tepe": round(float(d.max()), 1)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--yeni", required=True)
    p.add_argument("--eski", required=True)
    p.add_argument("--oran", default="4x5")
    p.add_argument("--etiket", default="")
    a = p.parse_args()
    r = karsilastir(a.yeni, a.eski, a.oran)
    gecti = r["ort"] <= KAPI
    print(f"{a.etiket or a.oran}: {r['olcu']} ort {r['ort']} medyan {r['medyan']} "
          f"p99 {r['p99']} tepe {r['tepe']} -> {'GECTI' if gecti else 'KALDI'} "
          f"(kapi ort <= {KAPI})")
    sys.exit(0 if gecti else 1)


if __name__ == "__main__":
    main()
