#!/usr/bin/env python3
"""Bir ciftin uretim ozeti (OZET.json): kontrol sonucu ve dosya piksel ozetleri.
Durum: HATA (isim/mesaj tasmasi, dala cakisma ya da dala < 1,1 mm), GOZ (burc < 1,95 mm, burc alt sinirda ya da dala 1,1-1,2 mm: gozle bakilacak), TAMAM.
Piksel ozeti (sha256, cozulmus RGB) yerel ve Actions ciktisinin birebir aynı oldugunu dogrulamak icindir.
Kullanim: python3 -I ozet.py <cift_klasoru> <CIFT>"""
import glob, hashlib, json, os, re, sys
import numpy as np
from PIL import Image

D, CIFT = sys.argv[1:3]
D = os.path.abspath(D)


def piksel(p):
    return hashlib.sha256(np.ascontiguousarray(np.asarray(Image.open(p).convert('RGB'))).tobytes()).hexdigest()[:16]


ozet = {'cift': CIFT, 'stil': {}, 'dosya': {}, 'sorun': [], 'goz': []}
for satir in open(f'{D}/olcum.txt', encoding='utf-8'):
    m = re.match(r'^([A-Za-z ]+?)( 15 oz)?: on: isim cap ([\d.]+) mm .*?burc cap ([\d.]+) mm', satir)
    if not m or m.group(1).startswith(('Kisa', 'Uzun')):
        continue
    ad, boy = m.group(1), ('15oz' if m.group(2) else '11oz')
    st = ozet['stil'].setdefault(ad, {})
    st[f'isim_{boy}'], st[f'burc_{boy}'] = float(m.group(3)), float(m.group(4))
    t = re.search(r'tasma: isim (\w+), burc (\w+), mesaj (\w+)', satir)
    if t and (t.group(1) == 'True' or t.group(3) == 'True'):
        ozet['sorun'].append(f'{ad} {boy} tasma isim {t.group(1)}, mesaj {t.group(3)}')
    if t and t.group(2) == 'True':
        # burc satiri 1,70 mm alt sinirda on gorunus 14 px payini tam saglayamadi; karar baskidaki gercek olcumle
        # (kontrol_burc: cakisma 0 ve dala >= 1,1 mm ise GOZ, aksi HATA; Serdar + ChatGPT 19.10)
        ozet['goz'].append(f'{ad} {boy} burc alt sinirda (on gorunus payi dar)')
    if float(m.group(4)) < 1.95 - 1e-6:
        ozet['goz'].append(f'{ad} {boy} burc {m.group(4)} mm')
ADLAR = {'orange': 'Orange Blossom', 'fig': 'Purple Fig', 'olive': 'Olive Breeze', 'pomegranate': 'Pomegranate Bloom',
         'almond': 'Almond Blossom', 'lemon': 'Lemon Grove', 'grape': 'Blue Grape', 'loquat': 'Golden Loquat'}
k = f'{D}/kontrol/burc_mesafe.txt'
if os.path.exists(k):
    for satir in open(k, encoding='utf-8'):
        p = satir.split()
        ad = ADLAR[p[0]]
        mes = float(satir.split('dala en kisa ')[1].split(' mm')[0])
        cak = int(satir.split('cakisma px ')[1].split(',')[0])
        ozet['stil'].setdefault(ad, {})['dala_mm'] = mes
        if cak or mes < 1.1:
            ozet['sorun'].append(f'{ad} dala {mes:.2f} mm, cakisma {cak} px')
        elif mes < 1.2:
            ozet['goz'].append(f'{ad} dala {mes:.2f} mm')
else:
    ozet['sorun'].append('kontrol yok')
for p in sorted(glob.glob(f'{D}/baski/B_*_baski_1[15]oz.png') + glob.glob(f'{D}/galeri/[01]*.jpg')):
    ozet['dosya'][os.path.relpath(p, D)] = piksel(p)
v = glob.glob(f'{D}/video/*.mp4')
ozet['video'] = os.path.basename(v[0]) if v else None
if not v:
    ozet['sorun'].append('video yok')
if len([x for x in ozet['dosya'] if x.startswith('galeri/')]) != 14:
    ozet['sorun'].append('galeri 14 degil')
if len([x for x in ozet['dosya'] if x.startswith('baski/')]) != 16:
    ozet['sorun'].append('baski 16 degil')
ozet['durum'] = 'HATA' if ozet['sorun'] else ('GOZ' if ozet['goz'] else 'TAMAM')
json.dump(ozet, open(f'{D}/OZET.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(CIFT, ozet['durum'], '; '.join(ozet['sorun'] + ozet['goz']))
