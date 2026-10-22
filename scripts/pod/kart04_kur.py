#!/usr/bin/env python3
"""CL kart 04 (Each name goes under its own sign.) 3000x2250 yeniden kurulum.
ChatGPT taslagi (1200x900) yalniz YERLESIM ve METIN kaynagidir (koordinatlar x2.5).
- Sol gorsel: onayli kapaktaki GERCEK poster (sikistirma geri alinmis 1560x1988), isim/mesaj bandi
  birebir kirpilir (yeniden cizim yok).
- Yazilar: canli DNA fontlari (EB Garamond + Montserrat), olculer canli kart 03'ten kalibre:
  baslik Garamond 120 wght 450, alt baslik Montserrat 49 wght 500.
- Ust etiket ve alt cizgi+alt satir: canli kart 03 / onayli kart 03 v2'den piksel kopya.
QC: boyut, zemin, sol gorsel NCC >= 0.99, kutu tasmasi yok, uzun/orta tire yok.
Kullanim: kart04_kur.py KAPAK.jpg CANLI_03.jpg KART03_V2.jpg GARAMOND.ttf MONTSERRAT.ttf CIKIS.jpg
"""
import re
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

KAPAK, C03, K03V2, GAR, MON, CIK = sys.argv[1:7]
BG = (237, 232, 226); NAVY_T = (25, 34, 49); SANS_T = (23, 25, 30)
KUTU_IC, KUTU_KENAR = (252, 251, 249), (190, 187, 180)
out = Image.new('RGB', (3000, 2250), BG); d = ImageDraw.Draw(out)

def font(yol, boy, w):
    f = ImageFont.truetype(yol, boy); f.set_variation_by_axes([w]); return f

def boy_bul(yol, w, txt, hedef_gen):
    en = min(range(20, 200), key=lambda s: abs(font(yol, s / 1, w).getbbox(txt, anchor='ls')[2]
                                                 - font(yol, s, w).getbbox(txt, anchor='ls')[0] - hedef_gen))
    return en

def yaz(x, y, txt, f, renk):
    """Murekkep kutusunun sol-ust kosesi (x, y) olacak sekilde yazar."""
    b = f.getbbox(txt, anchor='ls'); d.text((x - b[0], y - b[1]), txt, font=f, fill=renk, anchor='ls')
    return (x, y, x + b[2] - b[0], y + b[3] - b[1])

C = Image.open(C03).convert('RGB'); V2 = Image.open(K03V2).convert('RGB')
# ust etiket (ayni metin) ve alt bolum (cizgi + PERSONALIZED ZODIAC COUPLE WALL ART)
out.paste(C.crop((0, 70, 1500, 140)), (0, 70))
out.paste(V2.crop((0, 2130, 3000, 2250)), (0, 2130))

# baslik ve alt baslik: canli 03 ile ayni taban cizgisi mantigi
FT = font(GAR, 120, 450); FS = font(MON, 49, 500)
def taban(f, canli_txt, ust):  # canli metnin murekkep ustu -> taban cizgisi
    return ust - f.getbbox(canli_txt, anchor='ls')[1]
bt = taban(FT, 'Two signs. One shared symbol.', 201)
bs = taban(FS, 'Cancer and Libra, united in an original AstroLove design.', 336)
lt = FT.getbbox('Two signs. One shared symbol.', anchor='ls')[0]; ls_ = FS.getbbox('Cancer and Libra, united in an original AstroLove design.', anchor='ls')[0]
d.text((143 - lt, bt), 'Each name goes under its own sign.', font=FT, fill=NAVY_T, anchor='ls')
d.text((147 - ls_, bs), 'Type each name in the field for its sign.', font=FS, fill=SANS_T, anchor='ls')

# sol gorsel: gercek poster bandi
P = Image.open(KAPAK).convert('RGB').crop((734, 130, 2268, 2118)).resize((1560, 1988), Image.LANCZOS)
SOL = (145, 830, 1425, 1413)
band = P.crop((90, 1195, 1483, 1829)).resize((SOL[2] - SOL[0], SOL[3] - SOL[1]), Image.LANCZOS)
out.paste(band, SOL[:2])

# sag: etiket + kutu (ChatGPT yerlesimi x2.5)
FL = font(MON, boy_bul(MON, 500, 'Name under Cancer', 402), 500)
FK = font(MON, boy_bul(MON, 450, 'It Began With a Kiss in the Rain', 732), 450)
alanlar = [('Name under Cancer', 'EMILY', 832, (1575, 885, 2855, 995)),
           ('Name under Libra', 'JAMES', 1038, (1575, 1090, 2855, 1200)),
           ('Your message', 'It Began With a Kiss in the Rain', 1245, (1575, 1295, 2855, 1405))]
kutular = []
for et, deg, ey, k in alanlar:
    yaz(1588, ey, et, FL, SANS_T)
    d.rounded_rectangle(k, radius=10, fill=KUTU_IC, outline=KUTU_KENAR, width=3)
    b = FK.getbbox('EMILY', anchor='ls'); cap = -b[1]
    taban_y = round((k[1] + k[3]) / 2 + cap / 2)
    bb = FK.getbbox(deg, anchor='ls'); d.text((1620 - bb[0], taban_y), deg, font=FK, fill=SANS_T, anchor='ls')
    kutular.append((k, 1620 + bb[2] - bb[0]))

# alt metinler
FE = font(MON, boy_bul(MON, 500, 'EMILY = CANCER    JAMES = LIBRA', 700), 500)
yaz(435, 1750, 'EMILY = CANCER    JAMES = LIBRA', FE, SANS_T)
FN = font(GAR, boy_bul(GAR, 450, 'Names print in capitals. Your message prints as you type it.', 1193), 450)
b = FN.getbbox('Names print in capitals. Your message prints as you type it.', anchor='ls')
d.text((1500 - (b[2] + b[0]) / 2, 1900 - b[1]), 'Names print in capitals. Your message prints as you type it.', font=FN, fill=NAVY_T, anchor='ls')
FP = font(MON, boy_bul(MON, 400, 'We send you a preview before we finalize your order.', 615), 400)
b = FP.getbbox('We send you a preview before we finalize your order.', anchor='ls')
d.text((1500 - (b[2] + b[0]) / 2, 2008 - b[1]), 'We send you a preview before we finalize your order.', font=FP, fill=SANS_T, anchor='ls')
out.save(CIK, quality=95, subsampling=0)

# QC
R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
n_sol = ncc(R[SOL[1]:SOL[3], SOL[0]:SOL[2]].mean(2), np.asarray(band).astype(np.float32).mean(2))
zemin = [tuple(int(v) for v in R[y, x]) for (x, y) in [(60, 600), (2900, 600), (1500, 1550), (2900, 1700), (60, 2100)]]
zemin_ok = all(max(abs(a - b) for a, b in zip(z, BG)) <= 2 for z in zemin)
tasma = [k for k, sag in kutular if sag > k[2] - 40]
metin = 'Each name goes under its own sign. Type each name in the field for its sign. Names print in capitals. Your message prints as you type it. We send you a preview before we finalize your order.'
tire = bool(re.search(r'[‒-―−]', metin))
print(f'boyut {R.shape[1]}x{R.shape[0]} | sol gorsel NCC {n_sol:.4f} | zemin {zemin_ok} | kutu tasmasi {len(tasma)} | tire {tire}')
print(f'font boylari: etiket {FL.size} kutu {FK.size} esit satiri {FE.size} serif {FN.size} onizleme {FP.size}')
print('PASS' if R.shape[:2] == (2250, 3000) and n_sol >= 0.99 and zemin_ok and not tasma and not tire else 'FAIL')
