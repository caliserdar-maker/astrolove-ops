#!/usr/bin/env python3
"""CL kart 10 v3 (Find the right fit for your wall.) 13 boy ile 3000x2250 yeniden kurulum.
Serdar 27 Eyl: 3 menu, 13 boy (30x40, 24x32, A1 cikti; Etsy 3 menude 400 urun siniri).
v2 stili korunur ve olculerek kullanilir: en buyuk kutu dolgu (218,210,199), ic kutular zemin renginde,
lacivert cizgi (33,33,43) 3 px, kutular tek olcekte (px/inc), ic ice ve alt kenardan hizali.
Yazilar DNA: baslik Garamond 120, alt baslik Montserrat 49 (canli 03 konumu); ust etiket canli 03'ten,
alt cizgi+satir kart 03 v2'den. cm donusumleri v2 ile ayni (dogrulanmisti).
QC: 13 boy, olcek tutarli (kutu yuksekligi = inc x olcek, +-1 px), sutunlar esit aralik, kenarlar esit, gruplar buyukten kucuge, tire yok.
Kullanim: kart10_kur.py CANLI_03.jpg KART03_V2.jpg GARAMOND.ttf MONTSERRAT.ttf CIKIS.jpg
"""
import re
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

C03, K03V2, GAR, MON, CIK = sys.argv[1:6]
BG = (237, 232, 226); NAVY_T = (25, 34, 49); SANS_T = (23, 25, 30); DOLGU = (218, 210, 199); CIZ = (33, 33, 43)
out = Image.new('RGB', (3000, 2250), BG); d = ImageDraw.Draw(out)
C3 = Image.open(C03).convert('RGB'); V2 = Image.open(K03V2).convert('RGB')
out.paste(C3.crop((0, 70, 1500, 140)), (0, 70)); out.paste(V2.crop((0, 2130, 3000, 2250)), (0, 2130))

def font(yol, boy, w):
    f = ImageFont.truetype(yol, boy); f.set_variation_by_axes([w]); return f

FT = font(GAR, 120, 450); FS = font(MON, 49, 500)
b = FT.getbbox('Two signs. One shared symbol.', anchor='ls'); d.text((143 - b[0], 201 - b[1]), 'Find the right fit for your wall.', font=FT, fill=NAVY_T, anchor='ls')
b = FS.getbbox('Cancer and Libra, united in an original AstroLove design.', anchor='ls'); d.text((147 - b[0], 336 - b[1]), '13 sizes, grouped by print proportions.', font=FS, fill=SANS_T, anchor='ls')

CM = 1 / 2.54
# gruplar buyukten kucuge (Serdar 27 Eyl): en buyuk boya gore 2:3 > 4:5 > 3:4 > A SERIES > 11:14
GRUP = [('2:3', [('12 × 18', 12, 18, '12 × 18 in (30 × 46 cm)'), ('16 × 24', 16, 24, '16 × 24 in (41 × 61 cm)'),
                 ('20 × 30', 20, 30, '20 × 30 in (51 × 76 cm)'), ('24 × 36', 24, 36, '24 × 36 in (61 × 91 cm)')]),
        ('4:5', [('8 × 10', 8, 10, '8 × 10 in (20 × 25 cm)'), ('16 × 20', 16, 20, '16 × 20 in (41 × 51 cm)'), ('24 × 30', 24, 30, '24 × 30 in (61 × 76 cm)')]),
        ('3:4', [('12 × 16', 12, 16, '12 × 16 in (30 × 41 cm)'), ('18 × 24', 18, 24, '18 × 24 in (46 × 61 cm)')]),
        ('A SERIES', [('A4', 21 * CM, 29.7 * CM, 'A4 (21 × 29.7 cm)'), ('A3', 29.7 * CM, 42 * CM, 'A3 (29.7 × 42 cm)'),
                      ('A2', 42 * CM, 59.4 * CM, 'A2 (42 × 59.4 cm)')]),
        ('11:14', [('11 × 14', 11, 14, '11 × 14 in (28 × 36 cm)')])]
OLCEK = 750 / 36                                    # en uzun kutu (24x36) v2'deki 30x40 ile ayni yukseklikte
ALT = 1358                                          # kutu alt kenari (v2 ile ayni)
FK = font(MON, 34, 500); FG = font(MON, 50, 500); FL = font(MON, 42, 400); SAT = 66

def gen(f, t):
    bb = f.getbbox(t, anchor='ls'); return bb[2] - bb[0]
sut_w = [max(max(w for _, w, h, _ in g) * OLCEK, max(gen(FL, s[3]) for s in g)) for _, g in GRUP]
ara = (2710 - sum(sut_w)) / (len(GRUP) - 1)
x = 145.0; kutular = []; satirlar = []
for (ad, g), sw in zip(GRUP, sut_w):
    cx = x + sw / 2
    for i, (et, w, h, _) in enumerate(sorted(g, key=lambda s: -s[2])):
        W, H = w * OLCEK, h * OLCEK
        box = (round(cx - W / 2), round(ALT - H), round(cx + W / 2), ALT)
        d.rectangle(box, fill=DOLGU if i == 0 else BG, outline=CIZ, width=3)
        bb = FK.getbbox(et, anchor='ls'); d.text((cx - (bb[0] + bb[2]) / 2, box[1] + 22 - bb[1]), et, font=FK, fill=CIZ, anchor='ls')
        kutular.append((et, h, box[3] - box[1]))
    bb = FG.getbbox(ad, anchor='ls'); d.text((cx - (bb[0] + bb[2]) / 2, ALT + 45 - bb[1]), ad, font=FG, fill=SANS_T, anchor='ls')
    for j, (_, _, _, s) in enumerate(g):
        bb = FL.getbbox(s, anchor='ls'); d.text((cx - (bb[0] + bb[2]) / 2, ALT + 135 + j * SAT - FL.getbbox('A', anchor='ls')[1]), s, font=FL, fill=SANS_T, anchor='ls')
        satirlar.append(s)
    x += sw + ara
t = 'Every size is available as a print and in all 4 frame colors.'
FN = font(MON, 33, 400); bb = FN.getbbox(t, anchor='ls'); d.text((1500 - (bb[0] + bb[2]) / 2, 1959 - bb[1]), t, font=FN, fill=SANS_T, anchor='ls')
out.save(CIK, quality=95, subsampling=0)

R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
olcek_ok = all(abs(px - h * OLCEK) <= 1.5 for _, h, px in kutular)
m = np.abs(R[560:1900] - np.array(BG)).max(2) > 25; xs = np.where(m.any(0))[0]
tire = bool(re.search(r'[‒-―−]', ' '.join(satirlar) + t))
sira = [max(h for _, _, h, _ in g) for _, g in GRUP]
azalan = all(a >= b for a, b in zip(sira, sira[1:]))
print(f'boy {len(kutular)} | olcek {OLCEK:.2f} px/in tutarli {olcek_ok} | aralik {ara:.0f} | sol {xs.min()} sag {2999 - xs.max()} | azalan {azalan} | tire {tire}')
print('PASS' if len(kutular) == 13 and olcek_ok and abs(xs.min() - (2999 - xs.max())) <= 5 and azalan and not tire else 'FAIL')
