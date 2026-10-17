#!/usr/bin/env python3
"""Eski 78 kart 02 (Choose your format) IKI SUTUN surumu (Serdar 15 Eki: Framed secenegi kalkiyor; kagit ifadesi genel).
Taban: kart02_duvar_kur.py (canli 02'yi ureten hat; ayni krem kaynak, ayni duvar, ayni golge modeli, ayni yazi olculeri).
Degisen:
  - Framed sutunu (cerceve nesnesi + 'Framed' basligi + 2 aciklama satiri) kaldirilir.
  - Dijital yigin ve baski nesneleri iki sutuna kaydirilir: sutun merkezleri x 986 ve 2012 (16 px MCU hizasi).
    Nesne pikselleri krem kaynaktan aynen kopyalanir (kaydirma tam sayi px), golge nesneyle birlikte kayar.
  - Alt baslik: 'One design, two ways to enjoy it.'
  - Print aciklamasi: tedarikciden bagimsiz genel ifade (BASKI_SATIR).
  - Ust etiket: marka kurali (1 Eki, CLAUDE.md MARKA ADI) -> 'ASTROLOVEART / A + B'.
  - Digital File aciklamasi: tek kaynak kart02_dijital_metin.YENI (canli metin), yeni sutun merkezinde.
QC (PASS/FAIL): 3000x2250; tum yazi kontrasti >= 4.5; yasak sozcuk yok (Hahnem, Photo Rag, gsm, cotton, Framed, giclee);
  uzun/orta tire yok; nesne pikselleri kaynakla ayni (kaydirilmis krem kaynak vs cikti, nesne ici max fark <= 10 (17 Eki: 78 ciftte 5-7 olculdu, JPEG);
  canli hat kart02_duvar_kur ayni olcumde 5).
Kullanim: kart02_iki_sutun.py KREM_02.jpg DUVAR.png FONT_KLASORU CIKIS.jpg [BURC_A BURC_B]
"""
import json
import re
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from duvar_zemin import KREM, duvar, duvar_lum, kontrast, lum, yazi_rengi
import kart02_dijital_metin as KD

ESKI, SAHNE, FD, CIK = sys.argv[1:5]
BA, BB = sys.argv[5:7] if len(sys.argv) > 6 else ('Cancer', 'Libra')
ALT_BASLIK = 'One design, two ways to enjoy it.'
BASKI_SATIR = ['Premium matte art paper, long-lasting inks.', 'Unframed, ready for your frame.']
YASAK = (r'hahnem', r'photo rag', r'\bgsm\b', r'cotton', r'\bframed\b', r'gicl', r'prodigi', r'printful', '\u2014', '\u2013')  # 'Unframed' serbest (C aciklama satiri)
K = Image.open(ESKI).convert('RGB')
D = duvar(SAHNE)

# --- kart02_duvar_kur.py geometrisi (ayni sabitler) ---
PW, PH, ALT, BANT = 586, 760, 1294, (430, 1408)
E_ON, e_kutu = (244, 520, 809, 1295), (172, 496, 809, 1295)
sx, sy = PW / (E_ON[2] - E_ON[0]), PH / (E_ON[3] - E_ON[1])
ew, eh = e_kutu[2] - e_kutu[0], e_kutu[3] - e_kutu[1]
maske_eski = Image.new('L', K.size, 0)
for k in range(5):
    x0, y0 = E_ON[0] - 18 * k, E_ON[1] - 6 * k
    maske_eski.paste(255, (x0, y0, x0 + 565, y0 + 775))
yw, yh = round(ew * sx), round(eh * sy)
yigin_m = maske_eski.crop(e_kutu).resize((yw, yh), Image.LANCZOS)
on_x, on_y = round((E_ON[0] - e_kutu[0]) * sx), yh - PH
yigin_m.paste(255, (on_x, on_y, on_x + PW, on_y + PH))
# (maske, eski konum, yeni konum): kaydirma 16'nin kati (kaynak JPEG 4:2:0 MCU 16x16 hizasi korunur):
# dijital +496 (merkez 490 -> 986), baski +512 (1500 -> 2012); sutun ortasi 1499 (kart merkezi 1500)
MERKEZ = {'dijital': (490, 986), 'baski': (1500, 2012)}
yer = {'dijital': (yigin_m, (round(490 - yw / 2), ALT - yh), (round(490 - yw / 2) + 496, ALT - yh)),
       'baski': (Image.new('L', (PW, PH), 255), (1500 - PW // 2, ALT - PH), (1500 - PW // 2 + 512, ALT - PH))}

A0 = np.asarray(K).astype(np.float32)
A = np.empty_like(A0); A[:] = np.array(KREM, np.float32)
M = Image.new('L', K.size, 0); sil = Image.new('L', K.size, 0)
for m_, (ex, ey), (nx, ny) in yer.values():
    w_, h_ = m_.size
    A[ny:ny + h_, nx:nx + w_] = A0[ey:ey + h_, ex:ex + w_]
    M.paste(m_, (nx, ny), m_); sil.paste(m_, (nx + 15, ny + 18), m_)
m = np.asarray(M).astype(np.float32)[..., None] / 255
alfa = np.asarray(sil.filter(ImageFilter.GaussianBlur(26))).astype(np.float32) / 255
golge = np.ones(alfa.shape, np.float32); golge[BANT[0]:BANT[1]] = 1 - (59 / 232) * alfa[BANT[0]:BANT[1]]
zemin_eski = np.array(KREM, np.float32)[None, None, :] * golge[..., None]
zemin_yeni = np.asarray(D).astype(np.float32) * golge[..., None]
o = np.where(m > 0, A + (1 - m) * (zemin_yeni - zemin_eski), zemin_yeni)
out = Image.fromarray(np.clip(np.rint(o), 0, 255).astype(np.uint8))
d = ImageDraw.Draw(out)
d.rectangle((140, 2100, 2860, 2101), fill=(205, 191, 169))


def font(fy, s, w):
    f = ImageFont.truetype(os.path.join(FD, fy), s)
    if w:
        f.set_variation_by_axes([w])
    return f


# eski olculen satir merkezleri (kart02_duvar_kur.YAZI) + sutun kaydirmasi
def eski_merkez(t, fy, s, w, x):
    b = font(fy, s, w).getbbox(t, anchor='ls'); return x + (b[0] + b[2]) / 2


dD = MERKEZ['dijital'][1] - MERKEZ['dijital'][0]; dP = MERKEZ['baski'][1] - MERKEZ['baski'][0]
LAT, GAR = 'Lato-Regular.ttf', 'EBGaramond[wght].ttf'
c_dbas = eski_merkez('Digital File', GAR, 64, 400, 355) + dD
c_pbas = eski_merkez('Print', GAR, 64, 400, 1437) + dP
c_p1 = eski_merkez('Hahnemühle Photo Rag fine art paper.', LAT, 38, None, 1182) + dP
c_p2 = eski_merkez('Unframed, ready for your frame.', LAT, 38, None, 1233) + dP
YAZI = [  # (metin, font, wght, punto, x (None = merkez c), taban y, onayli renk, merkez)
    (f'ASTROLOVEART / {BA.upper()} + {BB.upper()}', LAT, None, 40, 140, 130, (174, 143, 83), None),
    ('Choose your format.', GAR, 430, 102, 140, 246, (22, 38, 65), None),
    (ALT_BASLIK, LAT, None, 52, 145, 367, (37, 45, 57), None),
    ('Digital File', GAR, 400, 64, None, 1456, (22, 38, 65), c_dbas),
    ('Print', GAR, 400, 64, None, 1456, (22, 38, 65), c_pbas),
    (BASKI_SATIR[0], LAT, None, 38, None, 1558, (37, 44, 56), c_p1),
    (BASKI_SATIR[1], LAT, None, 38, None, 1603, (37, 45, 57), c_p2),
    (f'A personal gift for {BA} and {BB} couples.', GAR, 430, 43, None, 1865, (23, 39, 66), 'hediye'),
    ('PERSONALIZED ZODIAC COUPLE WALL ART', LAT, None, 30, 140, 2172, (174, 143, 83), None),
]
satirlar = []
for t, fy, w, s, x, y, renk, c in YAZI:
    f = font(fy, s, w)
    b = f.getbbox(t, anchor='ls')
    if c == 'hediye':   # kart02_duvar_kur ile ayni: onayli CL satirinin (x 1128) murekkep merkezi
        e = f.getbbox('A personal gift for Cancer and Libra couples.', anchor='ls')
        x = round(1128 + (e[0] + e[2]) / 2 - (b[0] + b[2]) / 2)
    elif c is not None:
        x = round(c - (b[0] + b[2]) / 2)
    kutu = (x + b[0], y + b[1], x + b[2], y + b[3])
    lw = duvar_lum(D, kutu); r = yazi_rengi(renk, lw)
    d.text((x, y), t, font=f, fill=r, anchor='ls')
    satirlar.append(dict(metin=t, kutu=kutu, renk=r, kontrast=round(kontrast(float(lum(np.array(r))), lw), 2)))
KD.MERKEZ_X = KD.MERKEZ_X + dD      # Digital File aciklamasi yeni sutun merkezinde (tek kaynak metin)
for t, kutu, r in KD.ciz(d, D, FD, KD.YENI, duvar_lum, yazi_rengi, ImageFont, os):
    satirlar.append(dict(metin=t, kutu=kutu, renk=r, kontrast=round(kontrast(float(lum(np.array(r))), duvar_lum(D, kutu)), 2)))
out.save(CIK, quality=95, subsampling=0)

# --- QC ---
O = np.asarray(Image.open(CIK).convert('RGB')).astype(int)
nesne_fark = 0
for m_, (ex, ey), (nx, ny) in yer.values():
    mm = np.asarray(m_) == 255
    ic = ndi.binary_erosion(mm, iterations=8)                          # tam ic (maske kenarindan 8 px iceride)
    w_, h_ = m_.size
    nesne_fark = max(nesne_fark, int(np.abs(O[ny:ny + h_, nx:nx + w_][ic] - A0[ey:ey + h_, ex:ex + w_][ic].astype(int)).max()))
metin = ' '.join(s_['metin'] for s_ in satirlar)
yasak = [y for y in YASAK if re.search(y, metin.lower())]
k_min = min(s_['kontrast'] for s_ in satirlar)
ok = O.shape[:2] == (2250, 3000) and k_min >= 4.5 and not yasak and nesne_fark <= 10 and not any(
    ch in metin for ch in '—–')
json.dump(dict(satirlar=satirlar, nesne_fark=nesne_fark, yasak=yasak, kontrast_min=k_min, PASS=ok),
          open(os.path.splitext(CIK)[0] + '.json', 'w'), ensure_ascii=False, indent=1)
for s_ in satirlar:
    print(f"{s_['metin'][:44]:44s} kontrast {s_['kontrast']}")
print(f"nesne_fark {nesne_fark} | kontrast_min {k_min} | yasak {yasak}")
print('PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
