#!/usr/bin/env python3
"""Sahnedeki kupa govdesini yukari uzatir: 11 oz oran (yukseklik/cap 3.80/3.23).
Agiz bandi (BANT_UST..BANT_ALT) aynen yukari otelenir, altindaki govde (BANT_ALT..ESNET_SON) dikey esnetilir.
ESNET_SON sapin ust birlesiminin USTUNDE secilir; boylece sap ve birlesim yeri hic degismez.
Yalniz govde sutunlari (xl-6..xr+7) islenir.
Kullanim: python3 -I uzat.py <sahne> <cikti> <xl> <xr> <yt_kenar> <yb_kenar> <bant_ust> <bant_alt> <esnet_son>"""
import sys, json
import numpy as np
from PIL import Image
from scipy import ndimage

S, C = sys.argv[1:3]
xl, xr, yt, yb = (float(v) for v in sys.argv[3:7])
BU, BA, ES = (int(v) for v in sys.argv[7:10])
ORAN = 3.80 / 3.23
d = round(ORAN * (xr - xl) - (yb - yt))          # yukari kayma (px)
assert d > 0 and BU < yt < BA < ES, 'bant sirasi yanlis'
a = np.asarray(Image.open(S).convert('RGB')).astype(np.float32)
x0, x1 = int(xl) - 6, int(xr) + 7
ust = BU - d
yy = np.arange(ust, ES, dtype=np.float32)
src = np.where(yy < BA - d, yy + d,                                   # agiz bandi: oteleme
               BA + (yy - (BA - d)) * (ES - BA) / (ES - (BA - d)))    # govde: esnetme
Y, X = np.meshgrid(src, np.arange(x0, x1, dtype=np.float32), indexing='ij')
blok = np.stack([ndimage.map_coordinates(a[..., c], [Y, X], order=1) for c in range(3)], -1)
w = np.ones(x1 - x0, np.float32); w[:4] = np.linspace(0, 1, 4); w[-4:] = np.linspace(1, 0, 4)
out = a.copy()
out[ust:ES, x0:x1] = out[ust:ES, x0:x1] * (1 - w[None, :, None]) + blok * w[None, :, None]
Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(C)
print(json.dumps({"kayma": d, "esneme_kati": round((ES - (BA - d)) / (ES - BA), 3), "yeni_yt": yt - d,
                  "oran": round((yb - (yt - d)) / (xr - xl), 4)}))
