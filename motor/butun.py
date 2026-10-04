#!/usr/bin/env python3
"""BUTUNLESTIRME katmani (Serdar 4 Eki): ogeler zemine yapistirilmis gibi gorunmesin, poster tek parca tablo gibi.
Tek kural, tek isik yonu: SOL UST. Girdi: doku_poster ciktisi POSTER.png + ALFA.png (tum ogelerin birlesik alfasi).

1 temas golgesi : alfa Gauss bulanik, isigin tersine (sag alt) kaydirilmis; yalniz zemine (1 - alfa), lacivert tona
                  (GOLGE_RENK, siyah degil) dogru karisim.
2 yansima       : altinin zemine sicak pariltisi; dar Gauss (alfa disinda), renk = ogelerin olculen ortalama altini,
                  dusuk opaklik, yalniz zemine.
3 ortak isik    : tum sayfaya ayni yumusak isik egimi (sol ust acik, sag alt koyu, carpimsal +-isik) + ince tane
                  (luma, 0.7 px bulanik Gauss gurultu, sabit tohum). Ogelerin sekli / konumu degismez.
Dozlar DOZ tablosunda; QC: altin dE00 (doz 0'a gore, oge cekirdegi), isim kontrasti, hale genisligi (glow >= 1 seviye).

Kullanim: butun.py --poster POSTER.png --alfa ALFA.png --rapor POSTER.json --cikti DIR [--doz HAFIF ORTA BELIRGIN]
"""
import argparse, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import doku_cila as dc                                               # noqa: E402

Image.MAX_IMAGE_PIXELS = None
LUMA = np.array([0.299, 0.587, 0.114], np.float32)
ISIK = (-1.0, -1.0)                       # isik yonu: sol ust (x, y); golge tersine kayar
GOLGE_RENK = np.array([1.0, 4.0, 18.0], np.float32)   # derin lacivert (zemin kose rengi civari, siyah degil)
TOHUM = 20261004
DOZ = {
    'HAFIF':    {'golge_op': 0.18, 'golge_sigma': 10, 'golge_kayma': 8,  'parilti_op': 0.06, 'parilti_sigma': 6,
                 'tane': 0.8, 'isik': 0.015},
    'ORTA':     {'golge_op': 0.30, 'golge_sigma': 14, 'golge_kayma': 12, 'parilti_op': 0.10, 'parilti_sigma': 8,
                 'tane': 1.3, 'isik': 0.03},
    'BELIRGIN': {'golge_op': 0.45, 'golge_sigma': 18, 'golge_kayma': 16, 'parilti_op': 0.15, 'parilti_sigma': 10,
                 'tane': 2.0, 'isik': 0.05},
}


def kaydir(m, dx, dy):
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(m, M, (m.shape[1], m.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)


def uygula(I, A, d, sicak):
    H, W = A.shape
    ux, uy = -ISIK[0] / np.hypot(*ISIK), -ISIK[1] / np.hypot(*ISIK)
    zem = (1 - A)[..., None]
    # 1 golge
    S = kaydir(cv2.GaussianBlur(A, (0, 0), d['golge_sigma']), ux * d['golge_kayma'], uy * d['golge_kayma'])
    k = (d['golge_op'] * S)[..., None] * zem
    O = I + k * (GOLGE_RENK - I)
    del S, k
    # 2 parilti (yansima)
    G = np.clip(cv2.GaussianBlur(A, (0, 0), d['parilti_sigma']) - A, 0, 1)
    glow = (d['parilti_op'] * G)[..., None] * zem * sicak
    O += glow
    hale = G * d['parilti_op'] * float(sicak @ LUMA)
    del G, glow
    # 3 ortak isik + tane
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    t = ((xx / W) * ux + (yy / H) * uy) / (abs(ux) + abs(uy))          # 0 sol ust .. 1 sag alt (yaklasik)
    O *= (1 + d['isik'] * (0.5 - t) * 2)[..., None]
    del yy, xx, t
    rng = np.random.default_rng(TOHUM)
    n = cv2.GaussianBlur(rng.standard_normal((H, W), dtype=np.float32), (0, 0), 0.7)
    n *= d['tane'] / max(float(n.std()), 1e-6)
    O += n[..., None]
    del n
    return O, hale


def main():
    ap = argparse.ArgumentParser()
    for k in ('poster', 'alfa', 'rapor', 'cikti'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--doz', nargs='+', default=list(DOZ))
    a = ap.parse_args()
    C = Path(a.cikti); C.mkdir(parents=True, exist_ok=True)
    I = np.asarray(Image.open(a.poster).convert('RGB'), np.float32)
    A = np.asarray(Image.open(a.alfa), np.float32) / 255
    kut = json.loads(Path(a.rapor).read_text())['kutu']
    ce = A > 0.95
    sicak = I[ce].mean(0)                                            # ogelerin olculen ortalama altini
    # QC orneklemi: oge cekirdegi (seyrek), isim cekirdegi ve cevresi
    ys, xs = np.nonzero(ce); sec = np.random.default_rng(1).choice(len(ys), min(400000, len(ys)), replace=False)
    ys, xs = ys[sec], xs[sec]
    dist = cv2.distanceTransform((A < 0.01).astype(np.uint8), cv2.DIST_L2, 5)

    def isim_kontrast(O):
        r = []
        for ad in ('isim1', 'isim2', 'tagline'):
            x0, y0, x1, y1 = kut[ad]
            a_ = A[y0:y1, x0:x1]; L = O[y0:y1, x0:x1] @ LUMA; dd = dist[y0:y1, x0:x1]
            ic = L[a_ > 0.95].mean(); dis = L[(dd > 3) & (dd < 40)].mean()
            r.append(round(float((ic + 12.75) / (dis + 12.75)), 2))   # basit kontrast orani (0.05 ofsetli, 0-255)
        return r
    rap = {'isik': 'sol ust', 'sicak_rgb': [round(float(v), 1) for v in sicak], 'doz': {}}
    rap['doz']['0'] = {'isim_kontrast': isim_kontrast(I)}
    lab0 = dc.lab(I[ys, xs][None])[0]
    for ad in a.doz:
        d = DOZ[ad]
        O, hale = uygula(I, A, d, sicak)
        de = dc.de2000_px(dc.lab(np.clip(O[ys, xs], 0, 255)[None])[0], lab0) if hasattr(dc, 'de2000_px') else None
        if de is None:
            de = np.array([dc.de2000(p, q) for p, q in zip(dc.lab(np.clip(O[ys[:20000], xs[:20000]], 0, 255)[None])[0],
                                                          lab0[:20000])])
        hm = (hale >= 1.0) & (A < 0.01)
        rap['doz'][ad] = {'param': d, 'altin_dE00_ort': round(float(np.mean(de)), 2), 'altin_dE00_p95': round(float(np.percentile(de, 95)), 2),
                          'isim_kontrast': isim_kontrast(O),
                          'hale_px_p99': round(float(np.percentile(dist[hm], 99)), 1) if hm.any() else 0.0}
        print(ad, json.dumps(rap['doz'][ad], ensure_ascii=False), flush=True)
        Image.fromarray(np.clip(np.round(O), 0, 255).astype(np.uint8)).save(C / f'BUTUN_{ad}.png', dpi=(300, 300))
        del O, hale
    (C / 'BUTUN.json').write_text(json.dumps(rap, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
