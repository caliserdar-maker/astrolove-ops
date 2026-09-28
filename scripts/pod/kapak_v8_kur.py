#!/usr/bin/env python3
"""CL kapak v8: cilali altin cerceve (eski ilan kapaklarindaki) + gercek BASKI_11x14, 3000x2250 tam kanama.
Serdar 28 Eyl karari: kapak ve sahne kartlari cilali cerceveyle (dijital/print alicisi icin premium algi);
gercek Prodigi cerceveleri 02 format, 07 cerceveler ve 08 boylar kartlarinda kalir.
Sahne: ChatGPT bos duvar (panel yok, dolgu yok). Golge + sahne isigi cerceve_master dilinde.
QC: poster NCC >= 0.99, cerceve renk kilidi (ust yuz bandi) <= 16, 3000x2250.
Kullanim: kapak_v8_kur.py SAHNE.png BASKI_11x14.jpg CILA_KAYNAK.png CIKIS.jpg [BX0 BY0 BX1 TABAN]
"""
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cerceve_master import cila_blank, sahne_isik

SAHNE, BASKI, CILA, CIK = sys.argv[1:5]
G = Image.open(SAHNE).convert('RGB')
BX0, BY0, BX1, TABAN = (int(v) for v in sys.argv[5:9]) if len(sys.argv) > 8 else (532, 24, 1194, 808)
CX = (BX0 + BX1) // 2

# poster yuksekligi: cerceve dis yuksekligi OH olacak sekilde (kaynak halka 1053, ic 1007)
OH = TABAN - BY0
PH = round(OH * 1007 / 1053)
PW = round(PH * 11 / 14)
B = Image.open(BASKI).convert('RGB')
kx, ky = round(B.width * 5 / 279.4), round(B.height * 5 / 355.6)
poster = B.crop((kx, ky, B.width - kx, B.height - ky)).resize((PW, PH), Image.LANCZOS)
fr, ix, iy, YUZ = cila_blank(CILA, poster)
FX, FY = CX - fr.width // 2, TABAN - fr.height

# golge (cerceveden once): temas + yumusak, alt-sag
a = np.asarray(G).astype(np.float32)
for dx, dy, sg, guc in [(14, 10, 30, 0.13), (5, 4, 7, 0.30)]:
    sil = Image.new('L', G.size, 0)
    sil.paste(255, (FX + dx, FY + dy, FX + dx + fr.width, FY + dy + fr.height))
    m = np.asarray(sil.filter(ImageFilter.GaussianBlur(sg))).astype(np.float32) / 255
    a = a * (1 - guc * m)[..., None]
G = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

yuz_ref = np.asarray(fr).astype(np.float32)[2:YUZ - 2, fr.width // 2 - 100:fr.width // 2 + 100].reshape(-1, 3).mean(0)
fr = sahne_isik(fr, G, (FX, FY, FX + fr.width, FY + fr.height), guc=0.12)
# kaynak kenarindaki 1-2 px duvar sizmasi paste edilmez
_mk = Image.new('L', fr.size, 0)
ImageDraw.Draw(_mk).rectangle((2, 2, fr.width - 3, fr.height - 3), fill=255)
G.paste(fr, (FX, FY), _mk)

# 4:3 pencere ve 3000x2250
PENC_W = round(G.height * 4 / 3)
x0 = min(max(CX - PENC_W // 2, 0), G.width - PENC_W)   # cerceve pencerede ortalanir (Serdar 28 Eyl)
out = G.crop((x0, 0, x0 + PENC_W, G.height)).resize((3000, 2250), Image.LANCZOS)
out.save(CIK, quality=95, subsampling=0)

# QC
R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
s = 3000 / PENC_W
fx, fy = (FX - x0) * s, FY * s
def ncc(p, q):
    p = p - p.mean(); q = q - q.mean(); return float((p * q).sum() / np.sqrt((p * p).sum() * (q * q).sum()))
pr = poster.resize((round(PW * s), round(PH * s)), Image.LANCZOS)
P = np.asarray(pr).astype(np.float32)[30:-30, 30:-30].mean(2)
# olcekleme yuvarlamasi +-1 px kaydirabilir; NCC en iyi hizada olculur (icerik sadakati, hiza degil)
n = -1.0
for dy in range(-3, 4):
    for dx in range(-3, 4):
        px0, py0 = round(fx + ix * s) + 30 + dx, round(fy + iy * s) + 30 + dy
        n = max(n, ncc(R[py0:py0 + P.shape[0], px0:px0 + P.shape[1]].mean(2), P))
yuz_cik = R[round(fy + 3 * s):round(fy + YUZ * s) - 2, round(fx + fr.width * s / 2) - 100:round(fx + fr.width * s / 2) + 100].reshape(-1, 3).mean(0)
sapma = float(np.abs(yuz_cik - yuz_ref).max())
print(f'cerceve {fr.width}x{fr.height} yuz {YUZ} (sahnede) | poster NCC {n:.4f} | cerceve renk sapmasi {sapma:.1f} (<=16)')
print('PASS' if R.shape[:2] == (2250, 3000) and n >= 0.99 and sapma <= 16 else 'FAIL')
