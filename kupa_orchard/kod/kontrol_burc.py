#!/usr/bin/env python3
"""Bagimsiz kontrol: uretilmis baski dosyalarinda burc satiri ile susleme arasi en kisa fiziksel mesafe (mm) ve isim satiri ayrimi.
Her stil icin ayni girdilerle BURC_YOK baskisi uretilir, fark = burc yazisi.
Kullanim: python3 -I kontrol_burc.py <cift_klasoru> <burc1> <burc2> <sembol_klasoru>"""
import os, subprocess, sys, time
import numpy as np
from PIL import Image
from scipy import ndimage

D, B1, B2, SEM = sys.argv[1:5]
D, SEM = os.path.abspath(D), os.path.abspath(SEM)
KOD = os.path.dirname(os.path.abspath(__file__)) + '/'
V = os.path.abspath(os.path.join(KOD, '..', 'varlik')) + '/'
RENK = {'orange': '10,40,24', 'fig': '52,18,48', 'olive': '12,24,78', 'pomegranate': '100,16,24', 'almond': '52,22,14',
        'lemon': '12,22,76', 'grape': '16,30,90', 'loquat': '62,24,10'}
MM = 300 / 25.4
os.makedirs(D + '/kontrol', exist_ok=True)
t0 = time.time()
sonuc = []
for i, st in enumerate(RENK, 1):
    on = f'{D}/kontrol/{st}_yok'
    r = subprocess.run(['python3', '-I', KOD + 'baski_kes.py', V + 'kes/' + st.upper() + 'R', SEM, 'Maximilian', 'Josephine', B1, B2,
                        'Forever my favorite adventure!', RENK[st], on], capture_output=True, text=True, cwd=KOD,
                       env={'PATH': '/usr/bin:/bin', 'BURC_YOK': '1'})
    if r.returncode:
        raise SystemExit(r.stderr[-1500:])
    P = np.asarray(Image.open(f'{D}/baski/B_{st}_baski_11oz.png').convert('RGB')).astype(float)
    Q = np.asarray(Image.open(on + '_baski_11oz.png').convert('RGB')).astype(float)
    bm = np.abs(P - Q).max(-1) > 40
    ys, xs = np.where(bm)
    y0, y1 = ys.min(), ys.max()
    sus = np.zeros(bm.shape, bool)
    band = slice(max(0, y0 - 20), y1 + 21)
    sus[band] = Q[band].min(-1) < 235
    en_kisa = max(0.0, ndimage.distance_transform_edt(~sus)[bm].min() - 1) / MM
    cx = (xs.min() + xs.max()) // 2
    ust = Q[max(0, y0 - 90):y0, cx - 150:cx + 150].min(-1) < 120
    iy = np.where(ust.any(1))[0]
    ayrim = (y0 - (max(0, y0 - 90) + iy.max())) / MM if len(iy) else float('nan')
    durum = 'TAMAM' if en_kisa >= 1.2 and not (bm & sus).any() else 'SORUN'
    sonuc.append(f'{st:12s} dala en kisa {en_kisa:.2f} mm, cakisma px {int((bm & sus).sum())}, isim ayrimi {ayrim:.2f} mm -> {durum}')
    g = time.time() - t0
    print(f'[{i}/8 %{100 * i // 8}] {sonuc[-1]} (gecen {g:.0f}s, kalan ~{g / i * (8 - i):.0f}s)', flush=True)
open(D + '/kontrol/burc_mesafe.txt', 'w').write('\n'.join(sonuc) + '\n')
