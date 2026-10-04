#!/usr/bin/env python3
"""Canva dokulu sayfalara SON CILA (Serdar 4 Eki): yalniz renk / parlaklik esitleme, hedef ozgun AQUARIUS_ARIES.

1 hizalama : Canva ciktisi girdi sayfasi boyuna (INTER_AREA) indirilir; ECC (affine) ile kalan kayma olculur.
2 doku     : glif basina r (Canva kalinlik farki) + kayma; kenar kenara esleme (asagida); Canva disi kalan Telea ile.
             Alfa her zaman vektor maskeden (sekil Canva'dan alinmaz).
3 olcum    : maske ici pikseller (alfa > 0.5, kenar dahil, referans hucresi haric): Lab ortalama, L* %10 / %50 / %90.
             Hedef: main_aquarius_aries_gold.png (ozgun sembol) x 0.5007 (24x36 baski olcegi), alfa > 0.5.
4 duzeltme : sayfa basina global esleme (olcumle ayni pikseller): L* ton egrisi
             (101 yuzdelik eslemesi, monoton, alt uc sifira dogrusal) + L*'a bagli a*/b* dengesi
             (10 kutu ortalama farki, yumusak). Piksel siralamasi korunur: doku / kabartma / sekil degismez.
5 kabartma : duzeltme SONRASI kenardan ic uzakliga gore L* profili (0-12 px) ve kenar bandi gradyani (1-6 px).
"""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
LUMA = np.array([0.299, 0.587, 0.114], np.float32)
REF_OLCEK = 0.5007          # main symbol asset -> 24x36 baski px (SCORPIO_VIRGO_*_24x36 buyuk_sembol olcek)
NQ = 101
NB = 10


def lab(rgb):
    return cv2.cvtColor(np.clip(rgb, 0, 255).astype(np.float32) / 255, cv2.COLOR_RGB2LAB)


def rgb_(L):
    return cv2.cvtColor(L.astype(np.float32), cv2.COLOR_LAB2RGB) * 255


def de2000(a, b):
    L1, a1, b1 = a; L2, a2, b2 = b
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2); Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dL, dC = L2 - L1, C2p - C1p
    dh = h2p - h1p; dh = dh - 360 if dh > 180 else dh + 360 if dh < -180 else dh
    dH = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2
    hm = (h1p + h2p) / 2 + (180 if abs(h1p - h2p) > 180 else 0)
    T = 1 - 0.17 * np.cos(np.radians(hm - 30)) + 0.24 * np.cos(np.radians(2 * hm)) + 0.32 * np.cos(np.radians(3 * hm + 6)) \
        - 0.20 * np.cos(np.radians(4 * hm - 63))
    Sl = 1 + 0.015 * (Lm - 50) ** 2 / np.sqrt(20 + (Lm - 50) ** 2); Sc = 1 + 0.045 * Cpm; Sh = 1 + 0.015 * Cpm * T
    Rt = -2 * np.sqrt(Cpm ** 7 / (Cpm ** 7 + 25 ** 7)) * np.sin(np.radians(60 * np.exp(-((hm - 275) / 25) ** 2)))
    return float(np.sqrt((dL / Sl) ** 2 + (dC / Sc) ** 2 + (dH / Sh) ** 2 + Rt * (dC / Sc) * (dH / Sh)))


def hizala(girdi_png, girdi_json, canva_jpg):
    j = json.loads(Path(girdi_json).read_text())
    W, H = j['boyut']
    O = np.asarray(Image.open(girdi_png).convert('L'), np.float32) / 255
    x0, y0, x1, y1 = j['referans_kutu']
    O[y0:y1, x0:x1] = 0
    C = np.asarray(Image.open(canva_jpg).convert('RGB'), np.float32)
    cw, ch = C.shape[1], C.shape[0]
    Cd = cv2.resize(C, (W, H), interpolation=cv2.INTER_AREA)
    L = Cd @ LUMA
    Ar = np.clip((L - 20) / 40, 0, 1); Ar[y0:y1, x0:x1] = 0
    wm = np.eye(2, 3, dtype=np.float32)
    cc, wm = cv2.findTransformECC(cv2.GaussianBlur(O, (0, 0), 2), cv2.GaussianBlur(Ar, (0, 0), 2), wm, cv2.MOTION_AFFINE,
                                  (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
    Ca = cv2.warpAffine(Cd, wm, (W, H), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
    # glif / oge basina: Canva sekli bizimkinden kalin (r px, alan farki / cevre) ve hafif kaymis olabilir.
    # kayma: ECC (oteleme) bizim maskenin r kadar genisletilmis hali ile Canva kapsamasi arasinda.
    # doku eslemesi: ic uzaklik d olan piksel, Canva'da kenardan ayni oransal konuma (d -> d + r(1 - d/w)) esler;
    # kenar kenara, orta eksen orta eksene (w = yerel yari kalinlik). Kabartma kenari boylece maskeye girer.
    t = np.zeros_like(Ca); ok = np.zeros((H, W), bool); gl = []
    hucreler = [g['hucre'] for g in j['glifler']] if 'glifler' in j else [o['kutu'] for o in j['ogeler']]
    adlar = [g['karakter'] for g in j['glifler']] if 'glifler' in j else [o['oge'] for o in j['ogeler']]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for ad, (gx0, gy0, gx1, gy1) in zip(adlar, hucreler):
        p = 24
        X0, Y0, X1, Y1 = max(gx0 - p, 0), max(gy0 - p, 0), min(gx1 + p, W), min(gy1 + p, H)
        o = O[Y0:Y1, X0:X1].copy(); Lc = Ca[Y0:Y1, X0:X1] @ LUMA
        ic_c = Lc[Lc > 60]
        c = (Lc > 0.5 * float(np.median(ic_c))).astype(np.float32) if ic_c.size else np.zeros_like(Lc)   # Canva yari parlaklik siniri
        m = (o > 0.5).astype(np.uint8)
        if m.sum() == 0:
            continue
        cevre = max(float(cv2.Canny(m * 255, 50, 150).sum() / 255), 1.0)
        r = float(np.clip((c.sum() - o.sum()) / cevre, -6, 12))      # < 0: Canva bizimkinden ince
        sd = cv2.distanceTransform(m, cv2.DIST_L2, 5) - cv2.distanceTransform(1 - m, cv2.DIST_L2, 5)
        od = np.clip(sd + r + 0.5, 0, 1)
        w2 = np.eye(2, 3, dtype=np.float32)
        try:
            _, w2 = cv2.findTransformECC(cv2.GaussianBlur(od.astype(np.float32), (0, 0), 1.5),
                                         cv2.GaussianBlur(c.astype(np.float32), (0, 0), 1.5), w2, cv2.MOTION_TRANSLATION,
                                         (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-5), None, 3)
        except cv2.error:
            pass
        sdb = cv2.GaussianBlur(sd, (0, 0), 1.5)
        gx = cv2.Sobel(sdb, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(sdb, cv2.CV_32F, 0, 1, ksize=3)
        gn = np.maximum(np.hypot(gx, gy), 1e-3); nx, ny = -gx / gn, -gy / gn          # disa normal
        d = np.clip(sd, 0, None)
        wl = cv2.dilate(d, np.ones((41, 41), np.uint8))                               # yerel yari kalinlik
        k = r * np.clip(1 - d / np.maximum(wl, 1), 0, 1)
        mx = xx[Y0:Y1, X0:X1] + w2[0, 2] + k * nx; my = yy[Y0:Y1, X0:X1] + w2[1, 2] + k * ny
        tt = cv2.remap(Ca, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        sel = o > 0
        t[Y0:Y1, X0:X1][sel] = tt[sel]
        ok[Y0:Y1, X0:X1] |= sel & ((tt @ LUMA) > 12)
        gl.append({'ad': ad, 'r_px': round(r, 2), 'kayma_px': [round(float(w2[0, 2]), 2), round(float(w2[1, 2]), 2)]})
    gerek = cv2.dilate((O > 0).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool) & ~ok
    t = cv2.inpaint(np.clip(np.round(t), 0, 255).astype(np.uint8), gerek.astype(np.uint8), 5, cv2.INPAINT_TELEA)
    ic = O > 0.5
    ic[y0:y1, x0:x1] = False
    olc = {'canva_boyut': [cw, ch], 'girdi_boyut': [W, H], 'olcek': [round(cw / W, 4), round(ch / H, 4)],
           'ecc_cc': round(float(cc), 4), 'ek_olcek': [round(float(np.hypot(wm[0, 0], wm[1, 0])), 5),
                                                     round(float(np.hypot(wm[0, 1], wm[1, 1])), 5)],
           'kayma_px': [round(float(wm[0, 2]), 2), round(float(wm[1, 2]), 2)],
           'donme_der': round(float(np.degrees(np.arctan2(wm[1, 0], wm[0, 0]))), 4),
           'dolgu_orani': round(float((gerek & (O > 0.5)).sum() / max((O > 0.5).sum(), 1)), 4), 'glif': gl}
    return t.astype(np.float32), O, ic, olc


def referans(asset_png):
    im = cv2.imread(str(asset_png), cv2.IMREAD_UNCHANGED)[..., [2, 1, 0, 3]].astype(np.float32)
    im = cv2.resize(im, None, fx=REF_OLCEK, fy=REF_OLCEK, interpolation=cv2.INTER_AREA)
    A = im[..., 3] / 255
    return im[..., :3], A, A > 0.5


def dagilim(rgb, ic):
    P = lab(rgb)[ic]
    return {'lab_ort': P.mean(0).round(2).tolist(), 'L_p10_50_90': np.percentile(P[:, 0], [10, 50, 90]).round(2).tolist(),
            'a_p10_50_90': np.percentile(P[:, 1], [10, 50, 90]).round(2).tolist(),
            'b_p10_50_90': np.percentile(P[:, 2], [10, 50, 90]).round(2).tolist()}


def esleme_olc(rgb, ic, ref_rgb, ref_ic):
    """-> {'Lx', 'Ly' (ton egrisi dugumleri), 'bins', 'da', 'db'}"""
    P, R = lab(rgb)[ic], lab(ref_rgb)[ref_ic]
    q = np.linspace(0.5, 99.5, NQ)
    Lx, Ly = np.percentile(P[:, 0], q), np.percentile(R[:, 0], q)
    Lx = np.maximum.accumulate(Lx + np.arange(NQ) * 1e-4)                # kesin artan
    Ly = np.maximum.accumulate(Ly)
    Ly = np.convolve(np.pad(Ly, 3, mode='edge'), np.ones(7) / 7, 'valid')  # yumusak, monoton kalir
    Lm = np.interp(P[:, 0], Lx, Ly)
    kenar = np.percentile(R[:, 0], np.linspace(0, 100, NB + 1))
    bi = np.clip(np.searchsorted(kenar, Lm) - 1, 0, NB - 1); br = np.clip(np.searchsorted(kenar, R[:, 0]) - 1, 0, NB - 1)
    da = np.array([R[br == k, 1].mean() - P[bi == k, 1].mean() if (bi == k).sum() > 50 else np.nan for k in range(NB)])
    db = np.array([R[br == k, 2].mean() - P[bi == k, 2].mean() if (bi == k).sum() > 50 else np.nan for k in range(NB)])
    for v in (da, db):
        g = ~np.isnan(v); v[~g] = np.interp(np.nonzero(~g)[0], np.nonzero(g)[0], v[g]) if g.any() else 0
    sm = lambda v: np.convolve(np.pad(v, 1, mode='edge'), [0.25, 0.5, 0.25], 'valid')
    merk = (kenar[:-1] + kenar[1:]) / 2
    return {'Lx': Lx.round(3).tolist(), 'Ly': Ly.round(3).tolist(), 'merkez': merk.round(3).tolist(),
            'da': sm(da).round(3).tolist(), 'db': sm(db).round(3).tolist()}


def esleme_uygula(rgb, E):
    P = lab(rgb)
    Lm = np.interp(P[..., 0], E['Lx'], E['Ly'], left=None, right=None)
    # uclarda dogrusal uzatma (kenar bronzu / en parlak vurgu kesilmesin)
    Lx, Ly = np.asarray(E['Lx']), np.asarray(E['Ly'])
    s1 = (Ly[-1] - Ly[-4]) / max(Lx[-1] - Lx[-4], 1e-3)
    Lm = np.where(P[..., 0] < Lx[0], P[..., 0] * Ly[0] / max(Lx[0], 1e-3), Lm)     # alt uc: sifira dogrusal
    Lm = np.where(P[..., 0] > Lx[-1], Ly[-1] + (P[..., 0] - Lx[-1]) * s1, Lm)
    Lm = np.clip(Lm, 0, 100)
    # renk dengesi koyu kenar / zemin tasmasi piksellerinde sonumlenir (L* < 10: 0, L* > 35: tam) -> renkli sacak yok;
    # o piksellerde kroma, L* oraninda olceklenir (ton ayni kalir)
    wd = np.clip((P[..., 0] - 10) / 25, 0, 1)
    ko = np.where(P[..., 0] > 1, Lm / np.maximum(P[..., 0], 1), 1)
    a = P[..., 1] * (wd + (1 - wd) * np.clip(ko, 0, 1.5)) + wd * np.interp(Lm, E['merkez'], E['da'])
    b = P[..., 2] * (wd + (1 - wd) * np.clip(ko, 0, 1.5)) + wd * np.interp(Lm, E['merkez'], E['db'])
    return np.clip(rgb_(np.stack([Lm, a, b], -1)), 0, 255)


def kabartma(rgb, A, ic_disi=None):
    """kenardan ic uzaklik d (px) icin L* ortancasi (0..11) + kenar bandi (1-6 px) gradyan ortancasi + ince detay."""
    m = (A > 0.5).astype(np.uint8)
    if ic_disi is not None:
        m[ic_disi] = 0
    d = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    L = lab(rgb)[..., 0]
    prof = [float(np.median(L[(d >= i) & (d < i + 1)])) for i in range(12)]
    g = np.hypot(cv2.Sobel(L, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(L, cv2.CV_32F, 0, 1, ksize=3)) / 8
    band = (d >= 1) & (d < 6); ic = d >= 3
    return {'profil': np.round(prof, 2).tolist(), 'kenar_grad': round(float(np.median(g[band])), 3),
            'ic_grad': round(float(np.median(g[ic])), 3),
            'ince_std': round(float((L - cv2.GaussianBlur(L, (0, 0), 1))[ic].std()), 3)}
