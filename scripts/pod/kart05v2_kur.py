#!/usr/bin/env python3
"""CL kart 05 v2 (Five colors.) 3000x2250: 05 renk paleti + 06 dijital BIRLESIK kart.
ChatGPT galeri karari (27 Eyl): ust yarida 5 rengin esit boy karsilastirmasi; alt yarida iki net kural:
'Print or Framed: one selected color.' / 'Digital File: all five colors and all included ratios.'
Dijital detaylar (5 PDF, oranlar, 300 dpi, 24 saat, kargo yok) iki kucuk satirda.
Posterler CANLI kart 04'teki gercek 5 renk posterden birebir; yeniden cizim yok. Sira MB, DB, PW, CI, WP.
Yazilar DNA: Garamond 120 baslik, Montserrat 49 alt baslik; ust etiket canli 03'ten, alt bant kart 03 v2'den.
QC: boyut, 5 poster NCC >= 0.99, sira, zemin, tire yok, satir cakismasi yok, Menu 2 adlari birebir.
Kullanim: kart05v2_kur.py CANLI_04.jpg CANLI_03.jpg KART03_V2.jpg GARAMOND.ttf MONTSERRAT.ttf CIKIS.jpg
"""
import re
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

C04, C03, K03V2, GAR, MON, CIK = sys.argv[1:7]
BG = (237, 232, 226); NAVY_T = (25, 34, 49); SANS_T = (23, 25, 30); PW_KENAR = (170, 168, 166)
out = Image.new('RGB', (3000, 2250), BG); d = ImageDraw.Draw(out)

def font(yol, boy, w):
    f = ImageFont.truetype(yol, boy); f.set_variation_by_axes([w]); return f

satirlar = []
def yaz(x, y, txt, f, renk, orta=False):
    b = f.getbbox(txt, anchor='ls')
    x0 = x - (b[0] + b[2]) / 2 if orta else x - b[0]
    d.text((x0, y - b[1]), txt, font=f, fill=renk, anchor='ls')
    satirlar.append((y, y + b[3] - b[1], txt))

C3 = Image.open(C03).convert('RGB'); V2 = Image.open(K03V2).convert('RGB'); C4 = Image.open(C04).convert('RGB')
out.paste(C3.crop((0, 70, 1500, 140)), (0, 70))
out.paste(V2.crop((0, 2130, 3000, 2250)), (0, 2130))

FT = font(GAR, 120, 450); FS = font(MON, 49, 500)
b = FT.getbbox('Two signs. One shared symbol.', anchor='ls')
d.text((143 - b[0], 201 - b[1]), 'Five colors.', font=FT, fill=NAVY_T, anchor='ls')
b = FS.getbbox('Cancer and Libra, united in an original AstroLove design.', anchor='ls')
d.text((147 - b[0], 336 - b[1]), 'Your design comes in these five colors.', font=FS, fill=SANS_T, anchor='ls')

# posterler (canli kart 04, gercek)
KAYNAK = {'MB': (269, 499, 791, 1150), 'DB': (1240, 500, 1760, 1150), 'CI': (2208, 499, 2733, 1152),
          'PW': (755, 1310, 1275, 1960), 'WP': (1723, 1308, 2248, 1962)}
AD = {'MB': 'Midnight Blue', 'DB': 'Deep Black', 'PW': 'Pure White', 'CI': 'Champagne Ivory', 'WP': 'Warm Parchment'}
PWD, PHD, PY = 430, 537, 470
YER = {k: (145 + i * 570, PY) for i, k in enumerate(['MB', 'DB', 'PW', 'CI', 'WP'])}
FN = font(MON, 35, 500)
posterler = {}
for k, (px, py) in YER.items():
    p = C4.crop(KAYNAK[k]).resize((PWD, PHD), Image.LANCZOS); posterler[k] = p; out.paste(p, (px, py))
    if k == 'PW':
        d.rectangle((px - 1, py - 1, px + PWD, py + PHD), outline=PW_KENAR, width=2)
    yaz(px + PWD / 2, PY + PHD + 48, AD[k], FN, SANS_T, orta=True)

# iki kural (ChatGPT metni birebir): Garamond on + Montserrat devam, satir grup olarak ortali
FK = font(GAR, 64, 450); FR = font(MON, 46, 400)
def kural(y, on, devam):
    b1 = FK.getbbox(on, anchor='ls'); b2 = FR.getbbox(devam, anchor='ls'); ara = 26
    w = (b1[2] - b1[0]) + ara + (b2[2] - b2[0]); x = 1500 - w / 2
    d.text((x - b1[0], y - b1[1]), on, font=FK, fill=NAVY_T, anchor='ls')
    d.text((x + (b1[2] - b1[0]) + ara - b2[0], y - b2[1] + 12), devam, font=FR, fill=SANS_T, anchor='ls')
    satirlar.append((y, y + 70, on + ' ' + devam))
kural(1320, 'Print or Framed:', 'printed in the one color you choose.')
kural(1455, 'Digital File:', 'you receive all five colors.')

# dijital detay (kart 06'dan tasindi, sikistirildi)
RULE = tuple(int(v) for v in np.asarray(V2)[2145, 1500])
d.line((700, 1620, 2300, 1620), fill=RULE, width=2)
FD = font(MON, 40, 400)
yaz(1500, 1700, 'Five print ready PDF files, one for each color. Each PDF covers all sizes from 8 x 10 to 24 x 36 inches, plus A4 to A2.', FD, SANS_T, orta=True)
yaz(1500, 1785, 'High resolution 300 dpi files. Sent within 24 hours via Etsy Messages. Nothing is shipped.', FD, SANS_T, orta=True)
FC = font(GAR, 52, 450)
yaz(1500, 1935, 'Every size is available in every color.', FC, NAVY_T, orta=True)
out.save(CIK, quality=95, subsampling=0)

# QC
R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
n = {k: ncc(R[py + 2:py + PHD - 2, px + 2:px + PWD - 2].mean(2), np.asarray(posterler[k]).astype(np.float32)[2:-2, 2:-2].mean(2)) for k, (px, py) in YER.items()}
sira = [k for k, _ in sorted(YER.items(), key=lambda kv: kv[1][0])] == ['MB', 'DB', 'PW', 'CI', 'WP']
zemin = all(max(abs(int(a) - b) for a, b in zip(R[y, x], BG)) <= 2 for x, y in [(60, 1300), (2940, 1300), (60, 2050), (2940, 2050)])
tum = ' '.join(t for _, _, t in satirlar)
tire = bool(re.search(r'[‒–—―−]', tum))
adlar = all(a in tum for a in AD.values())
sl = sorted((a, b) for a, b, _ in satirlar if a > 1100)
cakisma = sum(1 for (a1, b1), (a2, b2) in zip(sl, sl[1:]) if a2 < b1 + 12 and a2 != a1)
print('boyut', f'{R.shape[1]}x{R.shape[0]}', '| NCC', {k: round(v, 4) for k, v in n.items()}, '| sira', sira,
      '| zemin', zemin, '| adlar', adlar, '| tire', tire, '| cakisma', cakisma)
print('PASS' if R.shape[:2] == (2250, 3000) and min(n.values()) >= 0.99 and sira and zemin and adlar and not tire and cakisma == 0 else 'FAIL')
