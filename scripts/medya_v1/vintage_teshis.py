#!/usr/bin/env python3
"""Teshis (salt olcum): vintage (Warm Parchment) sembol kapisi FAIL. Kapi degismez; ek olcum:
zemin dokusu farki (yeni yer - eski yer, murekkep maskesinde) ve doku-dengelenmis fark |(P - zemin_yeni) - (ref - zemin_eski)|.
Cikti: REVIEW/TAM_SET_<CIFT>/_teshis/ (json + kaynak|yeni gorselleri)."""
import sys, json
sys.argv = [sys.argv[0], sys.argv[1] if len(sys.argv) > 1 else 'ARIES_LEO']
import numpy as np, cv2
import tam_set as T
from tam_set import A, rc, KP, W
from PIL import Image
A.kisisel_hazirla()
import edisyon_uret as E
ed = 'vintage'
(E.YOL / ed / 'zemin').mkdir(parents=True, exist_ok=True)
rc('copy', f'{KP}/HAZIR/zemin_{ed}_4x5.png', str(E.YOL / ed / 'zemin'))
(E.YOL / ed / 'zemin' / f'zemin_{ed}_4x5.png').rename(E.YOL / ed / 'zemin' / '4x5.png')
rc('copy', T.SAYFA_HAM, str(W / 'ham'), '--include', 'vintage_*.png')
ciftler = sorted(x.strip('/') for x in rc('lsf', A.POD, '--dirs-only').split()); no = ciftler.index(T.CIFT) + 1
EP = T.EdPoster(ed); out = {}; D = T.CIK / '_teshis'; D.mkdir(exist_ok=True)
for ad, n in (('CL', 28), ('AL', no)):
    B = EP.sayfa_kur((W / 'ham' / f'{ed}_{n}.png').read_bytes(), n)
    p, b, kk = EP.uret(B, A.ISIM, A.TAG); s, S = B['s'], B['S']
    P = np.asarray(p.convert('RGB')).astype(np.float32); ref = np.asarray(S['ref']).astype(np.float32); Z = S['zemin_a']
    sk = b['sembol_kapisi']; r = {'kapi': sk}
    for y in ('sol', 'sag'):
        x0, y0, x1, y1 = sk[y]['kaynak_kutu']; dx = sk[y]['dx']
        mk = B['m'][y0:y1, x0:x1].astype(bool)
        # yeni yerin x'i: kapidaki en iyi eslesme (ex + dx) -> kapiyla ayni hesap
        # yeni yer: kaynak kirpimi ile P'de yatay arama (dy=0)
        src = ref[y0:y1, x0:x1]; en = None
        for X in range(max(0, x0 - 400), min(P.shape[1] - (x1 - x0), x0 + 400)):
            f = float(np.abs(P[y0:y1, X:X + x1 - x0] - src).max(2)[mk].mean()) if mk.any() else 0
            if en is None or f < en[0]: en = (f, X)
        f, X = en
        zo, zn = Z[y0:y1, x0:x1], Z[y0:y1, X:X + x1 - x0]
        r[y] = {'kayma_x': X - x0, 'fark_ham': round(f, 2),
                'zemin_doku_fark': round(float(np.abs(zn - zo).max(2)[mk].mean()), 2),
                'doku_dengeli_fark': round(float(np.abs((P[y0:y1, X:X + x1 - x0] - zn) - (src - zo)).max(2)[mk].mean()), 2),
                'zemin_std_bolge': round(float(zo.std()), 2)}
    out[ad] = r; A.sembol_gorseli(kk, f'../TAM_SET/_teshis/SEMBOL_vintage_{ad}.jpg')
    print(ad, json.dumps(r, default=str)[:900], flush=True)
(D / 'teshis.json').write_text(json.dumps(out, indent=1, default=str))
rc('copy', str(D), f'{T.HEDEF}/_teshis')
