#!/usr/bin/env python3
"""Duvar aydinlik secenekleri onizlemesi (Serdar 28 Eyl): her secenek 02 + 15 + mevcut kapak (01 v9e) yan yana,
gercek 4:3; ayrica tek sayfada karsilastirma (GUCLU referans + ACIK-1/2/3).
Kullanim: duvar_aydinlik_onizleme.py KOK CIKIS_KLASORU KAPAK_01.jpg MONTSERRAT.ttf [GUCLU_KOK]
  KOK/<acik1|acik2|acik3>/{02_format,15_renk_midnight_blue}.jpg ; GUCLU_KOK/{02_format,15_...}.jpg (istege bagli)
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

kok, cik, kapak, fyol = sys.argv[1:5]
guclu = sys.argv[5] if len(sys.argv) > 5 else None
f = ImageFont.truetype(fyol, 34); f.set_variation_by_axes([600])
g = ImageFont.truetype(fyol, 24); g.set_variation_by_axes([400])
AD = {'acik1': 'ACIK-1 (biraz, L* +5)', 'acik2': 'ACIK-2 (orta, L* +10)', 'acik3': 'ACIK-3 (belirgin, L* +15)'}
K = Image.open(kapak).convert('RGB')


def satir(klasor):
    return [Image.open(os.path.join(klasor, '02_format.jpg')), Image.open(os.path.join(klasor, '15_renk_midnight_blue.jpg')), K]


for sv, ad in AD.items():
    W = Image.new('RGB', (3600, 960), (250, 248, 245)); d = ImageDraw.Draw(W)
    d.text((16, 14), f'Duvar: GUCLU + {ad}', font=f, fill=(30, 30, 30))
    d.text((1816, 20), '02_format  |  15_renk_midnight_blue  |  01 kapak (v9e, degismez)  |  her biri 3000x2250, 4:3', font=g, fill=(80, 80, 80))
    for i, im in enumerate(satir(os.path.join(kok, sv))):
        W.paste(im.resize((1195, 896), Image.LANCZOS), (i * 1202, 62))
    W.save(os.path.join(cik, f'ONIZLEME_{sv.upper()}.jpg'), quality=90)

rows = ([('GUCLU (mevcut, referans)', guclu)] if guclu else []) + [(AD[s], os.path.join(kok, s)) for s in AD]
C = Image.new('RGB', (2430, len(rows) * 660 + 10), (250, 248, 245)); d = ImageDraw.Draw(C)
for r, (ad, kl) in enumerate(rows):
    y = r * 660 + 10
    d.text((14, y), ad, font=f, fill=(30, 30, 30))
    for i, im in enumerate(satir(kl)):
        C.paste(im.resize((800, 600), Image.LANCZOS), (i * 810 + 5, y + 50))
C.save(os.path.join(cik, 'KARSILASTIRMA_ACIK.jpg'), quality=90)
