#!/usr/bin/env python3
"""Galeri kart 13: bakim ve uretim. Bilgiler Printful urun 19 kaydindan (ceramic, dishwasher and microwave safe).
Kullanim: python kart_bakim.py <font_klasoru> <ust_baslik> <vurgu 'r,g,b'> <cikti_jpg>
"""
import sys, pathlib, math
from PIL import Image, ImageDraw, ImageFont

FNT, BASLIK, VURGU, CIKTI = pathlib.Path(sys.argv[1]), sys.argv[2], tuple(int(v) for v in sys.argv[3].split(",")), sys.argv[4]
W, K = 2576, 3
ZEMIN, YAZI, SOLUK, CIZGI = (246, 241, 233), (40, 36, 34), (120, 110, 100), (205, 195, 182)
im = Image.new("RGB", (W * K, W * K), ZEMIN)
d = ImageDraw.Draw(im)


def font(ad, px, w=None):
    f = ImageFont.truetype(str(FNT / ad), px * K)
    if w:
        f.set_variation_by_axes([w])
    return f


def gen(m, f, a=0):
    return sum(d.textlength(c, font=f) for c in m) + a * K * (len(m) - 1)


def ortala(m, y, f, r, a=0, cx=W / 2):
    x = (cx - gen(m, f, a) / K / 2) * K
    for c in m:
        d.text((x, y * K), c, font=f, fill=r); x += d.textlength(c, font=f) + a * K


def R(b, r=0, w=8):
    d.rounded_rectangle([v * K for v in b], radius=r * K, outline=VURGU, width=w * K)


def L(p, w=8):
    d.line([(x * K, y * K) for x, y in p], fill=VURGU, width=w * K, joint="curve")


def E(b, w=8, fill=None):
    d.ellipse([v * K for v in b], outline=VURGU, width=w * K, fill=fill)


def ikon_bulasik(cx, cy):
    R([cx - 110, cy - 130, cx + 110, cy + 130], 22)
    L([(cx - 110, cy - 70), (cx + 110, cy - 70)])
    E([cx + 50, cy - 108, cx + 74, cy - 84], 6); E([cx + 10, cy - 108, cx + 34, cy - 84], 6)
    for dx in (-60, -20, 20, 60):
        L([(cx + dx, cy - 30), (cx + dx, cy + 80)], 7)
    L([(cx - 80, cy + 95), (cx + 80, cy + 95)], 7)


def ikon_mikro(cx, cy):
    R([cx - 150, cy - 100, cx + 150, cy + 100], 20)
    R([cx - 120, cy - 70, cx + 50, cy + 70], 10, 7)
    E([cx + 80, cy - 60, cx + 120, cy - 20], 6); E([cx + 80, cy, cx + 120, cy + 40], 6)
    for k in range(3):
        y = cy - 30 + k * 30
        L([(cx - 90 + j * 10, y + 8 * math.sin(j)) for j in range(0, 12)], 5)


def ikon_kupa(cx, cy):
    R([cx - 90, cy - 100, cx + 70, cy + 110], 18)
    R([cx + 50, cy - 50, cx + 140, cy + 50], 40, 8)
    L([(cx - 30, cy - 160), (cx - 15, cy - 135), (cx - 30, cy - 115)], 6)
    L([(cx + 10, cy - 160), (cx + 25, cy - 135), (cx + 10, cy - 115)], 6)


def ikon_kalp(cx, cy):
    pts = []
    for t in [i / 200 * 2 * math.pi for i in range(201)]:
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * 7, cy - y * 7 + 10))
    L(pts, 8)
    E([cx - 150, cy - 150, cx + 150, cy + 150], 6)


ortala(BASLIK, 200, font("Cinzel[wght].ttf", 46, 500), SOLUK, a=10)
ortala("Care & making", 270, font("EBGaramond[wght].ttf", 150, 500), YAZI)

ogeler = [(ikon_bulasik, "Dishwasher safe", "Easy to clean."),
          (ikon_mikro, "Microwave safe", "Warm up your coffee or tea."),
          (ikon_kupa, "Glossy white ceramic", "Printed on both sides."),
          (ikon_kalp, "Made to order", "Printed for you after you order.")]
f_b, f_a = font("Cinzel[wght].ttf", 56, 600), font("EBGaramond[wght].ttf", 58, 400)
for i, (ik, b, a) in enumerate(ogeler):
    cx = W / 2 + (i % 2 * 2 - 1) * 560
    cy = 900 + (i // 2) * 780
    ik(cx, cy)
    ortala(b.upper(), cy + 210, f_b, YAZI, a=5, cx=cx)
    ortala(a, cy + 300, f_a, SOLUK, cx=cx)

d.line([((W / 2 - 600) * K, 2300 * K), ((W / 2 + 600) * K, 2300 * K)], fill=CIZGI, width=3 * K)
ortala("Original zodiac symbols designed by AstroLoveArt.", 2340, font("EBGaramond[wght].ttf", 56, 400), YAZI)
im.resize((W, W), Image.LANCZOS).save(CIKTI, quality=93)
print("tamam", CIKTI)
