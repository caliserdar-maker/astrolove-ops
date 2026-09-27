#!/usr/bin/env python3
"""CL kart 15 (Deep Black, framed in black.) 3000x2250 kurulum.
Taban: ChatGPT yazisiz oturma odasi sahnesi (1448x1086), 1.9:1 kirpim (y 100-862). Kitaplardaki okunaksiz sahte
yazilar scripts/pod/sahne_yazi_sil.py ile silinir (temiz.png).
Sahnedeki cerceve yerine (on cephe; dis (598,131)-(849,447)): Prodigi Classic BLACK chevron fotografinin gercek
profil seridi, 45 derece gonye (kart 07 yontemi; siyah icin on cephe bos fotograf yok); yuz 24x36 olcegi.
Poster: canli kart 04'teki GERCEK Deep Black (EMILY/JAMES).
Kullanim: kart15_kur.py SAHNE.png CANLI_04.jpg BK_CHEVRON.jpg CANLI_03.jpg KART03_V2.jpg GARAMOND.ttf MONTSERRAT.ttf CIKIS.jpg [oda|calisma]
v2 (calisma): ChatGPT'nin gec gelen calisma kosesi sahnesi (yazisiz, siyah cerceve, dis (637,96)-(1098,660)).
"""
import re
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

G15, C04, BKCH, C03, K03V2, GAR, MON, CIK = sys.argv[1:9]
# sahne secimi: 'oda' (v1, oturma odasi 1448x1086) | 'calisma' (v2, calisma kosesi 1729x910)
SAHNE = sys.argv[9] if len(sys.argv) > 9 else 'oda'
SAHNE_KIRP, CER = {'oda': ((0, 100, 1448, 862), (598, 131, 850, 448)),
                   'calisma': ((0, 0, 1729, 910), (637, 96, 1098, 660))}[SAHNE]
BG = (237, 232, 226); NAVY_T = (25, 34, 49); SANS_T = (23, 25, 30)

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cerceve_master import cerceve_chevron, sahne_isik, set_grade, temas_golge

def font(yol, boy, w):
    f = ImageFont.truetype(yol, boy); f.set_variation_by_axes([w]); return f


out = Image.new('RGB', (3000, 2250), BG); d = ImageDraw.Draw(out)
C3 = Image.open(C03).convert('RGB'); V2 = Image.open(K03V2).convert('RGB')
out.paste(C3.crop((0, 70, 1500, 140)), (0, 70)); out.paste(V2.crop((0, 2130, 3000, 2250)), (0, 2130))
FT = font(GAR, 120, 450); FS = font(MON, 49, 500)
b = FT.getbbox('Two signs. One shared symbol.', anchor='ls'); d.text((143 - b[0], 201 - b[1]), 'Deep Black, framed in black.', font=FT, fill=NAVY_T, anchor='ls')
b = FS.getbbox('Cancer and Libra, united in an original AstroLove design.', anchor='ls')
d.text((147 - b[0], 336 - b[1]), 'A modern look for a living room, hallway or office.', font=FS, fill=SANS_T, anchor='ls')

G = Image.open(G15).convert('RGB')
SC = SAHNE_KIRP; SX, SY = 145, 420; s = 2710 / (SC[2] - SC[0])
sahne = G.crop(SC).resize((2710, round((SC[3] - SC[1]) * s)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
DX0, DY0, DX1, DY1 = [round(v) for v in ((CER[0] - SC[0]) * s, (CER[1] - SC[1]) * s, (CER[2] - SC[0]) * s, (CER[3] - SC[1]) * s)]
# Serdar 27 Eyl: cerceve ince. Yuz = Prodigi 20 mm, 24x36 olceginde (gorunen 599.6 mm); dis olcu sahnedeki gibi kalir.
R_YUZ = 20 / 599.6
F = round((DX1 - DX0) * R_YUZ / (1 + 2 * R_YUZ))
CI = Image.open(C04).convert('RGB').crop((1240, 500, 1760, 1150))          # canli kart 04 Deep Black
kx, ky = round(CI.width * 5 / 406.4), round(CI.height * 5 / 508)
poster = CI.crop((kx, ky, CI.width - kx, CI.height - ky)).resize((DX1 - DX0 - 2 * F, DY1 - DY0 - 2 * F), Image.LANCZOS)
sahne, kazanc = set_grade(sahne)                       # set kurali: atmosfer koridora
fr = cerceve_chevron(BKCH, poster, F)                # master: gercek miter koseler
yuz_ref = np.asarray(fr).astype(np.float32)[2:F - 2, fr.width // 2 - 100:fr.width // 2 + 100].reshape(-1, 3).mean(0)
KUTU = (DX0, DY0, DX0 + fr.width, DY0 + fr.height)
sahne = temas_golge(sahne, KUTU)                       # temas + yumusak golge (cerceveden once)
fr = sahne_isik(fr, sahne, KUTU)                       # dusuk yogunluk ortam isigi, renk kilitli
sahne.paste(fr, (DX0, DY0))
mask = Image.new('L', sahne.size, 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, sahne.width - 1, sahne.height - 1), radius=30, fill=255)
out.paste(sahne, (SX, SY), mask)

satir = []
def orta(y, t, f, renk):
    b = f.getbbox(t, anchor='ls'); d.text((1500 - (b[0] + b[2]) / 2, y - b[1]), t, font=f, fill=renk, anchor='ls'); satir.append(t)
def fit(yol, w, t, hedef):
    return font(yol, min(range(24, 90), key=lambda z: abs((lambda bb: bb[2] - bb[0])(font(yol, z, w).getbbox(t, anchor='ls')) - hedef)), w)
t1 = 'Shown in Deep Black with a Black frame.'; t2 = 'Every color comes in all four frame finishes.'
orta(SY + sahne.height + 45, t1, fit(GAR, 450, t1, 1050), NAVY_T)
orta(SY + sahne.height + 132, t2, fit(MON, 400, t2, 740), SANS_T)
out.save(CIK, quality=95, subsampling=0)

R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
px0, py0 = SX + DX0 + F + 30, SY + DY0 + F + 30
n = ncc(R[py0:py0 + poster.height - 60, px0:px0 + poster.width - 60].mean(2), np.asarray(poster).astype(np.float32)[30:-30, 30:-30].mean(2))
zemin = all(max(abs(int(a) - b) for a, b in zip(R[y, x], BG)) <= 2 for x, y in [(60, 1000), (2950, 1000), (60, 2080)])
tire = bool(re.search(r'[\u2012-\u2015\u2212]', ' '.join(satir)))
alt = SY + sahne.height + 132 + 40
print(f'sahne {sahne.size} olcek {s:.3f} | cerceve dis {DX1 - DX0}x{DY1 - DY0} yuz {F} | poster {poster.size} NCC {n:.4f} | zemin {zemin} | tire {tire} | yazi alt ~{alt} (<2130)')
yuz_cik = R[SY + DY0 + 2:SY + DY0 + F - 2, SX + DX0 + fr.width // 2 - 100:SX + DX0 + fr.width // 2 + 100].reshape(-1, 3).mean(0)
sapma = float(np.abs(yuz_cik - yuz_ref).max())
print(f'set kazanc {kazanc} | cerceve renk sapmasi {sapma:.1f} (<=14)')
print('PASS' if R.shape[:2] == (2250, 3000) and n >= 0.99 and zemin and not tire and alt < 2130 and sapma <= 14 else 'FAIL')
