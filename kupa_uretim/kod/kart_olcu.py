#!/usr/bin/env python3
"""Galeri kart 12: olcu karti, 11 oz ve 15 oz, gercek oranda cizim.
Olculer: Printful urun 19 kaydi (11 oz 9,6 x 8,2 cm; 15 oz 11,9 x 8,5 cm).
Kullanim: python kart_olcu.py <font_klasoru> <ust_baslik> <vurgu_rgb 'r,g,b'> <cikti_jpg>
"""
import sys, pathlib
from PIL import Image, ImageDraw, ImageFont

FNT, BASLIK, VURGU, CIKTI = pathlib.Path(sys.argv[1]), sys.argv[2], tuple(int(v) for v in sys.argv[3].split(",")), sys.argv[4]
W, K = 2576, 3  # K: kenar yumusatma icin buyuk cizim
ZEMIN, YAZI, SOLUK, CIZGI = (246, 241, 233), (40, 36, 34), (120, 110, 100), (60, 56, 52)
KUPALAR = [("11 oz", "325 ml", 9.6, 8.2, 3.8, 3.2), ("15 oz", "444 ml", 11.9, 8.5, 4.7, 3.3)]
PXCM = 95
TABAN = 1960


def font(ad, px, w=None):
    f = ImageFont.truetype(str(FNT / ad), px * K)
    if w:
        f.set_variation_by_axes([w])
    return f


im = Image.new("RGB", (W * K, W * K), ZEMIN)
d = ImageDraw.Draw(im)


def gen(m, f, a=0):
    return sum(d.textlength(c, font=f) for c in m) + a * K * (len(m) - 1)


def yaz(x, y, m, f, r, a=0):
    x *= K
    for c in m:
        d.text((x, y * K), c, font=f, fill=r); x += d.textlength(c, font=f) + a * K


def ortala(m, y, f, r, a=0, cx=W / 2):
    yaz(cx - gen(m, f, a) / K / 2, y, m, f, r, a)


def L(pts, renk, w):
    d.line([(x * K, y * K) for x, y in pts], fill=renk, width=w * K)


ortala(BASLIK, 200, font("Cinzel[wght].ttf", 46, 500), SOLUK, a=10)
ortala("Two sizes", 270, font("EBGaramond[wght].ttf", 150, 500), YAZI)
ortala("Choose 11 oz or 15 oz from the Size menu. Same design on both.", 460, font("EBGaramond[wght].ttf", 60, 400), SOLUK)

merkezler = [790, 1786]
f_et, f_ol = font("Cinzel[wght].ttf", 64, 600), font("EBGaramond[wght].ttf", 56, 400)
for i, ((ad, ml, h, dcm, hin, din), cx) in enumerate(zip(KUPALAR, merkezler)):
    hp, wp = h * PXCM, dcm * PXCM
    x0, x1, y0, y1 = cx - wp / 2, cx + wp / 2, TABAN - hp, TABAN
    e = wp * 0.09
    sag = i == 1  # sag kupada kulp sagda, sol kupada solda (ic bosluk temiz)
    # kulp
    if sag:
        dis = [(x1 - 30), (y0 + hp * 0.18), (x1 + wp * 0.36), (y0 + hp * 0.72)]
        ic = [(x1 - 10), (y0 + hp * 0.27), (x1 + wp * 0.22), (y0 + hp * 0.63)]
    else:
        dis = [(x0 - wp * 0.36), (y0 + hp * 0.18), (x0 + 30), (y0 + hp * 0.72)]
        ic = [(x0 - wp * 0.22), (y0 + hp * 0.27), (x0 + 10), (y0 + hp * 0.63)]
    d.rounded_rectangle([v * K for v in dis], radius=int(wp * 0.16 * K), outline=CIZGI, width=7 * K, fill=(255, 255, 255))
    d.rounded_rectangle([v * K for v in ic], radius=int(wp * 0.09 * K), outline=CIZGI, width=6 * K, fill=ZEMIN)
    # govde
    d.rectangle([x0 * K, y0 * K, x1 * K, y1 * K], fill=(255, 255, 255))
    d.ellipse([x0 * K, (y1 - e) * K, x1 * K, (y1 + e) * K], fill=(255, 255, 255), outline=CIZGI, width=7 * K)
    d.rectangle([(x0 + 4) * K, (y1 - e - 2) * K, (x1 - 4) * K, y1 * K], fill=(255, 255, 255))
    L([(x0, y0), (x0, y1)], CIZGI, 7); L([(x1, y0), (x1, y1)], CIZGI, 7)
    d.ellipse([x0 * K, (y0 - e) * K, x1 * K, (y0 + e) * K], fill=(236, 232, 226), outline=CIZGI, width=7 * K)
    # yukseklik olcusu govdenin icinde, ortada
    fy = font("EBGaramond[wght].ttf", 54, 500)
    ya, yb_ = y0 + e + 30, y1 - 30
    L([(cx, ya), (cx, yb_)], VURGU, 4); L([(cx - 24, ya), (cx + 24, ya)], VURGU, 4); L([(cx - 24, yb_), (cx + 24, yb_)], VURGU, 4)
    ym = (ya + yb_) / 2
    d.rectangle([(cx - 150) * K, (ym - 75) * K, (cx + 150) * K, (ym + 75) * K], fill=(255, 255, 255))
    ortala(f"{hin} in", ym - 66, fy, YAZI, cx=cx); ortala(f"{h} cm", ym + 2, fy, SOLUK, cx=cx)
    # cap olcusu (altta)
    oy = y1 + e + 70
    L([(x0, oy), (x1, oy)], VURGU, 4); L([(x0, oy - 24), (x0, oy + 24)], VURGU, 4); L([(x1, oy - 24), (x1, oy + 24)], VURGU, 4)
    ortala(f"{din} in  ·  {dcm} cm", oy + 26, fy, YAZI, cx=cx)
    # etiket
    ortala(ad, y0 - e - 175, f_et, VURGU, a=4, cx=cx)
    ortala(ml, y0 - e - 92, f_ol, SOLUK, cx=cx)

ortala("Height and diameter of the mug body, handle not included.", 2340, font("EBGaramond[wght].ttf", 52, 400), SOLUK)
im.resize((W, W), Image.LANCZOS).save(CIKTI, quality=93)
print("tamam", CIKTI)
