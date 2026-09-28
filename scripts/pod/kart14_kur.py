#!/usr/bin/env python3
"""CL kart 14 (Made for the room you share.) 3000x2250 kurulum.
Taban: ChatGPT yazisiz yatak odasi sahnesi (1729x910; ikinci istekte yazi/marka/paspartu yok).
Sahnedeki bos cerceve yerine (on cephe; dis (699,57)-(1030,461)): Prodigi Classic Antique Gold bos cerceve
fotografi (059) 9 parca, yuz 24x36 olceginde; poster: canli kart 04'teki GERCEK Champagne Ivory (EMILY/JAMES).
Yazilar DNA (Garamond + Montserrat, canli 03 olculeri); ust etiket canli 03'ten, alt cizgi+satir kart 03 v2'den.
Kullanim: kart14_kur.py SAHNE.png CANLI_04.jpg AG_BLANK_059.jpg CANLI_03.jpg KART03_V2.jpg GARAMOND.ttf MONTSERRAT.ttf CIKIS.jpg
"""
import re
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

G14, C04, CILA, C03, K03V2, GAR, MON, CIK = sys.argv[1:9]
BG = (237, 232, 226); NAVY_T = (25, 34, 49); SANS_T = (23, 25, 30)

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cerceve_master import cila_blank, sahne_isik, set_grade, temas_golge

def font(yol, boy, w):
    f = ImageFont.truetype(yol, boy); f.set_variation_by_axes([w]); return f


out = Image.new('RGB', (3000, 2250), BG); d = ImageDraw.Draw(out)
C3 = Image.open(C03).convert('RGB'); V2 = Image.open(K03V2).convert('RGB')
out.paste(C3.crop((0, 70, 1500, 140)), (0, 70)); out.paste(V2.crop((0, 2130, 3000, 2250)), (0, 2130))
FT = font(GAR, 120, 450); FS = font(MON, 49, 500)
b = FT.getbbox('Two signs. One shared symbol.', anchor='ls'); d.text((143 - b[0], 201 - b[1]), 'Made for the room you share.', font=FT, fill=NAVY_T, anchor='ls')
b = FS.getbbox('Cancer and Libra, united in an original AstroLove design.', anchor='ls')
d.text((147 - b[0], 336 - b[1]), 'A calm, personal piece for your bedroom or living room.', font=FS, fill=SANS_T, anchor='ls')

G = Image.open(G14).convert('RGB')
SC = (0, 0, G.width, G.height); SX, SY = 145, 420; s = 2710 / (SC[2] - SC[0])
sahne = G.crop(SC).resize((2710, round((SC[3] - SC[1]) * s)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
DX0, DY0, DX1, DY1 = [round(v) for v in ((699 - SC[0]) * s, (57 - SC[1]) * s, (1031 - SC[0]) * s, (462 - SC[1]) * s)]
# cilali cerceve (kapak v9 ile ayni): dis yukseklik kutuya oturur, yatayda ortalanir (Serdar 28 Eyl)
PW = round((DX1 - DX0) * 777 / 821); PH = round(PW * 14 / 11)   # dis genislik kutuya esit; boy biraz tasar, eski cerceveyi orter
CI = Image.open(C04).convert('RGB').crop((2208, 499, 2733, 1152))          # canli kart 04 Champagne Ivory
kx, ky = round(CI.width * 5 / 406.4), round(CI.height * 5 / 508)
poster = CI.crop((kx, ky, CI.width - kx, CI.height - ky)).resize((PW, PH), Image.LANCZOS)
sahne, kazanc = set_grade(sahne)                       # set kurali: atmosfer koridora
fr, ix, iy, F = cila_blank(CILA, poster)
DX = DX0 + ((DX1 - DX0) - fr.width) // 2
DY = DY1 - fr.height                                   # alt kenar hizasi korunur, tasma yukari
yuz_ref = np.asarray(fr).astype(np.float32)[2:F - 2, fr.width // 2 - 100:fr.width // 2 + 100].reshape(-1, 3).mean(0)
KUTU = (DX, DY, DX + fr.width, DY + fr.height)
sahne = temas_golge(sahne, KUTU)
fr = sahne_isik(fr, sahne, KUTU)
_mk = Image.new('L', fr.size, 0)
ImageDraw.Draw(_mk).rectangle((2, 2, fr.width - 3, fr.height - 3), fill=255)
sahne.paste(fr, (DX, DY), _mk)
mask = Image.new('L', sahne.size, 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, sahne.width - 1, sahne.height - 1), radius=30, fill=255)
out.paste(sahne, (SX, SY), mask)

satir = []
def orta(y, t, f, renk):
    b = f.getbbox(t, anchor='ls'); d.text((1500 - (b[0] + b[2]) / 2, y - b[1]), t, font=f, fill=renk, anchor='ls'); satir.append(t)
def fit(yol, w, t, hedef):
    return font(yol, min(range(24, 90), key=lambda z: abs((lambda bb: bb[2] - bb[0])(font(yol, z, w).getbbox(t, anchor='ls')) - hedef)), w)
t1 = 'Shown in Champagne Ivory.'; t2 = 'Five colors, thirteen sizes, four frame finishes.'
orta(SY + sahne.height + 45, t1, fit(GAR, 450, t1, 1150), NAVY_T)
orta(SY + sahne.height + 132, t2, fit(MON, 400, t2, 760), SANS_T)
out.save(CIK, quality=95, subsampling=0)

R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
P = np.asarray(poster).astype(np.float32)[30:-30, 30:-30].mean(2)
n = -1.0
for _dy in range(-3, 4):
    for _dx in range(-3, 4):
        px0, py0 = SX + DX + ix + 30 + _dx, SY + DY + iy + 30 + _dy
        n = max(n, ncc(R[py0:py0 + P.shape[0], px0:px0 + P.shape[1]].mean(2), P))
zemin = all(max(abs(int(a) - b) for a, b in zip(R[y, x], BG)) <= 2 for x, y in [(60, 1000), (2950, 1000), (60, 2080)])
tire = bool(re.search(r'[\u2012-\u2015\u2212]', ' '.join(satir)))
alt = SY + sahne.height + 132 + 40
print(f'sahne {sahne.size} olcek {s:.3f} | cerceve dis {DX1 - DX0}x{DY1 - DY0} yuz {F} | poster {poster.size} NCC {n:.4f} | zemin {zemin} | tire {tire} | yazi alt ~{alt} (<2130)')
yuz_cik = R[SY + DY + 3:SY + DY + F - 2, SX + DX + fr.width // 2 - 100:SX + DX + fr.width // 2 + 100].reshape(-1, 3).mean(0)
sapma = float(np.abs(yuz_cik - yuz_ref).max())
print(f'set kazanc {kazanc} | cerceve renk sapmasi {sapma:.1f} (<=14)')
print('PASS' if R.shape[:2] == (2250, 3000) and n >= 0.99 and zemin and not tire and alt < 2130 and sapma <= 14 else 'FAIL')
