#!/usr/bin/env python3
"""LEKE KAPISI (Serdar 4 Eki: CANCER_LIBRA ana sembolu sol ustte leke; Canva parlak / solgun benekleri).

Leke = altinin icinde SOLGUN (dusuk doygunluk) ve PARLAK bolge: oge cekirdegi (maske > 0.95, 3 px asindirilmis)
icinde HSV doygunluk (2 px Gauss) < DOY_MAX ve parlaklik > PARLAK_MIN; bilesen alani >= ALAN_MIN px (24x36 baskida
~5 mm2, gozle secilen leke boyu). Olcu: leke alani / cekirdek alani, binde. Ayrica 2x2 ceyrek degerleri (lekenin yeri).
ESIK (binde 100): 4 Eki kalibrasyonu: onayli isim / tagline / logo 0-10, onayli kucuk sembollerin cogu 0-63 (LIBRA 189,
TAURUS 128 kucuk boyda gozle onayli, istisna); ana semboller SCORPIO_VIRGO 59, LEO_SAGITTARIUS 77 (sorun gorulmedi),
CANCER_LIBRA 147 (Serdar leke gordu). Esik disi ana sembol Canva'da yeniden uretilir.

Kullanim: leke_kapi.py --set S17 --sayfa-json DIR --sayfa ANA_DENEME [--onayli KUCUK_1A_P ...] [--kanit DIR]
"""
import argparse, json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

LUMA = np.array([0.299, 0.587, 0.114], np.float32)
DOY_MAX = 0.42
PARLAK_MIN = 0.55
ALAN_MIN = 800
ESIK = 100.0


def olc(t, O):
    ce = cv2.erode((O > 0.95).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(np.float32)
    hsv = cv2.cvtColor(np.ascontiguousarray(t), cv2.COLOR_RGB2HSV).astype(np.float32) / 255
    m = ((cv2.GaussianBlur(hsv[..., 1], (0, 0), 2) < DOY_MAX) & (hsv[..., 2] > PARLAK_MIN) & (ce > 0)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    iyi = np.zeros(n, bool); iyi[1:] = st[1:, cv2.CC_STAT_AREA] >= ALAN_MIN
    bm = iyi[lab]
    H, W = ce.shape
    cey = {}
    for ad, (ys, xs) in {'sol_ust': (slice(0, H // 2), slice(0, W // 2)), 'sag_ust': (slice(0, H // 2), slice(W // 2, W)),
                         'sol_alt': (slice(H // 2, H), slice(0, W // 2)), 'sag_alt': (slice(H // 2, H), slice(W // 2, W))}.items():
        cey[ad] = round(1000 * float(bm[ys, xs].sum()) / max(float(ce[ys, xs].sum()), 1), 3)
    return round(1000 * float(bm.sum()) / max(float(ce.sum()), 1), 3), cey, bm


def ogeler(S, J, sayfa):
    z = np.load(Path(S) / f'{sayfa}.npz'); j = json.loads((Path(J) / f'DOKU_AI_{sayfa}.json').read_text())
    for o in j['ogeler']:
        x0, y0, x1, y1 = o['kutu']
        yield o['oge'], z['t1'][y0:y1, x0:x1], z['O'][y0:y1, x0:x1].astype(np.float32) / 255


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--set', required=True); ap.add_argument('--sayfa-json', required=True)
    ap.add_argument('--onayli', nargs='*', default=[]); ap.add_argument('--sayfa', nargs='+', required=True)
    ap.add_argument('--kanit')
    a = ap.parse_args()
    on = {}
    for sf in a.onayli:
        for ad, t, O in ogeler(a.set, a.sayfa_json, sf):
            on[f'{sf}:{ad}'] = olc(t, O)[0]
    esik = ESIK
    rap = {'olcu': 'solgun-parlak leke alani binde (cekirdek px, bilesen >= %d px)' % ALAN_MIN, 'esik': esik,
           'onayli': on, 'semboller': {}, 'esik_disi': []}
    for sf in a.sayfa:
        for ad, t, O in ogeler(a.set, a.sayfa_json, sf):
            v, cey, bm = olc(t, O)
            rap['semboller'][ad] = {'leke': v, 'ceyrek': cey, 'sonuc': 'PASS' if v <= esik else 'FAIL'}
            if v > esik:
                rap['esik_disi'].append(ad)
            if a.kanit:
                g = t.astype(np.float32) * (O[..., None] > 0.02) * 0.6
                g[bm] = [255, 0, 255]
                Image.fromarray(g.astype(np.uint8)).save(Path(a.kanit) / f'LEKE_{ad}.jpg', quality=85)
    print(json.dumps(rap, ensure_ascii=False, indent=1))
    if a.kanit:
        (Path(a.kanit) / 'LEKE_KAPI.json').write_text(json.dumps(rap, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
