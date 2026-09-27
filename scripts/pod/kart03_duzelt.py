#!/usr/bin/env python3
"""CL kart 03 (Two signs. One shared symbol.) duzeltmesi.
Taban: CANLI kart 03 (3000x2250; zemin, yazilar ve ust iki burc sembolu oldugu gibi kalir).
1) Paneldeki yanlis birlesik sembol (yarim kivrim) silinir; yerine GERCEK Cancer+Libra birlesik
   sembolu konur: onayli kapaktaki posterden birebir kirpilir (yeniden cizim yok), kapaktaki %1.7
   yatay sikistirma geri alinir (1560/1534), alfa altinlik rampasiyla ayrilir, renk zeminden ayristirilir.
2) Alt satir "PERSONALIZED ZODIAC ART PRINT" -> "PERSONALIZED ZODIAC COUPLE WALL ART"
   (kabul olcutu 4). Font canli satirdan olculdu: Montserrat 30 px, wght 470, iz 0, sol-ust (148, 2189).
QC: boyut, eski kivrim kalmadi, sembol NCC >= 0.97, alt satir onek NCC >= 0.90,
    panel/yazi disi degisim yok.
Kullanim: kart03_duzelt.py CANLI_03.jpg KAPAK.jpg Montserrat.ttf CIKIS.jpg
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

CANLI, KAPAK, FONT, CIK = sys.argv[1:5]
K = Image.open(CANLI).convert('RGB'); A0 = np.asarray(K).astype(np.float32)
C = np.asarray(Image.open(KAPAK).convert('RGB')).astype(np.float32)
BG, NAVY = np.array([237, 232, 226], np.float32), np.array([6, 17, 37], np.float32)
PANEL = (1321, 481, 2830, 2009)
ESKI = (1740, 1500, 2400, 1815)           # yanlis kivrim kutusu (olculdu 1762-2378 x 1522-1795)
HEDEF_W, HEDEF_UST, MERKEZ_X = 611, 1360, 2075

# --- 1) sembolu kapaktan ayir
X0, Y0, X1, Y1 = 1158, 533, 1843, 1182    # birlesik sembol kutusu (bilesenler 3, 11, 20)
PAD = 30
cr = C[Y0 - PAD:Y1 + PAD, X0 - PAD:X1 + PAD]
r, g, b = cr[..., 0], cr[..., 1], cr[..., 2]
gold = (r > g) & (g > b) & ((r - b) >= 40) & (r >= 80)
lab, n = ndimage.label(ndimage.binary_closing(gold, iterations=3))
sz = ndimage.sum(gold, lab, range(1, n + 1)); sl = ndimage.find_objects(lab)
sec = np.zeros_like(gold)
for i in range(n):                          # halka yayi haric: kutunun icinde kalan buyuk bilesenler
    s = sl[i]
    if sz[i] > 5000 and s[1].start >= PAD - 5 and s[1].stop <= cr.shape[1] - PAD + 5:
        sec |= lab == i + 1
alan = ndimage.binary_dilation(sec, iterations=4)
lum = cr.mean(2)
bgl = float(np.percentile(lum[~alan], 60)); fgl = float(np.percentile(lum[sec], 85))
alfa = np.clip((lum - bgl) / (fgl - bgl), 0, 1) * alan
bg_rgb = np.median(cr[~alan], axis=0)
renk = np.where(alfa[..., None] > 0.04, (cr - (1 - alfa[..., None]) * bg_rgb) / np.maximum(alfa[..., None], 0.04), cr)
renk = np.clip(renk, 0, 255)
rgba = Image.fromarray(np.dstack([renk, alfa * 255]).astype(np.uint8), 'RGBA')
rgba = rgba.resize((round(rgba.width * 1560 / 1534), rgba.height), Image.LANCZOS)   # sikistirmayi geri al
ic_w = (X1 - X0) * 1560 / 1534
olcek = HEDEF_W / ic_w
rgba = rgba.resize((round(rgba.width * olcek), round(rgba.height * olcek)), Image.LANCZOS)
pad_s = PAD * olcek
px, py = round(MERKEZ_X - rgba.width / 2), round(HEDEF_UST - pad_s)

out = K.copy()
out.paste(tuple(int(v) for v in NAVY), ESKI)
out.paste(rgba, (px, py), rgba)

# --- 2) alt satir
F = ImageFont.truetype(FONT, 30); F.set_variation_by_axes([470])
def satir(txt):
    m = Image.new('L', (1600, 80), 0); d = ImageDraw.Draw(m); x = 0
    for ch in txt:
        d.text((x, 10), ch, font=F, fill=255); x += F.getlength(ch)
    a = np.asarray(m); ys, xs = np.where(a > 76)
    return m.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
# canli metnin rengi: tam kapli piksellerin ortancasi
cz = A0[2180:2220, 140:700]; kap = np.abs(cz - BG).max(2) > 90
METIN = tuple(int(v) for v in np.median(cz[kap], axis=0))
out.paste(tuple(int(v) for v in BG), (140, 2175, 1500, 2225))
yeni = satir('PERSONALIZED ZODIAC COUPLE WALL ART')
out.paste(METIN, (148, 2189), yeni)
out.save(CIK, quality=95, subsampling=0)

# --- QC
R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
al = np.asarray(rgba)[..., 3] / 255.0
beklenen = NAVY * (1 - al[..., None]) + np.asarray(rgba)[..., :3] * al[..., None]
kutu = R[py:py + rgba.height, px:px + rgba.width]
n_sym = ncc(kutu.mean(2), beklenen.mean(2))
# eski kivrim: sembol maskesi disinda panelde altin kalmadi
sym_m = np.zeros(R.shape[:2], bool); sym_m[py:py + rgba.height, px:px + rgba.width] = al > 0.02
eb = np.zeros_like(sym_m); eb[ESKI[1]:ESKI[3], ESKI[0]:ESKI[2]] = True
kalan = int(((np.abs(R - NAVY).max(2) > 30) & eb & ~ndimage.binary_dilation(sym_m, iterations=3)).sum())
# alt satir onek
onek = satir('PERSONALIZED ZODIAC ')
w = onek.width
n_alt = ncc(R[2189:2189 + onek.height, 148:148 + w].mean(2), A0[2189:2189 + onek.height, 148:148 + w].mean(2))
# degisim yalniz izinli bolgelerde
izin = np.zeros_like(sym_m); izin |= eb; izin[py:py + rgba.height, px:px + rgba.width] = True; izin[2175:2225, 140:1500] = True
fark = np.abs(R - A0).max(2); dis = fark[~izin]
print(f'boyut {R.shape[1]}x{R.shape[0]} | sembol {rgba.width}x{rgba.height} @({px},{py}) NCC {n_sym:.4f} | '
      f'eski kivrim kalan px {kalan} | alt satir onek NCC {n_alt:.3f} | izin disi fark ort {dis.mean():.3f} maks {int(dis.max())}')
ok = R.shape[:2] == (2250, 3000) and n_sym >= 0.97 and kalan < 30 and n_alt >= 0.90 and dis.mean() < 0.5
print('PASS' if ok else 'FAIL')
