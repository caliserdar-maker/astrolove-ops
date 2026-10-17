#!/usr/bin/env python3
"""Eski 78 galeri rank 12 ('Fine art, down to the paper.') GENEL KAGIT surumu (Serdar 15 Eki: kagit ifadesi tedarikciden
bagimsiz; Hahnemuhle / Photo Rag / 308 gsm / 100% cotton / giclee kartta gecmez).
Taban: canli rank 12 karti (CL: data/pod/cl_galeri_final19/13_kagit.jpg; kart_duvar_genel.py ciktisi, zemin = duvar).
Yontem: degisen yazi bolgeleri duvar (DUVAR.png) pikseliyle silinir (bu bolgelerde kart - duvar farki <= 5, olculdu),
  yeni yazilar ayni yerlesimle basilir. Baslik, poster, golge, dipnot, alt bilgi pikselleri DEGISMEZ.
Yerlesim/font (olculdu, 15 Eki, eski satirlarin murekkep kutularina uydurma):
  ust etiket  Montserrat 400 37 px, x 139, taban 122, renk (81,74,53)
  alt baslik  Montserrat 400 49 px, x 150, taban 373, renk (21,28,37)
  madde basligi EB Garamond 400 105 px, x 1365, tabanlar 633 / 989 / 1345 / 1700, renk (16,25,40)
  madde satiri  Montserrat 500 44 px, x 1365, tabanlar 711 / 1067 / 1421 / 1777, renk (16,24,32)
  Renk duvara karsi kontrast >= 4.5 olana dek ayni tonda koyulastirilir (duvar_zemin.yazi_rengi).
Ust etiket marka kurali (1 Eki): 'ASTROLOVEART / A + B'.
QC (PASS/FAIL): 3000x2250; kontrast >= 4.5; yasak sozcuk yok; uzun/orta tire yok; silme kutulari DISINDA girdiyle
  fark p99.9 <= 12 ve max <= 45 (yalniz JPEG yeniden kodlama; canli Etsy kaynaginda max 17-21 olculdu, 17 Eki; yanlis yere
  basilan yazi >= 100 fark verir); OCR (tesseract) madde satirlari metinle ayni.
Kullanim: kart12_kagit_genel.py KART12.jpg DUVAR.png FONT_KLASORU CIKIS.jpg [BURC_A BURC_B]
"""
import json
import os
import re
import subprocess
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from duvar_zemin import duvar, duvar_lum, kontrast, lum, yazi_rengi

GIR, SAHNE, FD, CIK = sys.argv[1:5]
BA, BB = sys.argv[5:7] if len(sys.argv) > 6 else ('Cancer', 'Libra')
ALT_BASLIK = 'Printed on premium matte art paper.'
MADDE = [('Premium paper', 'A smooth matte art paper with rich detail.'),
         ('Matte finish', 'A refined surface without a glossy coating.'),
         ('Long-lasting inks', 'Deep, even color across the whole design.'),
         ('Made for you', 'Printed after you approve your preview.')]
YASAK = (r'hahnem', r'photo rag', r'\bgsm\b', r'cotton', r'\bframed\b', r'gicl', r'archival', r'acid', r'museum',
         r'prodigi', r'printful', r'\byears?\b', '—', '–')
SIL = [(130, 80, 1500, 135), (140, 325, 1090, 395), (1340, 540, 2900, 1800)]   # ust etiket, alt baslik, sag sutun
MON, GAR = 'Montserrat[wght].ttf', 'EBGaramond[wght].ttf'

K = Image.open(GIR).convert('RGB')
D = duvar(SAHNE)
Ka = np.asarray(K).astype(int); Da = np.asarray(D).astype(int)
on = [int(np.abs(Ka[y0:y1, x0:x1] - Da[y0:y1, x0:x1]).max(2).mean() > 3) for x0, y0, x1, y1 in SIL]
out = K.copy()
for b in SIL:
    out.paste(D.crop(b), b[:2])
d = ImageDraw.Draw(out)


def font(fy, s, w):
    f = ImageFont.truetype(os.path.join(FD, fy), s); f.set_variation_by_axes([w]); return f


YAZI = [(f'ASTROLOVEART / {BA.upper()} + {BB.upper()}', MON, 400, 37, 139, 122, (81, 74, 53)),
        (ALT_BASLIK, MON, 400, 49, 150, 373, (21, 28, 37))]
for (bas, sat), tb, ts in zip(MADDE, (633, 989, 1345, 1700), (711, 1067, 1421, 1777)):
    YAZI += [(bas, GAR, 400, 105, 1365, tb, (16, 25, 40)), (sat, MON, 500, 44, 1365, ts, (16, 24, 32))]
satirlar = []
for t, fy, w, s, x, y, renk in YAZI:
    f = font(fy, s, w); b = f.getbbox(t, anchor='ls')
    x = x - b[0]                                            # murekkep sol kenari olculen x'te
    kutu = (x + b[0], y + b[1], x + b[2], y + b[3])
    lw = duvar_lum(D, kutu); r = yazi_rengi(renk, lw)
    d.text((x, y), t, font=f, fill=r, anchor='ls')
    satirlar.append(dict(metin=t, kutu=kutu, renk=r, kontrast=round(kontrast(float(lum(np.array(r))), lw), 2)))
out.save(CIK, quality=95, subsampling=0)

# --- QC ---
O = np.asarray(Image.open(CIK).convert('RGB')).astype(int)
dis = np.ones(O.shape[:2], bool)
for x0, y0, x1, y1 in SIL:
    dis[y0:y1, x0:x1] = False
_df = np.abs(O - Ka).max(2)[dis]
dis_fark = int(_df.max()); dis_p999 = float(np.percentile(_df, 99.9))  # canli (Etsy JPEG) kaynakta yeniden kodlama gurultusu
kutu_disi = [s_['metin'] for s_ in satirlar if not any(
    s_['kutu'][0] >= b[0] and s_['kutu'][1] >= b[1] and s_['kutu'][2] <= b[2] and s_['kutu'][3] <= b[3] for b in SIL)]
metin = ' '.join(s_['metin'] for s_ in satirlar)
yasak = [y for y in YASAK if re.search(y, metin.lower())]
k_min = min(s_['kontrast'] for s_ in satirlar)
ocr_ok = True; ocr = {}
for s_ in satirlar[2:]:
    x0, y0, x1, y1 = s_['kutu']; c = Image.open(CIK).crop((x0 - 20, y0 - 20, x1 + 20, y1 + 20))
    c = c.resize((c.width * 2, c.height * 2), Image.LANCZOS); p = os.path.splitext(CIK)[0] + '_ocr.png'; c.save(p)
    r = re.sub(r'\s+', ' ', subprocess.run(['tesseract', p, '-', '--psm', '7'], capture_output=True, text=True).stdout).strip()
    ocr[s_['metin']] = r; ocr_ok &= r == s_['metin']
    os.remove(p)
ok = (O.shape[:2] == (2250, 3000) and k_min >= 4.5 and not yasak and dis_p999 <= 12 and dis_fark <= 45 and not kutu_disi and ocr_ok)
json.dump(dict(satirlar=satirlar, sil_bolge_duvar_disi=on, dis_fark=dis_fark, kutu_disi=kutu_disi, yasak=yasak,
               kontrast_min=k_min, ocr=ocr, PASS=ok), open(os.path.splitext(CIK)[0] + '.json', 'w'), ensure_ascii=False, indent=1)
for s_ in satirlar:
    print(f"{s_['metin'][:44]:44s} kontrast {s_['kontrast']} ocr {'ok' if ocr.get(s_['metin'], s_['metin']) == s_['metin'] else ocr.get(s_['metin'])}")
print(f"dis_fark {dis_fark} p99.9 {dis_p999:.1f} | kontrast_min {k_min} | yasak {yasak} | kutu_disi {kutu_disi} | sil bolgesinde duvar disi piksel {on}")
print('PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
