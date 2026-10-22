#!/usr/bin/env python3
"""WP plate - onayli kaynak kagit KAYMA TANISI (salt okur; Serdar onayi 2 Eki, Test 4 e_kagit + plate FAIL).

Her boy icin: onayli WARM_PARCHMENT kaynagi (S) ile VINTAGE_<boy> plate'i (P0, siparis yolundaki gibi boyutla) arasinda
- zemin_uyumu: wp_ornek ile ayni uretim fonksiyonlari (wk.ozet / wk.dE / wk.murekkep_maskesi), esik ort <= 0.5
- e_kagit burada YOK (ders 33): uretim degeri kayma_uretim.py (surucu.wp_asamasi -> wp_bakir.qc)
- kayma: yuksek geciren luma (murekkep sifirlanmis) faz korelasyonu; global ve 4x4 karo
- kayma sonrasi (P1 = P0 global kaydirilmis) ayni olcumler
Isim / mesaj / musteri verisi YOK. Cikti: <cik>/KAYMA_<boy>.json + KESIT_<boy>.jpg (S | P0 | P1 | |S-P0| x4 | |S-P1| x4).
"""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def dE_parca(wk, A, B, parca=512):
    out = np.empty(A.shape[:2], np.float32)
    for y in range(0, A.shape[0], parca):
        out[y:y + parca] = wk.dE(A[y:y + parca], B[y:y + parca])
    return out


def olc(wk, S, P):
    """zemin_uyumu, wp_ornek ile ayni: wk.ozet(wk.dE(P, S), ~wk.murekkep_maskesi(S - P, kenar=0)), esik ort <= 0.5.
    e_kagit BURADA OLCULMEZ (ders 33): uretim wp_bakir.qc degeri kayma_uretim.py'den gelir."""
    mk = wk.murekkep_maskesi(S - P, kenar=0)
    d = dE_parca(wk, P, S)
    z = wk.ozet(d, ~mk)
    z['gecti'] = z.get('ort', 99) <= 0.5
    return {'zemin_uyumu': z}, d, mk


def yuksek(L, mk):
    h = L - cv2.GaussianBlur(L, (0, 0), 6)
    h[cv2.dilate(mk.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)] = 0
    return h.astype(np.float32)


def kayma(a, b):
    """b'yi a'ya oturtan (dx, dy): P(x - dx, y - dy) ~ S(x, y) -> P1 = P0 kaydir(dx, dy)."""
    win = cv2.createHanningWindow((a.shape[1], a.shape[0]), cv2.CV_32F)
    (dx, dy), r = cv2.phaseCorrelate(b, a, win)
    return round(float(dx), 2), round(float(dy), 2), round(float(r), 3)


def kaydir(P, dx, dy):
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(P, M, (P.shape[1], P.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--wp-kod', required=True)        # WP_REF checkout / scripts/medya_v1
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--plate', required=True)
    ap.add_argument('--boy', required=True)
    ap.add_argument('--cik', required=True)
    a = ap.parse_args()
    sys.path.insert(0, a.wp_kod)
    import wp_katman as wk
    t0 = time.time()
    cik = Path(a.cik); cik.mkdir(parents=True, exist_ok=True)
    S = wk.dizi(a.kaynak); H, W = S.shape[:2]
    pl = Image.open(a.plate)
    R = {'boy': a.boy, 'kaynak_px': [W, H], 'plate_px': list(pl.size)}
    P0 = wk.boyutla(wk.dizi(pl), (W, H)); del pl
    R['once'], d0, mk0 = olc(wk, S, P0)
    LS, LP = S @ wk.LUMA, P0 @ wk.LUMA
    hS, hP = yuksek(LS, mk0), yuksek(LP, mk0)
    dx, dy, r = kayma(hS, hP)
    R['kayma_global'] = {'dx': dx, 'dy': dy, 'tepe': r}
    karo = []
    n = 4
    for i in range(n):
        for j in range(n):
            y0, y1, x0, x1 = H * i // n, H * (i + 1) // n, W * j // n, W * (j + 1) // n
            kx, ky, kr = kayma(hS[y0:y1, x0:x1].copy(), hP[y0:y1, x0:x1].copy())
            dd = d0[y0:y1, x0:x1][~mk0[y0:y1, x0:x1]]
            karo.append({'satir': i, 'sutun': j, 'dx': kx, 'dy': ky, 'tepe': kr,
                         'once_ort': round(float(dd.mean()), 3) if dd.size else None})
    R['kayma_karo'] = karo
    # global = karo medyani (tum goruntu faz korelasyonu pencere / kenar etkisiyle 0.5 px sapabiliyor; sentetik test)
    dx = round(float(np.median([k['dx'] for k in karo])), 2); dy = round(float(np.median([k['dy'] for k in karo])), 2)
    R['kayma_global']['karo_medyan'] = {'dx': dx, 'dy': dy}
    P1 = kaydir(P0, dx, dy)
    R['sonra_global'], d1, mk1 = olc(wk, S, P1)
    for k in karo:
        y0, y1 = H * k['satir'] // n, H * (k['satir'] + 1) // n
        x0, x1 = W * k['sutun'] // n, W * (k['sutun'] + 1) // n
        dd = d1[y0:y1, x0:x1][~mk1[y0:y1, x0:x1]]
        k['sonra_ort'] = round(float(dd.mean()), 3) if dd.size else None
    # kesit: once en kotu karonun ortasi, 400x300
    kk = max((k for k in karo if k['once_ort'] is not None), key=lambda k: k['once_ort'])
    cy = H * (2 * kk['satir'] + 1) // (2 * n); cx = W * (2 * kk['sutun'] + 1) // (2 * n)
    y0, x0 = max(0, cy - 150), max(0, cx - 200)
    sl = (slice(y0, y0 + 300), slice(x0, x0 + 400))
    parca = [S[sl], P0[sl], P1[sl], np.clip(np.abs(S[sl] - P0[sl]) * 4, 0, 255), np.clip(np.abs(S[sl] - P1[sl]) * 4, 0, 255)]
    ara = np.full((300, 6, 3), 255, np.float32)
    seri = []
    for p in parca:
        seri += [p, ara]
    Image.fromarray(np.clip(np.concatenate(seri[:-1], 1), 0, 255).astype(np.uint8)).save(cik / f'KESIT_{a.boy}.jpg', quality=88)
    R['kesit'] = {'x0': x0, 'y0': y0, 'w': 400, 'h': 300, 'sira': 'kaynak | plate | plate kaydirilmis | |S-P0| x4 | |S-P1| x4'}
    R['sure_sn'] = round(time.time() - t0, 1)
    (cik / f'KAYMA_{a.boy}.json').write_text(json.dumps(R, indent=1))
    print('KAYMA', a.boy, json.dumps({q: R[q] for q in ('kayma_global', 'once', 'sonra_global', 'sure_sn')}), flush=True)
    print('KARO', a.boy, json.dumps([(k['dx'], k['dy'], k['once_ort'], k['sonra_ort']) for k in karo]), flush=True)


if __name__ == '__main__':
    main()
