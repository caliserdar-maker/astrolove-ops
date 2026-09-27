#!/usr/bin/env python3
"""CL renk varyasyon gorseli v2 (cercevesiz, format-notr) 3000x2250.
ChatGPT galeri karari (27 Eyl, Serdar onayli surec): varyasyon fotograflari cercevesiz ve
format acisindan tarafsiz; ayni zemin, ayni oran, ayni koordinat; poster yukseklik ~%78;
altta iki kucuk satir (RENK ADI / "Poster color. Format selected separately.");
5 gorselde ayni cok ince notr kontur; oda isigi/golge/metalik parilti yok.
Tek sapma: oran 2:3 degil 11:14 (5 rengin de GERCEK dosyasi bu oranda; WP icin 2:3 render yok, IS_0047).
Poster kaynaklari gercek dosyalar, yeniden cizim yok. Renk adi Menu 2 yazimiyla birebir.
QC: 3000x2250, poster ic NCC >= 0.99, oran 11:14 (+-1 px), zemin koseler, kontur var, tire yok.
Kullanim: renk_varyasyon_kur.py POSTER.jpg "RENK ADI" MONTSERRAT.ttf CIKIS.jpg
"""
import re
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

POSTER, RENK, MON, CIK = sys.argv[1:5]
DUVAR = (216, 209, 202)          # notr sicak gri, 5 gorselde ayni
KONTUR = (168, 162, 155)         # cok ince notr kontur, 5 gorselde ayni
SANS_T = (23, 25, 30)
W, H = 3000, 2250
PH = 1755                        # gorsel yuksekliginin %78'i
PW = round(PH * 11 / 14)
PY = 150                         # poster ust kenari; alt 1905, yazilar 1905-2130 bandinda
K = 3                            # kontur kalinligi

def font(yol, boy, w):
    f = ImageFont.truetype(yol, boy); f.set_variation_by_axes([w]); return f

B = Image.open(POSTER).convert('RGB')
# kaynagi 11:14'e getir: genisse yanlardan, uzunsa alt-ustten esit kirp (zemin dokusu, icerik kaybi yok)
hedef = 11 / 14
if B.width / B.height > hedef:
    yw = round(B.height * hedef); x0 = (B.width - yw) // 2; B = B.crop((x0, 0, x0 + yw, B.height))
else:
    yh = round(B.width / hedef); y0 = (B.height - yh) // 2; B = B.crop((0, y0, B.width, y0 + yh))
poster = B.resize((PW, PH), Image.LANCZOS)

out = Image.new('RGB', (W, H), DUVAR); d = ImageDraw.Draw(out)
PX = (W - PW) // 2
d.rectangle((PX - K, PY - K, PX + PW + K - 1, PY + PH + K - 1), fill=KONTUR)
out.paste(poster, (PX, PY))

FA = font(MON, 56, 600); FB = font(MON, 40, 400)
satir = [RENK, 'Poster color. Format selected separately.']
for t, f, y in [(satir[0], FA, 1985), (satir[1], FB, 2075)]:
    b = f.getbbox(t, anchor='ls'); d.text((1500 - (b[0] + b[2]) / 2, y - b[1]), t, font=f, fill=SANS_T, anchor='ls')
out.save(CIK, quality=95, subsampling=0)

# QC
R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
n = ncc(R[PY + 20:PY + PH - 20, PX + 20:PX + PW - 20].mean(2), np.asarray(poster).astype(np.float32)[20:-20, 20:-20].mean(2))
kose = all(max(abs(int(a) - b) for a, b in zip(R[y_, x_], DUVAR)) <= 3 for x_, y_ in [(60, 60), (2940, 60), (60, 2190), (2940, 2190)])
kontur = max(abs(int(a) - b) for a, b in zip(R[PY + PH + 1, 1500], KONTUR)) <= 25
tire = bool(re.search(r'[‒–—―−]', ' '.join(satir)))
oran = abs(PW / PH - 11 / 14) < 0.002
print(f'poster {PW}x{PH} (%{PH / H * 100:.0f}) NCC {n:.4f} | oran11:14 {oran} | zemin {kose} | kontur {kontur} | tire {tire}')
print('PASS' if R.shape[:2] == (H, W) and n >= 0.99 and kose and kontur and oran and not tire else 'FAIL')
