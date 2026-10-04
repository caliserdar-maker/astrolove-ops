#!/usr/bin/env python3
"""ONIZLEME JPG (Serdar 4 Eki, arka plan halkasi): tam cozunurluk PNG -> float alan ortalamasi kucultme -> kanal basina
TPDF +-1 LSB titresim -> 8 bit -> JPEG q100 4:4:4. Olculen (5 Eki): kucultme titresimi ortalayip siler, titresimsiz 8 bit
lacivert gradyanda 1 seviyelik basamak (halka) gorunur; JPEG q95 / q92 +-1 titresimi siler, q100 korur.
Kullanim: onizleme.py GIRDI.png CIKTI.jpg [--uzun 2000]
"""
import argparse

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
TOHUM = 20261005


def onizle(I, uzun):
    H, W = I.shape[:2]; f = uzun / max(W, H)
    w, h = round(W * f), round(H * f)
    F = cv2.resize(I.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA)
    rng = np.random.default_rng(TOHUM)
    F += rng.random(F.shape, np.float32) + rng.random(F.shape, np.float32) - 1
    return np.clip(np.round(F), 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('girdi'); ap.add_argument('cikti'); ap.add_argument('--uzun', type=int, default=2000)
    ap.add_argument('--kalite', type=int, default=100)
    a = ap.parse_args()
    U = onizle(np.asarray(Image.open(a.girdi).convert('RGB')), a.uzun)
    Image.fromarray(U).save(a.cikti, 'JPEG', quality=a.kalite, subsampling=0)


if __name__ == '__main__':
    main()
