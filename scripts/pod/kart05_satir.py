#!/usr/bin/env python3
"""CL kart 05 (Five colors.) satir duzeltmeleri (Serdar 28 Eyl): birlesik sifat tireleri.
  'Five print ready PDF files'   -> 'Five print-ready PDF files'
  'High resolution 300 dpi files' -> 'High-resolution 300 dpi files'
Satirlar onayli krem karttan olculdu: Montserrat wght 400, 40 punto, renk (23,23,28), ortali; krem uzerinde alfa farki
0.025 / 0.033. Yalniz her satirin bandi krem ile silinip yeni metin ayni merkeze basilir; kartin geri kalani piksel olarak
aynidir (QC: bantlar disi fark 0).
Kullanim: kart05_satir.py KREM_05.jpg MONTSERRAT.ttf CIKIS.png
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

GIR, MON, CIK = sys.argv[1:4]
KREM = (237, 232, 226); RENK = (23, 23, 28)
SATIRLAR = [  # (bant y0, y1), onayli metin, yeni metin, olculen x, taban y
    ((1694, 1743), 'Five print ready PDF files, one for each color. Each PDF covers all sizes from 8 x 10 to 24 x 36 inches, plus A4 to A2.',
     'Five print-ready PDF files, one for each color. Each PDF covers all sizes from 8 x 10 to 24 x 36 inches, plus A4 to A2.', 379, 1730),
    ((1779, 1828), 'High resolution 300 dpi files. Sent within 24 hours via Etsy Messages. Nothing is shipped.',
     'High-resolution 300 dpi files. Sent within 24 hours via Etsy Messages. Nothing is shipped.', 617, 1815),
]
A = Image.open(GIR).convert('RGB')
f = ImageFont.truetype(MON, 40); f.set_variation_by_axes([400])
out = A.copy(); d = ImageDraw.Draw(out)
dis = np.ones((A.height, A.width), bool)
for (y0, y1), eski, yeni, x, taban in SATIRLAR:
    e = f.getbbox(eski, anchor='ls'); merkez = x + (e[0] + e[2]) / 2
    b = f.getbbox(yeni, anchor='ls')
    d.rectangle((0, y0, A.width - 1, y1 - 1), fill=KREM)
    d.text((merkez - (b[0] + b[2]) / 2, taban), yeni, font=f, fill=RENK, anchor='ls')
    dis[y0:y1] = False
    print(f'satir: {yeni[:34]}... | merkez {merkez:.1f}')
out.save(CIK)
fark = int(np.abs(np.asarray(A).astype(int) - np.asarray(out).astype(int)).max(2)[dis].max())
print(f'bantlar disi fark maks {fark} | {"PASS" if fark == 0 else "FAIL"}')
sys.exit(0 if fark == 0 else 1)
