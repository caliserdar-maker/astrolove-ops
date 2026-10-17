#!/usr/bin/env python3
"""Galeri kart 11: kisa ve uzun isim/mesaj ornegi (2x2).
Kullanim: python kart_uzunluk.py <kisa_on> <uzun_on> <kisa_arka> <uzun_arka> <font_klasoru> <ust_baslik> <cikti_jpg>
Gorseller: tek kupa sahnelerine giydirilmis 2576 kare goruntuler.
"""
import sys, pathlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter

KO, UO, KA, UA = sys.argv[1:5]
FNT, BASLIK, CIKTI = pathlib.Path(sys.argv[5]), sys.argv[6], sys.argv[7]
W = 2576
ZEMIN, YAZI, SOLUK = (246, 241, 233), (40, 36, 34), (120, 110, 100)


def font(ad, px, w=None):
    f = ImageFont.truetype(str(FNT / ad), px)
    if w:
        f.set_variation_by_axes([w])
    return f


def gen(d, m, f, a=0):
    return sum(d.textlength(c, font=f) for c in m) + a * (len(m) - 1)


def yaz(d, x, y, m, f, r, a=0):
    for c in m:
        d.text((x, y), c, font=f, fill=r); x += d.textlength(c, font=f) + a


def ortala(d, m, y, f, r, a=0, cx=W / 2):
    yaz(d, cx - gen(d, m, f, a) / 2, y, m, f, r, a)


im = Image.new("RGB", (W, W), ZEMIN)
d = ImageDraw.Draw(im)
ortala(d, BASLIK, 150, font("Cinzel[wght].ttf", 46, 500), SOLUK, a=10)
ortala(d, "Short or long, it fits", 215, font("EBGaramond[wght].ttf", 130, 500), YAZI)
ortala(d, "Names up to 10 letters each. Messages up to 30 characters.", 390, font("EBGaramond[wght].ttf", 58, 400), SOLUK)

T, G = 920, 60
x_sol = (W - 2 * T - G) / 2
f_cip = font("Cinzel[wght].ttf", 40, 600)
kareler = [(KO, "SHORT NAMES", 1230), (UO, "LONG NAMES", 1230), (KA, "SHORT MESSAGE", 1350), (UA, "LONG MESSAGE", 1350)]
for i, (p, et, cx) in enumerate(kareler):
    kaynak = Image.open(p).convert("RGB")
    boy = 1900
    k = kaynak.crop((cx - boy / 2, 1330 - boy / 2, cx + boy / 2, 1330 + boy / 2)).resize((T, T), Image.LANCZOS)
    x0 = int(x_sol + (i % 2) * (T + G)); y0 = int(540 + (i // 2) * (T + G))
    golge = Image.new("L", (W, W), 0)
    ImageDraw.Draw(golge).rounded_rectangle([x0, y0 + 10, x0 + T, y0 + T + 10], 24, fill=60)
    im.paste((205, 195, 182), (0, 0), golge.filter(ImageFilter.GaussianBlur(14)))
    maske = Image.new("L", (T, T), 0)
    ImageDraw.Draw(maske).rounded_rectangle([0, 0, T - 1, T - 1], 24, fill=255)
    im.paste(k, (x0, y0), maske)
    gw = gen(d, et, f_cip, 6) + 60
    d.rounded_rectangle([x0 + 30, y0 + 30, x0 + 30 + gw, y0 + 104], 37, fill=(255, 255, 255))
    yaz(d, x0 + 60, y0 + 44, et, f_cip, YAZI, 6)
im.save(CIKTI, quality=93)
print("tamam", CIKTI)
