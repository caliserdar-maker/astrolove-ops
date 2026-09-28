#!/usr/bin/env python3
"""Duvar leke seviyesi onizlemesi (Serdar 28 Eyl): her seviye 02 + 15 yan yana, gercek 4:3.
Kullanim: duvar_onizleme.py SEVIYE_KOK CIKIS_KLASORU MONTSERRAT.ttf  (SEVIYE_KOK/<hafif|orta|guclu>/*.jpg)
"""
import sys
from PIL import Image, ImageDraw, ImageFont
kok, cik, font = sys.argv[1], sys.argv[2], sys.argv[3]
f = ImageFont.truetype(font, 34); f.set_variation_by_axes([600])
g = ImageFont.truetype(font, 24); g.set_variation_by_axes([400])
AD = {'hafif': 'HAFIF', 'orta': 'ORTA', 'guclu': 'GUCLU'}
for sv, ad in AD.items():
    W = Image.new('RGB', (2400, 960), (250, 248, 245)); d = ImageDraw.Draw(W)
    d.text((16, 14), f'Duvar leke azaltma: {ad}', font=f, fill=(30, 30, 30))
    d.text((1216, 20), '02_format (sol)  |  15_renk_midnight_blue (sag)  |  her kart 3000x2250, 4:3', font=g, fill=(80, 80, 80))
    W.paste(Image.open(f'{kok}/{sv}/02_format.jpg').resize((1195, 896), Image.LANCZOS), (0, 62))
    W.paste(Image.open(f'{kok}/{sv}/15_renk_midnight_blue.jpg').resize((1195, 896), Image.LANCZOS), (1205, 62))
    W.save(f'{cik}/ONIZLEME_{ad}.jpg', quality=90)
