#!/usr/bin/env python3
"""CL kart 10 (Find the right fit for your wall.) duzeltmesi. Taban: ChatGPT karti (3000x2250).
Icerik dogrulandi: 16 boy canli SKU'larla ayni; cm donusumleri dogru; kutular tek olcekte (12.5 px/in, 2000 olcekte).
Duzeltmeler (icerik degismez, piksel tasima):
  1) 5 sutun blogu esit aralikla yeniden dizilir: sag kenar bosluk 73 px idi (sol 145), simdi 145/145.
  2) Diyagram+liste bandi 80 px yukari: baslik alti bosluk ile alt satir ustu bosluk dengelenir.
  3) Alt not Lato -> Montserrat; alt cizgi+satir kart 03 v2'den.
QC: bloklar piksel ayni (NCC >= 0.999), sol/sag bosluk esit, aralik esit, izin disi degisim yok.
Kullanim: kart10_duzelt.py CHATGPT_10.jpg KART03_V2.jpg MONTSERRAT.ttf CIKIS.jpg
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

G10, K03V2, MON, CIK = sys.argv[1:5]
BG = (237, 232, 226); SANS_T = (23, 25, 30)
K = Image.open(G10).convert('RGB'); A0 = np.asarray(K).astype(np.float32); V2 = Image.open(K03V2).convert('RGB')
BLOK = [(145, 709), (858, 1310), (1457, 1899), (2048, 2499), (2574, 2927)]   # olculdu (bos sutun araliklari)
Y0, Y1, YUK = 650, 1840, 80
gen = [b - a + 1 for a, b in BLOK]; ara = (2855 - 145 + 1 - sum(gen)) / (len(BLOK) - 1)
out = K.copy(); out.paste(BG, (0, Y0 - YUK, 3000, Y1))
yeni_x = []; x = 145.0
for (a, b), w in zip(BLOK, gen):
    out.paste(K.crop((a, Y0, b + 1, Y1)), (round(x), Y0 - YUK)); yeni_x.append(round(x)); x += w + ara
d = ImageDraw.Draw(out)
t = 'Every size is available as a print and in all 4 frame colors.'
def font(s):
    f = ImageFont.truetype(MON, s); f.set_variation_by_axes([400]); return f
F = font(min(range(24, 60), key=lambda s: abs((lambda b: b[2] - b[0])(font(s).getbbox(t, anchor='ls')) - 925)))
out.paste(BG, (600, 1945, 2400, 2010))
b = F.getbbox(t, anchor='ls'); d.text((1500 - (b[0] + b[2]) / 2, 1959 - b[1]), t, font=F, fill=SANS_T, anchor='ls')
out.paste(V2.crop((0, 2130, 3000, 2250)), (0, 2130))
out.save(CIK, quality=95, subsampling=0)

R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
def ncc(p, q):
    p = p - p.mean(); q = q - q.mean(); return float((p * q).sum() / np.sqrt((p * p).sum() * (q * q).sum()))
n = [ncc(R[Y0 - YUK:Y1 - YUK, nx:nx + w].mean(2), A0[Y0:Y1, a:a + w].mean(2)) for (a, _), w, nx in zip(BLOK, gen, yeni_x)]
m = np.abs(R[Y0 - YUK:Y1 - YUK] - np.array(BG)).max(2) > 25; xs = np.where(m.any(0))[0]
sol, sag = xs.min(), 2999 - xs.max()
izin = np.zeros(R.shape[:2], bool); izin[Y0 - YUK:Y1] = True; izin[1945:2010] = True; izin[2130:] = True
fark = np.abs(R - A0).max(2)[~izin]
print(f'blok NCC min {min(n):.4f} | sol {sol} sag {sag} | aralik {ara:.1f} | alt not font {F.size} | izin disi fark ort {fark.mean():.3f}')
print('PASS' if min(n) >= 0.999 and abs(sol - sag) <= 3 and fark.mean() < 0.5 else 'FAIL')
