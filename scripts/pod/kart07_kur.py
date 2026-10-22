#!/usr/bin/env python3
"""CL kart 07 (Four classic frames.) 3000x2250 kurulum.
Cerceveler (master sistem, ChatGPT karari 27 Eyl): her kaplama kendi Prodigi fotografindan, cizim yok.
AG: on cephe bos cerceve fotografi 059 (9 parca, gercek koseler). BK/WH/NA: chevron kose fotografi
037/039/041'den GERCEK miter kosesi FxF blok olarak kirpilir (4 koseye aynalanir), kenarlar ayni kolun
duz seridinden. 4 kaplamada geometri kilitli: ayni dis olcu, ayni ic acir, ayni yuz F.
Olcu (Prodigi foyu): yuz 20 mm, rebate 5 mm (baskinin 5 mm'si cerceve altinda), paspartu yok.
Olcek 16x20: gorunen baski 396.4 mm -> yuz = gorunen genislik x 20/396.4.
Poster: canli kart 04'teki gercek Midnight Blue poster (4:5).
Yazilar: EB Garamond + Montserrat (canli 03 kalibrasyonu); ust etiket canli 03'ten, alt cizgi+satir kart 03 v2'den.
QC: boyut, 4 cerceve ayni olcu ve alt cizgi, poster NCC >= 0.99 (ic bolge), zemin, tire yok.
Kullanim: kart07_kur.py CANLI_04.jpg CANLI_03.jpg KART03_V2.jpg KAYNAK_DIR GARAMOND.ttf MONTSERRAT.ttf CIKIS.jpg
"""
import re
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

C04, C03, K03V2, KAY, GAR, MON, CIK = sys.argv[1:8]
KAY = Path(KAY)
BG = (237, 232, 226); NAVY_T = (25, 34, 49); SANS_T = (23, 25, 30); GOLD_T = (123, 108, 74)
CHEVRON = {'AG': '045_Classic_20antique_20gold_20frame_20chevron.jpg', 'BK': '037_Classic_20black_20frame_20chevron.jpg',
           'WH': '039_Classic_20white_20frame_20chevron.jpg', 'NA': '041_Classic_20natural_20frame_20chevron.jpg'}
AD = {'AG': 'Antique Gold Frame', 'BK': 'Black Frame', 'WH': 'White Frame', 'NA': 'Natural Frame'}  # Menu 1 ile harf harf ayni
PV_W, PV_H = 540, 675                      # gorunen baski
# Olcek 16x20 (Serdar 27 Eyl: cerceve ince, gorsel buyuk): gorunen baski 406.4-10 = 396.4 mm
F = round(PV_W * 20 / 396.4)               # cerceve yuzu (px)
OW, OH = PV_W + 2 * F, PV_H + 2 * F


def _maske(im):
    a = np.asarray(im).astype(int); m = (255 - a.min(2)) > 10
    m = ndimage.binary_opening(m, iterations=2); lab, k = ndimage.label(m)
    return lab == (np.argmax(ndimage.sum(m, lab, range(1, k + 1))) + 1)


def _dondur(src, aci):
    return src.rotate(aci, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))


def _ilk_kosu(v):
    kop = np.where(np.diff(v) > 1)[0]
    return v[:kop[0] + 1] if len(kop) else v


def parcalar(yol):
    """Chevron fotografini Γ konumuna dondurur (dikey kol sol, yatay kol ust), gercek olculerle
    3 parca dondurur: FxF gercek miter KOSE blogu, dikey kol duz seridi, yatay kol duz seridi.
    Hicbir sey cizilmez; dis kenardan 1 px iceriden kirpilir (beyaz halo girmesin)."""
    src = Image.open(yol).convert('RGB')
    m0 = _maske(_dondur(src, -45)); ys, xs = np.where(m0); y0 = ys.min()
    Yy = np.arange(y0 + 400, y0 + 1150, 10)
    Xx = np.array([np.where(m0[y, :])[0].min() for y in Yy])
    aci = float(np.degrees(np.arctan(np.polyfit(Yy, Xx, 1)[0])))
    im = _dondur(src, -45 - aci); m = _maske(im)
    dis, ic = [], []
    ys, xs = np.where(m); y0 = ys.min(); x0 = xs.min()
    for y in range(y0 + 400, y0 + 1150, 10):                     # dikey kol (satirlarda)
        v = _ilk_kosu(np.where(m[y, :])[0]); dis.append(v.min()); ic.append(v.max())
    x_dis, x_ic = max(dis) + 1, min(ic)
    dis2, ic2 = [], []
    for x in range(x_dis + 400, x_dis + 1150, 10):               # yatay kol (sutunlarda)
        v = _ilk_kosu(np.where(m[:, x])[0]); dis2.append(v.min()); ic2.append(v.max())
    y_dis, y_ic = max(dis2) + 1, min(ic2)
    fs = min(x_ic - x_dis, y_ic - y_dis)
    kose = im.crop((x_dis, y_dis, x_dis + fs, y_dis + fs))       # gercek miter birlesimi
    s_v = im.crop((x_dis, y_dis + 400, x_dis + fs, y_dis + 1150))
    s_h = im.crop((x_dis + 400, y_dis, x_dis + 1150, y_dis + fs))
    bilgi = {'aci': round(aci, 2), 'profil_px': int(fs), 'kenar_sapma_px': int(max(dis) - min(dis))}
    return kose, s_v, s_h, bilgi


BLANK = {'AG': '059_Classic_20Antique_20Gold_20Frame_blank.jpg'}   # Serdar 27 Eyl: AG, Prodigi on cephe fotografindan


def blank_kenarlar(yol):
    """Prodigi Classic Antique Gold bos cerceve fotografi (059): 9 parca; olculen dis (455,282)-(1543,1672), kirpim 46 px."""
    src = Image.open(yol).convert('RGB'); X0, Y0, X1, Y1, f = 455, 282, 1544, 1673, 46
    r = lambda b, w, h: src.crop(b).resize((w, h), Image.LANCZOS)
    return {'ust': r((X0 + f, Y0, X1 - f, Y0 + f), OW - 2 * F, F), 'alt': r((X0 + f, Y1 - f, X1 - f, Y1), OW - 2 * F, F),
            'sol': r((X0, Y0 + f, X0 + f, Y1 - f), F, OH - 2 * F), 'sag': r((X1 - f, Y0 + f, X1, Y1 - f), F, OH - 2 * F),
            'k1': r((X0, Y0, X0 + f, Y0 + f), F, F), 'k2': r((X1 - f, Y0, X1, Y0 + f), F, F),
            'k3': r((X0, Y1 - f, X0 + f, Y1), F, F), 'k4': r((X1 - f, Y1 - f, X1, Y1), F, F)}


def cerceve(kod, poster):
    """Master kompozit: poster ic dudak golgesiyle icte; kenarlar ve GERCEK miter koseleri
    kaplamanin kendi fotografindan. AG on cephe bos cerceve (059), digerleri chevron parcalari."""
    fr = Image.new('RGB', (OW, OH), (0, 0, 0))
    p = poster.copy().convert('RGB'); pa = np.asarray(p).astype(np.float32)
    yy = np.arange(PV_H)[:, None]; xx = np.arange(PV_W)[None, :]
    g = 1 - 0.28 * np.exp(-yy / 9.0) - 0.22 * np.exp(-xx / 9.0) - 0.08 * np.exp(-(PV_H - 1 - yy) / 5.0) - 0.08 * np.exp(-(PV_W - 1 - xx) / 5.0)
    fr.paste(Image.fromarray(np.clip(pa * g[..., None], 0, 255).astype(np.uint8)), (F, F))
    if kod in BLANK:
        k = blank_kenarlar(KAY / BLANK[kod])
        fr.paste(k['ust'], (F, 0)); fr.paste(k['alt'], (F, OH - F)); fr.paste(k['sol'], (0, F)); fr.paste(k['sag'], (OW - F, F))
        fr.paste(k['k1'], (0, 0)); fr.paste(k['k2'], (OW - F, 0)); fr.paste(k['k3'], (0, OH - F)); fr.paste(k['k4'], (OW - F, OH - F))
        return fr, {'kaynak': BLANK[kod]}
    kose, s_v, s_h, bilgi = parcalar(KAY / CHEVRON[kod])
    K = kose.resize((F, F), Image.LANCZOS)
    V = s_v.resize((F, OH - 2 * F), Image.LANCZOS)
    Hs = s_h.resize((OW - 2 * F, F), Image.LANCZOS)
    fr.paste(Hs, (F, 0)); fr.paste(Hs.transpose(Image.FLIP_TOP_BOTTOM), (F, OH - F))
    fr.paste(V, (0, F)); fr.paste(V.transpose(Image.FLIP_LEFT_RIGHT), (OW - F, F))
    fr.paste(K, (0, 0)); fr.paste(K.transpose(Image.FLIP_LEFT_RIGHT), (OW - F, 0))
    fr.paste(K.transpose(Image.FLIP_TOP_BOTTOM), (0, OH - F)); fr.paste(K.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM), (OW - F, OH - F))
    return fr, {**bilgi, 'kaynak': CHEVRON[kod]}


def font(yol, boy, w):
    f = ImageFont.truetype(yol, boy); f.set_variation_by_axes([w]); return f


out = Image.new('RGB', (3000, 2250), BG); d = ImageDraw.Draw(out)
C3 = Image.open(C03).convert('RGB'); V2 = Image.open(K03V2).convert('RGB'); C4 = Image.open(C04).convert('RGB')
out.paste(C3.crop((0, 70, 1500, 140)), (0, 70))
out.paste(V2.crop((0, 2130, 3000, 2250)), (0, 2130))
FT = font(GAR, 120, 450); FS = font(MON, 49, 500)
b = FT.getbbox('Two signs. One shared symbol.', anchor='ls'); d.text((143 - b[0], 201 - b[1]), 'Four classic frames.', font=FT, fill=NAVY_T, anchor='ls')
b = FS.getbbox('Cancer and Libra, united in an original AstroLove design.', anchor='ls'); d.text((147 - b[0], 336 - b[1]), 'Choose the finish that suits your space.', font=FS, fill=SANS_T, anchor='ls')

# poster: canli 04 MB (520x650), rebate 5 mm / 203.2 mm her kenardan
mb = C4.crop((269, 499, 791, 1150)).resize((520, 650), Image.LANCZOS)
kx, ky = round(520 * 5 / 406.4), round(650 * 5 / 508)
poster = mb.crop((kx, ky, 520 - kx, 650 - ky)).resize((PV_W, PV_H), Image.LANCZOS)

SIRA = ['AG', 'BK', 'WH', 'NA']
GAP = (2710 - 4 * OW) / 3
UST = 540
yerler = {k: (round(145 + i * (OW + GAP)), UST) for i, k in enumerate(SIRA)}
cer = {}; bilgiler = {}
for k in SIRA:
    cer[k], bilgiler[k] = cerceve(k, poster)
# golge (kart 02 ile ayni: dx 15, dy 18, sigma 26, koyuluk 59/232)
sil = Image.new('L', out.size, 0)
for k, (x, y) in yerler.items():
    sil.paste(255, (x + 15, y + 18, x + 15 + OW, y + 18 + OH))
alfa = np.asarray(sil.filter(ImageFilter.GaussianBlur(26))).astype(np.float32) / 255
o = np.asarray(out).astype(np.float32); bant = np.zeros(alfa.shape, bool); bant[440:1400] = True
o[bant] *= (1 - (59 / 232) * alfa[bant])[:, None]; out = Image.fromarray(np.clip(o, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(out)
for k, (x, y) in yerler.items():
    out.paste(cer[k], (x, y))

satirlar = []
def yaz(x, y, txt, f, renk, orta=True, feat=None):
    b = f.getbbox(txt, anchor='ls', features=feat); x0 = x - (b[0] + b[2]) / 2 if orta else x - b[0]
    d.text((x0, y - b[1]), txt, font=f, fill=renk, anchor='ls', features=feat); satirlar.append((y, y + b[3] - b[1], txt))

FN = font(MON, 35, 500)
for k, (x, y) in yerler.items():
    yaz(x + OW / 2, y + OH + 58, AD[k], FN, SANS_T)

# ozellik bandi: ince cizgi + "EVERY FRAME" + 4 hucre
RULE = tuple(int(v) for v in np.asarray(V2)[2145, 1500])
d.line((145, 1440, 2855, 1440), fill=RULE, width=2)
FE = font(MON, 37, 500)
etiket = 'E V E R Y   F R A M E'
yaz(1500, 1492, etiket, FE, GOLD_T)
FH = font(GAR, 51, 450); FA = font(MON, 30, 400)
huc = [('20 mm wood frame', '0.8 in face, satin finish'), ('Clear acrylic front', 'Protects your print'),
       ('No mat', 'Your print fills the frame'), ('Ready to hang', 'Hook fitted on the back')]
for i, (t, s) in enumerate(huc):
    cx = yerler[SIRA[i]][0] + OW / 2
    yaz(cx, 1590, t, FH, NAVY_T); yaz(cx, 1668, s, FA, SANS_T)
FNOT = font(GAR, 44, 450)
yaz(1500, 1845, 'Framed prints use 200 gsm enhanced matte fine art paper.', FNOT, NAVY_T)
out.save(CIK, quality=95, subsampling=0)

# QC
R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
ref = np.asarray(poster).astype(np.float32)[40:-40, 40:-40].mean(2)
n = {k: ncc(R[y + F + 40:y + F + PV_H - 40, x + F + 40:x + F + PV_W - 40].mean(2), ref) for k, (x, y) in yerler.items()}
alt = {k: y + OH for k, (x, y) in yerler.items()}
zemin = all(max(abs(int(a) - b) for a, b in zip(R[y, x], BG)) <= 2 for x, y in [(60, 1300), (2950, 1300), (1500, 1990), (60, 1990)])
tum = ' '.join(t for _, _, t in satirlar)
tire = bool(re.search(r'[‒-―−]', tum))
yasak = bool(re.search(r'hahnem|cotton|photo rag|OBA|bright white|instant download', tum, re.I))
print(f'cerceve {OW}x{OH} yuz {F}px | bosluk {GAP:.0f} | NCC', {k: round(v, 4) for k, v in n.items()}, '| alt', set(alt.values()),
      '| zemin', zemin, '| tire', tire, '| cerceveli yasak ifade', yasak)
print('kaynaklar:', bilgiler)
print('PASS' if R.shape[:2] == (2250, 3000) and min(n.values()) >= 0.99 and len(set(alt.values())) == 1 and zemin and not tire and not yasak else 'FAIL')
