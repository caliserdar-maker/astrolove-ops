#!/usr/bin/env python3
"""CL kart 11 (Made for you, step by step.) 3000x2250 yeniden kurulum.
ChatGPT taslagi yalniz METIN kaynagi: Lato yazi, eski tip rakam (oɪ), DNA disi baslik yeri ve buyuk bos alanlar vardi.
Yazi stili canli kart 03 listesinden olculdu: rakam Garamond duz (lnum) altin, yukseklik 58 px, x 174;
baslik Garamond 78 wght 450, x 342; govde Montserrat 45 wght 500, basliktan 97 px asagi.
2x2 izgara (ince cizgili), icerik dikeyde dengeli. Ust etiket canli 03'ten, alt cizgi+satir kart 03 v2'den.
Metin (aciklama v3 ile ayni): 24 saatte onizleme; onay/24 saat kurali; 7 is gunu (28 Eyl: hazirlik 4-7 is gunu); paketleme (Prodigi: boya gore duz ya da rulo, 28 Eyl); ABD takipli.
QC: boyut, zemin, tire yok, satir tasmasi/cakisma yok.
Kullanim: kart11_kur.py CANLI_03.jpg KART03_V2.jpg GARAMOND.ttf MONTSERRAT.ttf CIKIS.jpg
"""
import re
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

C03, K03V2, GAR, MON, CIK = sys.argv[1:6]
BG = (237, 232, 226); NAVY_T = (25, 34, 49); SANS_T = (23, 25, 30); GOLD = (140, 114, 70)
out = Image.new('RGB', (3000, 2250), BG); d = ImageDraw.Draw(out)
C3 = Image.open(C03).convert('RGB'); V2 = Image.open(K03V2).convert('RGB')
out.paste(C3.crop((0, 70, 1500, 140)), (0, 70)); out.paste(V2.crop((0, 2130, 3000, 2250)), (0, 2130))
RULE = tuple(int(v) for v in np.asarray(V2)[2145, 1500])

def font(yol, boy, w):
    f = ImageFont.truetype(yol, boy); f.set_variation_by_axes([w]); return f

FT = font(GAR, 120, 450); FS = font(MON, 49, 500)
b = FT.getbbox('Two signs. One shared symbol.', anchor='ls'); d.text((143 - b[0], 201 - b[1]), 'Made for you, step by step.', font=FT, fill=NAVY_T, anchor='ls')
b = FS.getbbox('Cancer and Libra, united in an original AstroLove design.', anchor='ls'); d.text((147 - b[0], 336 - b[1]), 'Prints and framed prints, made to order.', font=FS, fill=SANS_T, anchor='ls')

LN = ['lnum']
FNUM = font(GAR, min(range(60, 130), key=lambda s: abs((lambda bb: bb[3] - bb[1])(font(GAR, s, 450).getbbox('01', anchor='ls', features=LN)) - 58)), 450)
FH = font(GAR, 78, 450); FB = font(MON, 45, 500); SAT = 66

def sar(txt, genislik):
    satir, cur = [], ''
    for w in txt.split():
        t = (cur + ' ' + w).strip()
        if FB.getbbox(t, anchor='ls')[2] <= genislik:
            cur = t
        else:
            satir.append(cur); cur = w
    return satir + [cur]

HUC = [('01', 'Your preview', 'We send a preview via Etsy Messages within 24 hours of your order.'),
       ('02', 'Your approval', 'We print as soon as you approve. No reply in 24 hours? We print as shown.'),
       ('03', 'Made to order', 'Printed and shipped within 7 business days after approval.'),
       ('04', 'Delivered with care', 'Prints are carefully packed flat or rolled, depending on size. Framed prints come boxed with corner guards. US orders ship tracked.')]
CX = [145, 1600]; CW = 1255; RY = [650, 1230]
kutular = []
for i, (n, t, s) in enumerate(HUC):
    x0, y0 = CX[i % 2], RY[i // 2]
    d.line((x0, y0, x0 + CW, y0), fill=RULE, width=2)
    ust = y0 + 80
    bn = FNUM.getbbox(n, anchor='ls', features=LN); d.text((x0 + 29 - bn[0], ust - bn[1]), n, font=FNUM, fill=GOLD, anchor='ls', features=LN)
    bh = FH.getbbox(t, anchor='ls'); d.text((x0 + 197 - bh[0], ust - bh[1]), t, font=FH, fill=NAVY_T, anchor='ls')
    by = ust + 97; cap = -FB.getbbox('W', anchor='ls')[1]
    satirlar = sar(s, CW - 197)
    for j, ln in enumerate(satirlar):
        bb = FB.getbbox(ln, anchor='ls'); d.text((x0 + 197 - bb[0], by + cap + j * SAT), ln, font=FB, fill=SANS_T, anchor='ls')
        kutular.append((x0 + 197, x0 + 197 + bb[2] - bb[0], x0 + CW))
    kutular.append(('alt', by + cap + (len(satirlar) - 1) * SAT + 20, RY[1] if i < 2 else 1860))
FN = font(MON, 42, 400); t = 'See the listing for the delivery estimate to your address.'
b = FN.getbbox(t, anchor='ls'); d.text((1500 - (b[0] + b[2]) / 2, 1900 - b[1]), t, font=FN, fill=SANS_T, anchor='ls')
out.save(CIK, quality=95, subsampling=0)

R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
tasma = [k for k in kutular if k[0] != 'alt' and k[1] > k[2]]
cakisma = [k for k in kutular if k[0] == 'alt' and k[1] > k[2]]
zemin = all(max(abs(int(a) - b) for a, b in zip(R[y, x], BG)) <= 2 for x, y in [(60, 1000), (2950, 1000), (1500, 1650), (1500, 2050)])
tum = ' '.join(x[1] + ' ' + x[2] for x in HUC) + ' ' + t
tire = bool(re.search(r'[‒-―−]', tum))
print(f'rakam font {FNUM.size} | tasma {len(tasma)} | cakisma {len(cakisma)} | zemin {zemin} | tire {tire}')
print('PASS' if R.shape[:2] == (2250, 3000) and not tasma and not cakisma and zemin and not tire else 'FAIL')
