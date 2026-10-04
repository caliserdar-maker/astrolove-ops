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


# ---- IKI KATMAN (Serdar 4 Eki): parilti dolgusu + pah matcap'i -------------------------------------------------
def parilti(rgb, A, sigma):
    """genis olcekli altin dolgu: maskeli (A >= 0.95) normalize Gauss; maske disina (kutu) dikissiz genisletme
    (artan sigma ile normalize konvolusyon, ic piksel degismez)."""
    ok = (A >= 0.95).astype(np.float32)
    F = np.zeros_like(rgb)
    den = cv2.GaussianBlur(ok, (0, 0), sigma)
    for c in range(3):
        F[..., c] = cv2.GaussianBlur(rgb[..., c] * ok, (0, 0), sigma) / np.maximum(den, 1e-6)
    dolu = den > 1e-3
    s2 = sigma
    while not dolu.all() and s2 < 4 * max(rgb.shape[:2]):
        s2 *= 2
        d2 = cv2.GaussianBlur(ok, (0, 0), s2)
        for c in range(3):
            g = cv2.GaussianBlur(rgb[..., c] * ok, (0, 0), s2) / np.maximum(d2, 1e-6)
            F[..., c] = np.where(dolu, F[..., c], g)
        dolu |= d2 > 1e-3
    return F


def iki_katman_olc(rgb, A, sigma, w, profil, yumusak=1.0):
    F = parilti(rgb, A, sigma)
    R = rgb - F + 128.0                                                # artik (kenar etkisi), 128 kaydirmali
    mc = matcap_olc(R, A, w, profil, yumusak)
    return F, mc


def iki_katman_uygula(A, F, mc, w, profil, yumusak=1.0, tane=None):
    return np.clip(F + matcap_uygula(A, mc, w, profil, yumusak, tane=tane) - 128.0, 0, 255)


def oz_test_iki(rgb, A, sigma, w, profil, yumusak=1.0):
    F, mc = iki_katman_olc(rgb, A, sigma, w, profil, yumusak)
    yeni = iki_katman_uygula(A, F, mc, w, profil, yumusak)
    ok = A >= 0.95
    L0, L1 = rgb[ok] @ LUMA, yeni[ok] @ LUMA
    lab = lambda x: cv2.cvtColor(np.clip(x, 0, 255).astype(np.float32)[None] / 255, cv2.COLOR_RGB2LAB)[0]
    dE = np.linalg.norm(lab(rgb[ok]) - lab(yeni[ok]), axis=1)
    r2 = 1 - ((L0 - L1) ** 2).sum() / ((L0 - L0.mean()) ** 2).sum()
    return {'sigma': sigma, 'w': w, 'profil': profil, 'R2_luma': round(float(r2), 3),
            'dE_ortanca': round(float(np.median(dE)), 2), 'dE_p90': round(float(np.percentile(dE, 90)), 2)}, F, mc, yeni


# ---- pah katmani v2: (kenardan mutlak uzaklik d, disa normal acisi) tablosu, artik renk (ana sembol pikselleri) ------
D_ADIM, D_MAX, A_SAY = 0.5, 24.0, 36


def dt_alan(A):
    m = (A > 0.5).astype(np.uint8)
    sd = cv2.distanceTransform(m, cv2.DIST_L2, 5) - cv2.distanceTransform(1 - m, cv2.DIST_L2, 5)
    sd = cv2.GaussianBlur(sd, (0, 0), 0.7) + 0.5
    s2 = cv2.GaussianBlur(sd, (0, 0), 1.5)
    gx = cv2.Sobel(s2, cv2.CV_32F, 1, 0, ksize=5); gy = cv2.Sobel(s2, cv2.CV_32F, 0, 1, ksize=5)
    return np.clip(sd, 0, None), np.degrees(np.arctan2(-gy, -gx))


def dtab_olc(R, A):
    d, th = dt_alan(A)
    ok = (A >= 0.95) & (d < D_MAX)
    nd = int(D_MAX / D_ADIM)
    di = np.clip((d / D_ADIM).astype(int), 0, nd - 1); ai = ((th + 180) / (360 / A_SAY)).astype(int) % A_SAY
    k = (di * A_SAY + ai)[ok]
    T = np.full((nd * A_SAY, 3), np.nan, np.float32)
    say = np.bincount(k, minlength=nd * A_SAY)
    order = np.argsort(k); ss = R[ok][order]; sinir = np.r_[0, np.cumsum(say)]
    for c in np.nonzero(say >= 5)[0]:
        T[c] = np.median(ss[sinir[c]:sinir[c + 1]], 0)
    T = T.reshape(nd, A_SAY, 3)
    for i in range(nd):                                                 # bos aci hucreleri: dairesel ara deger
        v = ~np.isnan(T[i, :, 0])
        if v.any():
            for c in range(3):
                T[i, :, c] = np.interp(np.arange(A_SAY), np.nonzero(v)[0], T[i, v, c], period=A_SAY)
    return np.nan_to_num(T, nan=128.0)


def dtab_uygula(A, T):
    d, th = dt_alan(A)
    nd = T.shape[0]
    fy = np.clip(d / D_ADIM - 0.5, 0, nd - 1).astype(np.float32)
    fx = ((th + 180) / (360 / A_SAY) - 0.5).astype(np.float32)
    Tp = np.concatenate([T[:, -1:], T, T[:, :1]], 1)                    # aci dairesel
    out = np.stack([cv2.remap(np.ascontiguousarray(Tp[..., c]), fx + 1, fy, cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REPLICATE) for c in range(3)], -1)
    ic = d >= D_MAX
    out[ic] = 128.0                                                     # pah disi: yalniz dolgu
    return out


def oz_test_v2(rgb, A, sigma):
    F = parilti(rgb, A, sigma)
    T = dtab_olc(rgb - F + 128.0, A)
    yeni = np.clip(F + dtab_uygula(A, T) - 128.0, 0, 255)
    ok = A >= 0.95
    L0, L1 = rgb[ok] @ LUMA, yeni[ok] @ LUMA
    lab = lambda x: cv2.cvtColor(np.clip(x, 0, 255).astype(np.float32)[None] / 255, cv2.COLOR_RGB2LAB)[0]
    dE = np.linalg.norm(lab(rgb[ok]) - lab(yeni[ok]), axis=1)
    r2 = 1 - ((L0 - L1) ** 2).sum() / ((L0 - L0.mean()) ** 2).sum()
    return {'sigma': sigma, 'R2_luma': round(float(r2), 3), 'dE_ortanca': round(float(np.median(dE)), 2),
            'dE_p90': round(float(np.percentile(dE, 90)), 2)}, F, T, yeni


# ---- v3: ic dolgu (pah disi) + carpimsal pah tablosu S(d, aci) = renk / dolgu ------------------------------------
IC_D = 15.0


def ic_dolgu(rgb, A, sigma):
    """dolgu yalniz pah disi ic piksellerden (d > IC_D), kenarlara ve kutuya dikissiz genisletilir."""
    d, _ = dt_alan(A)
    A2 = np.where(d > IC_D, A, 0)
    return parilti(rgb, A2, sigma)


def oz_test_v3(rgb, A, sigma):
    F = ic_dolgu(rgb, A, sigma)
    Sr = rgb / np.maximum(F, 1.0) * 128.0                               # oran, 128 = 1
    T = dtab_olc(Sr, A)
    yeni = np.clip(F * dtab_uygula(A, T) / 128.0, 0, 255)
    ok = A >= 0.95
    L0, L1 = rgb[ok] @ LUMA, yeni[ok] @ LUMA
    lab = lambda x: cv2.cvtColor(np.clip(x, 0, 255).astype(np.float32)[None] / 255, cv2.COLOR_RGB2LAB)[0]
    dE = np.linalg.norm(lab(rgb[ok]) - lab(yeni[ok]), axis=1)
    r2 = 1 - ((L0 - L1) ** 2).sum() / ((L0 - L0.mean()) ** 2).sum()
    return {'sigma': sigma, 'R2_luma': round(float(r2), 3), 'dE_ortanca': round(float(np.median(dE)), 2),
            'dE_p90': round(float(np.percentile(dE, 90)), 2)}, F, T, yeni


# ---- v5: kosullu tablo T[d, aci, dolgu seviyesi] (ana sembol pikselleri; pah rengi dolguyla birlikte degisir) --------
F_SEV = 10


def ktab_olc(rgb, A, F, d_adim=0.5, d_max=24.0, a_say=36):
    d, th = dt_alan(A)
    Lf = F @ LUMA
    ok = A >= 0.95
    q = np.percentile(Lf[ok], np.linspace(0, 100, F_SEV + 1)[1:-1])
    fi = np.searchsorted(q, Lf)
    nd = int(d_max / d_adim)
    di = np.clip((d / d_adim).astype(int), 0, nd - 1); ai = ((th + 180) / (360 / a_say)).astype(int) % a_say
    k = ((di * a_say + ai) * F_SEV + fi)[ok]
    n = nd * a_say * F_SEV
    T = np.full((n, 3), np.nan, np.float32)
    say = np.bincount(k, minlength=n)
    order = np.argsort(k); ss = rgb[ok][order]; sinir = np.r_[0, np.cumsum(say)]
    for c in np.nonzero(say >= 3)[0]:
        T[c] = np.median(ss[sinir[c]:sinir[c + 1]], 0)
    T = T.reshape(nd, a_say, F_SEV, 3)
    # bos hucre: once dolgu seviyesi komsusu, sonra aci komsusu (dairesel), sonra d komsusu
    for ax, per in ((2, None), (1, a_say), (0, None)):
        Tm = np.moveaxis(T, ax, -2)
        sh = Tm.shape
        flat = Tm.reshape(-1, sh[-2], 3)
        for r in range(flat.shape[0]):
            v = ~np.isnan(flat[r, :, 0])
            if v.any() and not v.all():
                for c in range(3):
                    flat[r, :, c] = np.interp(np.arange(sh[-2]), np.nonzero(v)[0], flat[r, v, c], period=per)
        T = np.moveaxis(flat.reshape(sh), -2, ax)
    return {'T': np.nan_to_num(T, nan=128.0), 'q': q, 'd_adim': d_adim, 'd_max': d_max, 'a_say': a_say}


def ktab_uygula(A, F, tab):
    d, th = dt_alan(A)
    T, q = tab['T'], tab['q']
    nd, a_say = T.shape[0], tab['a_say']
    fi = np.searchsorted(q, F @ LUMA)
    di = np.clip((d / tab['d_adim']).astype(int), 0, nd - 1)
    ai = ((th + 180) / (360 / a_say)).astype(int) % a_say
    out = T[di, ai, fi]
    ic = d >= tab['d_max']
    out[ic] = F[ic]
    return out


def oz_test_v5(rgb, A, sigma):
    F = ic_dolgu(rgb, A, sigma)
    tab = ktab_olc(rgb, A, F)
    yeni = ktab_uygula(A, F, tab)
    ok = A >= 0.95
    L0, L1 = rgb[ok] @ LUMA, yeni[ok] @ LUMA
    lab = lambda x: cv2.cvtColor(np.clip(x, 0, 255).astype(np.float32)[None] / 255, cv2.COLOR_RGB2LAB)[0]
    dE = np.linalg.norm(lab(rgb[ok]) - lab(yeni[ok]), axis=1)
    r2 = 1 - ((L0 - L1) ** 2).sum() / ((L0 - L0.mean()) ** 2).sum()
    return {'sigma': sigma, 'R2_luma': round(float(r2), 3), 'dE_ortanca': round(float(np.median(dE)), 2),
            'dE_p90': round(float(np.percentile(dE, 90)), 2)}, F, tab, yeni


# ---- v8: genel kosullu tablo: eksenler secilebilir (d mutlak, t goreli, r yerel yaricap, aci, dolgu seviyesi) --------
def eksenler(A, F):
    d, th = dt_alan(A)
    m = (A > 0.5).astype(np.uint8)
    dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    r = cv2.dilate(dt, np.ones((31, 31), np.uint8))                     # yerel cizgi yari genisligi (sirt degeri)
    t = np.clip(d / np.maximum(r, 1), 0, 1)
    return {'d': d, 't': t, 'r': r, 'a': th, 'f': F @ LUMA}


def gtab(rgb, A, F, spec, ok_eval=None, ok_fit=None):
    """spec: [(eksen, kutu_kenarlari or ('aci', n) or ('q', n))] -> tablo + tahmin (ayni pikseller)."""
    E = eksenler(A, F)
    ok = A >= 0.95
    idx = np.zeros(A.shape, np.int64); n = 1
    for ad, kut in spec:
        v = E[ad]
        if ad == 'a':
            i = ((v + 180) / (360 / kut)).astype(int) % kut; k = kut
        elif isinstance(kut, int):
            q = np.percentile(v[ok], np.linspace(0, 100, kut + 1)[1:-1]); i = np.searchsorted(q, v); k = kut
        else:
            i = np.clip(np.searchsorted(kut, v) - 1, 0, len(kut) - 2); k = len(kut) - 1
        idx = idx * k + i; n *= k
    of = ok if ok_fit is None else (ok & ok_fit)
    kk = idx[of]
    say = np.bincount(kk, minlength=n)
    T = np.zeros((n, 3), np.float32)
    order = np.argsort(kk); ss = rgb[of][order]; sinir = np.r_[0, np.cumsum(say)]
    glob = np.median(rgb[of], 0)
    for c in np.nonzero(say)[0]:
        T[c] = np.median(ss[sinir[c]:sinir[c + 1]], 0) if say[c] >= 3 else glob
    T[say == 0] = glob
    return T[idx]
