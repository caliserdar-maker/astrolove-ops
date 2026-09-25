#!/usr/bin/env python3
"""video-v1 kart 3 (Mo, 25 Eyl 2026): sign order alani yok.
Sol panel aynen (poster + alt yazi). Sag panel: ters sirali poster yerine Etsy kisisellestirme alanlarinin dolu hali.
Baslik/alt baslik/alt not referans kartin olculen font, boyut, izleme ve taban cizgisiyle (medya_v1 textlayer.fit/replace).
Alan etiketleri ve degerleri referans alt yazi fontundan (EMILY = CANCER) olculen parametrelerle.
Kullanim: kart3.py REF_KART.jpg CIKTI.jpg SOL_BURC SAG_BURC [--poster POSTER_EJ.png --hiza kart3_panel_hiza.json]
77 cift (Serdar, 25 Eyl): ust satir burc adlari; sol panel cift posterinden (POSTER_EJ, kisisel-v1), Cancer-Libra kisisel posterinden
olculen afin (ECC 0.992) + ton ile; sol alt yazi burc adlariyla. Ayni burc: Left/Right name, 'Each name goes under its own side.',
'Type each name in its own field.'"""
import json, sys, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'medya_v1/uretim'))
import textlayer as T
from metin_kurali import denetle

import argparse, cv2
ap_ = argparse.ArgumentParser(); ap_.add_argument('ref'); ap_.add_argument('out'); ap_.add_argument('s1'); ap_.add_argument('s2')
ap_.add_argument('--poster'); ap_.add_argument('--hiza'); a_ = ap_.parse_args()
ref, out, s1, s2 = a_.ref, a_.out, a_.s1.upper(), a_.s2.upper()
n1, n2, msg = 'EMILY', 'JAMES', 'It Began With a Kiss in the Rain'
t0 = time.time()
BG = np.array([237., 232., 226.])
ayni = s1.upper() == s2.upper()
if ayni:
    BASLIK, ALT = 'Each name goes under its own side.', 'Type each name in its own field.'
    ALANLAR = [('Left name', n1), ('Right name', n2), ('Your message', msg)]
else:
    BASLIK, ALT = 'Each name goes under its own sign.', 'Type each name in the field for its sign.'
    ALANLAR = [(f'Name under {s1.title()}', n1), (f'Name under {s2.title()}', n2), ('Your message', msg)]
NOT = 'Names print in capitals. Your message prints as you type it.'
metinler = [BASLIK, ALT, NOT] + [f'{a}: {b}' for a, b in ALANLAR]
hata = [h for m in metinler for h in denetle(m)]
assert not hata, f'metin_kurali FAIL: {hata}'

card = np.asarray(Image.open(ref).convert('RGB')).astype(np.float64)
log = {}
def rep(box, old, new, key, align='left'):
    global card
    card, p = T.replace(card, box, old, new, key, align=align, bg=BG)
    log.setdefault('metin', []).append({'old': old, 'new': new, **{k: p[k] for k in ('size', 'w', 'track', 'mse', 'box')}})
if (s1, s2) != ('CANCER', 'LIBRA'):
    rep((418, 80, 760, 135), 'CANCER + LIBRA', f'{s1} + {s2}', 'mont')
rep((130, 180, 1800, 330), 'Choose which sign goes on the left.', BASLIK, 'ebg')
rep((130, 325, 1800, 395), 'Each name stays with its zodiac sign when you switch the order.', ALT, 'mont')
rep((1000, 1975, 2000, 2060), 'Choose by zodiac sign, not by gender.', NOT, 'ebg', align='center')
# alt yazi fontu olcumu (sol alt yazi 'JAMES' kelimesi, cards.py card03 ile ayni yontem)
pc = T.fit(card, (822, 1738, 972, 1792), 'JAMES', 'mont', BG, (500,), sub=True, sizes_fixed=list(np.arange(38.0, 40.51, 0.25)))
log['alt_yazi_font'] = {k: pc[k] for k in ('size', 'w', 'track', 'mse', 'box', 'ink')}
# kaldirilanlar: 'Cancer left' / 'Libra left' etiketleri (sira secimi yok), sag panel, sag alt yazi
for x0, y0, x1, y1 in ((560, 490, 1010, 590), (2030, 490, 2400, 590), (1560, 815, 2870, 1430), (1840, 1735, 2590, 1795)):
    card[y0:y1, x0:x1] = BG
if a_.poster:   # sol panel: cift posteri (panel ici, 1 px kenar referanstan)
    h = json.load(open(a_.hiza)); Mp = np.array(h['M_panel'], np.float32); ton = [np.array(t) for t in h['ton']]
    P = np.asarray(Image.open(a_.poster).convert('RGB')).astype(np.float32)
    Pw = cv2.warpAffine(P, Mp, (1281, 585), flags=cv2.INTER_AREA)
    Pt = np.clip(np.stack([np.polyval(ton[c], Pw[..., c]) for c in range(3)], 2), 0, 255)
    card[830:1413, 145:1424] = Pt[1:584, 1:1280]
    log['sol_panel'] = {'poster': Path(a_.poster).name, 'M_panel': h['M_panel']}
if ayni or (s1, s2) != ('CANCER', 'LIBRA'):   # sol alt yazi: cards.caption03 kurali
    card[1735:1795, 400:1180] = BG
    base_c = pc['oy'] + pc['base0']
    cap = f'LEFT NAME = {n1}   RIGHT NAME = {n2}' if ayni else f'{n1} = {s1}   {n2} = {s2}'
    card = T.draw_with(card, pc, cap, cx=786, base=base_c); log['sol_alt_yazi'] = cap
# sag panel: dolu Etsy alanlari, panel kutusu 1575..2855 x 829..1413 (olculdu)
PX0, PY0, PX1, PY1 = 1575, 829, 2856, 1414
lab_p = dict(pc)                                   # etiket: alt yazi fontu (Montserrat 500), koyu
val_p = dict(pc); val_p['size'] = pc['size'] * 1.15; val_p['w'] = 500
KUTU_H, ETIKET_KUTU, ARA = 112, 22, 44
etiket_cap = pc['size'] * 0.70                     # Montserrat cap yuksekligi ~0.70 em
blok = etiket_cap + ETIKET_KUTU + KUTU_H
toplam = 3 * blok + 2 * ARA
y = PY0 + (PY1 - PY0 - toplam) / 2
SS = 4
kutular = []
for etiket, deger in ALANLAR:
    base_l = y + etiket_cap
    card = T.draw_with(card, lab_p, etiket, x=PX0 + 10 - 2, base=base_l)
    ky0 = base_l + ETIKET_KUTU; ky1 = ky0 + KUTU_H
    kutular.append([PX0, round(ky0), PX1, round(ky1)])
    y = ky1 + ARA
# kutular: 4x ornekleme ile yumusak kenar, beyaz dolgu, ince kenar
h, w = PY1 - PY0 + 40, PX1 - PX0 + 40
L = Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
for x0, y0, x1, y1 in kutular:
    d.rounded_rectangle([(x0 - PX0 + 20) * SS, (y0 - PY0 + 20) * SS, (x1 - PX0 + 20) * SS - 1, (y1 - PY0 + 20) * SS - 1],
                        radius=10 * SS, fill=(252, 251, 249, 255), outline=(190, 181, 170, 255), width=3 * SS)
L = np.asarray(L.resize((w, h), Image.LANCZOS)).astype(np.float64)
reg = card[PY0 - 20:PY0 - 20 + h, PX0 - 20:PX0 - 20 + w]
a = L[..., 3:4] / 255.0
card[PY0 - 20:PY0 - 20 + h, PX0 - 20:PX0 - 20 + w] = reg * (1 - a) + L[..., :3] * a
val_cap = val_p['size'] * 0.70
for (etiket, deger), (x0, y0, x1, y1) in zip(ALANLAR, kutular):
    card = T.draw_with(card, val_p, deger, x=x0 + 36 + 10 - 2, base=(y0 + y1) / 2 + val_cap / 2)
log.update({'alanlar': ALANLAR, 'kutular': kutular, 'baslik': BASLIK, 'alt_baslik': ALT, 'alt_not': NOT, 'ayni_burc': ayni,
            'metin_kurali': 'PASS', 'sure_sn': round(time.time() - t0, 1)})
Image.fromarray(np.clip(np.rint(card), 0, 255).astype(np.uint8)).save(out, quality=95, subsampling=0)
json.dump(log, open(out.rsplit('.', 1)[0] + '_log.json', 'w'), indent=1, default=float)
print(f'bitti {time.time()-t0:.1f}s', json.dumps({k: log[k] for k in ('baslik', 'kutular')}), [round(m['mse'], 1) for m in log['metin']])
