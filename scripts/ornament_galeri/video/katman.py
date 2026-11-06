#!/usr/bin/env python3
"""Baski 954 -> katman maskeleri (halka, sembol, kucuk burclar) + sembolsuz ve sembol+halkasiz baski (Telea, AI yok)."""
import sys, json
import numpy as np, cv2
from PIL import Image
src, out = sys.argv[1], sys.argv[2]
p = np.asarray(Image.open(src).convert("RGBA")).copy()
rgb = p[..., :3].copy()
h = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
g = ((h[..., 0] >= 10) & (h[..., 0] <= 36) & (h[..., 1] > 60) & (h[..., 2] > 70)).astype(np.uint8)
n, lab, st, cen = cv2.connectedComponentsWithStats(g, 8)
halka = np.zeros_like(g); sembol = np.zeros_like(g); sol = np.zeros_like(g); sag = np.zeros_like(g)
for i in range(1, n):
    x, y, w, hh, a = st[i]; cx, cy = cen[i]
    if w > 500 and hh > 400:
        halka[lab == i] = 1
    elif 240 < cy < 570 and 300 < cx < 650:
        sembol[lab == i] = 1
    elif 590 <= cy <= 670 and cx < 400:
        sol[lab == i] = 1
    elif 590 <= cy <= 670 and cx > 550:
        sag[lab == i] = 1
# halka: geometrik daire uydurma; ince uc (esik alti) da maskeye girsin (annulus, isim / glif bolgesine girmeden)
ys, xs = np.nonzero(halka)
A_ = np.c_[2 * xs, 2 * ys, np.ones(len(xs))]; b_ = xs ** 2 + ys ** 2
cxh, cyh, c_ = np.linalg.lstsq(A_, b_, rcond=None)[0]; rh = float(np.sqrt(c_ + cxh ** 2 + cyh ** 2))
yy, xx = np.mgrid[:g.shape[0], :g.shape[1]]
ann = (np.abs(np.hypot(xx - cxh, yy - cyh) - rh) < 9) & (yy < 720)
diger = cv2.dilate(((sol | sag) > 0).astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
renkli = (h[..., 1] > 25) & (np.abs(rgb.astype(int) - cv2.GaussianBlur(rgb, (0, 0), 6).astype(int)).max(2) > 6)
halka = np.maximum(halka, (ann & renkli & ~diger).astype(np.uint8))
HALKA = dict(cx=float(cxh), cy=float(cyh), r=rh)
def gen(m, k=5):
    return cv2.dilate(m, np.ones((k, k), np.uint8))
M = {"halka": halka, "sembol": sembol, "sol": sol, "sag": sag}
np.savez_compressed(f"{out}/maske954.npz", **M)
def sil(m):
    r = cv2.inpaint(rgb, gen(m, 7), 6, cv2.INPAINT_TELEA)
    q = p.copy(); q[..., :3] = r; return q
Image.fromarray(sil(sembol)).save(f"{out}/baski_semsiz.png")
Image.fromarray(sil(np.maximum(sembol, halka))).save(f"{out}/baski_bos.png")
print(json.dumps({k: int(v.sum()) for k, v in M.items()})); json.dump(HALKA, open(f"{out}/halka.json", "w")); print(HALKA)
