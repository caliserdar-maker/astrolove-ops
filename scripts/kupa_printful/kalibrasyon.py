#!/usr/bin/env python3
"""2700x1050 kalibrasyon dosyasi: on yuz (kirmizi FRONT), arka yuz (mavi BACK), orta (yesil CENTER), uclar.
Yuz merkezleri: FW/2 -/+ 3.35*pi/4*300 (kupa capi 3.35 inc). Kullanim: python kalibrasyon.py <cikti.png>"""
import math, sys
from PIL import Image, ImageDraw, ImageFont

FW, FH, D = 2700, 1050, 3.35
Q = D * math.pi / 4 * 300
ON, ARKA = FW / 2 - Q, FW / 2 + Q
im = Image.new("RGB", (FW, FH), "white")
d = ImageDraw.Draw(im)
fb = ImageFont.load_default(size=120)
fk = ImageFont.load_default(size=56)


def yaz(x, y, t, f, renk):
    w = d.textlength(t, font=f)
    d.text((x - w / 2, y), t, font=f, fill=renk)


for x, t, r in [(ON, "FRONT", (200, 0, 0)), (ARKA, "BACK", (0, 0, 200))]:
    d.line([(x, 60), (x, FH - 60)], fill=r, width=8)
    yaz(x, 380, t, fb, r)
    d.ellipse([x - 300, 200, x + 300, 800], outline=r, width=6)
d.line([(FW / 2, 0), (FW / 2, FH)], fill=(0, 140, 0), width=8)
yaz(FW / 2, 450, "CENTER", fk, (0, 140, 0))
yaz(190, 880, "LEFT END", fk, (120, 120, 120))
yaz(FW - 190, 880, "RIGHT END", fk, (120, 120, 120))
d.rectangle([0, 0, FW - 1, FH - 1], outline=(0, 0, 0), width=6)
im.save(sys.argv[1], dpi=(300, 300))
print("OZET kalibrasyon", sys.argv[1], im.size, "on_merkez", round(ON, 1), "arka_merkez", round(ARKA, 1))
