#!/usr/bin/env python3
"""GOLGE (Serdar 4 Eki): tum ogelere tek isikla (sol ust) sag alta dusen, yumusak, koyu lacivert golge; 3 kademe.
Yalniz golge (parilti / tane / isik egimi YOK). Golge yalniz zemine (oge disi, 1 - alfa) duser; oge sekli, konumu,
altin rengi degismez.

Oge alfalari: birlesik ALFA.png ayrilir: cember = HALKA_24x36 alfasi (sayfa 1:1), digerleri POSTER.json kutulari.
Olcek: f = oge yuksekligi / ana sembol yuksekligi, [F_MIN, 1]; cember f = cizgi kalinligi orani (CEMBER_F).
Oge golgesi: kayma = KAYMA x f (45 derece sag alt), Gauss sigma = BULANIK x f, opaklik = OPAK x (0.6 + 0.4 f).
Birlesim: ogelerin golgeleri max ile (ust uste koyulasma yok); renk GOLGE_RENK (zemin kose laciverti, siyah degil).

Kullanim: golge.py --poster POSTER.png --alfa ALFA.png --rapor POSTER.json --cikti DIR
"""
import argparse, json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
Image.MAX_IMAGE_PIXELS = None
LUMA = np.array([0.299, 0.587, 0.114], np.float32)
GOLGE_RENK = np.array([1.0, 2.0, 9.0], np.float32)
F_MIN = 0.25
CEMBER_F = 0.5
KADEME = {1: {'kayma': 28, 'bulanik': 12, 'opak': 0.55},     # 2. deneme (1. deneme 14/8/0.45, 32/18/0.65, 60/30/0.85:
          2: {'kayma': 60, 'bulanik': 24, 'opak': 0.75},     # tam sayfada 0 ile 1 ayirt edilmiyordu)
          3: {'kayma': 110, 'bulanik': 40, 'opak': 0.95}}
OGELER = ('ana_sembol', 'kucuk_sol', 'kucuk_sag', 'isim1', 'sonsuz', 'isim2', 'tagline')


def oge_alfalari(A, kut):
    H, W = A.shape
    h = np.asarray(Image.open(KOK / 'varlik' / 'halka' / 'HALKA_24x36.png').convert('L'), np.float32) / 255
    out = {'cember': (h, [0, 0, W, H])}
    geri = A * (h < 0.01)
    hm = kut['ana_sembol'][3] - kut['ana_sembol'][1]
    f = {'cember': CEMBER_F}
    for ad in OGELER:
        x0, y0, x1, y1 = kut[ad]
        m = np.zeros_like(A); m[y0:y1, x0:x1] = geri[y0:y1, x0:x1]
        out[ad] = (m, [x0, y0, x1, y1])
        f[ad] = float(np.clip((y1 - y0) / hm, F_MIN, 1))
    return out, f


def golge(A, kut, k):
    H, W = A.shape
    oa, f = oge_alfalari(A, kut)
    S = np.zeros((H, W), np.float32); deg = {}
    for ad, (m, (x0, y0, x1, y1)) in oa.items():
        kay = k['kayma'] * f[ad]; sg = k['bulanik'] * f[ad]; op = k['opak'] * (0.6 + 0.4 * f[ad])
        p = int(kay + 4 * sg) + 4
        X0, Y0, X1, Y1 = max(0, x0 - p), max(0, y0 - p), min(W, x1 + p), min(H, y1 + p)
        b = cv2.GaussianBlur(m[Y0:Y1, X0:X1], (0, 0), sg)
        d = kay / np.sqrt(2)
        b = cv2.warpAffine(b, np.float32([[1, 0, d], [0, 1, d]]), (X1 - X0, Y1 - Y0), flags=cv2.INTER_LINEAR)
        S[Y0:Y1, X0:X1] = np.maximum(S[Y0:Y1, X0:X1], op * b)
        deg[ad] = {'f': round(f[ad], 3), 'kayma_px': round(kay, 1), 'bulaniklik_sigma_px': round(sg, 1), 'opaklik': round(op, 3)}
    return S, deg


def main():
    ap = argparse.ArgumentParser()
    for k in ('poster', 'alfa', 'rapor', 'cikti'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--kademe', nargs='+', type=int, default=[1, 2, 3])
    a = ap.parse_args()
    C = Path(a.cikti); C.mkdir(parents=True, exist_ok=True)
    I = np.asarray(Image.open(a.poster).convert('RGB'), np.float32)
    A = np.asarray(Image.open(a.alfa), np.float32) / 255
    kut = json.loads(Path(a.rapor).read_text())['kutu']
    dist = cv2.distanceTransform((A < 0.01).astype(np.uint8), cv2.DIST_L2, 5)

    def kontrast(O):
        r = []
        for ad in ('isim1', 'isim2', 'tagline'):
            x0, y0, x1, y1 = kut[ad]
            a_ = A[y0:y1, x0:x1]; L = O[y0:y1, x0:x1] @ LUMA; dd = dist[y0:y1, x0:x1]
            r.append(round(float((L[a_ > 0.95].mean() + 12.75) / (L[(dd > 3) & (dd < 40)].mean() + 12.75)), 2))
        return r
    rap = {'isik': 'sol ust, golge sag alt 45 derece', 'renk': GOLGE_RENK.tolist(), 'kademe': {}, '0': {'kontrast': kontrast(I)}}
    for kd in a.kademe:
        S, deg = golge(A, kut, KADEME[kd])
        O = I + (S * (1 - A))[..., None] * (GOLGE_RENK - I)
        del S
        rap['kademe'][kd] = {'deger': KADEME[kd], 'oge': deg, 'kontrast': kontrast(O),
                             'altin_degisim_maks': float(np.abs(O - I)[A > 0.99].max())}
        print(kd, json.dumps({'ana': deg['ana_sembol'], 'isim1': deg['isim1'], 'cember': deg['cember'],
                              'kontrast': rap['kademe'][kd]['kontrast'], 'altin_maks': rap['kademe'][kd]['altin_degisim_maks']}), flush=True)
        Image.fromarray(np.clip(np.round(O), 0, 255).astype(np.uint8)).save(C / f'GOLGE_{kd}.png', dpi=(300, 300))
        del O
    (C / 'GOLGE.json').write_text(json.dumps(rap, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
