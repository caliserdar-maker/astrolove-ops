#!/usr/bin/env python3
"""Tek kupa sahnelerinde govde geometrisini olcer (kaba tahminden, dar pencerelerle) ve kontrol paftasi cizer.
Kullanim: python olcum_tek.py <tahmin_json> <kontrol_jpg>
tahmin_json: {"ad": {"dosya": "...jpg", "yuz": "sol"|"sag", "t": [xl, xr, agiz_ust, alt_orta]} }  (t ekran 1932 olceginde)
Her ad icin geo_<ad>.json yazar.
"""
import json, sys, time
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

tah = json.load(open(sys.argv[1]))
kontrol = sys.argv[2]
US = np.array([-0.7, -0.5, -0.3, 0, 0.3, 0.5, 0.7])
paf = []
t0 = time.time()
for i, (ad, v) in enumerate(tah.items(), 1):
    im = Image.open(v["dosya"]).convert("RGB")
    K = im.width / 1932
    a = np.asarray(im).astype(float)
    L = ndimage.gaussian_filter(a.mean(-1), 1.2)
    gx = np.abs(ndimage.sobel(L, axis=1))
    gy = np.abs(ndimage.sobel(L, axis=0))
    xl, xr, ust, alt = [q * K for q in v["t"]]
    H = alt - ust

    def kenar(x0):
        xs = []
        for f in np.linspace(0.45, 0.62, 12):
            y = int(ust + f * H)
            s = gx[y, int(x0 - 45):int(x0 + 45)]
            xs.append(int(x0 - 45) + int(np.argmax(s)))
        return float(np.median(xs))

    xl, xr = kenar(xl), kenar(xr)
    xc, R = (xl + xr) / 2, (xr - xl) / 2
    c = np.sqrt(1 - US ** 2)
    ya, yu = [], []
    for u in US:
        x = int(xc + u * R)
        s = L[int(alt - 0.12 * H):int(alt + 0.05 * H), x]
        ya.append(int(alt - 0.12 * H) + int(np.argmin(s)))
        y0, y1 = int(ust + 0.02 * H), int(ust + 0.14 * H)
        s = gy[y0:y1, x]
        yu.append(y0 + int(np.argmax(s)))
    A = np.stack([np.ones_like(c), c], 1)

    def saglam(y):
        y = np.array(y, float)
        (b0, b1), *_ = np.linalg.lstsq(A, y, rcond=None)
        r = np.abs(y - (b0 + b1 * c))
        m = r < max(6, 2.5 * np.median(r))
        (b0, b1), *_ = np.linalg.lstsq(A[m], y[m], rcond=None)
        return float(b0), float(b1)

    yb, eb = saglam(ya)
    yt, et = saglam(yu)
    geo = [round(xl, 1), round(xr, 1), round(yt, 1), round(yb, 1), round(et, 1), round(eb, 1)]
    json.dump({v["yuz"]: geo}, open(f"geo_{ad}.json", "w"))
    d = ImageDraw.Draw(im)
    uu = np.linspace(-1, 1, 160)
    for yy, ee in ((yt, et), (yb, eb)):
        d.line([(xc + u * R, yy + ee * np.sqrt(1 - u * u)) for u in uu], fill=(255, 0, 0), width=4)
    d.line([(xl, yt), (xl, yb)], fill=(0, 0, 255), width=4); d.line([(xr, yt), (xr, yb)], fill=(0, 0, 255), width=4)
    for u, y1, y2 in zip(US, ya, yu):
        x = xc + u * R
        d.ellipse([x - 8, y1 - 8, x + 8, y1 + 8], outline=(0, 170, 0), width=3)
        d.ellipse([x - 8, y2 - 8, x + 8, y2 + 8], outline=(0, 170, 0), width=3)
    y0 = int(yt - 80); y1 = int(yb + eb + 60); x0 = int(xl - 40); x1 = int(xr + 40)
    ust_k = im.crop((x0, y0, x1, y0 + 260)); alt_k = im.crop((x0, y1 - 300, x1, y1))
    w = 700
    ust_k = ust_k.resize((w, int(260 * w / (x1 - x0)))); alt_k = alt_k.resize((w, int(300 * w / (x1 - x0))))
    c_ = Image.new("RGB", (w, ust_k.height + alt_k.height + 30), "white")
    c_.paste(ust_k, (0, 0)); c_.paste(alt_k, (0, ust_k.height + 26))
    ImageDraw.Draw(c_).text((4, ust_k.height + 6), f"{ad} {geo}", fill=(0, 0, 0))
    paf.append(c_)
    g = time.time() - t0
    print(f"{i}/{len(tah)} {ad} {geo}  {g:.0f} sn kalan ~{g / i * (len(tah) - i):.0f} sn %{100 * i // len(tah)}")
Hm = max(p.height for p in paf)
o = Image.new("RGB", (3 * 710, ((len(paf) + 2) // 3) * (Hm + 10)), "white")
for i, p in enumerate(paf):
    o.paste(p, ((i % 3) * 710, (i // 3) * (Hm + 10)))
o.save(kontrol, quality=85)
