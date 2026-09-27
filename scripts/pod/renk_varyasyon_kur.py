#!/usr/bin/env python3
"""CL renk varyasyon gorseli (Etsy renk secimi onizlemesi) 3000x2250 kurulum.
Serdar 27 Eyl: musteri Menu 2'de renk secince bu gorsel cikacak; ChatGPT mockuplari
(AI cizim poster + AI cerceve + alt kenarda lacivert serit artefakti) reddedildi,
ayni konsept gercek dosyalardan kurulur.
  - Poster: gercek baski dosyasi (11x14, EMILY/JAMES), 5 mm rebate kirpilir. Yeniden cizim yok.
  - Cerceve: Prodigi Classic Antique Gold bos cerceve fotografi (059) 9 parca (kart12'deki cerceve_blank).
  - Yuz kalinligi: onayli ince olcek R_YUZ = 20/599.6 (kart 12/13 v4 ile ayni).
  - Zemin: sade sicak gri duvar (Serdar mockup rengi ~(216,209,202)), hafif dikey isik egimi.
  - Golge: DNA (dx 15, dy 18, sigma 26, koyuluk 59/232).
QC: 3000x2250, poster ic bolge NCC >= 0.99, zemin rengi koselerde dogru, yazi yok (tire yok).
Kullanim: renk_varyasyon_kur.py BASKI_11x14.jpg AG_BLANK_059.jpg CIKIS.jpg
"""
import sys
import numpy as np
from PIL import Image, ImageFilter

BASKI, AGCH, CIK = sys.argv[1:4]
DUVAR = (216, 209, 202)

def cerceve_blank(yol, poster, F):
    src = Image.open(yol).convert('RGB'); X0, Y0, X1, Y1, f = 455, 282, 1544, 1673, 46
    PW, PH = poster.size; OW, OH = PW + 2 * F, PH + 2 * F
    fr = Image.new('RGB', (OW, OH))
    pa = np.asarray(poster).astype(np.float32); yy = np.arange(PH)[:, None]; xx = np.arange(PW)[None, :]
    g = 1 - 0.22 * np.exp(-yy / 10.0) - 0.16 * np.exp(-xx / 10.0) - 0.06 * np.exp(-(PH - 1 - yy) / 5.0) - 0.06 * np.exp(-(PW - 1 - xx) / 5.0)
    fr.paste(Image.fromarray(np.clip(pa * g[..., None], 0, 255).astype(np.uint8)), (F, F))
    r = lambda b, w, h: src.crop(b).resize((w, h), Image.LANCZOS)
    fr.paste(r((X0 + f, Y0, X1 - f, Y0 + f), OW - 2 * F, F), (F, 0))
    fr.paste(r((X0 + f, Y1 - f, X1 - f, Y1), OW - 2 * F, F), (F, OH - F))
    fr.paste(r((X0, Y0 + f, X0 + f, Y1 - f), F, OH - 2 * F), (0, F))
    fr.paste(r((X1 - f, Y0 + f, X1, Y1 - f), F, OH - 2 * F), (OW - F, F))
    fr.paste(r((X0, Y0, X0 + f, Y0 + f), F, F), (0, 0)); fr.paste(r((X1 - f, Y0, X1, Y0 + f), F, F), (OW - F, 0))
    fr.paste(r((X0, Y1 - f, X0 + f, Y1), F, F), (0, OH - F)); fr.paste(r((X1 - f, Y1 - f, X1, Y1), F, F), (OW - F, OH - F))
    return fr

# zemin: sade duvar + hafif dikey isik egimi (ustte %2 acik, altta %2 koyu)
W, H = 3000, 2250
y = np.linspace(0.02, -0.02, H)[:, None, None]
zemin = np.clip(np.array(DUVAR, np.float32) * (1 + y), 0, 255)
out = Image.fromarray(np.tile(zemin.astype(np.uint8), (1, W, 1)))

# cerceve + poster (dis yukseklik 2110, 11:14 oran; onayli ince yuz)
R_YUZ = 20 / 599.6
DH = 2110
B = Image.open(BASKI).convert('RGB')
kx, ky = round(B.width * 5 / 279.4), round(B.height * 5 / 355.6)
Bk = B.crop((kx, ky, B.width - kx, B.height - ky))
PH = round(DH / (1 + 2 * R_YUZ * B.width / B.height))   # yuz F = PW * R_YUZ
PW = round(PH * Bk.width / Bk.height)
F = round(PW * R_YUZ)
PH = DH - 2 * F
poster = Bk.resize((PW, PH), Image.LANCZOS)
fr = cerceve_blank(AGCH, poster, F)
FX, FY = (W - fr.width) // 2, (H - fr.height) // 2

# DNA golgesi
sil = Image.new('L', (W, H), 0); sil.paste(255, (FX + 15, FY + 18, FX + 15 + fr.width, FY + 18 + fr.height))
alfa = np.asarray(sil.filter(ImageFilter.GaussianBlur(26))).astype(np.float32) / 255
o = np.asarray(out).astype(np.float32) * (1 - (59 / 232) * alfa)[..., None]
out = Image.fromarray(np.clip(o, 0, 255).astype(np.uint8))
out.paste(fr, (FX, FY))
out.save(CIK, quality=95, subsampling=0)

# QC
R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
px0, py0 = FX + F + 40, FY + F + 40
n = ncc(R[py0:py0 + PH - 80, px0:px0 + PW - 80].mean(2), np.asarray(poster).astype(np.float32)[40:-40, 40:-40].mean(2))
kose = all(max(abs(int(a) - b) for a, b in zip(R[y_, x_], DUVAR)) <= 8 for x_, y_ in [(60, 60), (2940, 60), (60, 2190), (2940, 2190)])
print(f'cerceve dis {fr.width}x{fr.height} yuz {F} | poster {PW}x{PH} NCC {n:.4f} | zemin {kose}')
print('PASS' if R.shape[:2] == (2250, 3000) and n >= 0.99 and kose else 'FAIL')
