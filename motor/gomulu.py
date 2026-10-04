#!/usr/bin/env python3
"""GOMULU (Serdar 4 Eki): ogeler zemin dokusunun icine gomulu gorunsun. Golge / parilti YOK.

T (ortak yuzey dokusu): MB plate'in (BLUE_24x36) yuksek frekans bileseni, luma: L - Gauss(L, BANT_SIGMA), 0.8 px
  yumusatma (JPEG blok izi). Yildiz diskleri, cember (HALKA alfa + 15 px) ve |T| > 5 std aykiri pikseller maskelenir;
  maskeli yerler ayni dokunun kaydirilmis kopyasiyla doldurulur (doku duragan). Std = 1'e normalize.
A AYNI YUZEY: tum sayfaya ayni koordinatta T eklenir (sRGB seviye): genlik = zemin T_ZEMIN x (1 - alfa) + altin
  T_ALTIN x alfa; renk korunur (rgb x (1 + d / luma)). Desen oge sinirinda kesilmez (genlik alfa ile yumusak gecer).
B GOMULU: A + oge kenarinin ICINDE (KENAR_PX genislik) sol ust isiga gore ince derinlik: ic normal . isik yonu;
  isiga bakan ic duvar (sol ust kenar) koyu, karsi duvar hafif acik. Disari tasma yok.
Leke kapisi ayri: leke_kapi.py.

Kullanim: gomulu.py --poster POSTER.png --alfa ALFA.png --plate BLUE_24x36.png --cikti DIR
"""
import argparse, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import zemin_gradient as zg                                          # noqa: E402

Image.MAX_IMAGE_PIXELS = None
LUMA = np.array([0.299, 0.587, 0.114], np.float32)
BANT_SIGMA = 4.0
T_ALTIN = 5.0             # sRGB seviye std, altin ustunde (~2 L*)
ISIK = np.array([-1.0, -1.0], np.float32) / np.sqrt(2)   # sol ust (x, y)
KENAR_PX = 4.0
KOYU, ACIK = 0.40, 0.15


def doku(plate_f):
    P = np.asarray(Image.open(plate_f).convert('RGB'), np.float32)
    L = P @ LUMA
    T = cv2.GaussianBlur(L - cv2.GaussianBlur(L, (0, 0), BANT_SIGMA), (0, 0), 0.8)
    H, W = L.shape
    m = np.zeros((H, W), np.uint8)
    YL, _ = zg.yildizlar(P)
    del P
    for cx, cy, r, _ in YL:
        cv2.circle(m, (int(cx), int(cy)), int(r) + 6, 1, -1)
    h = np.asarray(Image.open(KOK / 'varlik' / 'halka' / 'HALKA_24x36.png').convert('L'))
    m |= cv2.dilate((h > 0).astype(np.uint8), np.ones((31, 31), np.uint8))
    s0 = float(T[m == 0].std())
    m |= (np.abs(T) > 5 * s0).astype(np.uint8)
    for dx, dy in ((523, 311), (-457, 389), (601, -277), (-333, -541)):
        if not m.any():
            break
        Ts = np.roll(T, (dy, dx), (0, 1)); ms = np.roll(m, (dy, dx), (0, 1))
        ok = (m == 1) & (ms == 0)
        T[ok] = Ts[ok]; m[ok] = 0
    T[m == 1] = 0
    s = float(T.std())
    return T / s, {'zemin_std_seviye': round(s0, 3), 'yildiz': len(YL), 'kalan_maske_orani': float(m.mean())}


def uygula_tane(I, A, T, t_zemin):
    amp = (t_zemin * (1 - A) + T_ALTIN * A) * T
    lum = np.maximum(I @ LUMA, 1.0)
    return I * (1 + amp / lum)[..., None]


def gomme(I, A):
    Ab = cv2.GaussianBlur(A, (0, 0), 1.5)
    gx = cv2.Sobel(Ab, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(Ab, cv2.CV_32F, 0, 1, ksize=3)
    n = np.hypot(gx, gy) + 1e-6
    sh = (gx * ISIK[0] + gy * ISIK[1]) / n                    # ic normal . isik: -1 isiga bakan ic duvar (koyu)
    del gx, gy, n, Ab
    d = cv2.distanceTransform((A > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    band = np.clip(1 - d / KENAR_PX, 0, 1) * np.clip(A, 0, 1)
    del d
    f = np.where(sh < 0, KOYU * sh, ACIK * sh) * band
    return I * (1 + f)[..., None]


def main():
    ap = argparse.ArgumentParser()
    for k in ('poster', 'alfa', 'plate', 'cikti'):
        ap.add_argument('--' + k, required=True)
    a = ap.parse_args()
    C = Path(a.cikti); C.mkdir(parents=True, exist_ok=True)
    T, bil = doku(a.plate)
    I = np.asarray(Image.open(a.poster).convert('RGB'), np.float32)
    A = np.asarray(Image.open(a.alfa), np.float32) / 255
    t_zemin = bil['zemin_std_seviye']
    OA = uygula_tane(I, A, T, t_zemin)
    del T, I
    Image.fromarray(np.clip(np.round(OA), 0, 255).astype(np.uint8)).save(C / 'GOMULU_A.png', dpi=(300, 300))
    OB = gomme(OA, A)
    del OA
    Image.fromarray(np.clip(np.round(OB), 0, 255).astype(np.uint8)).save(C / 'GOMULU_B.png', dpi=(300, 300))
    rap = {'doku': bil, 'T_zemin_seviye': t_zemin, 'T_altin_seviye': T_ALTIN, 'bant_sigma': BANT_SIGMA,
           'isik': 'sol ust', 'kenar_px': KENAR_PX, 'koyu': KOYU, 'acik': ACIK}
    (C / 'GOMULU.json').write_text(json.dumps(rap, indent=1, ensure_ascii=False))
    print(json.dumps(rap, ensure_ascii=False))


if __name__ == '__main__':
    main()
