#!/usr/bin/env python3
"""Kapak basligi: BURC1 / & / BURC2, Cinzel 650, koyu yesil #163422 (karar 18.10).
1254 px kapak olcusu: font 104 px, & %62, satir arasi %12, baslik ~y 200-424 -> sahne genisligine olceklenir.
Kullanim: python3 -I baslik.py <kapak_jpg> <burc1> <burc2> <cikti_jpg>"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
CIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'varlik', 'font', 'Cinzel[wght].ttf')
RENK = np.array(tuple(int(v) for v in os.environ.get("RENK", "22,52,34").split(",")), float)
src, b1, b2, out = sys.argv[1:5]
im = np.asarray(Image.open(src).convert('RGB')).astype(float)
W = im.shape[1]; K = W / 1254


def yaz(m, boy):
    f = ImageFont.truetype(CIN, round(boy)); f.set_variation_by_axes([650])
    bb = ImageDraw.Draw(Image.new('L', (1, 1))).textbbox((0, 0), m, font=f)
    t = Image.new('L', (bb[2] - bb[0] + 40, bb[3] - bb[1] + 40), 0)
    ImageDraw.Draw(t).text((20 - bb[0], 20 - bb[1]), m, font=f, fill=255)
    a = np.asarray(t).astype(float) / 255
    ys, xs = np.where(a > 0.05)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


BOY = 104 * K
satirlar = [yaz(b1.upper(), BOY), yaz('&', BOY * 0.62), yaz(b2.upper(), BOY)]
ara = BOY * 0.12
toplam = sum(s.shape[0] for s in satirlar) + 2 * ara
y = (300 * K + 40) - toplam / 2          # baslik merkezi ~y 312 (1254 olcusunde 200-424 araligi)
for s in satirlar:
    h, w = s.shape
    x0, y0 = int(round((W - w) / 2)), int(round(y))
    sub = im[y0:y0 + h, x0:x0 + w]
    im[y0:y0 + h, x0:x0 + w] = sub * (1 - s[..., None]) + RENK * s[..., None]
    y += h + ara
print(f'baslik y {312 * K - toplam / 2:.0f}-{y - ara:.0f} (sahne {W} px; 1254 olcusunde {(312 * K - toplam / 2) / K:.0f}-{(y - ara) / K:.0f})')
Image.fromarray(np.clip(im, 0, 255).astype(np.uint8)).save(out, quality=95)
