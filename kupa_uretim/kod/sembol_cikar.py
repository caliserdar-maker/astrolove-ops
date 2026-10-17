#!/usr/bin/env python3
"""Midnight Blue posterinden (4800x6000 veya 7200x9000) orijinal sembol maskelerini cikarir.
Sembol yeniden cizilmez: altin pikseller maske olarak alinir.
Cikti: ana, sol, sag, halka_ring, halka_sembol (+ mevcut sonsuz kopyalanir)
Kullanim: python cikar.py <poster> <cikti_klasoru> <sonsuz_png>"""
import sys, shutil, pathlib
import numpy as np
from PIL import Image
from scipy import ndimage

src, out, sonsuz = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
out.mkdir(parents=True, exist_ok=True)
im = Image.open(src).convert("RGB")
if im.size != (4800, 6000):
    im = im.resize((4800, 6000), Image.LANCZOS)
im = np.asarray(im).astype(np.float32)
a = np.clip((im[..., 0] - im[..., 2] - 12.0) / 28.0, 0, 1)

def temizle(a, oran=0.02):
    lab, n = ndimage.label(a > 0.3)
    if not n:
        return a
    sz = ndimage.sum(np.ones_like(a), lab, range(1, n + 1))
    keep = [i + 1 for i, s in enumerate(sz) if s >= oran * sz.max()]
    return a * ndimage.binary_dilation(np.isin(lab, keep), iterations=3)

def kaydet(a, ad, bb=None):
    m = Image.fromarray((a * 255).astype(np.uint8), "L")
    if bb is None:
        bb = m.getbbox(); m = m.crop(bb)
    rgba = Image.new("RGBA", m.size, (255, 255, 255, 0)); rgba.putalpha(m)
    rgba.save(out / f"{ad}.png"); print(ad, bb, m.size)

# halka: 3346 px cap, ust kenari orta kolondaki ilk altin piksel
R = 1673
ys = np.where(a[600:1500, 2380:2420].max(1) > 0.3)[0]
y_ust = 600 + ys.min()
xs = np.where(a[1500:3300].max(0) > 0.3)[0]          # halka yanlari (yildizlar kucuk; en dis kolonlar)
cx = 2400.0
x0, y0 = int(round(cx - R)), int(y_ust)
can = a[y0:y0 + 2756, x0:x0 + 3346]
yy, xx = np.mgrid[0:can.shape[0], 0:can.shape[1]]
d = np.hypot(xx - R, yy - R)
ring = temizle(np.where(np.abs(d - R) < 45, can, 0))
sem = temizle(np.where(d < R - 70, can, 0))
kaydet(ring, "halka_ring", bb=(0, 0, 3346, 2756)) if False else None
for ad, arr in (("halka_ring", ring), ("halka_sembol", sem)):
    m = Image.fromarray((arr * 255).astype(np.uint8), "L")
    rgba = Image.new("RGBA", m.size, (255, 255, 255, 0)); rgba.putalpha(m); rgba.save(out / f"{ad}.png")
    print(ad, m.getbbox())
kaydet(sem, "ana")
for ad, (bx0, by0, bx1, by1) in {"sol": (600, 3650, 2350, 4300), "sag": (2450, 3650, 4200, 4300)}.items():
    kaydet(temizle(a[by0:by1, bx0:bx1].copy()), ad)
shutil.copy(sonsuz, out / "sonsuz.png")
