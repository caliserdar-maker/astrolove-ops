#!/usr/bin/env python3
"""CL kapak v4 (arama sonucu / galeri 1. gorsel) 3000x2250.
ChatGPT karari (27 Eyl): Midnight Blue + Antique Gold Frame; temiz, simetrik, tam karsidan;
cerceve gercek Prodigi kaynagindan (059 bos cerceve, 9 parca); fiziksel alt-sag golge; yazi yok.
Set kurali (Serdar): atmosfer cerceveye uyar, cerceve rengi SABIT; duvar set grisi (216,209,202).
Poster: gercek BASKI_11x14 (EMILY/JAMES), rebate 5 mm kirpilir. Yeniden cizim yok.
Golge iki katman: temas (dx6 dy8 sigma8 0.38) + yumusak duvar (dx20 dy26 sigma42 0.20).
QC: 3000x2250, poster ic NCC >= 0.99, duvar koseleri, golge alt-sag yonlu (sol/ust temiz), yazi eklenmedi.
Kullanim: kapak_v4_kur.py BASKI_11x14.jpg AG_BLANK_059.jpg CIKIS.jpg
"""
import sys
import numpy as np
from PIL import Image, ImageFilter

BASKI, AGCH, CIK = sys.argv[1:4]
DUVAR = (216, 209, 202)
W, H = 3000, 2250

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

# duvar: set grisi + cok hafif dikey isik (ustte %2.5 acik, altta %2.5 koyu)
y = np.linspace(0.025, -0.025, H)[:, None, None]
zemin = np.clip(np.array(DUVAR, np.float32) * (1 + y), 0, 255)
out = Image.fromarray(np.tile(zemin.astype(np.uint8), (1, W, 1)))

# cerceve + poster (onayli ince yuz orani, dis yukseklik 2060, tam ortada)
R_YUZ = 20 / 599.6
DH = 2060
B = Image.open(BASKI).convert('RGB')
kx, ky = round(B.width * 5 / 279.4), round(B.height * 5 / 355.6)
Bk = B.crop((kx, ky, B.width - kx, B.height - ky))
PH = round(DH / (1 + 2 * R_YUZ * Bk.width / Bk.height))
PW = round(PH * Bk.width / Bk.height)
F = round(PW * R_YUZ)
PH = DH - 2 * F
poster = Bk.resize((PW, PH), Image.LANCZOS)
fr = cerceve_blank(AGCH, poster, F)
FX, FY = (W - fr.width) // 2, (H - fr.height) // 2

def golge(taban, dx, dy, sigma, guc):
    sil = Image.new('L', (W, H), 0)
    sil.paste(255, (FX + dx, FY + dy, FX + dx + fr.width, FY + dy + fr.height))
    a = np.asarray(sil.filter(ImageFilter.GaussianBlur(sigma))).astype(np.float32) / 255
    return np.clip(np.asarray(taban).astype(np.float32) * (1 - guc * a)[..., None], 0, 255)

out = Image.fromarray(golge(out, 20, 26, 42, 0.20).astype(np.uint8))
out = Image.fromarray(golge(out, 6, 8, 8, 0.38).astype(np.uint8))
out.paste(fr, (FX, FY))
out.save(CIK, quality=95, subsampling=0)

# QC
R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
px0, py0 = FX + F + 40, FY + F + 40
n = ncc(R[py0:py0 + PH - 80, px0:px0 + PW - 80].mean(2), np.asarray(poster).astype(np.float32)[40:-40, 40:-40].mean(2))
kose = all(max(abs(int(a) - b) for a, b in zip(R[y_, x_], DUVAR)) <= 10 for x_, y_ in [(60, 60), (2940, 60), (60, 2190), (2940, 2190)])
# golge yonu: cercevenin hemen sagi/alti, sol/ustunden koyu olmali
sag = R[FY + fr.height // 2, FX + fr.width + 12].mean(); sol = R[FY + fr.height // 2, FX - 12].mean()
alt = R[FY + fr.height + 12, FX + fr.width // 2].mean(); ust = R[FY - 12, FX + fr.width // 2].mean()
yon = sag < sol - 6 and alt < ust - 6
print(f'cerceve dis {fr.width}x{fr.height} yuz {F} | poster {PW}x{PH} NCC {n:.4f} | duvar {kose} | golge alt-sag {yon} (sol {sol:.0f} sag {sag:.0f} ust {ust:.0f} alt {alt:.0f})')
print('PASS' if R.shape[:2] == (H, W) and n >= 0.99 and kose and yon else 'FAIL')
