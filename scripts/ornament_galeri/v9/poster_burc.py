#!/usr/bin/env python3
"""poster_burc.py (8 Kas): asama 1 = posterin kucultulmus onizlemesi + ust/alt bolge kesitleri (burclarin yeri belirlensin).
kullanim: python poster_burc.py POSTER_BURC.json poster_dir cikti_dir"""
import json, sys
from pathlib import Path
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
c = json.load(open(sys.argv[1])); P, O = Path(sys.argv[2]), Path(sys.argv[3])
for cift in c["posterler"]:
    im = Image.open(P / f"{cift}_7200x10800.jpg").convert("RGB")
    print(cift, im.size)
    k = im.copy(); k.thumbnail((1200, 1800)); k.save(O / f"{cift}_ONIZLEME_1200.jpg", quality=88)
    for i, (y0, y1) in enumerate([(0, 3600), (3600, 7200), (7200, 10800)]):
        b = im.crop((0, y0, 7200, y1)); b.thumbnail((2400, 1200)); b.save(O / f"{cift}_BOLGE{i}.jpg", quality=88)
