# GOZ (DUR) icin: eski sistem DB/PW posteri | yeni, ayni olcu, TAM cozunurluk yan yana (eski solda) + 2000 px onizleme.
# Kullanim: python yanyana.py ESKI_JPG YENI_JPG CIKTI_JPG ONIZLEME_JPG
import sys, numpy as np
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
e, y, out, on = sys.argv[1:5]
E, Y = Image.open(e).convert('RGB'), Image.open(y).convert('RGB')
if E.size != Y.size: raise SystemExit(f'HATA boyut farkli {E.size} {Y.size}')
w, h = Y.size; ara = max(40, w // 120)
T = Image.new('RGB', (2 * w + ara, h), (128, 128, 128)); T.paste(E, (0, 0)); T.paste(Y, (w + ara, 0))
T.save(out, quality=95, subsampling=0, dpi=(300, 300))
k = T.resize((2000, int(round(2000 * h / (2 * w + ara)))), Image.LANCZOS); d = ImageDraw.Draw(k)
for x, s in ((10, 'ESKI'), (1000 + 10, 'YENI')): d.rectangle((x, 8, x + 70, 34), fill=(128, 128, 128)); d.text((x + 8, 14), s, fill=(255, 0, 0))
k.save(on, quality=90)
print('yan yana', out, T.size)
