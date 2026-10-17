#!/usr/bin/env python3
"""Tek kupa on/arka sahne ciftinde kupa boyutunu ve yerini esitler.
Kucuk kupali sahne kirpilip buyutulur: iki sahnede kupa govdesi ayni genislikte, taban cizgisi ayni yukseklikte,
yatayda ayna konumda (on sahnede kupa ortasi x ise arka sahnede W - x) olur.
Kullanim: python esitle.py <on_jpg> <on_geo> <arka_jpg> <arka_geo> <cikti_onek>
Cikti: <onek>_on.jpg, <onek>_on_geo.json, <onek>_arka.jpg, <onek>_arka_geo.json
"""
import json, sys
from PIL import Image

on_jpg, on_geo, arka_jpg, arka_geo, onek = sys.argv[1:6]
g_on = json.load(open(on_geo))["sol"]
g_ar = json.load(open(arka_geo))["sag"]


def bilgi(g):
    xl, xr, yt, yb, et, eb = g
    return (xl + xr) / 2, (xr - xl) / 2, yb + eb  # merkez x, yaricap, orta taban y


def donustur(jpg, g, s, x0, y0, W):
    im = Image.open(jpg).convert("RGB")
    kutu = (x0, y0, x0 + W / s, y0 + W / s)
    im = im.resize((W, W), Image.LANCZOS, box=kutu)
    xl, xr, yt, yb, et, eb = g
    yeni = [(xl - x0) * s, (xr - x0) * s, (yt - y0) * s, (yb - y0) * s, et * s, eb * s]
    return im, [round(v, 1) for v in yeni]


W = Image.open(on_jpg).width
c_on, r_on, t_on = bilgi(g_on)
c_ar, r_ar, t_ar = bilgi(g_ar)
if r_on >= r_ar:
    ref = ("on", c_on, r_on, t_on); kuc = ("arka", arka_jpg, g_ar, c_ar, r_ar, t_ar)
else:
    ref = ("arka", c_ar, r_ar, t_ar); kuc = ("on", on_jpg, g_on, c_on, r_on, t_on)
_, rc, rr, rt = ref
ad, jpg, g, c, r, t = kuc
s = rr / r
hedef_x = W - rc  # ayna konum
x0 = c - hedef_x / s
y0 = t - rt / s
boy = W / s
x0 = min(max(x0, 0), W - boy)
y0 = min(max(y0, 0), W - boy)
im, yeni = donustur(jpg, g, s, x0, y0, W)
anahtar = "sol" if ad == "on" else "sag"
im.save(f"{onek}_{ad}.jpg", quality=95)
json.dump({anahtar: yeni}, open(f"{onek}_{ad}_geo.json", "w"))
# referans sahne oldugu gibi kopyalanir
ref_ad = ref[0]
Image.open(on_jpg if ref_ad == "on" else arka_jpg).convert("RGB").save(f"{onek}_{ref_ad}.jpg", quality=95)
json.dump({"sol": g_on} if ref_ad == "on" else {"sag": g_ar}, open(f"{onek}_{ref_ad}_geo.json", "w"))
print(f"buyutulen: {ad}  olcek {s:.3f}  kirpma ({x0:.0f},{y0:.0f}) boy {boy:.0f}  yeni geo {yeni}")
