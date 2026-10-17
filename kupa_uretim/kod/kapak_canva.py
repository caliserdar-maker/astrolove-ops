#!/usr/bin/env python3
"""Canva AI bos kupa sahnesine baski dosyasini giydirir: sol kupa ON (sap solda), sag kupa ARKA (sap sagda).
Kullanim: python kapak_canva.py <sahne_jpg> <baski_png> <geo_json> <cikti_jpg> [ortu_npy]
ortu_npy (istege bagli): kupanin onundeki yaprak vb. icin True maske; bu piksellere baski yapilmaz
geo_json'da yalniz "sol" (on yuz) ya da yalniz "sag" (arka yuz) olabilir (tek kupa sahnesi).
SABIT_YUKSEKLIK=1 ortam degiskeni: govde yuksekligi 3,80 inc kabul edilir (yakin cekim, perspektifte kisalan govde icin)
geo_json: {"sol": [xl, xr, yt, yb, et, eb], "sag": [xl, xr, yt, yb, et, eb]}
  xl/xr: govde sol/sag kenari, yt/yb: kenarda ust agiz ve alt cizgi, et/eb: ortada ek sarkma (elips yari yuksekligi)
"""
import json, math, os, sys, time, pathlib
import numpy as np
from PIL import Image
from scipy import ndimage

SAHNE, BASKI, GEO, CIKTI = (pathlib.Path(a) for a in sys.argv[1:5])
ORTU = np.load(sys.argv[5]) if len(sys.argv) > 5 else None
DPI, FW, FH = 300, 2700, 1050
D_IN = 3.35
QUARTER = D_IN * math.pi / 4 * DPI
FACE = {"on": FW / 2 - QUARTER, "arka": FW / 2 + QUARTER}


def giydir(sahne, baski, geo, yuz):
    xl, xr, yt, yb, et, eb = geo
    xc, R = (xl + xr) / 2, (xr - xl) / 2
    pxin = R / (D_IN / 2)
    H = yb - yt
    H_in = 3.80 if os.environ.get("SABIT_YUKSEKLIK") == "1" else H / pxin
    marj_in = (H_in - FH / DPI) / 2
    k = min(1.0, pxin * 1.6 / DPI)
    b = np.asarray(Image.fromarray(baski.astype(np.uint8)).resize((round(FW * k), round(FH * k)), Image.LANCZOS)).astype(np.float32)
    y0, y1 = max(0, int(yt - 4)), min(sahne.shape[0], int(yb + eb + 6))
    x0, x1 = max(0, int(math.floor(xl)) - 5), min(sahne.shape[1], int(math.ceil(xr)) + 5)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    u = (xx + 0.5 - xc) / R
    ic = np.abs(u) < 0.995
    th = np.arcsin(np.clip(u, -1, 1))
    c = np.cos(th)
    t = (yy - yt - et * c) / (H + (eb - et) * c)
    fy = (t * H_in - marj_in) * DPI
    fx = FACE[yuz] + th * (D_IN / 2) * DPI
    dfy = np.maximum(np.abs(np.gradient(fy, axis=0)), 1e-3)
    dfx = np.maximum(np.abs(np.gradient(fx, axis=1)), 1e-3)
    kap = (np.clip((fy + 0.5) / dfy + 0.5, 0, 1) * np.clip((FH - 0.5 - fy) / dfy + 0.5, 0, 1)
           * np.clip((fx + 0.5) / dfx + 0.5, 0, 1) * np.clip((FW - 0.5 - fx) / dfx + 0.5, 0, 1))
    kenar = np.clip((0.995 - np.abs(u)) * R / 1.5, 0, 1)
    kap = np.where(ic, kap, 0.0) * kenar
    if ORTU is not None:
        kap = kap * (1 - ndimage.gaussian_filter(ORTU[y0:y1, x0:x1].astype(np.float32), 1.0))
    kap = kap[..., None]
    orn = np.stack([ndimage.map_coordinates(b[..., ch], [fy * k, fx * k], order=1, mode="nearest") for ch in range(3)], -1)
    bolge = sahne[y0:y1, x0:x1].copy()
    L = bolge.mean(-1)
    sonuc = bolge * orn / 255.0
    taban = ndimage.gaussian_filter(L, 18)
    parla = np.clip(L - taban, 0, None)[..., None] * 2.2
    koyu = 1 - orn.mean(-1, keepdims=True) / 255.0
    sonuc = np.clip(sonuc + parla * koyu + np.clip(L - 235, 0, None)[..., None] * 1.5 * koyu, 0, 255)
    sahne[y0:y1, x0:x1] = np.where(kap > 0, bolge * (1 - kap) + sonuc * kap, bolge)


t0 = time.time()
geo = json.loads(GEO.read_text())
sahne = np.asarray(Image.open(SAHNE).convert("RGB")).astype(np.float32)
b = np.asarray(Image.open(BASKI).convert("RGB")).astype(np.float32)
isler = [(ad, yuz) for ad, yuz in (("sol", "on"), ("sag", "arka")) if ad in geo]
for i, (ad, yuz) in enumerate(isler, 1):
    giydir(sahne, b, geo[ad], yuz)
    g = time.time() - t0
    n = len(isler)
    print(f"{i}/{n} {ad} {g:.1f} sn kalan ~{g / i * (n - i):.1f} sn %{100 * i // n}")
Image.fromarray(np.clip(sahne, 0, 255).astype(np.uint8)).save(CIKTI, quality=95)
print("tamam", CIKTI)
