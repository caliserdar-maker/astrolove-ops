#!/usr/bin/env python3
"""Cercevesiz kapak ORNEGI (Serdar 15 Eki: eski 78 ilandan cerceve kalkar). Etsy'ye/Drive'a yazmaz; yalniz yerel dosya.
Ayni sahne (data/pod/kapak_sahne_v9.png, kapak_v9_toplu ile ayni 1213x910 olcek ve konum), cerceve yok:
poster duvara dogrudan asili baski (temas + yumusak golge, sahne isigi), ayni orta eksen ve taban.
Poster: onayli kapaktaki gercek poster (cerceve ici) kirpilir; boyut = eski cerceve dis yuksekligi (kompozisyon ayni).
QC: 3000x2250; poster NCC (kaynak kirpima) >= 0.99; poster cevresinde altin cerceve pikseli yok (sari doygunluk bandi).
Kullanim: cercevesiz_kapak_ornek.py ONAYLI_KAPAK.jpg CIKIS.jpg
"""
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cerceve_master import sahne_isik  # noqa: E402

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KAPAK, CIK = sys.argv[1:3]
BX0, BY0, BX1, TABAN = 295, 30, 919, 880          # kapak_v9_toplu.py ile ayni (1213x910 sahnede)
CX = (BX0 + BX1) // 2

# 1) onayli kapaktan poster (cerceve ici): koyu lacivert dikdortgen
K = np.asarray(Image.open(KAPAK).convert('RGB')).astype(np.float32)
s = K.shape[1] / 1213
lum = K.mean(2)
koyu = lum < 60
satir = koyu[:, int(CX * s) - 200:int(CX * s) + 200].mean(1) > 0.9
sutun = koyu[int(1100 / 2250 * K.shape[0]) - 300:int(1100 / 2250 * K.shape[0]) + 300].mean(0) > 0.9
ys, xs = np.where(satir)[0], np.where(sutun)[0]
py0, py1, px0, px1 = ys.min(), ys.max(), xs.min(), xs.max()
ic = 6                                            # cerceve dudagindan uzak dur
poster_k = Image.fromarray(K[py0 + ic:py1 - ic, px0 + ic:px1 - ic].astype(np.uint8))
print(f'poster kirpim {px1 - px0}x{py1 - py0} @ ({px0},{py0}) oran {(px1 - px0) / (py1 - py0):.4f} (11/14 = {11 / 14:.4f})')

# 2) sahne (v9 ile ayni)
G = Image.open(os.path.join(KOK, 'data/pod/kapak_sahne_v9.png')).convert('RGB').resize((1213, 910), Image.LANCZOS)
G = G.resize((3000, 2250), Image.LANCZOS)
S = 3000 / 1213
PH = round((TABAN - BY0) * S)                     # eski cerceve dis yuksekligi
PW = round(PH * 11 / 14)
FX, FY = round(CX * S) - PW // 2, round(TABAN * S) - PH
poster = poster_k.resize((PW, PH), Image.LANCZOS)

# 3) golge: kagit duvara yakin -> temas kisa ve sert, yumusak hafif (cerceveden daha ince)
a = np.asarray(G).astype(np.float32)
for dx, dy, sg, guc in [(18, 26, 40, 0.12), (5, 8, 8, 0.22)]:
    sil = Image.new('L', G.size, 0)
    sil.paste(255, (FX + dx, FY + dy, FX + dx + PW, FY + dy + PH))
    m = np.asarray(sil.filter(ImageFilter.GaussianBlur(sg))).astype(np.float32) / 255
    a = a * (1 - guc * m)[..., None]
G = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

# 4) sahne isigi (dusuk) + kagit kenar parlamasi (1 px, ust/sol)
p2 = sahne_isik(poster, G, (FX, FY, FX + PW, FY + PH), guc=0.10)
pa = np.asarray(p2).astype(np.float32)
pa[:2, :] = pa[:2, :] * 0.6 + 255 * 0.4 * np.array([1.0, 0.97, 0.92])
pa[:, :2] = pa[:, :2] * 0.7 + 255 * 0.3 * np.array([1.0, 0.97, 0.92])
G.paste(Image.fromarray(np.clip(pa, 0, 255).astype(np.uint8)), (FX, FY))
G.save(CIK, quality=95, subsampling=0)

# QC
R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)


def ncc(p, q):
    p = p - p.mean(); q = q - q.mean(); return float((p * q).sum() / np.sqrt((p * p).sum() * (q * q).sum()))


n = ncc(R[FY + 40:FY + PH - 40, FX + 40:FX + PW - 40].mean(2),
        np.asarray(poster).astype(np.float32)[40:-40, 40:-40].mean(2))
# cerceve kontrolu: poster disinda 10-60 px bant; altin cerceve = yuksek doygunluk + parlak sari
bant = np.concatenate([R[FY - 60:FY - 10, FX:FX + PW].reshape(-1, 3), R[FY:FY + PH, FX - 60:FX - 10].reshape(-1, 3),
                       R[FY:FY + PH, FX + PW + 10:FX + PW + 60].reshape(-1, 3)])
mx, mn = bant.max(1), bant.min(1)
doy = (mx - mn) / np.maximum(mx, 1)
altin = float(((doy > 0.55) & (mx > 150)).mean())
print(f'poster {PW}x{PH} @ ({FX},{FY}) | NCC {n:.4f} | cevre altin oran {altin:.4f} (<= 0.01)')
print('PASS' if R.shape[:2] == (2250, 3000) and n >= 0.99 and altin <= 0.01 else 'FAIL')
