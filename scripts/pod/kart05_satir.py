#!/usr/bin/env python3
"""CL kart 05 (Five colors.) tek satir duzeltmesi (Serdar 28 Eyl): 'Five print ready PDF files' -> 'print-ready'.
Satir onayli krem karttan olculdu: Montserrat wght 400, 40 punto, renk (23,23,28), taban y 1730, ortali (eski ink
x 383-2619, merkez 1501); krem uzerinde alfa farki 0.025. Yalniz satir bandi (y 1694-1743) krem ile silinip yeni metin
ayni merkeze basilir; kartin geri kalani piksel olarak aynidir (QC: bant disi fark 0).
Kullanim: kart05_satir.py KREM_05.jpg MONTSERRAT.ttf CIKIS.png
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

GIR, MON, CIK = sys.argv[1:4]
KREM = (237, 232, 226)
BANT = (1694, 1743)
ESKI = 'Five print ready PDF files, one for each color. Each PDF covers all sizes from 8 x 10 to 24 x 36 inches, plus A4 to A2.'
YENI = 'Five print-ready PDF files, one for each color. Each PDF covers all sizes from 8 x 10 to 24 x 36 inches, plus A4 to A2.'
A = Image.open(GIR).convert('RGB')
f = ImageFont.truetype(MON, 40); f.set_variation_by_axes([400])
e = f.getbbox(ESKI, anchor='ls'); merkez = 379 + (e[0] + e[2]) / 2       # olculen x 379 ile eski metnin merkezi
b = f.getbbox(YENI, anchor='ls')
out = A.copy(); d = ImageDraw.Draw(out)
d.rectangle((0, BANT[0], A.width - 1, BANT[1] - 1), fill=KREM)
d.text((merkez - (b[0] + b[2]) / 2, 1730), YENI, font=f, fill=(23, 23, 28), anchor='ls')
out.save(CIK)
a, o = np.asarray(A).astype(int), np.asarray(out).astype(int)
dis = np.ones(a.shape[:2], bool); dis[BANT[0]:BANT[1]] = False
fark = int(np.abs(a - o).max(2)[dis].max())
print(f'satir: {YENI[:32]}... | merkez {merkez:.1f} | bant disi fark maks {fark} | {"PASS" if fark == 0 else "FAIL"}')
sys.exit(0 if fark == 0 else 1)
