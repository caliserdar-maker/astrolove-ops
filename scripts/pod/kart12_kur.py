#!/usr/bin/env python3
"""CL kart 12 (A gift for your story.) 3000x2250 kurulum.
Taban: ChatGPT hediye sahnesi (1448x1086; Serdar 'guzel, cerceve degismis'). Sahne 2.01x buyutulur.
Sahnedeki yapay cerceve+poster yerine (on cephe, dikdortgen; dis (443,226)-(893,788), ic (466,248)-(869,762)):
  - cerceve: Prodigi Classic Antique Gold bos cerceve fotografi (059, on cephe) 9 parca (Serdar: chevron seridi Prodigi gibi gorunmedi)
  - poster: gercek CL baski dosyasi BASKI_11x14 (EMILY/JAMES), rebate 5 mm kirpilir
  - sahne isigina uyum: soldan saga %3 -> %-7 parlaklik egimi, hafif sicak ton (yalniz cerceveli nesneye)
Yazilar DNA (Garamond + Montserrat, canli 03 olculeri); ust etiket canli 03'ten, alt cizgi+satir kart 03 v2'den.
QC: boyut, poster NCC >= 0.99, cerceve yuzu 4 kenarda esit, zemin, tire yok.
Kullanim: kart12_kur.py CHATGPT_12.png BASKI_11x14.jpg AG_BLANK_059.jpg CANLI_03.jpg KART03_V2.jpg GARAMOND.ttf MONTSERRAT.ttf CIKIS.jpg
"""
import re
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

G12, BASKI, AGCH, C03, K03V2, GAR, MON, CIK = sys.argv[1:9]
BG = (237, 232, 226); NAVY_T = (25, 34, 49); SANS_T = (23, 25, 30)

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cerceve_master import cerceve_blank, sahne_isik, set_grade, temas_golge

def font(yol, boy, w):
    f = ImageFont.truetype(yol, boy); f.set_variation_by_axes([w]); return f

out = Image.new('RGB', (3000, 2250), BG); d = ImageDraw.Draw(out)
C3 = Image.open(C03).convert('RGB'); V2 = Image.open(K03V2).convert('RGB')
out.paste(C3.crop((0, 70, 1500, 140)), (0, 70)); out.paste(V2.crop((0, 2130, 3000, 2250)), (0, 2130))
FT = font(GAR, 120, 450); FS = font(MON, 49, 500)
b = FT.getbbox('Two signs. One shared symbol.', anchor='ls'); d.text((143 - b[0], 201 - b[1]), 'A gift for your story.', font=FT, fill=NAVY_T, anchor='ls')
b = FS.getbbox('Cancer and Libra, united in an original AstroLove design.', anchor='ls')
d.text((147 - b[0], 336 - b[1]), "For anniversaries, engagements, weddings, Valentine's Day and birthdays.", font=FS, fill=SANS_T, anchor='ls')

# sahne
G = Image.open(G12).convert('RGB')
SC = (50, 195, 1398, 879); SX, SY = 145, 440; s = 2710 / (SC[2] - SC[0])
sahne = G.crop(SC).resize((2710, round((SC[3] - SC[1]) * s)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
# gercek cerceve + poster
DX0, DY0, DX1, DY1 = [round(v) for v in ((443 - SC[0]) * s, (226 - SC[1]) * s, (893 - SC[0]) * s, (788 - SC[1]) * s)]
IX0, IX1 = (466 - SC[0]) * s, (869 - SC[0]) * s
# Serdar 27 Eyl: cerceve ince. Yuz = Prodigi 20 mm, 24x36 olceginde (gorunen 599.6 mm); dis olcu sahnedeki gibi kalir.
R_YUZ = 20 / 599.6
F = round((DX1 - DX0) * R_YUZ / (1 + 2 * R_YUZ))
B = Image.open(BASKI).convert('RGB')
kx, ky = round(B.width * 5 / 279.4), round(B.height * 5 / 355.6)
poster = B.crop((kx, ky, B.width - kx, B.height - ky)).resize((DX1 - DX0 - 2 * F, DY1 - DY0 - 2 * F), Image.LANCZOS)
sahne, kazanc = set_grade(sahne)                       # set kurali: atmosfer koridora
fr = cerceve_blank(AGCH, poster, F)                    # master AG (gercek koseler)
yuz_ref = np.asarray(fr).astype(np.float32)[2:F - 2, fr.width // 2 - 100:fr.width // 2 + 100].reshape(-1, 3).mean(0)
KUTU = (DX0, DY0, DX0 + fr.width, DY0 + fr.height)
sahne = temas_golge(sahne, KUTU)
fr = sahne_isik(fr, sahne, KUTU)
sahne.paste(fr, (DX0, DY0))
mask = Image.new('L', sahne.size, 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, sahne.width - 1, sahne.height - 1), radius=30, fill=255)
out.paste(sahne, (SX, SY), mask)

satir = []
def orta(y, t, f, renk):
    b = f.getbbox(t, anchor='ls'); d.text((1500 - (b[0] + b[2]) / 2, y - b[1]), t, font=f, fill=renk, anchor='ls'); satir.append(t)
def fit(yol, w, t, hedef):
    return font(yol, min(range(24, 90), key=lambda z: abs((lambda bb: bb[2] - bb[0])(font(yol, z, w).getbbox(t, anchor='ls')) - hedef)), w)
t1 = 'Your two names and your own message, in one shared symbol.'
orta(SY + sahne.height + 90, t1, fit(GAR, 450, t1, 1208), NAVY_T)
out.save(CIK, quality=95, subsampling=0)

R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
px0, py0 = SX + DX0 + F + 40, SY + DY0 + F + 40
n = ncc(R[py0:py0 + poster.height - 80, px0:px0 + poster.width - 80].mean(2), np.asarray(poster).astype(np.float32)[40:-40, 40:-40].mean(2))
zemin = all(max(abs(int(a) - b) for a, b in zip(R[y, x], BG)) <= 2 for x, y in [(60, 1000), (2950, 1000), (60, 2050)])
tire = bool(re.search(r'[‒-―−]', ' '.join(satir)))
yuz_cik = R[SY + DY0 + 2:SY + DY0 + F - 2, SX + DX0 + fr.width // 2 - 100:SX + DX0 + fr.width // 2 + 100].reshape(-1, 3).mean(0)
sapma = float(np.abs(yuz_cik - yuz_ref).max())
print(f'sahne {sahne.size} olcek {s:.3f} | cerceve dis {DX1 - DX0}x{DY1 - DY0} yuz {F} | poster {poster.size} NCC {n:.4f} | zemin {zemin} | tire {tire}')
print(f'set kazanc {kazanc} | cerceve renk sapmasi {sapma:.1f} (<=14)')
print('PASS' if R.shape[:2] == (2250, 3000) and n >= 0.99 and zemin and not tire and sapma <= 14 else 'FAIL')
