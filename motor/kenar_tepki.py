#!/usr/bin/env python3
"""Ana sembolun KENAR TEPKISI (Serdar 4 Eki, EMILY turu 2): ana sembolun gercek piksellerinden olculen kenar
tablosu, harflere AYNI piksel olceginde uygulanir (Canva altin efektinin pahi mutlak boyutlu: orijinal posterin ince
isimlerinde (r ~ 5 px) pah tum yari cizgiyi kaplar; ana sembolde (r ~ 25 px) kenarda ~10 px bant kalir).

Olcum (ana sembol, orijinal poster): kenardan ic uzaklik d (1 px kutular, 0-15 px) x disa normal acisi (15 derece
kutular) icin luma ortancasi - yuz lumasi -> M(d, aci). Renk: ana sembol piksellerinin luma -> RGB ortanca tablosu
(tek_doku.egri_olc). Tane: d4ea867 aktariminin (doku_aktar) ince detayi (yuksek gecirgen) eklenir.
Uygulama: L = yuz + guc x M(d_harf, aci_harf); renk = egri(L) + tane; kapsama ile zemine.
"""
import json, sys
from pathlib import Path

import cv2
import numpy as np

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import tek_doku as tdk                                               # noqa: E402

LUMA = tdk.LUMA
DMAX = 16
DELIK = 300              # px; cizgi ici bosluk esigi
NA = 24


def alan(A):
    """ic uzaklik (px, alt piksel: isaretli uzaklik), disa normal acisi (derece)."""
    m = (A > 0.5).astype(np.uint8)
    sd = cv2.distanceTransform(m, cv2.DIST_L2, 5) - cv2.distanceTransform(1 - m, cv2.DIST_L2, 5)
    sd = cv2.GaussianBlur(sd, (0, 0), 1.0)
    gx = cv2.Sobel(sd, cv2.CV_32F, 1, 0, ksize=5); gy = cv2.Sobel(sd, cv2.CV_32F, 0, 1, ksize=5)
    return np.clip(sd + 0.5, 0, None), np.degrees(np.arctan2(-gy, -gx))


def kapsama(rgb, zem):
    """altin kapsamasi RENK doygunlugundan (R - B): koyu bronz kenar da altindir (parlaklik kapsamasi onu yari saydam
    sayip olcumden dusuruyordu). Zemin (R - B) ve altin govde (R - B) ortancasi arasinda dogrusal."""
    rb = rgb[..., 0] - rgb[..., 2]
    rz = zem[..., 0] - zem[..., 2]
    ic = rb[(rb - rz) > 100]
    A_r = np.clip((rb - rz) / max(float(np.median(ic) - np.median(rz)), 1.0), 0, 1)
    # 4 Eki: soluk sari vurgularda (B yuksek) R - B dusuk -> maske delikleri; parlaklik kapsamasiyla birlesim
    D = (rgb - zem) @ LUMA
    A_l = np.clip(D / max(float(np.median(D[D > 40])), 1.0), 0, 1)
    A = np.maximum(A_r, A_l)
    # cizgi icindeki kucuk bosluklar (murekkeple cevrili, < DELIK px): altin (koyu / notr pah pikseli), zemin degil
    m = (A > 0.5).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(1 - m, 4)
    kucuk = np.zeros(n, bool); kucuk[1:] = st[1:, cv2.CC_STAT_AREA] < DELIK
    kenar = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])
    kucuk[kenar] = False
    A[kucuk[lab]] = 1.0
    return A


def olc(rgb, zem):
    """ana sembol: M (DMAX x NA), yuz lumasi, egri."""
    A = kapsama(rgb, zem)
    d, th = alan(A)
    L = rgb @ LUMA
    yuz = float(np.median(L[d > DMAX]))
    ai = ((th + 180) / (360 / NA)).astype(int) % NA
    di = np.clip(d.astype(int), 0, DMAX - 1)
    ok = (A >= 0.95) & (d < DMAX)
    M = np.full((DMAX, NA), np.nan)
    for i in range(DMAX):
        for j in range(NA):
            s = ok & (di == i) & (ai == j)
            if s.sum() >= 30:
                M[i, j] = np.median(L[s]) - yuz
    # bos hucreler: aci boyunca dairesel ara deger; kutu yumusatma (1 x 1)
    for i in range(DMAX):
        v = ~np.isnan(M[i])
        if v.any():
            M[i] = np.interp(np.arange(NA), np.nonzero(v)[0], M[i, v], period=NA)
    M = np.nan_to_num(M)
    M = cv2.GaussianBlur(np.tile(M, (1, 3)).astype(np.float32), (0, 0), 0.8)[:, NA:2 * NA]
    egri = tdk.egri_olc(rgb[A >= 0.95].astype(np.float32))
    return {'M': M.round(2).tolist(), 'yuz': round(yuz, 1), 'egri': egri.round(1).tolist(), 'dmax': DMAX, 'na': NA}


def uygula(A, model, guc=1.0, tane=None):
    """harf kapsamasi A icin renk: L = yuz + guc x M(d, aci); egri; + tane (yuksek gecirgen, ayni boy)."""
    d, th = alan(A)
    M = np.asarray(model['M'], np.float32)
    x = (th + 180) / (360 / NA) - 0.5
    j0 = np.floor(x).astype(int); fj = x - j0
    i = np.clip(d - 0.5, 0, DMAX - 1); i0 = np.floor(i).astype(int); fi = i - i0; i1 = np.clip(i0 + 1, 0, DMAX - 1)
    g = lambda ii, jj: M[ii, jj % NA]
    m = ((1 - fi) * ((1 - fj) * g(i0, j0) + fj * g(i0, j0 + 1)) + fi * ((1 - fj) * g(i1, j0) + fj * g(i1, j0 + 1)))
    m = np.where(d >= DMAX, 0, m)
    L = model['yuz'] + guc * m
    rgb = tdk.renk(L, np.asarray(model['egri'], np.float32))
    if tane is not None:
        hp = tane - cv2.GaussianBlur(tane, (0, 0), 1.2)
        rgb = rgb + hp
    return np.clip(rgb, 0, 255)
