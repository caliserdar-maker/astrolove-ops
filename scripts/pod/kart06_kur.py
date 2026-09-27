#!/usr/bin/env python3
"""CL kart 06 (Your digital file. All five colors.) 3000x2250 yeniden kurulum.
ChatGPT taslagi (1200x900) yalniz YERLESIM ve METIN kaynagi (x2.5). Posterler CANLI kart 04'teki gercek
5 renk posterden birebir (ChatGPT'ninkiler yeniden cizilmis). Sira MB, DB, PW, CI, WP.
Numaralar: canli DNA'daki gibi DUZ (lining) rakam, altin (ChatGPT eski tip 'oɪ' kullanmisti, hata 12).
Metin duzeltmesi: '300 dpi, sharp up to 24 x 36 in.' yalniz 2:3 icin dogru; siparis hattindaki
gercek olculerle degistirildi: '300 dpi at 16 x 20, 18 x 24, 24 x 36, 11 x 14 in and A2.'
Orta iki satir liste ile cakismasin diye asagi alindi (1905 / 1990).
QC: boyut, 5 poster NCC >= 0.99, sira, zemin, tire yok, satir cakismasi yok.
Kullanim: kart06_kur.py CANLI_04.jpg CANLI_03.jpg KART03_V2.jpg GARAMOND.ttf MONTSERRAT.ttf CIKIS.jpg
"""
import re
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

C04, C03, K03V2, GAR, MON, CIK = sys.argv[1:7]
BG = (237, 232, 226); NAVY_T = (25, 34, 49); SANS_T = (23, 25, 30); GOLD = (140, 114, 70); PW_KENAR = (170, 168, 166)
out = Image.new('RGB', (3000, 2250), BG); d = ImageDraw.Draw(out)

def font(yol, boy, w):
    f = ImageFont.truetype(yol, boy); f.set_variation_by_axes([w]); return f

def gen(f, t, feat=None):
    b = f.getbbox(t, anchor='ls', features=feat); return b[2] - b[0]

def boy_bul(yol, w, txt, hedef):
    return min(range(20, 200), key=lambda s: abs(gen(font(yol, s, w), txt) - hedef))

satirlar = []
def yaz(x, y, txt, f, renk, feat=None, orta=False):
    b = f.getbbox(txt, anchor='ls', features=feat)
    x0 = x - (b[0] + b[2]) / 2 if orta else x - b[0]
    d.text((x0, y - b[1]), txt, font=f, fill=renk, anchor='ls', features=feat)
    satirlar.append((y, y + b[3] - b[1], txt))

C3 = Image.open(C03).convert('RGB'); V2 = Image.open(K03V2).convert('RGB'); C4 = Image.open(C04).convert('RGB')
out.paste(C3.crop((0, 70, 1500, 140)), (0, 70))
out.paste(V2.crop((0, 2130, 3000, 2250)), (0, 2130))

FT = font(GAR, 120, 450); FS = font(MON, 49, 500)
b = FT.getbbox('Two signs. One shared symbol.', anchor='ls')
d.text((143 - b[0], 201 - b[1]), 'Your digital file. All five colors.', font=FT, fill=NAVY_T, anchor='ls')
b = FS.getbbox('Cancer and Libra, united in an original AstroLove design.', anchor='ls')
d.text((147 - b[0], 336 - b[1]), 'Choose Digital File and "All 5 colors, Digital".', font=FS, fill=SANS_T, anchor='ls')

# posterler
KAYNAK = {'MB': (269, 499, 791, 1150), 'DB': (1240, 500, 1760, 1150), 'CI': (2208, 499, 2733, 1152),
          'PW': (755, 1310, 1275, 1960), 'WP': (1723, 1308, 2248, 1962)}
AD = {'MB': 'Midnight Blue', 'DB': 'Deep Black', 'PW': 'Pure White', 'CI': 'Champagne Ivory', 'WP': 'Warm Parchment'}
PWD, PHD, PY = 370, 462, 505
YER = {k: (165 + i * 570, PY) for i, k in enumerate(['MB', 'DB', 'PW', 'CI', 'WP'])}
FN = font(MON, 35, 500)
posterler = {}
for k, (px, py) in YER.items():
    p = C4.crop(KAYNAK[k]).resize((PWD, PHD), Image.LANCZOS); posterler[k] = p; out.paste(p, (px, py))
    if k == 'PW':
        d.rectangle((px - 1, py - 1, px + PWD, py + PHD), outline=PW_KENAR, width=2)
    yaz(px + PWD / 2, 1005, AD[k], FN, SANS_T, orta=True)

# liste
FLT = font(GAR, boy_bul(GAR, 450, 'Five PDFs', 203), 450)
FLS = font(MON, boy_bul(MON, 400, 'One print ready file for each color.', 505), 400)
LNUM = ['lnum']
liste = [('01', 'Five PDFs', 'One print ready file for each color.'),
         ('02', 'Five ratios', '4:5, 3:4, 2:3, 11:14 and ISO A in every file.'),
         ('03', 'High resolution', '300 dpi at 16 x 20, 18 x 24, 24 x 36, 11 x 14 in and A2.'),
         ('04', 'Within 24 hours', 'Sent via Etsy Messages, checked by hand.')]
cap = -FLT.getbbox('F', anchor='ls')[1]
for i, (n, t, s) in enumerate(liste):
    ust = 1198 + i * 174
    taban_y = ust + cap
    bn = FLT.getbbox(n, anchor='ls', features=LNUM)
    d.text((272 - bn[0], taban_y), n, font=FLT, fill=GOLD, anchor='ls', features=LNUM)
    bt = FLT.getbbox(t, anchor='ls'); d.text((432 - bt[0], taban_y), t, font=FLT, fill=NAVY_T, anchor='ls')
    satirlar.append((ust, taban_y + bt[3], t))
    yaz(430, ust + 72, s, FLS, SANS_T)

FC1 = font(GAR, boy_bul(GAR, 450, 'Digital file only. Nothing is shipped. For personal use.', 787), 450)
FC2 = font(MON, boy_bul(MON, 400, 'Short on time? A thoughtful last minute gift.', 645), 400)
yaz(1500, 1905, 'Digital file only. Nothing is shipped. For personal use.', FC1, NAVY_T, orta=True)
yaz(1500, 1990, 'Short on time? A thoughtful last minute gift.', FC2, SANS_T, orta=True)
out.save(CIK, quality=95, subsampling=0)

# QC
R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
n = {k: ncc(R[py + 2:py + PHD - 2, px + 2:px + PWD - 2].mean(2), np.asarray(posterler[k]).astype(np.float32)[2:-2, 2:-2].mean(2)) for k, (px, py) in YER.items()}
sira = [k for k, _ in sorted(YER.items(), key=lambda kv: kv[1][0])] == ['MB', 'DB', 'PW', 'CI', 'WP']
zemin = all(max(abs(int(a) - b) for a, b in zip(R[y, x], BG)) <= 2 for x, y in [(60, 1300), (2900, 1300), (2500, 1600), (60, 2050)])
tum = ' '.join(t for _, _, t in satirlar)
tire = bool(re.search(r'[‒-―−]', tum))
sl = sorted((a, b) for a, b, _ in satirlar if a > 1100)
cakisma = sum(1 for (a1, b1), (a2, b2) in zip(sl, sl[1:]) if a2 < b1 + 12 and a2 != a1)
print('boyut', f'{R.shape[1]}x{R.shape[0]}', '| NCC', {k: round(v, 4) for k, v in n.items()}, '| sira', sira, '| zemin', zemin, '| tire', tire, '| cakisma', cakisma)
print('fontlar: liste baslik', FLT.size, 'alt', FLS.size, 'orta', FC1.size, FC2.size)
print('PASS' if R.shape[:2] == (2250, 3000) and min(n.values()) >= 0.99 and sira and zemin and not tire and cakisma == 0 else 'FAIL')
