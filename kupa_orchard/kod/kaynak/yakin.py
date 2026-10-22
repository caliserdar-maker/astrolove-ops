#!/usr/bin/env python3
"""Tek kupa on sahnesinden yakin plan sahnesi: kare kirpar, 2576'ya buyutur, geo'yu donusturur.
Kullanim: python yakin.py <sahne_jpg> <geo_json> <genislik_R_kati> <alt_bosluk_px> <cikti_onek>
"""
import json, sys
from PIL import Image
sah, geo, kat, alt_b, onek = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
g = json.load(open(geo)); anahtar = list(g)[0]; xl, xr, yt, yb, et, eb = g[anahtar]
im = Image.open(sah).convert("RGB"); W = im.width
xc, R = (xl + xr) / 2, (xr - xl) / 2
boy = kat * R
x0 = xc - boy / 2
y1 = yb + eb + alt_b; y0 = y1 - boy
s = W / boy
im.resize((W, W), Image.LANCZOS, box=(x0, y0, x0 + boy, y0 + boy)).save(f"{onek}.jpg", quality=95)
yeni = [(xl - x0) * s, (xr - x0) * s, (yt - y0) * s, (yb - y0) * s, et * s, eb * s]
json.dump({anahtar: [round(v, 1) for v in yeni]}, open(f"{onek}_geo.json", "w"))
print("olcek", round(s, 3), "kutu", [round(v) for v in (x0, y0, x0 + boy, y1)])
