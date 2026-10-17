#!/usr/bin/env python3
"""Olcum icin yakin kesit paftasi: her kupa icin kenarlar, ust dudak ve alt cizgi (u=-0.7, 0, +0.7).
Kullanim: python pafta.py <sahne_jpg> <tahmin_json> <cikti_jpg>
"""
import json, sys
from PIL import Image, ImageDraw

im = Image.open(sys.argv[1]).convert("RGB")
K = im.width / 1932
t = json.load(open(sys.argv[2]))
Z, CW, CH = 3, 100, 110
hucre = []
for ad in ("sol", "sag"):
    xl, xr, ust, alt = [v * K for v in t[ad]]
    H = alt - ust; xc, R = (xl + xr) / 2, (xr - xl) / 2
    ym = ust + 0.5 * H
    hucre.append((f"{ad} sol kenar", xl, ym))
    hucre.append((f"{ad} sag kenar", xr, ym))
    for u in (-0.7, 0, 0.7):
        hucre.append((f"{ad} ust u={u}", xc + u * R, ust + 0.06 * H))
    for u in (-0.7, 0, 0.7):
        hucre.append((f"{ad} alt u={u}", xc + u * R, alt - 0.02 * H))
W, Hh = CW * Z, CH * Z + 30
o = Image.new("RGB", (4 * W, 4 * Hh), "white")
for i, (etk, x, y) in enumerate(hucre):
    x0, y0 = int(x - CW / 2), int(y - CH / 2)
    c = im.crop((x0, y0, x0 + CW, y0 + CH)).resize((CW * Z, CH * Z), Image.NEAREST)
    d = ImageDraw.Draw(c)
    for gx in range(x0 - x0 % 10, x0 + CW + 1, 10):
        X = (gx - x0) * Z
        if 0 <= X < CW * Z:
            d.line([(X, 0), (X, 14 if gx % 50 else 30)], fill=(0, 0, 255), width=2)
            if gx % 50 == 0: d.text((X + 3, 32), str(gx), fill=(0, 0, 255))
    for gy in range(y0 - y0 % 10, y0 + CH + 1, 10):
        Y = (gy - y0) * Z
        if 0 <= Y < CH * Z:
            d.line([(0, Y), (14 if gy % 50 else 30, Y)], fill=(255, 0, 0), width=2)
            if gy % 50 == 0: d.text((32, Y - 5), str(gy), fill=(255, 0, 0))
    cx, cy = (i % 4) * W, (i // 4) * Hh
    o.paste(c, (cx, cy + 30))
    ImageDraw.Draw(o).text((cx + 5, cy + 8), f"{i+1}. {etk}", fill=(0, 0, 0))
o.save(sys.argv[3], quality=90)
