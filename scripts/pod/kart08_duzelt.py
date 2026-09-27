#!/usr/bin/env python3
"""CL kart 08 (Fine art, down to the paper.) duzeltmesi. Taban: ChatGPT karti (3000x2250).
1) Poster yeniden cizilmisti (canli MB'ye NCC 0.74): yerine onayli kapaktaki GERCEK poster
   (11x14, sikistirma geri alinmis 1560x1988) ayni yukseklikte, ayni merkezde; golge kart 02 ile ayni.
2) Metin kurali: "Natural white, softly textured paper." (izinli listede yok) ->
   "Natural white and acid-free." (izinli: natural white, acid-free).
3) Alt not ve alt satir Lato idi: alt not Montserrat ile yeniden yazilir; alt cizgi+satir kart 03 v2'den.
QC: boyut, poster NCC(kaynak) >= 0.99, yasak/izinsiz ifade yok, tire yok, degisim yalniz izinli bolgelerde.
Kullanim: kart08_duzelt.py CHATGPT_08.jpg KAPAK.jpg KART03_V2.jpg MONTSERRAT.ttf CIKIS.jpg
"""
import re
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

G08, KAPAK, K03V2, MON, CIK = sys.argv[1:6]
BG = (237, 232, 226); SANS_T = (23, 25, 30)
K = Image.open(G08).convert('RGB'); A0 = np.asarray(K).astype(np.float32)
V2 = Image.open(K03V2).convert('RGB')
out = K.copy(); d = ImageDraw.Draw(out)

def font(boy, w):
    f = ImageFont.truetype(MON, boy); f.set_variation_by_axes([w]); return f

def gen(f, t):
    b = f.getbbox(t, anchor='ls'); return b[2] - b[0]

# 1) poster
PH = 1225; CX = 679.5; TOP = 595
P = Image.open(KAPAK).convert('RGB').crop((734, 130, 2268, 2118)).resize((1560, 1988), Image.LANCZOS)
PW = round(1560 * PH / 1988); poster = P.resize((PW, PH), Image.LANCZOS)
px = round(CX - PW / 2)
POSTER_BOL = (100, 540, 1300, 1905)
out.paste(BG, POSTER_BOL)
sil = Image.new('L', out.size, 0); sil.paste(255, (px + 15, TOP + 18, px + 15 + PW, TOP + 18 + PH))
alfa = np.asarray(sil.filter(ImageFilter.GaussianBlur(26))).astype(np.float32) / 255
o = np.asarray(out).astype(np.float32); m = np.zeros(alfa.shape, bool)
m[POSTER_BOL[1]:POSTER_BOL[3], POSTER_BOL[0]:POSTER_BOL[2]] = True
o[m] *= (1 - (59 / 232) * alfa[m])[:, None]
out = Image.fromarray(np.clip(o, 0, 255).astype(np.uint8)); out.paste(poster, (px, TOP)); d = ImageDraw.Draw(out)

# 2) ikinci ozellik satiri: olcu ayni satirin komsusundan (A substantial fine art paper.) kalibre
ref_t = 'A substantial fine art paper.'
FSUB = font(min(range(30, 60), key=lambda s: abs(gen(font(s, 500), ref_t) - (1990 - 1365))), 500)
SUB_RENK = tuple(int(v) for v in np.median(A0[677:720, 1365:1991][np.abs(A0[677:720, 1365:1991] - BG).max(2) > 150], axis=0))
SATIR2 = (1360, 1025, 2400, 1085)
out.paste(BG, SATIR2)
yeni = 'Natural white and acid-free.'
b = FSUB.getbbox(yeni, anchor='ls'); b0 = FSUB.getbbox(ref_t, anchor='ls')
taban = 1032 - b0[1]                                # ayni tip satir ustu (A/N buyuk harf)
d.text((1369 - b[0], taban), yeni, font=FSUB, fill=SUB_RENK, anchor='ls')

# 3) alt not (Montserrat) + alt cizgi/satir (kart 03 v2)
not_t = 'Print option: an unframed fine art print. Gold tones are printed color, not metallic foil.'
FN = font(min(range(24, 50), key=lambda s: abs(gen(font(s, 400), not_t) - 1407)), 400)
NOT_BOL = (600, 1945, 2400, 2010)
out.paste(BG, NOT_BOL)
b = FN.getbbox(not_t, anchor='ls'); d.text((1500 - (b[0] + b[2]) / 2, 1959 - b[1]), not_t, font=FN, fill=SANS_T, anchor='ls')
out.paste(V2.crop((0, 2130, 3000, 2250)), (0, 2130))
out.save(CIK, quality=95, subsampling=0)

# QC
R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
n = ncc(R[TOP + 3:TOP + PH - 3, px + 3:px + PW - 3].mean(2), np.asarray(poster).astype(np.float32)[3:-3, 3:-3].mean(2))
izin = np.zeros(R.shape[:2], bool)
for x0, y0, x1, y1 in (POSTER_BOL, SATIR2, NOT_BOL, (0, 2130, 3000, 2250)):
    izin[y0:y1, x0:x1] = True
fark = np.abs(R - A0).max(2)[~izin]
metin = ('Fine art, down to the paper. Printed on Hahnemuhle Photo Rag. 308 gsm A substantial fine art paper. 100% cotton '
         + yeni + ' Matte finish A refined surface without a glossy coating. Pigment giclee Printed with archival pigment inks. ' + not_t)
yasak = re.search(r'OBA|bright white|\d+\s*years|12.?colou?r|instant download|textured', metin, re.I)
tire = re.search(r'[‒-―−]', metin)
print(f'boyut {R.shape[1]}x{R.shape[0]} | poster {PW}x{PH} NCC {n:.4f} | izin disi fark ort {fark.mean():.3f} maks {int(fark.max())} | '
      f'yasak {bool(yasak)} | tire {bool(tire)} | font alt satir {FSUB.size} not {FN.size}')
print('PASS' if R.shape[:2] == (2250, 3000) and n >= 0.99 and fark.mean() < 0.5 and not yasak and not tire else 'FAIL')
