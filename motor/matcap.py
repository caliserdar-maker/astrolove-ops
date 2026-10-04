#!/usr/bin/env python3
"""MATCAP (Serdar 4 Eki, EMILY turu 3): ana sembolun malzeme haritasi; parametrik golge YOK.

1) Ana sembol maskesi (kapsama RENK doygunlugundan, kenar_tepki.kapsama) -> yukseklik haritasi: kenardan ic uzaklik d
   (alt piksel, isaretli uzaklik) MUTLAK px pah genisligi w ile h = profil(clip(d / w, 0, 1)); sirt yumusatma
   (Gauss YUMUSAK px) -> normal n = (-dh/dx, -dh/dy, 1) / |.|.
2) Matcap tablosu: (nx, ny) birim diskinde IZGARA x IZGARA hucre; her hucre = ana sembolun o normaldeki GERCEK
   piksellerinin ortanca rengi (bos hucre: en yakin dolu hucre).
3) Uygulama: hedef maskeden ayni w, ayni profil -> normal -> matcap rengi (bilineer). Tane: doku aktariminin ince detayi.
4) Oz test: matcap ana sembolun kendi maskesine uygulanir, orijinal ana sembolle fark olculur (w ve profil bu farki en
   kucuk yapan degerlerden secilir).
"""
import json, sys
from pathlib import Path

import cv2
import numpy as np

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import tek_doku as tdk                                               # noqa: E402
from kenar_tepki import kapsama                                      # noqa: E402

LUMA = tdk.LUMA
IZGARA = 33
PROFIL = {
    'dogrusal': lambda x: x,
    'yuvarlak': lambda x: np.sqrt(np.clip(1 - (1 - x) ** 2, 0, 1)),
    'kosinus': lambda x: 0.5 - 0.5 * np.cos(np.pi * x),
}


def normaller(A, w, profil, yumusak=1.0):
    m = (A > 0.5).astype(np.uint8)
    sd = cv2.distanceTransform(m, cv2.DIST_L2, 5) - cv2.distanceTransform(1 - m, cv2.DIST_L2, 5)
    sd = cv2.GaussianBlur(sd, (0, 0), 0.7) + 0.5
    h = PROFIL[profil](np.clip(sd / w, 0, 1)).astype(np.float32) * w      # yukseklik px biriminde (egim acisi olcekten bagimsiz)
    if yumusak > 0:
        h = cv2.GaussianBlur(h, (0, 0), yumusak)                         # sirt / kesisim kirisini yumusat (M capraz dikisi)
    gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3) / 8; gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3) / 8
    nz = 1 / np.sqrt(1 + gx ** 2 + gy ** 2)
    return -gx * nz, -gy * nz


def _hucre(nx, ny):
    return (np.clip(((nx + 1) / 2 * (IZGARA - 1)).round(), 0, IZGARA - 1).astype(int),
            np.clip(((ny + 1) / 2 * (IZGARA - 1)).round(), 0, IZGARA - 1).astype(int))


def matcap_olc(rgb, A, w, profil, yumusak=1.0):
    nx, ny = normaller(A, w, profil, yumusak)
    ok = A >= 0.95
    ix, iy = _hucre(nx[ok], ny[ok])
    k = iy * IZGARA + ix
    C = np.full((IZGARA * IZGARA, 3), np.nan, np.float32)
    say = np.bincount(k, minlength=IZGARA * IZGARA)
    src = rgb[ok]
    order = np.argsort(k)
    ks, ss = k[order], src[order]
    sinir = np.r_[0, np.cumsum(say)]
    for c in np.nonzero(say >= 5)[0]:
        C[c] = np.median(ss[sinir[c]:sinir[c + 1]], 0)
    dolu = ~np.isnan(C[:, 0])
    yy, xx = np.divmod(np.arange(IZGARA * IZGARA), IZGARA)
    dy, dx = yy[dolu], xx[dolu]
    for c in np.nonzero(~dolu)[0]:
        j = np.argmin((dy - yy[c]) ** 2 + (dx - xx[c]) ** 2)
        C[c] = C[np.nonzero(dolu)[0][j]]
    return C.reshape(IZGARA, IZGARA, 3)


def matcap_uygula(A, mc, w, profil, yumusak=1.0, tane=None):
    nx, ny = normaller(A, w, profil, yumusak)
    fx = (nx + 1) / 2 * (IZGARA - 1); fy = (ny + 1) / 2 * (IZGARA - 1)
    out = np.stack([cv2.remap(np.ascontiguousarray(mc[..., c]), fx.astype(np.float32), fy.astype(np.float32),
                              cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE) for c in range(3)], -1)
    if tane is not None:
        out = out + (tane - cv2.GaussianBlur(tane, (0, 0), 1.2))
    return np.clip(out, 0, 255)


def oz_test(rgb, A, w, profil, yumusak=1.0):
    """matcap kendi maskesine: tam kapsama (A >= 0.95) piksellerinde ortalama |dL|, dE76 ortanca, luma R^2."""
    mc = matcap_olc(rgb, A, w, profil, yumusak)
    yeni = matcap_uygula(A, mc, w, profil, yumusak)
    ok = A >= 0.95
    L0, L1 = rgb[ok] @ LUMA, yeni[ok] @ LUMA
    lab = lambda x: cv2.cvtColor(np.clip(x, 0, 255).astype(np.float32)[None] / 255, cv2.COLOR_RGB2LAB)[0]
    dE = np.linalg.norm(lab(rgb[ok]) - lab(yeni[ok]), axis=1)
    r2 = 1 - ((L0 - L1) ** 2).sum() / ((L0 - L0.mean()) ** 2).sum()
    return {'w': w, 'profil': profil, 'yumusak': yumusak, 'dL_ort': round(float(np.abs(L0 - L1).mean()), 2),
            'dE_ortanca': round(float(np.median(dE)), 2), 'dE_p90': round(float(np.percentile(dE, 90)), 2),
            'R2_luma': round(float(r2), 3)}, mc, yeni
