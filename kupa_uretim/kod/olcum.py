#!/usr/bin/env python3
"""Kaba tahminden kupa geometrisini olcer ve kontrol gorseli cizer.
Kullanim: python olcum.py <sahne_jpg> <tahmin_json> <geo_cikti_json> <kontrol_jpg>
tahmin_json (ekran 1932 olcegi): {"sol": [xl, xr, agiz_ust, alt_orta], "sag": [...]}
"""
import json, sys, pathlib
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

SAHNE, TAHMIN, GEO, KONTROL = (pathlib.Path(a) for a in sys.argv[1:5])
im = Image.open(SAHNE).convert("RGB")
K = im.width / 1932
a = np.asarray(im).astype(float)
L = ndimage.gaussian_filter(a.mean(-1), 1.2)
gx = np.abs(ndimage.sobel(L, axis=1))
gy = ndimage.sobel(L, axis=0)
tah = json.loads(TAHMIN.read_text())
geo = {}


def kenar(x0, ylar, ara=30):
    xs = []
    for y in ylar:
        s = gx[y, int(x0 - ara):int(x0 + ara)]
        xs.append(int(x0 - ara) + int(np.argmax(s)))
    return float(np.median(xs))


for ad in ("sol", "sag"):
    xl, xr, ust, alt = [v * K for v in tah[ad]]
    H = alt - ust
    ylar = [int(ust + H * f) for f in np.linspace(0.42, 0.62, 9)]
    xl = kenar(xl, ylar); xr = kenar(xr, ylar)
    xc, R = (xl + xr) / 2, (xr - xl) / 2
    us = np.array([-0.85, -0.7, -0.55, -0.4, -0.2, 0, 0.2, 0.4, 0.55, 0.7, 0.85])
    c = np.sqrt(1 - us ** 2)
    # alt: temas golgesi (en koyu)
    ya = []
    for u in us:
        x = int(xc + u * R)
        s = L[int(alt - 0.16 * H):int(alt + 0.06 * H), x]
        ya.append(int(alt - 0.16 * H) + int(np.argmin(s)))
    A = np.stack([np.ones_like(c), c], 1)
    (yb, eb), *_ = np.linalg.lstsq(A, np.array(ya, float), rcond=None)
    # ust: on dudak (ic griden parlak dudaga gecis), agiz ust + %3..%17 H
    yu = []
    for u in us:
        x = int(xc + u * R)
        y0, y1 = int(ust + 0.035 * H), int(ust + 0.17 * H)
        s = np.abs(gy[y0:y1, x])
        yu.append(y0 + int(np.argmax(s)))
    (yt, et), *_ = np.linalg.lstsq(A, np.array(yu, float), rcond=None)
    geo[ad] = [round(xl, 1), round(xr, 1), round(float(yt), 1), round(float(yb), 1), round(float(et), 1), round(float(eb), 1)]
    geo[ad + "_nokta"] = {"alt": ya, "ust": yu}

GEO.write_text(json.dumps(geo))
d = ImageDraw.Draw(im)
for ad in ("sol", "sag"):
    xl, xr, yt, yb, et, eb = geo[ad]
    xc, R = (xl + xr) / 2, (xr - xl) / 2
    for u0, u1 in zip(np.linspace(-1, 1, 80)[:-1], np.linspace(-1, 1, 80)[1:]):
        for (yy, ee) in ((yt, et), (yb, eb)):
            d.line([(xc + u0 * R, yy + ee * np.sqrt(1 - u0 ** 2)), (xc + u1 * R, yy + ee * np.sqrt(1 - u1 ** 2))], fill=(255, 0, 0), width=3)
    d.line([(xl, yt), (xl, yb)], fill=(0, 0, 255), width=3); d.line([(xr, yt), (xr, yb)], fill=(0, 0, 255), width=3)
    us = [-0.85, -0.7, -0.55, -0.4, -0.2, 0, 0.2, 0.4, 0.55, 0.7, 0.85]
    for u, y1, y2 in zip(us, geo[ad + "_nokta"]["alt"], geo[ad + "_nokta"]["ust"]):
        x = xc + u * R
        d.ellipse([x - 6, y1 - 6, x + 6, y1 + 6], outline=(0, 160, 0), width=3)
        d.ellipse([x - 6, y2 - 6, x + 6, y2 + 6], outline=(0, 160, 0), width=3)
im.resize((1000, 1000)).save(KONTROL, quality=88)
print(SAHNE.name, {k: v for k, v in geo.items() if "nokta" not in k})
