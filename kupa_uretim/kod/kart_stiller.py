#!/usr/bin/env python3
"""Galeri kart 2: 7 stil tek kartta ("Choose your style").
Kullanim: python kart_stiller.py <kapak_klasoru> <font_klasoru> <cift_basligi> <cikti_jpg>
kapak_klasoru icinde KAPAK_0N_<Stil>.jpg dosyalari beklenir.
"""
import sys, pathlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter

KAP, FNT, BASLIK, CIKTI = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3], sys.argv[4]
W = 2576
ZEMIN = (246, 241, 233)
YAZI = (40, 36, 34)
SOLUK = (120, 110, 100)
STILLER = [("01_Botanical", "Botanical"), ("02_Gold", "Gold"), ("03_NazarBond", "Nazar Bond"), ("04_RoseRibbon", "Rose Ribbon"),
           ("05_PromiseLine", "Promise Line"), ("06_AegeanTile", "Aegean Tile"), ("07_Mediterranean", "Mediterranean")]


def font(ad, px, w=None):
    f = ImageFont.truetype(str(FNT / ad), px)
    if w:
        f.set_variation_by_axes([w])
    return f


def ortala(d, metin, y, f, renk, aralik=0):
    gen = sum(d.textlength(c, font=f) for c in metin) + aralik * (len(metin) - 1)
    x = (W - gen) / 2
    for c in metin:
        d.text((x, y), c, font=f, fill=renk)
        x += d.textlength(c, font=f) + aralik


im = Image.new("RGB", (W, W), ZEMIN)
d = ImageDraw.Draw(im)
ortala(d, BASLIK, 230, font("Cinzel[wght].ttf", 46, 500), SOLUK, aralik=10)
ortala(d, "Choose your style", 310, font("EBGaramond[wght].ttf", 150, 500), YAZI)
ortala(d, "One zodiac symbol, seven looks. Pick yours from the Style menu.", 510, font("EBGaramond[wght].ttf", 62, 400), SOLUK)

T, G, M = 560, 46, 130
ust = 700
f_ad = font("Cinzel[wght].ttf", 44, 500)
for i, (dosya, ad) in enumerate(STILLER):
    satir, sutun = (0, i) if i < 4 else (1, i - 4)
    n = 4 if satir == 0 else 3
    x0 = (W - (n * T + (n - 1) * G)) / 2 + sutun * (T + G)
    y0 = ust + satir * (T + 150)
    k = Image.open(KAP / f"KAPAK_{dosya}.jpg").convert("RGB").resize((T, T), Image.LANCZOS)
    maske = Image.new("L", (T, T), 0)
    ImageDraw.Draw(maske).rounded_rectangle([0, 0, T - 1, T - 1], 22, fill=255)
    golge = Image.new("L", (T + 60, T + 60), 0)
    ImageDraw.Draw(golge).rounded_rectangle([30, 36, T + 30, T + 36], 22, fill=70)
    golge = golge.filter(ImageFilter.GaussianBlur(14))
    im.paste((200, 190, 178), (int(x0) - 30, int(y0) - 30), golge)
    im.paste(k, (int(x0), int(y0)), maske)
    gen = d.textlength(ad.upper(), font=f_ad) + 4 * (len(ad) - 1)
    x = x0 + (T - gen) / 2
    for c in ad.upper():
        d.text((x, y0 + T + 34), c, font=f_ad, fill=YAZI)
        x += d.textlength(c, font=f_ad) + 4

d.line([(W / 2 - 520, 2150), (W / 2 + 520, 2150)], fill=(205, 195, 182), width=3)
ortala(d, "Printed on both sides: your symbol and names on the front,", 2200, font("EBGaramond[wght].ttf", 60, 400), YAZI)
ortala(d, "your message on the back.", 2280, font("EBGaramond[wght].ttf", 60, 400), YAZI)
im.save(CIKTI, quality=93)
print("tamam", CIKTI)
