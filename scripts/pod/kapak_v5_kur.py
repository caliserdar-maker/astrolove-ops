#!/usr/bin/env python3
"""CL kapak v5 (ChatGPT otel duvari sahnesi) 3000x2250, tam kanama (yazi yok).
Sahne: ChatGPT 1729x910, bos poster alani ~kare; bizim poster DIKEY 11:14 oldugundan
alanin yan seritleri komsu duvar dokusunun AYNASIYLA kapatilir (yeniden cizim yok),
sonra gercek BASKI_11x14 + Prodigi AG master cerceve konsola oturur sekilde yerlestirilir.
Golge: temas + yumusak (cerceve_master ile ayni dil). Kirpim: 4:3 pencere, 3000x2250.
QC: poster NCC >= 0.99, eski bos alanda beyaz kalinti yok, golge temasi, cerceve renk kilidi.
Kullanim: kapak_v5_kur.py SAHNE.png BASKI_11x14.jpg AG_BLANK_059.jpg CIKIS.jpg
"""
import sys
import os
import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cerceve_master import cerceve_blank, sahne_isik

SAHNE, BASKI, AGCH, CIK = sys.argv[1:5]
G = Image.open(SAHNE).convert('RGB')
# bos alan kutusu (ince altin cizgi dahil) argumanla; varsayilan 2. sahne olcumu
BX0, BY0, BX1, TABAN = (int(v) for v in sys.argv[5:9]) if len(sys.argv) > 8 else (470, 2, 1262, 878)
CX = (BX0 + BX1) // 2

# cerceve olculeri: yukseklik taban-2, oran 11:14, yuz F = PW x 20/599.6
R_YUZ = 20 / 599.6
OH = TABAN - 2
PH = round(OH / (1 + 2 * R_YUZ * (11 / 14)))
PW = round(PH * 11 / 14)
F = round(PW * R_YUZ)
PH = OH - 2 * F
B = Image.open(BASKI).convert('RGB')
kx, ky = round(B.width * 5 / 279.4), round(B.height * 5 / 355.6)
poster = B.crop((kx, ky, B.width - kx, B.height - ky)).resize((PW, PH), Image.LANCZOS)
fr = cerceve_blank(AGCH, poster, F)
FX, FY = CX - fr.width // 2, TABAN - fr.height

# yan seritleri komsu duvardan KAYDIRMALI yama ile kapat (ayna yok: isik gradyani bozulmasin),
# dis kenarda 14 px yumusak gecis; ic kenar cerceve ve temas golgesi altinda kalir.
def yama(hedef_x0, hedef_x1, kaynak_x0):
    gen = hedef_x1 - hedef_x0
    par = G.crop((kaynak_x0, 0, kaynak_x0 + gen, TABAN))
    m = Image.new('L', par.size, 255)
    mp = np.tile(np.linspace(0, 255, 14), (TABAN, 1)).astype(np.uint8)
    if kaynak_x0 < hedef_x0:   # sol yama: dis kenar solda
        m.paste(Image.fromarray(mp), (0, 0))
    else:                       # sag yama: dis kenar sagda
        m.paste(Image.fromarray(mp[:, ::-1]), (gen - 14, 0))
    G.paste(par, (hedef_x0, 0), m)
gen_sol = FX - BX0 + 4
gen_sag = BX1 - (FX + fr.width) + 4
yama(BX0 - 2, BX0 - 2 + gen_sol, BX0 - 2 - gen_sol)
yama(BX1 + 2 - gen_sag, BX1 + 2, BX1 + 2)

# golge (cerceveden once): temas + yumusak, alt-sag
a = np.asarray(G).astype(np.float32)
for dx, dy, sg, guc in [(14, 10, 30, 0.13), (5, 4, 7, 0.30)]:
    sil = Image.new('L', G.size, 0)
    sil.paste(255, (FX + dx, FY + dy, FX + dx + fr.width, FY + dy + fr.height))
    m = np.asarray(sil.filter(ImageFilter.GaussianBlur(sg))).astype(np.float32) / 255
    a = a * (1 - guc * m)[..., None]
G = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

yuz_ref = np.asarray(fr).astype(np.float32)[2:F - 2, fr.width // 2 - 100:fr.width // 2 + 100].reshape(-1, 3).mean(0)
fr = sahne_isik(fr, G, (FX, FY, FX + fr.width, FY + fr.height), guc=0.12)
G.paste(fr, (FX, FY))

# 4:3 pencere ve 3000x2250
PENC_W = round(G.height * 4 / 3)
x0 = min(max(CX - PENC_W // 2 - 60, 0), G.width - PENC_W)   # zeytin dali icin hafif sola
out = G.crop((x0, 0, x0 + PENC_W, G.height)).resize((3000, 2250), Image.LANCZOS)
out.save(CIK, quality=95, subsampling=0)

# QC
R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
s = 3000 / PENC_W
fx, fy = (FX - x0) * s, FY * s
def ncc(p, q):
    p = p - p.mean(); q = q - q.mean(); return float((p * q).sum() / np.sqrt((p * p).sum() * (q * q).sum()))
pr = poster.resize((round(PW * s), round(PH * s)), Image.LANCZOS)
px0, py0 = round(fx + F * s) + 30, round(fy + F * s) + 30
n = ncc(R[py0:py0 + pr.height - 60, px0:px0 + pr.width - 60].mean(2), np.asarray(pr).astype(np.float32)[30:-30, 30:-30].mean(2))
# eski bos alanda beyaz kalinti (cerceve disinda)
Ri = np.asarray(out).astype(int)
kalinti = 0
for xa, xb in [((BX0 - x0) * s, fx - 1), (fx + fr.width * s + 1, (BX1 - x0) * s)]:
    b = Ri[round(20 * s):round((TABAN - 20) * s), round(xa):round(xb)]
    if b.size: kalinti += int(((b.min(2) > 236) & ((b.max(2) - b.min(2)) < 15)).sum())
yuz_cik = R[round(fy) + 2:round(fy + F * s) - 2, round(fx + fr.width * s / 2) - 100:round(fx + fr.width * s / 2) + 100].reshape(-1, 3).mean(0)
sapma = float(np.abs(yuz_cik - yuz_ref).max())
print(f'cerceve {fr.width}x{fr.height} yuz {F} (sahnede) | poster NCC {n:.4f} | beyaz kalinti {kalinti} px (=0) | cerceve renk sapmasi {sapma:.1f} (<=16)')
print('PASS' if R.shape[:2] == (2250, 3000) and n >= 0.99 and kalinti == 0 and sapma <= 16 else 'FAIL')
