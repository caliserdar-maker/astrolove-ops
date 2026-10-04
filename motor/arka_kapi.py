#!/usr/bin/env python3
"""ARKA PLAN HALKA KAPISI (Serdar 4 Eki): lacivert radyal kararmada halka (bantlanma) olcumu, PASS/FAIL.

Gradyan geometrisi (zemin_gradient: merkez = 24x36 halka merkezi, 4:5 elips): her piksel icin elips yaricapi r.
Zemin pikselleri: ogeler (ALFA > 0.005) + golge payi (GOLGE_PAY px, sayfa olceginde) disi, luma < LUMA_MAX (yildiz/altin
disi). Radyal profil: r'nin 1 px (goruntu olceginde) kutularinda her kanalin ortalamasi (yildiz artigi icin ust %5 atilir).
Halka kontrasti = profil - Gauss(profil, SIGMA_PROFIL px sayfa olceginde) artiginin p99 |.| degeri (8 bit seviye), en cok
degisen kanal (B). Monotonluk: yumusak profil disa dogru artmamali (B; ihlal toplami). Basamak: kuantalama + titresimsiz
8 bit sayfada artik testere disi (~0.3-0.5 seviye); titresimli sayfada kutu ortalamasi puruzsuz (< 0.1).
Gecme: halka_kontrast <= ESIK ve monotonluk ihlali <= MONO_ESIK.

Kullanim: arka_kapi.py GORUNTU [GORUNTU ...] --alfa ALFA.png [--json OUT]
"""
import argparse, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
SAYFA_W = 7200
MERKEZ = (3598.97, 4388.09)          # 24x36 halka merkezi (doku_poster h24)
ELIPS = 1.25
GOLGE_PAY = 300
LUMA_MAX = 40
SIGMA_PROFIL = 40
ESIK = 0.12
MONO_ESIK = 0.5


def profil(I, A, w_say=SAYFA_W):
    H, W = I.shape[:2]
    s = W / w_say
    a = cv2.resize(A, (W, H), interpolation=cv2.INTER_AREA) if A.shape != (H, W) else A
    k = max(3, int(round(2 * GOLGE_PAY * s)) | 1)
    zem = cv2.dilate((a > 0.005).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))) == 0
    zem &= (I.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)) < LUMA_MAX
    yy, xx = np.nonzero(zem)
    r = np.hypot(xx - MERKEZ[0] * s, (yy - MERKEZ[1] * s) / ELIPS)
    b = r.astype(np.int64)
    n = np.bincount(b)
    out = {}
    for c, ad in enumerate('RGB'):
        v = I[yy, xx, c].astype(np.float64)
        # yildiz artigi: kutu basina ust %5 atma yerine global: yerel ortalamanin 6 seviye ustu atilir
        m0 = np.bincount(b, v, len(n)) / np.maximum(n, 1)
        ok = v <= m0[b] + 6
        nn = np.bincount(b[ok], minlength=len(n))
        out[ad] = np.bincount(b[ok], v[ok], len(n)) / np.maximum(nn, 1)
    return out, n, s


def olc(I, A):
    P, n, s = profil(I, A)
    gec = np.nonzero(n >= 200)[0]
    r0, r1 = gec.min(), gec.max()
    sig = SIGMA_PROFIL * s
    res = {}
    for ad, p in P.items():
        x = p[r0:r1 + 1]; ok = n[r0:r1 + 1] >= 200
        xi = np.interp(np.arange(len(x)), np.nonzero(ok)[0], x[ok])
        sm = cv2.GaussianBlur(xi[None].astype(np.float64), (0, 0), sig)[0]
        art = (xi - sm)[ok][int(3 * sig):-int(3 * sig) or None]
        d = np.diff(sm)
        res[ad] = {'halka_kontrast_p99': round(float(np.percentile(np.abs(art), 99)), 3),
                   'artik_std': round(float(art.std()), 3), 'aralik': [round(float(sm.min()), 1), round(float(sm.max()), 1)],
                   'mono_ihlal': round(float(d[d > 0].sum()), 3)}
    k = max(res, key=lambda q: res[q]['aralik'][1] - res[q]['aralik'][0])
    return {'kanallar': res, 'olcu_kanal': k, 'halka_kontrast': res[k]['halka_kontrast_p99'],
            'mono_ihlal': res[k]['mono_ihlal'], 'esik': ESIK, 'mono_esik': MONO_ESIK,
            'sonuc': 'PASS' if res[k]['halka_kontrast_p99'] <= ESIK and res[k]['mono_ihlal'] <= MONO_ESIK else 'FAIL'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('goruntu', nargs='+'); ap.add_argument('--alfa', required=True); ap.add_argument('--json')
    a = ap.parse_args()
    A = np.asarray(Image.open(a.alfa), np.float32) / 255
    R = {}
    for f in a.goruntu:
        I = np.asarray(Image.open(f).convert('RGB'))
        R[Path(f).name] = r = olc(I, A)
        print(f"{Path(f).name:40s} {I.shape[1]}x{I.shape[0]} halka {r['halka_kontrast']:.3f} mono {r['mono_ihlal']:.3f} {r['sonuc']}")
    if a.json:
        Path(a.json).write_text(json.dumps(R, indent=1, ensure_ascii=False))
    sys.exit(0 if all(r['sonuc'] == 'PASS' for r in R.values()) else 1)


if __name__ == '__main__':
    main()
