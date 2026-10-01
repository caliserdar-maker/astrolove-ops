#!/usr/bin/env python3
"""Poster/kucuk resim kenar tasmasi olcumu (Serdar 1 Eki): her poster kutusunun disindaki SERIT px seritte acik
piksel (R+G+B > ESIK) sayisi. Kutular: 05 (5 kucuk resim, galeri77_kur.kart05), 15-19 (renk_varyasyon_kur poster),
01 kapak (galeri77_kur.KAPAK_KIRP, onayli kapakta poster; cerceve/paspartu seritte olabilir, yalniz bilgi).
Kullanim: galeri77_serit.py PAKET_DIR  -> kart basina sayilar (tek satir/kart); cikis 0 her zaman (QC kapisi galeri77_qc)
"""
import os
import sys
import numpy as np
from PIL import Image

SERIT, ESIK = 12, 700
K05 = [(145 + i * 570, 470, 430, 537) for i in range(5)]
PH = 1755; PW = round(PH * 11 / 14); K_RENK = [((3000 - PW) // 2, 150, PW, PH)]
K01 = [(734, 130, 2268 - 734, 2118 - 130)]
KARTLAR = {'01_kapak': K01, '05_renk_ve_dijital': K05, '15_renk_midnight_blue': K_RENK, '16_renk_deep_black': K_RENK,
           '17_renk_pure_white': K_RENK, '18_renk_champagne_ivory': K_RENK, '19_renk_warm_parchment': K_RENK}


def serit(yol, kutular, s=SERIT, esik=ESIK):
    a = np.asarray(Image.open(yol).convert('RGB')).astype(np.int32)
    acik = a.sum(2) > esik
    out = []
    for x, y, w, h in kutular:
        m = np.zeros(acik.shape, bool)
        m[max(0, y - s):y + h + s, max(0, x - s):x + w + s] = True
        m[y:y + h, x:x + w] = False
        out.append(int((acik & m).sum()))
    return out


if __name__ == '__main__':
    P = sys.argv[1]
    for k, kut in KARTLAR.items():
        f = os.path.join(P, k + '.jpg')
        if os.path.exists(f):
            print(f'serit {k}: {serit(f, kut)}')
