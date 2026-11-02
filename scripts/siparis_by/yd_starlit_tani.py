#!/usr/bin/env python3
"""F7 Starlit tani (ETSY YOK, uretim yok): 12x18 ciktida Merkez'in "nokta"si (x 1652, y 3736) ile cevresindeki doku tanesinin
parlaklik (lum - medyan 31) ve bilesen boyutu dagilimi. Yalniz sayi yazar. Kullanim: yd_starlit_tani.py <jpg>"""
import sys
import numpy as np
import cv2
from PIL import Image

a = np.asarray(Image.open(sys.argv[1]).convert("RGB")).astype(np.float32)
L = a @ np.float32([0.299, 0.587, 0.114])
px, py = 1652, 3736
y0, y1, x0, x1 = 3300, 4300, 300, 3300                        # isimler / baslik / tarih bandi (12x18, yaklasik)
Lc = L[y0:y1, x0:x1]
d = Lc - cv2.medianBlur(np.clip(Lc, 0, 255).astype(np.uint8), 31).astype(np.float32)
sat = (a[y0:y1, x0:x1].max(2) - a[y0:y1, x0:x1].min(2))
print("probe d max (13x13):", round(float(d[py - y0 - 6:py - y0 + 7, px - x0 - 6:px - x0 + 7].max()), 2),
      "L:", round(float(L[py, px]), 1), "sat:", round(float(sat[py - y0, px - x0]), 1))
w = d[py - y0 - 15:py - y0 + 16, px - x0 - 15:px - x0 + 16]
print("probe 31x31 d >= 5 px:", int((w >= 5).sum()), ">= 8:", int((w >= 8).sum()), ">= 12:", int((w >= 12).sum()))
yy, xx = np.unravel_index(np.argmax(w), w.shape); print("probe tepe konum:", px - 15 + xx, py - 15 + yy)
print("d yuzdelik (bant):", {q: round(float(np.percentile(d, q)), 2) for q in (50, 90, 99, 99.9, 99.99)})
for t in (5, 8, 10, 12, 15, 20, 25):
    m = (d >= t) & (sat < 60)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    ar = st[1:, 4]
    print(f"esik {t}: bilesen {n - 1}, alan 1-2: {(ar <= 2).sum()}, 3-15: {((ar >= 3) & (ar <= 15)).sum()}, 16-80: {((ar >= 16) & (ar <= 80)).sum()}, >80: {(ar > 80).sum()}",
          "| probe bileseni alan:", int(st[lab[py - y0, px - x0], 4]) if lab[py - y0, px - x0] else 0)
# probe cevresi 41x41 d haritasi (kaba, 5 px adim)
print("d harita (41x41, 5 px adim):")
for j in range(-20, 21, 5):
    print(" ".join(f"{d[py - y0 + j, px - x0 + i]:5.1f}" for i in range(-20, 21, 5)))
