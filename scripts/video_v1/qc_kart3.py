#!/usr/bin/env python3
"""video-v1 kart 3 QC (PASS/FAIL). Kullanim: qc_kart3.py REF.jpg YENI.jpg YENI_log.json
1) Boyut referansla ayni.  2) Sol panel (144..1425 x 829..1414) degismedi: ort fark < 0.5.
3) Sol alt yazi (400..1180 x 1735..1795) degismedi: ort fark < 0.5 (farkli burc).
4) Sag panelde poster kalmadi: lacivert piksel (B > R+25 ve L < 90) sayisi = 0.
5) Eski metinler silindi: 'Cancer left'/'Libra left' etiket alanlari zemin (ort |fark-zemin| < 1).
6) metin_kurali: log'daki tum metinler PASS."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'medya_v1/uretim'))
from metin_kurali import denetle
r, y, lg = sys.argv[1:4]
R = np.asarray(Image.open(r).convert('RGB')).astype(float); Y = np.asarray(Image.open(y).convert('RGB')).astype(float)
L = json.load(open(lg)); BG = np.array([237., 232., 226.])
f = lambda sl: float(np.abs(R[sl] - Y[sl]).mean())
sp = Y[815:1430, 1560:2870]
lac = int(((sp[..., 2] > sp[..., 0] + 25) & (sp.mean(2) < 90)).sum())
et = max(float(np.abs(Y[490:590, 560:1010] - BG).mean()), float(np.abs(Y[490:590, 2030:2400] - BG).mean()))
metin = [L['baslik'], L['alt_baslik'], L['alt_not']] + [f'{a}: {b}' for a, b in L['alanlar']]
s = {'boyut': Y.shape == R.shape, 'sol_panel': f((slice(829, 1414), slice(144, 1425))),
     'sol_alt_yazi': f((slice(1735, 1795), slice(400, 1180))), 'sag_lacivert_px': lac, 'etiket_zemin': round(et, 3),
     'metin_kurali': [h for m in metin for h in denetle(m)]}
s['PASS'] = {'boyut': s['boyut'], 'sol_panel': s['sol_panel'] < 0.5, 'sol_alt_yazi': L['ayni_burc'] or s['sol_alt_yazi'] < 0.5,
             'sag_poster_yok': lac == 0, 'eski_etiket_yok': et < 1.0, 'metin_kurali': not s['metin_kurali']}
s['SONUC'] = 'PASS' if all(s['PASS'].values()) else 'FAIL'
print(json.dumps(s)); json.dump(s, open(y.rsplit('.', 1)[0] + '_qc.json', 'w'), indent=1)
sys.exit(0 if s['SONUC'] == 'PASS' else 1)
