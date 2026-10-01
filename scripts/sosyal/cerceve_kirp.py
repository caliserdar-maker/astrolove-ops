#!/usr/bin/env python3
"""Cerceveli kapak (Etsy 1. gorsel, TEMP/GALERI_77/<CIFT>/01_kapak.jpg, 3000x2250) icin dis cerceve kirpimi.
Olcum Etsy il_1588xN olceginde yapilir (ChatGPT pilotu bu olcekte kirpti): kapak 1588x1191'e LANCZOS ile
kucultulur, lacivert poster ici bulunur, her kenarda poster disindaki 60 px bantta duvar-cerceve gecisindeki
golge cizgisi (yerel minimum) aranir; kirpim o pikseli + 1 px JPEG sacagini icerir (yari-acik [l,t,r,b]).
Pilot (CANCER_LIBRA, il_1588xN.8638743279): [354,40,1236,1151]. Kabul: her kenarda fark <= 2 px.
Kullanim: cerceve_kirp.py KAPAK.jpg [...]  -> json satiri (kutu_1588, kutu_3000)"""
import json
import sys
import numpy as np
from PIL import Image

ETSY = (1588, 1191)
PILOT_CL = [354, 40, 1236, 1151]


def kirp_kutusu(yol):
    src = Image.open(yol).convert('RGB')
    k = src.resize(ETSY, Image.LANCZOS)
    L = np.asarray(k).astype(float).mean(2)
    koyu = L < 60
    xs = np.where(koyu.mean(0) > 0.5)[0]; ys = np.where(koyu.mean(1) > 0.5)[0]
    pl, pr, pt, pb = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    my, mx = (pt + pb) // 2, (pl + pr) // 2
    sat = L[my - 160:my + 160].mean(0)
    sut = L[:, mx - 160:mx + 160].mean(1)
    # cerceve bandi poster kenarindan ~20 px; golge cizgisi 15-35 px disarida
    sol = pl - 35 + int(np.argmin(sat[pl - 35:pl - 15])) - 1
    ust = pt - 35 + int(np.argmin(sut[pt - 35:pt - 15])) - 1
    sag = pr + 15 + int(np.argmin(sat[pr + 15:pr + 35])) + 2
    alt = pb + 15 + int(np.argmin(sut[pb + 15:pb + 35])) + 2
    k1588 = [sol, ust, sag, alt]
    o = src.width / ETSY[0]
    k3000 = [int(np.floor(sol * o)), int(np.floor(ust * o)), int(np.ceil(sag * o)), int(np.ceil(alt * o))]
    return {'dosya': yol, 'boyut': list(src.size), 'poster_ici_1588': [pl, pt, pr + 1, pb + 1],
            'kutu_1588': k1588, 'kutu_3000': k3000}


if __name__ == '__main__':
    for y in sys.argv[1:]:
        print(json.dumps(kirp_kutusu(y)))
