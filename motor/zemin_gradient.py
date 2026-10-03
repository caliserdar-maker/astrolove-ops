#!/usr/bin/env python3
"""Gece mavisi (MB) zemin: PURUZSUZ RADYAL GRADIENT + plate yildiz katmani (Serdar 3 Eki ek talimati).

Olcum (bir kez, halkasiz plate'ten; yildiz ve cember disi zemin pikselleri):
  merkez  : cemberin merkezi (halka_altin geometrisi; posterin gorsel merkezi)
  bicim   : 4:5 elips (s = hypot(dx, dy / 1.25) / kose) - olculen: cember merkezinde elips rmse 1.24 luma, daire 1.40
  egri    : s'nin %0.5'lik halkalarinda kanal ortalamalari -> izotonik regresyon (G, B disa dogru artmayan; R olculen
            hafif artis, azalmayan) -> Gauss yumusatma (6 halka) -> 201 dugum, dogrusal ara deger (float, 16 bit)
Yildiz katmani: plate'te yerel 31 px medyandan > YILDIZ_CEKIRDEK luma, tepe >= YILDIZ_TEPE_MIN, parlak cekirdegi
  (> tdk.YILDIZ_T) <= tdk.YILDIZ_ALAN bilesenler; her yildiz yaricap max(tdk.UZANIM x cekirdek, 2.5 x bilesen) + 16 px diskte (kosinus kenar) plate - yerel kanal medyani
  (91 px) - GURULTU (pozitif kisim). Isinlar ve hale korunur, plate lekesi tasinmaz.
Render (motor): zemin = egri(s) + yildiz katmani (yazi kutusu + pay icindeki yildizlar atilir); 8 bite TPDF dither
  (+-1 LSB, sabit tohum), yalniz zemine (1 - alfa).

Kullanim: zemin_gradient.py --plate motor/varlik/plates/BLUE_16x20_halkasiz.png --cikti motor/varlik/plates
"""
import argparse, hashlib, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import tek_doku as tdk                                               # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ELIPS = 1.25              # dikey / yatay (4:5)
DUGUM = 201
YILDIZ_CEKIRDEK = 6.0     # luma; yerel medyandan (yildiz cekirdegi adayi)
YILDIZ_TEPE_MIN = 10.0    # luma; plate leke dokusu tepesi < 10 (olculen gurultu p99 3)
GURULTU = 1.5             # luma; yildiz diskinde plate dokusu tabani (cikarilir)
TOHUM = 20261003


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def s_harita(H, W, g):
    cx, cy = g['merkez']
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    return (np.hypot(xx - cx, (yy - cy) / g['elips']) / g['kose']).astype(np.float32)


def gradient(H, W, g):
    s = s_harita(H, W, g)
    x = np.linspace(0, 1, len(g['egri'][0]))
    return np.stack([np.interp(s, x, np.asarray(g['egri'][c], np.float32)) for c in range(3)], -1).astype(np.float32)


def yildizlar(P):
    """plate yildizlari: [(cx, cy, r_disk, r_cekirdek)] + katman (float, H x W x 3)."""
    H, W = P.shape[:2]
    q = W / 4800
    L = P @ tdk.LUMA
    R = L - tdk.yerel_medyan(L, W)
    n, lab, st, cen = cv2.connectedComponentsWithStats((R > YILDIZ_CEKIRDEK).astype(np.uint8), 8)
    tepe = np.zeros(n, np.float32)
    np.maximum.at(tepe, lab.ravel(), R.ravel())
    kw = int(round(91 * q)) | 1
    u = np.clip(P, 0, 255).astype(np.uint8)
    med = np.stack([cv2.medianBlur(np.ascontiguousarray(u[..., c]), kw) for c in range(3)], -1).astype(np.float32)
    kat = np.zeros_like(P)
    ag = np.zeros((H, W), np.float32)
    F = max(4, int(round(8 * q)))
    liste = []
    cek = np.bincount(lab.ravel(), (R > tdk.YILDIZ_T).ravel(), n)       # parlak cekirdek alani (R > 15)
    for i in range(1, n):
        a = st[i, cv2.CC_STAT_AREA]
        if cek[i] > tdk.YILDIZ_ALAN * q ** 2 or tepe[i] < YILDIZ_TEPE_MIN:
            continue
        if cek[i] == 0 and a > tdk.YILDIZ_ALAN * q ** 2:
            continue
        cx, cy = cen[i]
        r0 = float(np.sqrt(max(cek[i], 1) / np.pi))
        rs = max(tdk.UZANIM * r0, 2.5 * np.sqrt(min(a, tdk.YILDIZ_ALAN * q ** 2) / np.pi)) + 16 * q
        h = int(np.ceil(rs)) + F
        x0, y0 = max(0, int(cx) - h), max(0, int(cy) - h)
        x1, y1 = min(W, int(cx) + h + 1), min(H, int(cy) + h + 1)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        d = np.hypot(xx - cx, yy - cy)
        w = np.clip((rs + F - d) / F, 0, 1)
        w = 0.5 - 0.5 * np.cos(np.pi * w)
        ag[y0:y1, x0:x1] = np.maximum(ag[y0:y1, x0:x1], w)
        liste.append([round(float(cx), 1), round(float(cy), 1), round(float(rs + F), 1), round(r0, 2)])
    kat = np.clip(P - med - GURULTU, 0, None) * ag[..., None]
    return liste, kat.astype(np.float32)


def pav(y, w, artan):
    """izotonik regresyon (pool adjacent violators), agirlikli."""
    y = np.asarray(y, np.float64) * (1 if artan else -1)
    blok = []
    for v, ww in zip(y, w):
        blok.append([v * ww, ww, 1])
        while len(blok) > 1 and blok[-2][0] / blok[-2][1] > blok[-1][0] / blok[-1][1]:
            a, b = blok.pop(), blok.pop()
            blok.append([a[0] + b[0], a[1] + b[1], a[2] + b[2]])
    out = np.concatenate([[b[0] / b[1]] * b[2] for b in blok])
    return out * (1 if artan else -1)


def dither(H, W):
    rng = np.random.default_rng(TOHUM)
    return (rng.random((H, W, 1), np.float32) + rng.random((H, W, 1), np.float32) - 1.0)   # TPDF +-1 LSB, kanallar ortak


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plate', required=True, help='halkasiz plate')
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    pf = Path(a.plate)
    P = np.asarray(Image.open(pf).convert('RGB'), np.float32)
    H, W = P.shape[:2]
    kay = json.loads(pf.with_suffix('.json').read_text())
    if sha(pf) != kay['halkasiz_zemin']['sha256']:
        sys.exit('FAIL: halkasiz plate sha')
    geo = kay['halka']['geometri']
    cx, cy = geo['merkez']
    kose = max(float(np.hypot(x - cx, (y - cy) / ELIPS)) for x in (0, W - 1) for y in (0, H - 1))
    g = {'merkez': [cx, cy], 'elips': ELIPS, 'kose': round(kose, 2)}
    liste, kat = yildizlar(P)
    L = P @ tdk.LUMA
    R = L - tdk.yerel_medyan(L, W)
    yil = cv2.dilate((R > YILDIZ_CEKIRDEK).astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool) | \
        (kat.max(2) > 0)
    al = np.asarray(Image.open(KOK.parent / kay['halka']['dosya'])) > 0
    zem = ~yil & ~cv2.dilate(al.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
    s = s_harita(H, W, g)
    nb = 200
    b = np.clip((s * nb).astype(int), 0, nb - 1)[zem]
    say = np.bincount(b, minlength=nb).astype(np.float64)
    egri = []
    for c in range(3):
        m = np.bincount(b, P[..., c][zem], nb) / np.maximum(say, 1)
        ok = say > 200
        m = pav(m[ok], say[ok], artan=(c == 0))                        # R azalmayan, G B artmayan (izotonik)
        m = np.interp(np.arange(nb), np.nonzero(ok)[0], m)
        m = np.pad(m, 24, mode='edge')
        m = cv2.GaussianBlur(m.astype(np.float32)[None], (0, 0), 6.0)[0][24:-24]   # monoton girdi -> monoton cikti
        x = (np.arange(nb) + 0.5) / nb
        egri.append([round(float(v), 4) for v in np.interp(np.linspace(0, 1, DUGUM), x, m)])
    g['egri'] = egri
    Gr = gradient(H, W, g)
    res = (P @ tdk.LUMA - Gr @ tdk.LUMA)[zem]
    C = Path(a.cikti)
    kf = C / f"{pf.stem.replace('_halkasiz', '')}_yildiz.png"
    Image.fromarray(np.clip(np.round(kat), 0, 255).astype(np.uint8)).save(kf)
    R_ = {'kaynak': {'dosya': str(pf), 'sha256': sha(pf)}, 'gradient': g,
          'yildiz': {'dosya': str(kf), 'sha256': sha(kf), 'sayi': len(liste), 'liste': liste,
                     'esik': {'cekirdek': YILDIZ_CEKIRDEK, 'tepe_min': YILDIZ_TEPE_MIN, 'gurultu': GURULTU}},
          'olcum': {'merkez_rgb': [round(v[0], 2) for v in egri], 'kose_rgb': [round(v[-1], 2) for v in egri],
                    'plate_kalan_luma_std': round(float(res.std()), 3),
                    'plate_kalan_luma_p1_p99': [round(float(np.percentile(res, 1)), 2),
                                                round(float(np.percentile(res, 99)), 2)]},
          'dither': {'tur': 'TPDF +-1 LSB', 'tohum': TOHUM}}
    jf = C / f"{pf.stem.replace('_halkasiz', '')}_gradient.json"
    jf.write_text(json.dumps(R_, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in R_.items() if k != 'yildiz'} | {'yildiz_sayi': len(liste)}, ensure_ascii=False)[:1500])


if __name__ == '__main__':
    main()
