#!/usr/bin/env python3
"""CL kart 15 (Deep Black, framed in black.) 3000x2250 kurulum.
Taban: ChatGPT yazisiz oturma odasi sahnesi (1448x1086), 1.9:1 kirpim (y 100-862). Kitaplardaki okunaksiz sahte
yazilar scripts/pod/sahne_yazi_sil.py ile silinir (temiz.png).
Sahnedeki cerceve yerine (on cephe; dis (598,131)-(849,447)): Prodigi Classic BLACK chevron fotografinin gercek
profil seridi, 45 derece gonye (kart 07 yontemi; siyah icin on cephe bos fotograf yok); yuz 24x36 olcegi.
Poster: canli kart 04'teki GERCEK Deep Black (EMILY/JAMES).
Kullanim: kart15_kur.py SAHNE.png CANLI_04.jpg BK_CHEVRON.jpg CANLI_03.jpg KART03_V2.jpg GARAMOND.ttf MONTSERRAT.ttf CIKIS.jpg [oda|calisma]
v2 (calisma): ChatGPT'nin gec gelen calisma kosesi sahnesi (yazisiz, siyah cerceve, dis (637,96)-(1098,660)).
"""
import re
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

G15, C04, BKCH, C03, K03V2, GAR, MON, CIK = sys.argv[1:9]
# sahne secimi: 'oda' (v1, oturma odasi 1448x1086) | 'calisma' (v2, calisma kosesi 1729x910)
SAHNE = sys.argv[9] if len(sys.argv) > 9 else 'oda'
SAHNE_KIRP, CER = {'oda': ((0, 100, 1448, 862), (598, 131, 850, 448)),
                   'calisma': ((0, 0, 1729, 910), (637, 96, 1098, 660))}[SAHNE]
BG = (237, 232, 226); NAVY_T = (25, 34, 49); SANS_T = (23, 25, 30)

def _maske(im):
    a = np.asarray(im).astype(int); m = (255 - a.min(2)) > 10
    m = ndimage.binary_opening(m, iterations=2); lab, k = ndimage.label(m)
    return lab == (np.argmax(ndimage.sum(m, lab, range(1, k + 1))) + 1)

def _dondur(src, aci):
    return src.rotate(aci, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))

def _ilk(v):
    kop = np.where(np.diff(v) > 1)[0]; return v[:kop[0] + 1] if len(kop) else v

def serit(yol):
    src = Image.open(yol).convert('RGB'); m0 = _maske(_dondur(src, -45)); ys, xs = np.where(m0); y0 = ys.min()
    Yy = np.arange(y0 + 400, y0 + 1150, 10); Xx = np.array([np.where(m0[y, :])[0].min() for y in Yy])
    aci = float(np.degrees(np.arctan(np.polyfit(Yy, Xx, 1)[0])))
    im = _dondur(src, -45 - aci); m = _maske(im); ys, xs = np.where(m); y0 = ys.min(); dis, ic = [], []
    for y in range(y0 + 400, y0 + 1150, 10):
        v = _ilk(np.where(m[y, :])[0]); dis.append(v.min()); ic.append(v.max())
    return im.crop((max(dis) + 1, y0 + 400, min(ic), y0 + 1150))

def cerceve(s, poster, F):
    PW, PH = poster.size; OW, OH = PW + 2 * F, PH + 2 * F
    V = s.resize((F, OH), Image.LANCZOS); Hs = s.resize((F, OW), Image.LANCZOS).transpose(Image.ROTATE_270)
    fr = Image.new('RGB', (OW, OH)); pa = np.asarray(poster).astype(np.float32)
    yy = np.arange(PH)[:, None]; xx = np.arange(PW)[None, :]
    g = 1 - 0.28 * np.exp(-yy / 12.0) - 0.22 * np.exp(-xx / 12.0) - 0.08 * np.exp(-(PH - 1 - yy) / 6.0) - 0.08 * np.exp(-(PW - 1 - xx) / 6.0)
    fr.paste(Image.fromarray(np.clip(pa * g[..., None], 0, 255).astype(np.uint8)), (F, F))
    fr.paste(Hs, (0, 0)); fr.paste(Hs.transpose(Image.FLIP_TOP_BOTTOM), (0, OH - F))
    yv = np.arange(OH)[:, None]; xv = np.arange(F)[None, :]
    mk = Image.fromarray(((yv >= xv) & (yv <= OH - 1 - xv)).astype(np.uint8) * 255)
    fr.paste(V, (0, 0), mk); fr.paste(V.transpose(Image.FLIP_LEFT_RIGHT), (OW - F, 0), mk.transpose(Image.FLIP_LEFT_RIGHT))
    a = np.asarray(fr).astype(np.float32)
    for i in range(F):
        for (y, x) in ((i, i), (i, OW - 1 - i), (OH - 1 - i, i), (OH - 1 - i, OW - 1 - i)):
            a[y, x] *= 0.86
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def cerceve_blank(yol, poster, F):
    """Prodigi'nin on cepheden cekilmis Classic Antique Gold bos cerceve fotografi (059, 2000x2000) 9 parcaya
    bolunur: koseler olduklari gibi, kenarlar boyuna uzatilir, hepsi hedef yuze (F) olceklenir. Yeniden cizim yok.
    Olculen: dis (455,282)-(1543,1672), yuz 46-49 px; kirpim 46 px (ic beyaz alan girmesin)."""
    src = Image.open(yol).convert('RGB'); X0, Y0, X1, Y1, f = 455, 282, 1544, 1673, 46
    PW, PH = poster.size; OW, OH = PW + 2 * F, PH + 2 * F
    fr = Image.new('RGB', (OW, OH))
    pa = np.asarray(poster).astype(np.float32); yy = np.arange(PH)[:, None]; xx = np.arange(PW)[None, :]
    g = 1 - 0.22 * np.exp(-yy / 10.0) - 0.16 * np.exp(-xx / 10.0) - 0.06 * np.exp(-(PH - 1 - yy) / 5.0) - 0.06 * np.exp(-(PW - 1 - xx) / 5.0)
    fr.paste(Image.fromarray(np.clip(pa * g[..., None], 0, 255).astype(np.uint8)), (F, F))
    r = lambda b, w, h: src.crop(b).resize((w, h), Image.LANCZOS)
    fr.paste(r((X0 + f, Y0, X1 - f, Y0 + f), OW - 2 * F, F), (F, 0))
    fr.paste(r((X0 + f, Y1 - f, X1 - f, Y1), OW - 2 * F, F), (F, OH - F))
    fr.paste(r((X0, Y0 + f, X0 + f, Y1 - f), F, OH - 2 * F), (0, F))
    fr.paste(r((X1 - f, Y0 + f, X1, Y1 - f), F, OH - 2 * F), (OW - F, F))
    fr.paste(r((X0, Y0, X0 + f, Y0 + f), F, F), (0, 0)); fr.paste(r((X1 - f, Y0, X1, Y0 + f), F, F), (OW - F, 0))
    fr.paste(r((X0, Y1 - f, X0 + f, Y1), F, F), (0, OH - F)); fr.paste(r((X1 - f, Y1 - f, X1, Y1), F, F), (OW - F, OH - F))
    return fr


def font(yol, boy, w):
    f = ImageFont.truetype(yol, boy); f.set_variation_by_axes([w]); return f


out = Image.new('RGB', (3000, 2250), BG); d = ImageDraw.Draw(out)
C3 = Image.open(C03).convert('RGB'); V2 = Image.open(K03V2).convert('RGB')
out.paste(C3.crop((0, 70, 1500, 140)), (0, 70)); out.paste(V2.crop((0, 2130, 3000, 2250)), (0, 2130))
FT = font(GAR, 120, 450); FS = font(MON, 49, 500)
b = FT.getbbox('Two signs. One shared symbol.', anchor='ls'); d.text((143 - b[0], 201 - b[1]), 'Deep Black, framed in black.', font=FT, fill=NAVY_T, anchor='ls')
b = FS.getbbox('Cancer and Libra, united in an original AstroLove design.', anchor='ls')
d.text((147 - b[0], 336 - b[1]), 'A modern look for a living room, hallway or office.', font=FS, fill=SANS_T, anchor='ls')

G = Image.open(G15).convert('RGB')
SC = SAHNE_KIRP; SX, SY = 145, 420; s = 2710 / (SC[2] - SC[0])
sahne = G.crop(SC).resize((2710, round((SC[3] - SC[1]) * s)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
DX0, DY0, DX1, DY1 = [round(v) for v in ((CER[0] - SC[0]) * s, (CER[1] - SC[1]) * s, (CER[2] - SC[0]) * s, (CER[3] - SC[1]) * s)]
# Serdar 27 Eyl: cerceve ince. Yuz = Prodigi 20 mm, 24x36 olceginde (gorunen 599.6 mm); dis olcu sahnedeki gibi kalir.
R_YUZ = 20 / 599.6
F = round((DX1 - DX0) * R_YUZ / (1 + 2 * R_YUZ))
CI = Image.open(C04).convert('RGB').crop((1240, 500, 1760, 1150))          # canli kart 04 Deep Black
kx, ky = round(CI.width * 5 / 406.4), round(CI.height * 5 / 508)
poster = CI.crop((kx, ky, CI.width - kx, CI.height - ky)).resize((DX1 - DX0 - 2 * F, DY1 - DY0 - 2 * F), Image.LANCZOS)
fr = cerceve(serit(BKCH), poster, F)
fa = np.asarray(fr).astype(np.float32); x = np.linspace(0, 1, fr.width)[None, :, None]
fa = fa * (1.02 - 0.05 * x)
sahne.paste(Image.fromarray(np.clip(fa, 0, 255).astype(np.uint8)), (DX0, DY0))
mask = Image.new('L', sahne.size, 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, sahne.width - 1, sahne.height - 1), radius=30, fill=255)
out.paste(sahne, (SX, SY), mask)

satir = []
def orta(y, t, f, renk):
    b = f.getbbox(t, anchor='ls'); d.text((1500 - (b[0] + b[2]) / 2, y - b[1]), t, font=f, fill=renk, anchor='ls'); satir.append(t)
def fit(yol, w, t, hedef):
    return font(yol, min(range(24, 90), key=lambda z: abs((lambda bb: bb[2] - bb[0])(font(yol, z, w).getbbox(t, anchor='ls')) - hedef)), w)
t1 = 'Shown in Deep Black with a Black frame.'; t2 = 'Every color comes in all four frame finishes.'
orta(SY + sahne.height + 45, t1, fit(GAR, 450, t1, 1050), NAVY_T)
orta(SY + sahne.height + 132, t2, fit(MON, 400, t2, 740), SANS_T)
out.save(CIK, quality=95, subsampling=0)

R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
px0, py0 = SX + DX0 + F + 30, SY + DY0 + F + 30
n = ncc(R[py0:py0 + poster.height - 60, px0:px0 + poster.width - 60].mean(2), np.asarray(poster).astype(np.float32)[30:-30, 30:-30].mean(2))
zemin = all(max(abs(int(a) - b) for a, b in zip(R[y, x], BG)) <= 2 for x, y in [(60, 1000), (2950, 1000), (60, 2080)])
tire = bool(re.search(r'[\u2012-\u2015\u2212]', ' '.join(satir)))
alt = SY + sahne.height + 132 + 40
print(f'sahne {sahne.size} olcek {s:.3f} | cerceve dis {DX1 - DX0}x{DY1 - DY0} yuz {F} | poster {poster.size} NCC {n:.4f} | zemin {zemin} | tire {tire} | yazi alt ~{alt} (<2130)')
print('PASS' if R.shape[:2] == (2250, 3000) and n >= 0.99 and zemin and not tire and alt < 2130 else 'FAIL')
