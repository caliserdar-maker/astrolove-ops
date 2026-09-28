#!/usr/bin/env python3
"""CL galeri 19 gorsel temas sayfasi (sirali, gercek 4:3), Serdar onayi icin.
Kullanim: galeri_temas.py PAKET_KLASORU CIKIS.jpg MONTSERRAT.ttf
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

kl, cik, fy = sys.argv[1:4]
dosya = sorted(f for f in os.listdir(kl) if f.lower().endswith('.jpg'))
f = ImageFont.truetype(fy, 22); f.set_variation_by_axes([500])
SU, W, H, PAY = 4, 720, 540, 44
sat = (len(dosya) + SU - 1) // SU
T = Image.new('RGB', (SU * (W + 16) + 16, sat * (H + PAY + 12) + 16), (250, 248, 245)); d = ImageDraw.Draw(T)
for i, ad in enumerate(dosya):
    x, y = 16 + (i % SU) * (W + 16), 16 + (i // SU) * (H + PAY + 12)
    d.text((x, y + 8), ad, font=f, fill=(40, 40, 40))
    T.paste(Image.open(os.path.join(kl, ad)).convert('RGB').resize((W, H), Image.LANCZOS), (x, y + PAY))
T.save(cik, quality=90)
print(f'temas sayfasi: {len(dosya)} gorsel -> {cik}')
