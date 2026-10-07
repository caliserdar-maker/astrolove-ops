#!/usr/bin/env python3
"""HEDEF GORUNUM OLCUMU (Serdar 7 Eki, ChatGPT referansi): REF (2000x3000) ve poster(ler) AYNI olcekte (2000x3000) ve
AYNI maskeyle olculur. Maske: posterin OGE_MASKE.npz cekirdekleri (7200x10800) sayfaya yerlestirilip alan ortalamasiyla
2000x3000'e indirilir, > 0.99 = 2000 olcekli cekirdek (yerlesim kaymasi 0; koordinator olcumu).

Oge basina: cekirdek L yuzdelikleri (1-99, 25), medyan Lab, doku (L yerel std 5x5, 2000 olcekte, cekirdek medyani),
kirmizimsi oran (a* > 25), metinde parca (harf) farklari. Zemin: arka_kapi geometrisi (24x36 halka merkezi, 4:5 elips),
oge + golge payi + yildiz disi pikseller; s = elips yaricapi / kose, %0.5'lik halkalarda kanal ortalamasi. Cember: her
1 derecede yaricap boyunca 0.1 px adimla luma fazlasi (yerel zemine gore); tepe ve genislik (alan / tepe).

Kullanim: ref_olc.py --ref REF.png --poster P.png [--poster P2.png ...] --dizin DIR --json OUT
"""
import argparse, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from skimage.color import rgb2lab, deltaE_ciede2000

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import doku_poster as dp                                             # noqa: E402

Image.MAX_IMAGE_PIXELS = None
W2, H2 = 2000, 3000
Q = np.linspace(1, 99, 25)
METIN = ('isim1', 'isim2', 'tagline')
KIRMIZI_A = 25.0
GOLGE_PAY = 300          # 7200 olcekte (arka_kapi ile ayni)
LUMA = np.array([0.299, 0.587, 0.114], np.float32)


def kucult(I):
    """7200x10800 (veya baska 2:3) -> 2000x3000, float alan ortalamasi."""
    I = np.asarray(I, np.float32)
    return I if I.shape[1] == W2 else cv2.resize(I, (W2, H2), interpolation=cv2.INTER_AREA)


def maskeler(dizin):
    Z = np.load(Path(dizin) / 'OGE_MASKE.npz')
    M = {}
    for ad in Z.files:
        v = Z[ad]; x0, y0, h, w = (int(q) for q in v[:4])
        m = np.unpackbits(v[4:].astype(np.uint8))[:h * w].reshape(h, w)
        T = np.zeros((10800, 7200), np.float32); T[y0:y0 + h, x0:x0 + w] = m
        M[ad] = kucult(T) > 0.99
    A = np.asarray(Image.open(Path(dizin) / 'ALFA.png'), np.float32) / 255
    return M, kucult(A)


def parca(Lc, m):
    n, pl = cv2.connectedComponents(cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)))
    pl = pl * m; P = []
    for i in range(1, n):
        c = pl == i
        if c.sum() < 25:
            continue
        md = np.median(Lc[c], 0); P.append((md[0], md[2], np.degrees(np.arctan2(md[2], md[1]))))
    P = np.array(P)
    return {'parca_n': len(P), 'parca_L_fark': round(float(np.ptp(P[:, 0])), 2),
            'parca_b_fark': round(float(np.ptp(P[:, 1])), 2), 'parca_ton_fark': round(float(np.ptp(P[:, 2])), 2)}


def zemin(I, A):
    """radyal profil (s %0.5 halkalari, kanal ortalamasi) + yuksek geciren std (halka)."""
    h24 = dp.halka_geo(dp.HALKA24); kose = 3745.65 * h24[2] / dp.halka_geo(dp.HALKA16)[2]
    s = W2 / 7200
    k = max(3, int(round(2 * GOLGE_PAY * s)) | 1)
    zem = cv2.dilate((A > 0.005).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))) == 0
    L = I @ LUMA
    zem &= L < 40
    zem &= (L - cv2.medianBlur(np.clip(L, 0, 255).astype(np.uint8), 15)) < 3      # yildiz disi
    yy, xx = np.nonzero(zem)
    r = np.hypot(xx - h24[0] * s, (yy - h24[1] * s) / 1.25) / (kose * s)
    b = np.clip((r * 200).astype(int), 0, 200)
    n = np.bincount(b, minlength=201)
    prof = [np.bincount(b, I[yy, xx, c], 201) / np.maximum(n, 1) for c in range(3)]
    ort = [round(float(I[yy, xx, c].mean()), 2) for c in range(3)]
    Lz = np.where(zem, L, np.nan)
    return {'ort_rgb': ort, 'profil_n': n.tolist(), 'profil': [[round(float(v), 3) for v in p] for p in prof]}


def cember(I, A):
    cx, cy, R = (v * W2 / 7200 for v in dp.halka_geo(dp.HALKA24))
    L = cv2.GaussianBlur(I @ LUMA, (0, 0), 0.5)
    d = np.arange(-12, 12.01, 0.1)
    out = []
    for t in range(0, 360):
        th = np.radians(t)
        xs = cx + (R + d) * np.cos(th); ys = cy + (R + d) * np.sin(th)
        if xs.min() < 1 or ys.min() < 1 or xs.max() > W2 - 2 or ys.max() > H2 - 2:
            out.append(None); continue
        v = cv2.remap(L, xs[None].astype(np.float32), ys[None].astype(np.float32), cv2.INTER_LINEAR)[0]
        bg = np.median(np.r_[v[:20], v[-20:]])
        e = np.maximum(v - bg, 0)
        tp = float(e.max())
        out.append(None if tp < 2 else {'tepe': round(tp, 2), 'genislik': round(float(e.sum() * 0.1 / tp), 3),
                                        'merkez': round(float((e * d).sum() / e.sum()), 3)})
    return out


def olc(f, M, A):
    I = kucult(np.asarray(Image.open(f).convert('RGB')))
    Lab = rgb2lab(np.clip(I, 0, 255) / 255).astype(np.float32)
    Lk = Lab[..., 0]
    mu = cv2.blur(Lk, (5, 5)); sd = np.sqrt(np.maximum(cv2.blur(Lk * Lk, (5, 5)) - mu * mu, 0))
    mu3 = cv2.blur(Lk, (3, 3)); sd3 = np.sqrt(np.maximum(cv2.blur(Lk * Lk, (3, 3)) - mu3 * mu3, 0))
    T = {}
    for ad, m in M.items():
        t = {'px': int(m.sum()), 'Lab': [round(float(v), 2) for v in np.median(Lab[m], 0)],
             'L_q': [round(float(v), 2) for v in np.percentile(Lk[m], Q)],
             'a_q': [round(float(v), 2) for v in np.percentile(Lab[..., 1][m], Q)],
             'b_q': [round(float(v), 2) for v in np.percentile(Lab[..., 2][m], Q)],
             'doku_std5': round(float(np.median(sd[m])), 3),
             # ic doku (7 Eki): 3x3 pencere tamamen cekirdek icinde (cekirdek 3x3 asindirilmis), kenar golgesi disi
             'doku_ic3': round(float(np.median(sd3[cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0])), 3),
             'kirmizi_yuzde': round(100 * float((Lab[..., 1][m] > KIRMIZI_A).mean()), 3)}
        if ad in METIN:
            t.update(parca(Lab, m))
        T[ad] = t
    return {'ogeler': T, 'zemin': zemin(I, A), 'cember': cember(I, A)}


def de(a, b):
    return round(float(deltaE_ciede2000(np.array(a, np.float64), np.array(b, np.float64))), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ref', required=True); ap.add_argument('--poster', action='append', default=[])
    ap.add_argument('--dizin', required=True); ap.add_argument('--json', required=True)
    a = ap.parse_args()
    M, A = maskeler(a.dizin)
    R = {'REF': olc(a.ref, M, A)}
    for f in a.poster:
        R[Path(f).parent.name + '/' + Path(f).name] = olc(f, M, A)
    ref = R['REF']['ogeler']
    for k, r in R.items():
        O = r['ogeler']
        for ad, t in O.items():
            t['dE00_ref'] = de(t['Lab'], ref[ad]['Lab'])
            t['dE00_oge_max'] = max(de(t['Lab'], u['Lab']) for u in O.values())
        print(k, 'zemin ort', r['zemin']['ort_rgb'])
        for ad, t in O.items():
            print(f"  {ad:11s} Lab {t['Lab']} L p5/50/95/99 {t['L_q'][1]:.1f}/{t['L_q'][12]:.1f}/{t['L_q'][23]:.1f}/"
                  f"{t['L_q'][24]:.1f} doku {t['doku_std5']:.2f} kirmizi {t['kirmizi_yuzde']:.2f} dE_ref {t['dE00_ref']:.2f}"
                  f" dE_max {t['dE00_oge_max']:.2f}" + (f" parca {t['parca_L_fark']}/{t['parca_b_fark']}/{t['parca_ton_fark']}"
                                                        if 'parca_n' in t else ''))
        c = [v for v in r['cember'] if v]
        print('  cember n', len(c), 'genislik med', np.median([v['genislik'] for v in c]), 'tepe med',
              np.median([v['tepe'] for v in c]))
    Path(a.json).write_text(json.dumps(R, ensure_ascii=False))


if __name__ == '__main__':
    main()
