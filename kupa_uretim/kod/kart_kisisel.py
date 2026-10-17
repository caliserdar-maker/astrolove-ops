#!/usr/bin/env python3
"""Galeri kart 10: kisisellestirme rehberi ("How to personalize").
Kullanim: python kart_kisisel.py <on_png> <arka_png> <font_klasoru> <burc1> <burc2> <isim1> <isim2> <mesaj> <cikti_jpg>
on/arka: Printful saydam mockup (kulp solda on yuz, kulp sagda arka yuz).
"""
import sys, pathlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ON, ARKA, FNT = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
B1, B2, I1, I2, MESAJ, CIKTI = sys.argv[4:10]
W = 2576
ZEMIN, YAZI, SOLUK, CIZGI = (246, 241, 233), (40, 36, 34), (120, 110, 100), (205, 195, 182)
VURGU = (130, 18, 46)


def font(ad, px, w=None):
    f = ImageFont.truetype(str(FNT / ad), px)
    if w:
        f.set_variation_by_axes([w])
    return f


def gen(d, metin, f, aralik=0):
    return sum(d.textlength(c, font=f) for c in metin) + aralik * (len(metin) - 1)


def yaz(d, x, y, metin, f, renk, aralik=0):
    for c in metin:
        d.text((x, y), c, font=f, fill=renk)
        x += d.textlength(c, font=f) + aralik


def ortala(d, metin, y, f, renk, aralik=0, cx=W / 2):
    yaz(d, cx - gen(d, metin, f, aralik) / 2, y, metin, f, renk, aralik)


im = Image.new("RGB", (W, W), ZEMIN)
d = ImageDraw.Draw(im)
ortala(d, f"{B1.upper()} · {B2.upper()}", 200, font("Cinzel[wght].ttf", 46, 500), SOLUK, aralik=10)
ortala(d, "How to personalize", 280, font("EBGaramond[wght].ttf", 150, 500), YAZI)

# 3 adim
adimlar = [("1", "Choose your style"), ("2", "Choose your size"), ("3", "Type your names and message")]
f_no, f_adim = font("Cinzel[wght].ttf", 52, 600), font("EBGaramond[wght].ttf", 60, 500)
for i, (no, metin) in enumerate(adimlar):
    cx = W / 2 + (i - 1) * 760
    d.ellipse([cx - 46, 520, cx + 46, 612], outline=VURGU, width=4)
    ortala(d, no, 532, f_no, VURGU, cx=cx)
    ortala(d, metin, 640, f_adim, YAZI, cx=cx)

# kisisellestirme kutusu
kx0, kx1, ky0, ky1 = W / 2 - 760, W / 2 + 760, 800, 1250
golge = Image.new("L", (W, W), 0)
ImageDraw.Draw(golge).rounded_rectangle([kx0, ky0 + 10, kx1, ky1 + 10], 26, fill=60)
im.paste((205, 195, 182), (0, 0), golge.filter(ImageFilter.GaussianBlur(16)))
d.rounded_rectangle([kx0, ky0, kx1, ky1], 26, fill=(255, 255, 255), outline=CIZGI, width=3)
yaz(d, kx0 + 70, ky0 + 50, "PERSONALIZATION", font("Cinzel[wght].ttf", 40, 600), SOLUK, aralik=6)
f_et, f_de = font("EBGaramond[wght].ttf", 64, 400), font("EBGaramond[wght].ttf", 64, 600)
if B1 == B2:   # ayni burclu cift: sol / sag sembol (ONERI 17 Eki)
    satirlar = [(f"Name under left {B1}:", I1), (f"Name under right {B2}:", I2), ("Message:", MESAJ)]
else:
    satirlar = [(f"Name under {B1}:", I1), (f"Name under {B2}:", I2), ("Message:", MESAJ)]
for j, (et, de) in enumerate(satirlar):
    y = ky0 + 140 + j * 92
    yaz(d, kx0 + 70, y, et, f_et, SOLUK)
    yaz(d, kx0 + 70 + gen(d, et, f_et) + 24, y, de, f_de, YAZI)

# ok
ax = W / 2
d.line([(ax, ky1 + 40), (ax, ky1 + 130)], fill=VURGU, width=6)
d.polygon([(ax - 26, ky1 + 118), (ax + 26, ky1 + 118), (ax, ky1 + 160)], fill=VURGU)

# sonuc: on ve arka (saydam bosluk kirpilir, ayni yukseklige olceklenir)
HY = 600
for k, (p, et) in enumerate([(ON, "FRONT"), (ARKA, "BACK")]):
    m = Image.open(p)
    cx = W / 2 + (k * 2 - 1) * 520
    y0 = int(ky1 + 190)
    if m.mode == "RGBA":   # Printful saydam mockup (Cancer-Libra onayli kart)
        m = m.crop(m.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox())
        m = m.resize((round(m.width * HY / m.height), HY), Image.LANCZOS)
        x0 = int(cx - m.width / 2)
        im.paste(m, (x0, y0), m)
    else:   # tek kupa sahnesi (2576 kare, kapak_canva TEK ciktisi): kart_uzunluk gibi yuvarlak koseli kare (ONERI 17 Eki)
        mx = 1230 if k == 0 else 1350
        m = m.convert("RGB").crop((mx - 950, 1330 - 950, mx + 950, 1330 + 950)).resize((HY, HY), Image.LANCZOS)
        x0 = int(cx - HY / 2)
        golge = Image.new("L", (W, W), 0)
        ImageDraw.Draw(golge).rounded_rectangle([x0, y0 + 10, x0 + HY, y0 + HY + 10], 22, fill=60)
        im.paste((205, 195, 182), (0, 0), golge.filter(ImageFilter.GaussianBlur(14)))
        maske = Image.new("L", (HY, HY), 0)
        ImageDraw.Draw(maske).rounded_rectangle([0, 0, HY - 1, HY - 1], 22, fill=255)
        im.paste(m, (x0, y0), maske)
    ortala(d, et, y0 + HY + 24, font("Cinzel[wght].ttf", 44, 600), YAZI, aralik=8, cx=cx)

d.line([(W / 2 - 700, 2190), (W / 2 + 700, 2190)], fill=CIZGI, width=3)
f_not = font("EBGaramond[wght].ttf", 56, 400)
ortala(d, "Names: up to 10 letters each, printed in capitals on the front.", 2235, f_not, YAZI)
ortala(d, "Message: up to 30 characters, one line. Leave it blank for the sample message.", 2310, f_not, YAZI)
im.save(CIKTI, quality=93)
print("tamam", CIKTI)
