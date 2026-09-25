#!/usr/bin/env python3
"""Yalniz secilen kartlar icin paket gorseli + REVIEW yan yana (review.py ile ayni ad, kalite ve olcek).
Kullanim: python3 tek_kart.py 3 7   (once: python3 cards.py 3 7)"""
import sys
from PIL import Image, ImageDraw, ImageFont
import os
import master as M
from review_ad import NAMES
R = M.ROOT; OUT = R / 'paket'; RV = OUT / 'REVIEW'; IM = OUT / 'images'
for d in (RV, IM): d.mkdir(parents=True, exist_ok=True)
FNT = ImageFont.truetype(os.environ.get('FONT_DIR', '/home/user/astrolove-ops/work/fonts/') + 'Montserrat[wght].ttf', 28)
REF = sorted((R / 'etsy/REF_4570143815').glob('[01]*.jpg'))
ns = [int(a) for a in sys.argv[1:]]
for k, n in enumerate(ns, 1):
    i = n - 1; nm = NAMES[i]
    im = Image.open(R / f'out/card{n:02d}.png').convert('RGB')
    im.save(IM / f'{nm}.jpg', quality=95, subsampling=0)
    ref = Image.open(REF[i]).convert('RGB'); H = 1125
    a = ref.resize((round(ref.width * H / ref.height), H), Image.LANCZOS); b = im.resize((round(im.width * H / im.height), H), Image.LANCZOS)
    page = Image.new('RGB', (a.width + b.width + 60, H + 70), 'white'); d = ImageDraw.Draw(page)
    page.paste(a, (20, 60)); page.paste(b, (a.width + 40, 60))
    d.text((20, 15), f'{n:02d} REFERANS 4570143815 ({ref.width}x{ref.height})', fill='black', font=FNT)
    d.text((a.width + 40, 15), f'{n:02d} KOVA-KOVA v1 ({im.width}x{im.height})', fill='black', font=FNT)
    page.save(RV / f'P{n:02d}_{nm}_yan_yana.jpg', quality=92)
    print(f'[{k}/{len(ns)}] %{100*k/len(ns):.0f} {nm}', flush=True)
