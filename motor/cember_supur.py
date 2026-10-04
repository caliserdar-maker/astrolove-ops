#!/usr/bin/env python3
"""CEMBER: tek dilimin dokusu tum halkaya supurulur (Serdar 4 Eki karari; 4 dilim birlesimi dikis yapiyordu).

1 kaynak  : cila sonrasi dilim dokusu (CEMBER_SAG_P), halka cercevesine (json halka.sayfa_kaydirma) tasinir.
2 kutupsal: halka merkez cizgisi rc(u) aci basina olculur (HALKA alfa agirlikli yaricap, 0.5 derece kutular,
            yumusatilmis); doku (rho = r - rc(u)) x (u) kutupsal goruntuye acilir. Aci adimi = yay uzunlugu 1 px.
            Cizgi kesiti (ic kenar -> dis kenar) rho ekseninde aynen korunur.
2b duzlestir: aci boyunca dusuk frekansli (2 derece) Lab egilimi cikarilir, rho satir ortalamasi korunur.
3 dose    : kaynak araligi [U0, U1] (dilimin tam kalinlikli kismi) ayna-tekrarli dosenir: dose i [i*(L-OV), +L],
            yon donusumlu; ortusmede (OV derece) yukseltilmis kosinus gecis.
4 halka   : her halka pikseli (u, rho) -> kutupsal dokudan ornek; alfa = HALKA_24x36 (uclar onayli incelme).
"""
import json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
Image.MAX_IMAGE_PIXELS = None
RHO = 30            # px, merkez cizgisinden ic / dis
OV = 8.0            # derece, dose ortusmesi


def merkez_cizgisi(h, cx, cy, su):
    ys, xs = np.nonzero(h > 0)
    w = h[ys, xs].astype(np.float64)
    r = np.hypot(xs - cx, ys - cy); u = (np.degrees(np.arctan2(-(ys - cy), xs - cx)) - su) % 360
    b = (u * 2).astype(int)
    sw = np.bincount(b, w, 720); sr = np.bincount(b, w * r, 720)
    ok = sw > 0
    rc = np.interp(np.arange(720), np.nonzero(ok)[0], sr[ok] / sw[ok])
    rc = cv2.GaussianBlur(rc[None].astype(np.float32), (0, 0), 4)[0]        # 2 derece yumusatma
    return lambda uu: np.interp(uu * 2, np.arange(720), rc)


def kaynak_kutupsal(t, j, h, U0, U1):
    """dilim dokusu (sayfa) -> kutupsal (rho x s), s: yay uzunlugu 1 px adim, U0..U1."""
    g = j['halka']; cx, cy = g['merkez']; su = g['sag_uc_aci']; dx, dy = g['sayfa_kaydirma']
    rc = merkez_cizgisi(h, cx, cy, su)
    du = np.degrees(1.0 / g['yaricap'])
    uu = np.arange(U0, U1, du); rr = np.arange(-RHO, RHO + 1, 1.0)
    U, Rh = np.meshgrid(uu, rr)
    R = rc(U) + Rh; th = np.radians(U + su)
    X = cx + R * np.cos(th) - dx; Y = cy - R * np.sin(th) - dy                # sayfa koordinati
    P = cv2.remap(t.astype(np.float32), X.astype(np.float32), Y.astype(np.float32), cv2.INTER_LINEAR,
                  borderMode=cv2.BORDER_CONSTANT)
    return P, du, rc


def duzlestir(P, du, sigma_derece=2.0):
    """aci boyunca dusuk frekansli isik / renk egilimi duzlestirilir (Canva dilime aci boyunca isik gradyani boyuyor;
    ayna-tekrar bunu periyodik parlak / koyu bolgelere cevirir). Her rho satirinda Lab egilimi (sigma derece Gauss)
    cikarilir, satirin aci ortalamasi eklenir: kesit profili (rho ortalamasi) ve ince doku korunur."""
    import doku_cila as dc
    Lab = dc.lab(np.clip(P, 0, 255))
    sx = sigma_derece / du
    egilim = cv2.GaussianBlur(Lab, (0, 0), sigmaX=sx, sigmaY=0.01, borderType=cv2.BORDER_REFLECT)
    ort = Lab.mean(1, keepdims=True)
    return np.clip(dc.rgb_(Lab - egilim + ort), 0, 255)


def dose(P, L_px, ov_px, n_px):
    """ayna-tekrarli dose + kosinus gecis: hedef s (0..n_px) icin kutupsal doku (rho x n_px x 3)."""
    out = np.zeros((P.shape[0], n_px, 3), np.float32); wt = np.zeros(n_px, np.float32)
    adim = L_px - ov_px; i = 0
    while i * adim < n_px:
        s0 = i * adim
        seg = P if i % 2 == 0 else P[:, ::-1]
        x = np.arange(L_px)
        w = np.ones(L_px, np.float32)
        r = np.clip(x / ov_px, 0, 1); w *= (0.5 - 0.5 * np.cos(np.pi * r)) if i > 0 else 1
        r2 = np.clip((L_px - 1 - x) / ov_px, 0, 1); w *= 0.5 - 0.5 * np.cos(np.pi * r2)
        a, b = s0, min(s0 + L_px, n_px)
        out[:, a:b] += seg[:, :b - a] * w[None, :b - a, None]; wt[a:b] += w[:b - a]
        i += 1
    wt[-ov_px:] = np.maximum(wt[-ov_px:], 1e-6)
    return out / np.maximum(wt, 1e-6)[None, :, None]


def supur(t, j, h, U0, U1, u_son, duz=True):
    P, du, rc = kaynak_kutupsal(t, j, h, U0, U1)
    if duz:
        P = duzlestir(P, du)
    g = j['halka']; cx, cy = g['merkez']; su = g['sag_uc_aci']
    n = int(np.ceil(u_son / du)) + 2
    Q = dose(P, P.shape[1], int(round(OV / du)), n)
    ys, xs = np.nonzero(h > 0)
    X0, Y0, X1, Y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    yy, xx = np.mgrid[Y0:Y1, X0:X1].astype(np.float32)
    u = (np.degrees(np.arctan2(-(yy - cy), xx - cx)) - su) % 360
    rho = np.hypot(xx - cx, yy - cy) - rc(u)
    mx = (u / du).astype(np.float32); my = (rho + RHO).astype(np.float32)
    rgb = cv2.remap(Q, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    alfa = h[Y0:Y1, X0:X1].astype(np.float32) / 255
    return rgb, alfa, [int(X0), int(Y0), int(X1), int(Y1)], {'kaynak_u': [U0, U1], 'adim_derece': du,
                                                             'dose_derece': U1 - U0, 'ortusme_derece': OV,
                                                             'periyot_derece': 2 * (U1 - U0 - OV)}
