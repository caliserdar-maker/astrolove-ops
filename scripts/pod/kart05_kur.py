#!/usr/bin/env python3
"""CL kart 05 (Five palettes. One personal story.) 3000x2250 yeniden kurulum.
ChatGPT taslagi (1200x900) yalniz YERLESIM ve METIN kaynagidir (x2.5). ChatGPT posterleri yeniden
cizilmisti (canliya NCC 0.07-0.71); posterler CANLI kart 04'teki gercek 5 renk posterden birebir alinir.
Sira (kabul olcutu 8): ust MB, DB, PW; alt CI, WP.
Yazilar: EB Garamond + Montserrat (canli 03 kalibrasyonu); ust etiket canli 03'ten, alt cizgi+satir
onayli kart 03 v2'den piksel kopya.
QC: boyut, 5 poster NCC(kaynak) >= 0.99, sira, zemin, tire yok.
Kullanim: kart05_kur.py CANLI_04.jpg CANLI_03.jpg KART03_V2.jpg GARAMOND.ttf MONTSERRAT.ttf CIKIS.jpg
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

def boy_bul(yol, w, txt, hedef):
    return min(range(20, 200), key=lambda s: abs((lambda b: b[2] - b[0])(font(yol, s, w).getbbox(txt, anchor='ls')) - hedef))

C3 = Image.open(C03).convert('RGB'); V2 = Image.open(K03V2).convert('RGB'); C4 = Image.open(C04).convert('RGB')
out.paste(C3.crop((0, 70, 1500, 140)), (0, 70))
out.paste(V2.crop((0, 2130, 3000, 2250)), (0, 2130))

FT = font(GAR, 120, 450); FS = font(MON, 49, 500)
def sol_taban(f, canli, ust, sol):
    b = f.getbbox(canli, anchor='ls'); return sol - b[0], ust - b[1]
x, y = sol_taban(FT, 'Two signs. One shared symbol.', 201, 143)
d.text((x, y), 'Five palettes. One personal story.', font=FT, fill=NAVY_T, anchor='ls')
x, y = sol_taban(FS, 'Cancer and Libra, united in an original AstroLove design.', 336, 147)
d.text((x, y), 'Choose your color from the Primary color menu. The digital file includes all five.', font=FS, fill=SANS_T, anchor='ls')

# canli kart 04 poster kutulari (olculdu, 520x650)
KAYNAK = {'MB': (269, 499, 791, 1150), 'DB': (1240, 500, 1760, 1150), 'CI': (2208, 499, 2733, 1152),
          'PW': (755, 1310, 1275, 1960), 'WP': (1723, 1308, 2248, 1962)}
AD = {'MB': 'Midnight Blue', 'DB': 'Deep Black', 'PW': 'Pure White', 'CI': 'Champagne Ivory', 'WP': 'Warm Parchment'}
PW_, PH_ = 473, 593
YER = {'MB': (252, 517), 'DB': (1262, 517), 'PW': (2272, 517), 'CI': (757, 1247), 'WP': (1767, 1247)}
FN = font(MON, boy_bul(MON, 500, 'Midnight Blue', 253), 500)
posterler = {}
for k, (px, py) in YER.items():
    p = C4.crop(KAYNAK[k]).resize((PW_, PH_), Image.LANCZOS); posterler[k] = p
    out.paste(p, (px, py))
    if k == 'PW':
        d.rectangle((px - 1, py - 1, px + PW_, py + PH_), outline=PW_KENAR, width=2)
    b = FN.getbbox(AD[k], anchor='ls'); cap = FN.getbbox('M', anchor='ls')[1]
    d.text((px + PW_ / 2 - (b[0] + b[2]) / 2, py + PH_ + 48 - cap), AD[k], font=FN, fill=SANS_T, anchor='ls')
out.save(CIK, quality=95, subsampling=0)

# QC
R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
n = {k: ncc(R[py + 2:py + PH_ - 2, px + 2:px + PW_ - 2].mean(2), np.asarray(posterler[k]).astype(np.float32)[2:-2, 2:-2].mean(2))
     for k, (px, py) in YER.items()}
sira = [k for k, _ in sorted(YER.items(), key=lambda kv: (kv[1][1], kv[1][0]))] == ['MB', 'DB', 'PW', 'CI', 'WP']
zemin = all(max(abs(int(a) - b) for a, b in zip(R[y, x], BG)) <= 2 for x, y in [(60, 700), (2900, 700), (1500, 1500), (2900, 1600), (500, 2050)])
metin = 'Five palettes. One personal story. Choose your color from the Primary color menu. The digital file includes all five.'
tire = bool(re.search(r'[‒-―−]', metin))
print('boyut', f'{R.shape[1]}x{R.shape[0]}', '| NCC', {k: round(v, 4) for k, v in n.items()}, '| sira', sira, '| zemin', zemin, '| tire', tire, '| isim font', FN.size)
print('PASS' if R.shape[:2] == (2250, 3000) and min(n.values()) >= 0.99 and sira and zemin and not tire else 'FAIL')
