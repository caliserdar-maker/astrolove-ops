import sys
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent / "k78/scripts/kapak78"))
import yd_kart_ornek as K
W, H = K.W, K.H
src = Image.open("S1_yeni2.jpg").convert("RGB")
a = np.asarray(src).astype(int)
# alt satirin yeri: NOT_Y civarinda koyu pikseller
band = (np.abs(a - np.array([245,240,231])).max(2) > 40)[int(K.NOT_Y)-60:int(K.NOT_Y)+140]
ys = np.nonzero(band.any(1))[0]; y0, y1 = ys.min()+int(K.NOT_Y)-60, ys.max()+int(K.NOT_Y)-60
print("alt satir", y0, y1)
for ad, alt in (("WA", "Personalized with your two names and your message"),
                ("KUPA", "Personalized with your two names and your message"),
                ("YD", "Personalized with your two names and your date")):
    im = src.copy(); d = ImageDraw.Draw(im)
    d.rectangle([0, y0-10, W, y1+10], fill=K.ZEMIN)
    K.yaz(d, K.METIN, [alt], W/2, K.NOT_Y, "center", W - 2*K.KENAR)
    im.save(f"S1_ortak_{ad}.jpg", quality=95)
