#!/usr/bin/env python3
"""Kupa kapagina iki satir baslik (Serdar 30 Eki): 1. satir 'BURC1 & BURC2' tek satir (Cinzel 650),
2. satir alt yazi (Cinzel, harf araligi acik). Ikisi de RENK; GOLGE=1 ise koyu yumusak golge (GOLGE_GUC).
Boy 78 ciftte sabit (BOY). 4:5 orta banda (BANT) sigmayan uzun ciftlerde YALNIZ burc satiri sigacak kadar kuculur;
alt yazi 78 kapakta ayni boy ve ayni yerde (Serdar 30 Eki). Burc satirinin tabani da 78'de sabit.
Satir yerleri BOY ve 12 burcun en derin harf inisine (Q kuyrugu) gore hesaplanir.
Ortam: ALT_ORAN (alt yazi boyu / baslik boyu), ALT_AGIRLIK, IZ_ORAN (harf araligi / alt yazi boyu), GOLGE_GUC.
Cikti once gecici dosyaya yazilir, sonra yerine konur (yarim dosya kalmaz).
Sade kupa: burc2 yerine '-' verilirse baslik yalniz BURC1.
Kullanim: python3 -I baslik2.py <girdi> <cikti> <burc1> <burc2> <xc> <blok_alt_y> <boy_px> <r,g,b> <alt_yazi> [golge 0/1]"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

G, C, B1, B2 = sys.argv[1:5]
XC, ALT, BOY = float(sys.argv[5]), float(sys.argv[6]), int(sys.argv[7])
RENK = tuple(int(v) for v in sys.argv[8].split(','))
ALT_YAZI = sys.argv[9]
GOLGE = len(sys.argv) > 10 and sys.argv[10] == '1'
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'varlik', 'font', 'Cinzel[wght].ttf')
BANT = (680, 2320)                      # baslik: 4:5 kirpma x 600-2400, iki yanda 80 px pay (golge dahil ~50 px bosluk)
BANT_ALT = (640, 2360)                  # alt yazi (her kapakta ayni, onayli genislik): iki yanda 40 px pay
BURCLAR = ['ARIES', 'TAURUS', 'GEMINI', 'CANCER', 'LEO', 'VIRGO', 'LIBRA', 'SCORPIO',
           'SAGITTARIUS', 'CAPRICORN', 'AQUARIUS', 'PISCES']
TEK = B2 == '-'                                  # sade kupa: tek burc basligi (B2 = '-')
assert B1.upper() in BURCLAR and (TEK or B2.upper() in BURCLAR), 'bilinmeyen burc'
assert len(RENK) == 3 and all(0 <= v <= 255 for v in RENK), 'renk r,g,b olmali'
assert not any(c in ALT_YAZI for c in '.+=—–'), 'alt yazida yasak karakter'
ALT_ORAN = float(os.environ.get('ALT_ORAN', 0.40))
ALT_AGIRLIK = int(os.environ.get('ALT_AGIRLIK', 500))
IZ_ORAN = float(os.environ.get('IZ_ORAN', 0.18))
GUC = float(os.environ.get('GOLGE_GUC', 1.0))
ARA_ORAN = 0.30                         # satir arasi (baslik boyuna gore)


def font(px, agirlik):
    f = ImageFont.truetype(FONT, px)
    f.set_variation_by_axes([agirlik])
    return f


def genislik(f, t):
    b = f.getbbox(t)
    return b[2] - b[0]


baslik = B1.upper() if TEK else f'{B1.upper()} & {B2.upper()}'
yari = min(XC - BANT[0], BANT[1] - XC)
boy = BOY
while genislik(font(boy, 650), baslik) > 2 * yari:
    boy -= 1
fb = font(boy, 650)
fs = font(round(BOY * ALT_ORAN), ALT_AGIRLIK)                  # alt yazi: 78 kapakta sabit
iz = round(BOY * ALT_ORAN * IZ_ORAN)
fB = font(BOY, 650)
alt_b = max(fB.getbbox(b, anchor='ls')[3] for b in BURCLAR)     # en derin inis (Q kuyrugu), standart boyda
ALT_REF = os.environ.get('ALT_REF', ALT_YAZI)   # dikey yerlesim olcu metni (stil gorselleri: kapak alt yazisi; Q kuyrugu baslik konumunu oynatmasin)
s_ust, s_alt = fs.getbbox(ALT_REF, anchor='ls')[1], fs.getbbox(ALT_REF, anchor='ls')[3]
y2 = ALT - s_alt                                                # alt yazi tabani
y1 = y2 + s_ust - round(BOY * ARA_ORAN) - alt_b                 # baslik tabani (78'de sabit)
s_gen = sum(fs.getlength(ch) for ch in ALT_YAZI) + iz * (len(ALT_YAZI) - 1)
assert s_gen <= 2 * min(XC - BANT_ALT[0], BANT_ALT[1] - XC), 'alt yazi bandi asiyor'

im = Image.open(G).convert('RGB')
kat = Image.new('L', im.size, 0)
d = ImageDraw.Draw(kat)
d.text((XC, y1), baslik, font=fb, fill=255, anchor='ms')
x = XC - s_gen / 2
for ch in ALT_YAZI:
    d.text((x, y2), ch, font=fs, fill=255, anchor='ls')
    x += fs.getlength(ch) + iz
if GOLGE:   # genis yumusak hale + yakin kayik golge
    a = np.zeros(im.size[::-1], np.float32)
    for blur, oran, dx, dy in ((22, 0.35, 0, 2), (7, 0.55, 5, 6)):
        g = np.asarray(kat.filter(ImageFilter.GaussianBlur(blur)), np.float32) / 255 * oran * GUC
        a = 1 - (1 - a) * (1 - np.clip(np.roll(g, (dy, dx), (0, 1)), 0, 1))
    im = Image.composite(Image.new('RGB', im.size, (35, 22, 10)), im,
                         Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)))
im = Image.composite(Image.new('RGB', im.size, RENK), im, kat)
gecici = C + '.gecici.jpg'
im.save(gecici, quality=95)
os.replace(gecici, C)
print(f'"{baslik}" boy {boy} (standart {BOY}), genislik {genislik(fb, baslik)}; alt yazi boy {round(BOY * ALT_ORAN)}, '
      f'{s_gen:.0f}px; baslik tabani {y1:.0f}, alt yazi tabani {y2:.0f}')
