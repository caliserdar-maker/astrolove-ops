#!/usr/bin/env python3
"""video-v1 kart 3 QC (PASS/FAIL). Kullanim: qc_kart3.py REF.jpg YENI.jpg YENI_log.json
1) Boyut referansla ayni.  2) Sol panel (144..1425 x 829..1414) degismedi: ort fark < 0.5.
3) Sol alt yazi (400..1180 x 1735..1795) degismedi: ort fark < 0.5 (farkli burc).
4) Sag panelde poster kalmadi: lacivert piksel (B > R+25 ve L < 90) sayisi < 50. (77 cift kosusunda 'Name under Aquarius/Capricorn'
   koyu metninin JPEG kenar pikseli 1 px yanlis pozitif verdi; gercek poster kalintisi ~700 bin px.)
5) Eski metinler silindi: 'Cancer left'/'Libra left' etiket alanlari zemin (ort |fark-zemin| < 1).
6) metin_kurali: log'daki tum metinler PASS.
--cift POSTER_EJ.png: 2-3 yerine sol panel = cift posterinin panel hizasiyla izdusumu (ort fark < 1.0) ve sembol alaninda referanstan farkli (16x16 blok ortalamasi maks > 20)."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'medya_v1/uretim'))
from metin_kurali import denetle
r, y, lg = sys.argv[1:4]
cift = sys.argv[sys.argv.index('--cift') + 1] if '--cift' in sys.argv else None
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
if cift:
    import cv2
    h = json.load(open(Path(__file__).resolve().parent / 'kart3_panel_hiza.json')); Mp = np.array(h['M_panel'], np.float32)
    Pw = cv2.warpAffine(np.asarray(Image.open(cift).convert('RGB')).astype(np.float32), Mp, (1281, 585), flags=cv2.INTER_AREA)
    Pt = np.clip(np.stack([np.polyval(np.array(h['ton'][c]), Pw[..., c]) for c in range(3)], 2), 0, 255)
    s['sol_panel_poster_fark'] = float(np.abs(Y[831:1412, 146:1423] - Pt[2:583, 2:1279]).mean())
    blk = np.abs(R[850:1030, 144:1425] - Y[850:1030, 144:1425]).mean(2)
    blk = blk[:blk.shape[0] // 16 * 16, :blk.shape[1] // 16 * 16].reshape(blk.shape[0] // 16, 16, -1, 16).mean((1, 3))
    s['sol_panel_ref_blok_maks'] = float(blk.max())
s['PASS'] = {'boyut': s['boyut'],
             'sol_panel': (s['sol_panel_poster_fark'] < 1.0 and s['sol_panel_ref_blok_maks'] > 20) if cift else s['sol_panel'] < 0.5,
             'sol_alt_yazi': bool(cift) or L['ayni_burc'] or s['sol_alt_yazi'] < 0.5,
             'sag_poster_yok': lac < 50, 'eski_etiket_yok': et < 1.0, 'metin_kurali': not s['metin_kurali']}
s['SONUC'] = 'PASS' if all(s['PASS'].values()) else 'FAIL'
print(json.dumps(s)); json.dump(s, open(y.rsplit('.', 1)[0] + '_qc.json', 'w'), indent=1)
sys.exit(0 if s['SONUC'] == 'PASS' else 1)
