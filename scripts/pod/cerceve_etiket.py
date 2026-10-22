#!/usr/bin/env python3
"""'Frame not included' etiketi (Serdar 15 Eki): ceriveli mockup gorsellerine kucuk, okunur, goze batmayan not.
Etsy'ye/Drive'a yazmaz; yalniz yerel dosya. 3000x2250 (4:3) kartlar icin.
Yerlesim: sag alt kose, sag kenardan 70 px, alttan 62 px (taban). Kare kirpim (orta 2250x2250) disinda kalip kalmadigi raporlanir
  (40 px metin 375 px kenar payina sigmaz; zorunlu degil).
Yazi: Montserrat 500, 40 px (galeri kart ust etiketi dili: Montserrat 500 37 px), harf araligi +1 px.
Renk: kart ust etiket rengi (133,116,83) arka plana gore koyulastirilir; hedef kontrast >= 3.0:1 (okunur), <= 4.5:1 (goze batmaz).
QC: kontrast 3.0-4.5; 3000x2250; metin posterin/cercevenin ustune binmez (sag alt duvar).
Kullanim: cerceve_etiket.py GIRDI.jpg CIKIS.jpg FONT_DIR [METIN]
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

GIR, CIK, FD = sys.argv[1:4]
METIN = sys.argv[4] if len(sys.argv) > 4 else "Frame not included"
BOY, AGIRLIK, SAG, TABAN, ARALIK = 40, 500, 70, 62, 1
TEMEL = np.array([133, 116, 83], np.float32)


def lum(c):
    c = np.asarray(c, np.float64) / 255
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def kontrast(a, b):
    la, lb = sorted([float(lum(a)), float(lum(b))], reverse=True)
    return (la + 0.05) / (lb + 0.05)


im = Image.open(GIR).convert("RGB")
W, H = im.size
f = ImageFont.truetype(os.path.join(FD, "Montserrat[wght].ttf"), BOY)
f.set_variation_by_axes([AGIRLIK])
gen = sum(f.getlength(ch) for ch in METIN) + ARALIK * (len(METIN) - 1)
asc, desc = f.getmetrics()
x0 = round(W - SAG - gen)
y0 = H - TABAN - asc
kutu = (x0 - 10, y0 - 6, round(x0 + gen) + 10, H - TABAN + desc + 6)
arka = np.asarray(im.crop(kutu)).reshape(-1, 3).astype(np.float32).mean(0)

renk = TEMEL.copy()
for _ in range(40):                                  # kontrast 3.0'a ulasana dek koyulastir
    if kontrast(renk, arka) >= 3.2:
        break
    renk *= 0.96
renk_t = tuple(int(v) for v in renk)

d = ImageDraw.Draw(im)
x = x0
for ch in METIN:
    d.text((x, y0), ch, font=f, fill=renk_t)
    x += f.getlength(ch) + ARALIK
im.save(CIK, quality=95, subsampling=0)

k = kontrast(renk, arka)
kare_x0 = (W - H) // 2
disarida = kutu[0] >= kare_x0 + H
print(f"metin '{METIN}' {round(gen)}x{asc + desc} px @ ({x0},{y0}) | renk {renk_t} arka {tuple(int(v) for v in arka)} | "
      f"kontrast {k:.2f} | kare kirpim disinda {disarida}")
print("PASS" if (W, H) == (3000, 2250) and 3.0 <= k <= 4.5 else "FAIL")
