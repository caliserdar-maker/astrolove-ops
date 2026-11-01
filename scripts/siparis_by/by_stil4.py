#!/usr/bin/env python3
"""Denetim 20261101F: YD (1st Anniversary) kalan 4 stil, 12x18 (3600x5400, 300 dpi) ORNEK. ETSY YOK, toplu uretim yok.
Serdar kurallari: hicbir oge tek yonde olceklenmez (yalniz esit oran); susleme ORIJINAL piksel (yeniden cizim yok); ayna / desen kopyasi
yok; urun sembolu ve yazilar yapay zekadan gecmez (Real-ESRGAN yalniz duz zemin dokusuna); eski 8x10 tasarim blogu 12x18'de esit olcek
1,5, dikeyde ortali (oy = 450; ORNEK3 ile ayni). Ogeler by_poster (KOD_REF, degistirilmeden) BY_SCALE'de cizilip esit olcekle indirilir.

Susleme aktarimi (Timeless altin dallar / yay, Botanical cicekler): krem kagit uzerinde koyu / renkli susleme, ORNEK3'teki "yalniz isik"
uygun degil (susleme kagittan koyu). Yontem: ORAN (carpim) katmani R = eski / yerel_zemin(eski) (susleme maskesi disarida, normalize
konvolusyon; yay_orijinal.yerel_zemin), maske disinda 1; yeni zemine out = zemin x R (esit olcek 1,5, Lanczos). Boylece susleme eski
kagida gore koyulugu / rengiyle tasinir, eski kagit dokusu tasinmaz (R ~ 1).
Stiller:
  Timeless: yeni krem doku (ESRGAN x2 -> 3600x5400) + yay ve tepe yildizi tasarim bloguyla (x1,5, oy 450) + 3 dal kendi koselerine sabit
            (kenara uzaklik eski x 1,5).
  FirstPage: yeni krem doku + bordo cerceve KODLA (8x10'dan olculen renk orani / FWHM), dort kenar payi esit = 8x10 yan payi x 1,5.
  Layers A KIRP: 8x10 zemin x1,8 (Lanczos; ogeler BY_SCALE'de) -> 4320x5400, iki yandan esit 360 px kirpilir.
  Layers B USTE SABIT: 8x10 zemin x1,5 uste (0..4500, ogeler ayni donusumle); duz seftali bolgesi (eski satir >= DUZ_Y, kemer yok)
            ESRGAN x2 ile buyutulup TEK parca esit olcekle (x2,5) satir 1,5*DUZ_Y..5400'u kaplar (ortadan kirpilir; kopya / ayna yok).
  Botanical: yeni tirtikli kagit + adacayi doku (ESRGAN) + 2 cicek dali kagit koselerine sabit (kagit kenarina uzaklik eski x 1,5).
Kullanim: by_stil4.py --kod <KOD_REF> --doku-dizin <dir: 2_Timeless/3_FirstPage/5_Botanical _2x3_kaynak.png> --esrgan <pth> --out <dir>
          [--hizli]  (yalniz yerel deneme: ESRGAN yerine Lanczos; uretimde kullanilmaz)"""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import by_ornek3 as B3  # noqa: E402  (esrgan, by_poster)
import yay_orijinal as YR  # noqa: E402  (yerel_zemin)

Z = "z/Baski_2400x3000_Buyutulmus"
K, OY = 1.5, 450
DUZ_Y = 2100           # Layers: eski 8x10'da kemer katmanlari satir 2050'de biter (olcum 1 Kas: satir 2050+ duz renkten > 25 sapan piksel 0)
KORELASYON, KAZANC, KAYMA, AFIN = 0.98, (0.95, 1.05), 0.5, 0.01


def lum(a):
    return a.astype(np.float32) @ np.float32([0.299, 0.587, 0.114])


def zemin_lum(a, k=61):
    return cv2.medianBlur(np.clip(lum(a), 0, 255).astype(np.uint8), k).astype(np.float32)


# ------------------------------------------------------------------ susleme maskeleri (eski 8x10)
def histerezis(guclu, zayif, en_az):
    n, lab, st, _ = cv2.connectedComponentsWithStats(guclu.astype(np.uint8), 8)
    tohum = np.isin(lab, [i for i in range(1, n) if st[i, 4] >= en_az])
    n2, lab2 = cv2.connectedComponents((zayif | tohum).astype(np.uint8), 8)
    ids = np.unique(lab2[tohum])
    return np.isin(lab2, ids[ids > 0])


def timeless_parcalar(e):
    d = zemin_lum(e) - lum(e)
    sat = e.max(2).astype(np.float32) - e.min(2)
    s0 = float(np.median(sat))
    m = histerezis((d > 10) | (sat - s0 > 15), (d > 4) | (sat - s0 > 8), 3000)
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) > 0
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    p = {}
    for i in range(1, n):
        x, y, w, h, a = (int(v) for v in st[i])
        if a < 3000:
            continue
        cx, cy = x + w / 2, y + h / 2
        ad = ("yay" if w > 1200 else "dal_sol_ust" if cx < 1200 and cy < 1500 else "dal_sol_alt" if cx < 1200 else "dal_sag_alt")
        p.setdefault(ad, np.zeros_like(m))
        p[ad] |= lab == i
    return p


def kagit(a):
    """tirtikli krem kagit maskesi (doldurulmus) ve kutusu"""
    L = lum(a); sat = a.max(2).astype(np.float32) - a.min(2)
    H, W = L.shape
    merkez = L[H // 3:2 * H // 3, W // 3:2 * W // 3]
    m = (L > np.median(merkez) - 30) & (sat < 45)
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((41, 41), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    i = 1 + int(np.argmax(st[1:, 4]))
    k = (lab == i).astype(np.uint8)
    dis = np.zeros((H + 2, W + 2), np.uint8); f = k.copy()
    cv2.floodFill(f, dis, (0, 0), 1)                                   # disaridan doldur -> delikler = ~f
    k = (k | (1 - f)).astype(bool)
    ys, xs = np.where(k)
    # kutu: tirtikli kenarin ic sinirina yakin, %1 / %99 yuzdelik (tek tirtik ucu belirlemesin)
    return k, [int(np.percentile(xs, 1)), int(np.percentile(ys, 1)), int(np.percentile(xs, 99)), int(np.percentile(ys, 99))]


def botanical_parcalar(e):
    km, kk = kagit(e)
    d = zemin_lum(e) - lum(e)
    sat = e.max(2).astype(np.float32) - e.min(2)
    s0 = float(np.median(sat[km]))
    # yerel deneme 1 Kas: kagidin tirtikli kenari / adacayi zemin maskeye karisiyordu (sol alt kutu x 19..2357) -> yalniz kagit ici
    ic = cv2.erode(km.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
    m = histerezis(((d > 25) | (sat - s0 > 25)) & ic, ((d > 10) | (sat - s0 > 12)) & ic, 3000)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    p = {}
    for i in range(1, n):
        x, y, w, h, a = (int(v) for v in st[i])
        if a < 3000:
            continue
        cx, cy = x + w / 2, y + h / 2
        ad = "cicek_sag_ust" if (cx > 1200 and cy < 1500) else "cicek_sol_alt" if (cx < 1200 and cy > 1500) else None
        if ad:
            p.setdefault(ad, np.zeros_like(m)); p[ad] |= lab == i
    # dala ait kucuk ayrik yapraklar (yerel bakis 1 Kas: sag ustte 1, sol altta 2 yaprak disarida kaliyordu): ana dal kutusuna 450 px
    # yakin, alani >= 600 px parcalar (kagit lifleri / tohum kirintilari < 600 px)
    aday = ((d > 18) | (sat - s0 > 20)) & ic & ~m
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(aday.astype(np.uint8), 8)
    for ad in list(p):
        x0, y0, x1, y1 = kutu(p[ad], 0)
        for i in range(1, n2):
            x, y, w, h, a_ = (int(v) for v in st2[i])
            if a_ >= 600 and x > x0 - 450 and x + w < x1 + 450 and y > y0 - 450 and y + h < y1 + 450:
                c = e[lab2 == i].astype(np.float32).mean(0)
                if c[1] - c[0] > -18:     # yesil yaprak (G - R -9..-14); kahverengi kagit kirintisi -21..-31 (olcum 1 Kas) alinmaz
                    p[ad] |= lab2 == i
    # yaprak ici delikleri doldur (yerel bakis 1 Kas: maske deliginde yeni kagit gorunuyor, yaprakta beyaz leke)
    for ad in p:
        x0, y0, x1, y1 = kutu(p[ad], 2)
        k = p[ad][y0:y1, x0:x1].astype(np.uint8)
        f = k.copy(); cv2.floodFill(f, np.zeros((k.shape[0] + 2, k.shape[1] + 2), np.uint8), (0, 0), 1)
        p[ad][y0:y1, x0:x1] |= f == 0
    return p, km, kk


def oran(e, maske, haric_ek=None):
    """R = eski / yerel zemin (maske ve haric_ek zemin tahmininden disarida); maske disinda 1, kenarda yumusak."""
    har = cv2.dilate(maske.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    if haric_ek is not None:
        har |= haric_ek
    z = YR.yerel_zemin(e, har)
    R = np.clip(e.astype(np.float32) / np.maximum(z, 1.0), 0.03, 1.8)
    w = cv2.GaussianBlur(cv2.dilate(maske.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32), (0, 0), 1.5)
    return 1 + (R - 1) * w[..., None], w


def kutu(m, pay=24):
    """goruntu sinirina KIRPILMIS kutu (yerel deneme 1 Kas: sinir disina tasan kutu kesik diziyi tek yonde esnetiyordu; SIFT sy 1,559)"""
    ys, xs = np.where(m)
    H, W = m.shape
    x0, y0 = max(0, int(xs.min()) - pay), max(0, int(ys.min()) - pay)
    x1, y1 = min(W, int(xs.max()) + pay + 1), min(H, int(ys.max()) + pay + 1)
    # cift koordinat: x 1,5 tam sayi olur (yerel deneme: (3000 - 2351) x 1,5 = 973,5 yuvarlamasi 0,5 px kayma veriyordu)
    return [x0 - x0 % 2, y0 - y0 % 2, min(W, x1 + x1 % 2), min(H, y1 + y1 % 2)]


def carp(dst, R, kt, X, Y):
    """R'nin kt kutusunu esit olcek K ile buyutup dst'ye (X, Y) sol ust kosesinden carpar; tuval disi kirpilir."""
    x0, y0, x1, y1 = kt
    r = R[y0:y1, x0:x1]
    w, h = round((x1 - x0) * K), round((y1 - y0) * K)
    r = cv2.resize(r, (w, h), interpolation=cv2.INTER_LANCZOS4)
    H, W = dst.shape[:2]
    a0, b0 = max(0, -X), max(0, -Y); a1, b1 = min(w, W - X), min(h, H - Y)
    dst[Y + b0:Y + b1, X + a0:X + a1] *= r[b0:b1, a0:a1]
    return [X, Y, X + w, Y + h], [X + a0, Y + b0, X + a1, Y + b1]


# ------------------------------------------------------------------ kapilar
def koyuluk(a, haric):
    z = YR.yerel_zemin(a, haric)
    return np.clip(1 - lum(a) / np.maximum(lum(z.clip(0, 255)), 1.0), 0, 1)


def faz(a, b):
    h, w = a.shape
    hn = np.outer(np.hanning(h), np.hanning(w)).astype(np.float32)
    (dx, dy), r = cv2.phaseCorrelate(a.astype(np.float32), b.astype(np.float32), hn)
    return float(dx), float(dy), float(r)


def sift_afin(a, b):
    """a (eski kirpim) -> b (yeni kirpim) SIFT + RANSAC afin; sx, sy (sutun normlari), x/y farki"""
    s = cv2.SIFT_create(4000)
    u = lambda x: cv2.normalize(x, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)  # noqa: E731
    k1, d1 = s.detectAndCompute(u(a), None); k2, d2 = s.detectAndCompute(u(b), None)
    if d1 is None or d2 is None or len(k1) < 8 or len(k2) < 8:
        return dict(hata="ozellik az", n1=len(k1 or []), n2=len(k2 or []))
    m = cv2.BFMatcher().knnMatch(d1, d2, k=2)
    iyi = [p[0] for p in m if len(p) == 2 and p[0].distance < 0.75 * p[1].distance]
    if len(iyi) < 8:
        return dict(hata="eslesme az", eslesme=len(iyi))
    A, inl = cv2.estimateAffine2D(np.float32([k1[x.queryIdx].pt for x in iyi]), np.float32([k2[x.trainIdx].pt for x in iyi]),
                                  method=cv2.RANSAC, ransacReprojThreshold=2.0)
    if A is None:
        return dict(hata="afin yok")
    sx, sy = float(np.hypot(A[0, 0], A[1, 0])), float(np.hypot(A[0, 1], A[1, 1]))
    return dict(sx=round(sx, 5), sy=round(sy, 5), xy_fark=round(abs(sx / sy - 1), 5), eslesme=len(iyi), inlier=int(inl.sum()),
                pass_=bool(abs(sx / sy - 1) <= AFIN))


def susleme_kapi(e, out, maske_e, kt, X, Y, haric_out):
    """bagimsiz: eski ve cikti koyulugu (1 - lum / yerel zemin) ayni yontemle; cikti kirpimi 1/1,5 INTER_AREA; maske >= 0,5 pikseller."""
    x0, y0, x1, y1 = kt
    w, h = x1 - x0, y1 - y0
    He, We = e.shape[:2]
    if X < 0 or Y < 0 or X + round(w * K) > out.shape[1] or Y + round(h * K) > out.shape[0]:
        # tuval disina tasan susleme (kenara degen dal): yalniz tuval icindeki kisim, eski tarafta karsiligi
        a0, b0 = max(0, -X), max(0, -Y)
        a1, b1 = min(round(w * K), out.shape[1] - X), min(round(h * K), out.shape[0] - Y)
        ex0, ey0 = x0 + int(np.ceil(a0 / K)), y0 + int(np.ceil(b0 / K))
        ex1, ey1 = x0 + int((a1) // K), y0 + int((b1) // K)
        X, Y = X + round((ex0 - x0) * K), Y + round((ey0 - y0) * K)
        x0, y0, x1, y1, w, h = ex0, ey0, ex1, ey1, ex1 - ex0, ey1 - ey0
    har_e = cv2.dilate(maske_e.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    De = koyuluk(e, har_e)[y0:y1, x0:x1]
    Do_t = koyuluk(out, haric_out)[Y:Y + round(h * K), X:X + round(w * K)]
    Do = cv2.resize(Do_t, (w, h), interpolation=cv2.INTER_AREA)
    m = maske_e[y0:y1, x0:x1] & (De > 0.02)
    xe, xo = De[m], Do[m]
    dx, dy, r = faz(De, Do)
    sift = sift_afin(lum(e[y0:y1, x0:x1]), lum(out[Y:Y + round(h * K), X:X + round(w * K)]))
    d = dict(korelasyon=round(float(np.corrcoef(xe, xo)[0, 1]), 4), kazanc=round(float((xe * xo).sum() / max((xe * xe).sum(), 1e-9)), 4),
             ort_mutlak_fark=round(float(np.abs(xo - xe).mean()), 4), px=int(m.sum()), kayma=[round(dx, 3), round(dy, 3)], faz_tepe=round(r, 3),
             sift=sift)
    d["pass_"] = bool(d["korelasyon"] >= KORELASYON and KAZANC[0] <= d["kazanc"] <= KAZANC[1] and max(abs(dx), abs(dy)) < KAYMA
                      and sift.get("pass_", False))
    return d


# ------------------------------------------------------------------ ogeler
def ogeler(bp, blok, fn):
    bp.bgimg = lambda name: Image.fromarray(blok)
    return np.asarray(getattr(bp, fn)().convert("RGB"))


def ogeli_blok(bp, fn, blok, S):
    """blok (4500x3600) uzerine by_poster ogeleri: S olceginde cizim -> esit olcekle 3600x4500; yalniz degisen pikseller aktarilir."""
    buyuk = cv2.resize(blok, (2400 * S, 3000 * S), interpolation=cv2.INTER_LANCZOS4)
    ciz = cv2.resize(ogeler(bp, buyuk, fn), (blok.shape[1], blok.shape[0]), interpolation=cv2.INTER_AREA)
    geri = cv2.resize(buyuk, (blok.shape[1], blok.shape[0]), interpolation=cv2.INTER_AREA)
    fark = (np.abs(ciz.astype(np.int16) - geri.astype(np.int16)).max(2) > 2)
    mk = cv2.GaussianBlur(cv2.dilate(fark.astype(np.float32), np.ones((5, 5), np.uint8)), (0, 0), 1.5)[..., None]
    return np.clip(blok * (1 - mk) + ciz * mk, 0, 255).astype(np.uint8), fark


def doku(yol, agirlik, hizli):
    k = np.asarray(Image.open(yol).convert("RGB"))
    if k.shape[:2] != (3600, 2400):
        raise SystemExit(f"DUR: {yol} {k.shape[1]}x{k.shape[0]} (2400x3600 beklenir)")
    if hizli:
        return cv2.resize(k, (3600, 5400), interpolation=cv2.INTER_LANCZOS4), "lanczos (YEREL DENEME)"
    z2, s = B3.esrgan(k, agirlik)
    return cv2.resize(z2, (3600, 5400), interpolation=cv2.INTER_AREA), f"Real-ESRGAN x{s} -> INTER_AREA"


# ------------------------------------------------------------------ stiller
def timeless(e, zem, bp, S):
    p = timeless_parcalar(e)
    tum = np.zeros(e.shape[:2], bool)
    for v in p.values():
        tum |= v
    out = zem.astype(np.float32); yer = {}
    for ad, m in p.items():
        R, _ = oran(e, m, haric_ek=tum & ~m)
        kt = kutu(m)
        x0, y0, x1, y1 = kt
        if ad == "yay":
            X, Y = round(x0 * K), round(y0 * K + OY)
        elif ad == "dal_sol_ust":
            X, Y = round(x0 * K), round(y0 * K)
        elif ad == "dal_sol_alt":
            X, Y = round(x0 * K), round(5400 - (3000 - y0) * K)
        else:
            X, Y = round(3600 - (2400 - x0) * K), round(5400 - (3000 - y0) * K)
        yer[ad] = dict(kutu_eski=kt, X=X, Y=Y, kenar_uzaklik_eski=dict(sol=x0, ust=y0, sag=2400 - x1, alt=3000 - y1),
                       kutu_yeni=carp(out, R, kt, X, Y)[0])
    out = np.clip(out, 0, 255).astype(np.uint8)
    son, fark = ogeli_tum(bp, "timeless", out, S)
    return son, fark, p, yer


def ogeli_tum(bp, fn, img, S):
    son = img.copy()
    b, fark = ogeli_blok(bp, fn, img[OY:OY + 4500], S)
    son[OY:OY + 4500] = b
    f = np.zeros(img.shape[:2], bool); f[OY:OY + 4500] = fark
    return son, f


def cerceve_olc(e):
    g = lum(e)
    prof = {"sol": g[800:2200, 60:140].mean(0), "sag": g[800:2200, 2260:2340].mean(0), "ust": g[60:130, 600:1800].mean(1),
            "alt": g[2860:2940, 600:1800].mean(1)}
    bas = {"sol": 60, "sag": 2260, "ust": 60, "alt": 2860}
    r = {}
    for ad, p in prof.items():
        z = np.median(np.r_[p[:8], p[-8:]]); pr = z - p; i = int(np.argmin(p))
        w = np.where(pr >= pr[i] / 2, pr, 0); c = bas[ad] + (w * np.arange(len(p))).sum() / w.sum()
        uz = c if ad in ("sol", "ust") else (2399 - c if ad == "sag" else 2999 - c)
        r[ad] = dict(merkez=round(float(c), 2), kenar_uzaklik=round(float(uz), 2), fwhm=int((pr >= pr[i] / 2).sum()))
    x = int(round(r["sol"]["merkez"]))
    cizgi = e[1000:2000, x].astype(np.float32).mean(0); kag = e[1000:2000, x - 20:x - 12].reshape(-1, 3).astype(np.float32).mean(0)
    r["oran_rgb"] = (cizgi / kag).round(4).tolist()
    r["yan_pay"] = round((r["sol"]["kenar_uzaklik"] + r["sag"]["kenar_uzaklik"]) / 2, 2)
    r["fwhm"] = float(np.median([r[k]["fwhm"] for k in ("sol", "sag", "ust", "alt")]))
    return r


def cerceve_ciz(img, olc):
    """dort kenar payi ESIT = 8x10 yan payi x 1,5 (cizgi merkezi, piksel merkezi koordinati); Gauss profil FWHM x 1,5; carpim orani."""
    H, W = img.shape[:2]
    m = olc["yan_pay"] * K
    sig = olc["fwhm"] * K / 2.355
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    x0, y0, x1, y1 = m, m, W - 1 - m, H - 1 - m
    dx = np.maximum(np.maximum(x0 - xx, xx - x1), 0); dy = np.maximum(np.maximum(y0 - yy, yy - y1), 0)
    dis = np.hypot(dx, dy)
    ic = np.minimum(np.minimum(xx - x0, x1 - xx), np.minimum(yy - y0, y1 - yy))
    d = np.where((dx > 0) | (dy > 0), dis, ic)
    w = np.exp(-d ** 2 / (2 * sig ** 2))
    R = 1 - (1 - np.float32(olc["oran_rgb"]))[None, None] * w[..., None]
    return np.clip(img.astype(np.float32) * R, 0, 255).astype(np.uint8), dict(pay_px=round(m, 2), sigma=round(sig, 3))


def cerceve_kapi(img):
    g = lum(img); H, W = g.shape
    r = {}
    for ad, p, bas in (("sol", g[1500:3900, 100:260].mean(0), 100), ("sag", g[1500:3900, W - 260:W - 100].mean(0), W - 260),
                       ("ust", g[100:260, 900:2700].mean(1), 100), ("alt", g[H - 260:H - 100, 900:2700].mean(1), H - 260)):
        z = np.median(np.r_[p[:10], p[-10:]]); pr = z - p; i = int(np.argmin(p))
        w = np.where(pr >= pr[i] / 2, pr, 0); c = bas + (w * np.arange(len(p))).sum() / w.sum()
        r[ad] = round(float(c if ad in ("sol", "ust") else ((W - 1 - c) if ad == "sag" else (H - 1 - c))), 2)
    r["fark_max"] = round(max(r.values()) - min(r.values()), 3)
    r["pass_"] = bool(r["fark_max"] <= 1.0)
    return r


def kemer_maske(a, duz):
    return np.abs(a.astype(np.float32) - np.float32(duz)).max(2) > 25


# ------------------------------------------------------------------ main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kod", required=True); ap.add_argument("--doku-dizin", required=True); ap.add_argument("--esrgan", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--pair", default="CANCER_LIBRA")
    ap.add_argument("--n1", default="EMMA"); ap.add_argument("--n2", default="JAMES"); ap.add_argument("--hizli", action="store_true")
    ap.add_argument("--stiller", default="Timeless,FirstPage,Layers,Botanical")
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    S = B3.BY_SCALE
    bp = B3.by_poster(a.kod, S, a.pair, a.n1, a.n2)
    bp1 = B3.by_poster(a.kod, 1, a.pair, a.n1, a.n2)
    rap = dict(hizli_yerel=a.hizli, by_scale=S, esik=dict(korelasyon=KORELASYON, kazanc=KAZANC, kayma=KAYMA, afin_xy=AFIN, cerceve_px=1.0))
    eski = lambda n: np.asarray(Image.open(Path(a.kod, Z, f"{n}_8x10_300ppi.png")).convert("RGB"))  # noqa: E731
    kontak = []
    stiller = a.stiller.split(",")
    t0 = time.time()

    def kayit(ad, img, e, fn, fark=None):
        Image.fromarray(img).save(out / f"{ad}_12x18.jpg", quality=95, subsampling=0, dpi=(300, 300))
        s8 = ogeler(bp1, e, fn)
        kontak.append((ad, s8, img))
        print(f"{ad} tamam ({time.time() - t0:.0f}s)", flush=True)

    if "Timeless" in stiller:
        e = eski("2_Timeless")
        zem, yon = doku(Path(a.doku_dizin, "2_Timeless_2x3_kaynak.png"), a.esrgan, a.hizli)
        son, fark, p, yer = timeless(e, zem, bp, S)
        har = cv2.dilate(fark.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
        tum_yeni = np.zeros(son.shape[:2], bool)
        for ad, y in yer.items():
            X0, Y0, X1, Y1 = y["kutu_yeni"]
            mm = cv2.resize(p[ad][y["kutu_eski"][1]:y["kutu_eski"][3], y["kutu_eski"][0]:y["kutu_eski"][2]].astype(np.uint8),
                            (X1 - X0, Y1 - Y0), interpolation=cv2.INTER_NEAREST) > 0
            a0, b0 = max(0, -X0), max(0, -Y0); a1, b1 = min(X1 - X0, 3600 - X0), min(Y1 - Y0, 5400 - Y0)
            tum_yeni[Y0 + b0:Y0 + b1, X0 + a0:X0 + a1] |= mm[b0:b1, a0:a1]
        har_o = (cv2.dilate(tum_yeni.astype(np.uint8), np.ones((21, 21), np.uint8)) > 0) | har
        kap = {ad: susleme_kapi(e, son, p[ad], y["kutu_eski"], y["X"], y["Y"], har_o) for ad, y in yer.items()}
        kes = int((cv2.dilate(tum_yeni.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & har).sum())
        rap["Timeless"] = dict(zemin=yon, yerlesim=yer, kapi=kap, susleme_oge_kesisim_px=kes,
                               pass_=bool(all(v["pass_"] for v in kap.values()) and kes == 0 and set(yer) == {"yay", "dal_sol_ust", "dal_sol_alt", "dal_sag_alt"}))
        kayit("Timeless", son, e, "timeless")

    if "FirstPage" in stiller:
        e = eski("3_FirstPage")
        zem, yon = doku(Path(a.doku_dizin, "3_FirstPage_2x3_kaynak.png"), a.esrgan, a.hizli)
        o = cerceve_olc(e)
        z, rc = cerceve_ciz(zem, o)
        son, fark = ogeli_tum(bp, "first_page", z, S)
        kc = cerceve_kapi(son)
        rap["FirstPage"] = dict(zemin=yon, cerceve_8x10=o, cerceve=rc, cerceve_kapi_12x18=kc,
                                beklenen_pay=round(o["yan_pay"] * K, 2), pass_=kc["pass_"] and abs(kc["sol"] - o["yan_pay"] * K) <= 1.0)
        kayit("FirstPage", son, e, "first_page")

    if "Layers" in stiller:
        e = eski("4_Layers")
        duz = np.median(e[2600:2950, 800:1600].reshape(-1, 3), 0)
        km = kemer_maske(e, duz)
        # ---- A KIRP (x1,8 -> 4320x5400, iki yandan 360)
        bgA = cv2.resize(e, (4320, 5400), interpolation=cv2.INTER_LANCZOS4)
        buyuk = cv2.resize(e, (2400 * S, 3000 * S), interpolation=cv2.INTER_LANCZOS4)
        ciz = cv2.resize(ogeler(bp, buyuk, "layers"), (4320, 5400), interpolation=cv2.INTER_AREA)
        geri = cv2.resize(buyuk, (4320, 5400), interpolation=cv2.INTER_AREA)
        fA = (np.abs(ciz.astype(np.int16) - geri.astype(np.int16)).max(2) > 2)
        mk = cv2.GaussianBlur(cv2.dilate(fA.astype(np.float32), np.ones((5, 5), np.uint8)), (0, 0), 1.5)[..., None]
        tamA = np.clip(bgA * (1 - mk) + ciz * mk, 0, 255).astype(np.uint8)
        A = tamA[:, 360:3960].copy()
        kmA = cv2.resize(km.astype(np.uint8), (4320, 5400), interpolation=cv2.INTER_NEAREST) > 0
        kesik = np.zeros(kmA.shape, bool); kesik[:, :360] = True; kesik[:, 3960:] = True
        rap["Layers_A"] = dict(olcek=1.8, kirpim_px_yan=360, kirpilan_bantta_oge_px=int((fA & kesik).sum()),
                               kemer_kesilen_px=int((kmA & kesik).sum()), kemer_toplam_px=int(kmA.sum()),
                               kemer_kesilen_oran=round(float((kmA & kesik).sum() / max(kmA.sum(), 1)), 4),
                               kemer_kesilen_eski_8x10_px_yan=200, sift=sift_afin(lum(e), lum(A)))
        rap["Layers_A"]["pass_"] = bool(rap["Layers_A"]["kirpilan_bantta_oge_px"] == 0 and rap["Layers_A"]["sift"].get("pass_", False))
        Image.fromarray(A).save(out / "Layers_A_12x18.jpg", quality=95, subsampling=0, dpi=(300, 300))
        # ---- B USTE SABIT (x1,5 uste; duz bolge tek parca x2,5)
        ust = cv2.resize(e, (3600, 4500), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
        duz_par = e[DUZ_Y:3000]
        if a.hizli:
            d2 = cv2.resize(duz_par, (4800, 1800), interpolation=cv2.INTER_LANCZOS4); dy = "lanczos (YEREL)"
        else:
            d2, s_ = B3.esrgan(duz_par, a.esrgan); dy = f"Real-ESRGAN x{s_}"
        s2 = (5400 - DUZ_Y * K) / (3000 - DUZ_Y)                          # duz bolge esit olcegi (2,5)
        dw = round(2400 * s2)
        alt = cv2.resize(d2, (dw, round((3000 - DUZ_Y) * s2)), interpolation=cv2.INTER_AREA)
        x0 = (dw - 3600) // 2
        alt = alt[:, x0:x0 + 3600].astype(np.float32)
        Bz = np.zeros((5400, 3600, 3), np.float32); Bz[:4500] = ust
        y_s = round(DUZ_Y * K)
        rampa = 120
        w = np.clip((np.arange(5400) - y_s) / rampa, 0, 1)[:, None, None]
        tam_alt = np.zeros_like(Bz); tam_alt[y_s:y_s + alt.shape[0]] = alt[:5400 - y_s]
        Bz = Bz * (1 - w) + tam_alt * w
        Bz[:y_s] = ust[:y_s]
        Bz = np.clip(Bz, 0, 255).astype(np.uint8)
        b, fB = ogeli_blok(bp, "layers", Bz[:4500], S)
        B = Bz.copy(); B[:4500] = b
        fBt = np.zeros((5400, 3600), bool); fBt[:4500] = fB
        kmB = np.zeros((5400, 3600), bool); kmB[:4500] = cv2.resize(km.astype(np.uint8), (3600, 4500), interpolation=cv2.INTER_NEAREST) > 0
        tasarim = np.where(fBt)
        rap["Layers_B"] = dict(ust_olcek=1.5, duz_y_eski=DUZ_Y, duz_olcek=round(s2, 4), duz_doku=dy, gecis_satir=[y_s, y_s + rampa],
                               eklenen_bantta_oge_px=int(fBt[y_s:].sum()), eklenen_bantta_kemer_px=int(kmB[y_s:].sum()),
                               tasarim_kutu=[int(tasarim[1].min()), int(tasarim[0].min()), int(tasarim[1].max()), int(tasarim[0].max())],
                               tasarim_alt_bosluk_px=int(5400 - 1 - tasarim[0].max()), kemer_ic_tepe_y=None,
                               sift_ust=sift_afin(lum(e[:DUZ_Y]), lum(B[:y_s])))
        rap["Layers_B"]["pass_"] = bool(rap["Layers_B"]["eklenen_bantta_kemer_px"] == 0 and rap["Layers_B"]["sift_ust"].get("pass_", False))
        Image.fromarray(B).save(out / "Layers_B_12x18.jpg", quality=95, subsampling=0, dpi=(300, 300))
        s8 = ogeler(bp1, e, "layers")
        kontak.append(("Layers_A", s8, A)); kontak.append(("Layers_B", s8, B))
        print(f"Layers tamam ({time.time() - t0:.0f}s)", flush=True)

    if "Botanical" in stiller:
        e = eski("5_Botanical")
        zem, yon = doku(Path(a.doku_dizin, "5_Botanical_2x3_kaynak.png"), a.esrgan, a.hizli)
        p, km_e, kk_e = botanical_parcalar(e)
        km_n, kk_n = kagit(zem)
        out_ = zem.astype(np.float32); yer = {}
        tum = np.zeros(e.shape[:2], bool)
        for v in p.values():
            tum |= v
        for ad, m in p.items():
            R, _ = oran(e, m, haric_ek=(tum & ~m) | ~km_e)
            kt = kutu(m); x0, y0, x1, y1 = kt
            if ad == "cicek_sag_ust":
                X = round(kk_n[2] - (kk_e[2] - x0) * K); Y = round(kk_n[1] + (y0 - kk_e[1]) * K)
            else:
                X = round(kk_n[0] + (x0 - kk_e[0]) * K); Y = round(kk_n[3] - (kk_e[3] - y0) * K)
            yer[ad] = dict(kutu_eski=kt, X=X, Y=Y, kagit_eski=kk_e, kagit_yeni=kk_n, kutu_yeni=carp(out_, R, kt, X, Y)[0])
        z = np.clip(out_, 0, 255).astype(np.uint8)
        son, fark = ogeli_tum(bp, "botanical", z, S)
        har = cv2.dilate(fark.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
        tum_yeni = np.zeros(son.shape[:2], bool)
        for ad, y in yer.items():
            X0, Y0, X1, Y1 = y["kutu_yeni"]
            mm = cv2.resize(p[ad][y["kutu_eski"][1]:y["kutu_eski"][3], y["kutu_eski"][0]:y["kutu_eski"][2]].astype(np.uint8),
                            (X1 - X0, Y1 - Y0), interpolation=cv2.INTER_NEAREST) > 0
            a0, b0 = max(0, -X0), max(0, -Y0); a1, b1 = min(X1 - X0, 3600 - X0), min(Y1 - Y0, 5400 - Y0)
            tum_yeni[Y0 + b0:Y0 + b1, X0 + a0:X0 + a1] |= mm[b0:b1, a0:a1]
        har_o = (cv2.dilate(tum_yeni.astype(np.uint8), np.ones((21, 21), np.uint8)) > 0) | har | ~km_n
        kap = {ad: susleme_kapi(e, son, p[ad], y["kutu_eski"], y["X"], y["Y"], har_o) for ad, y in yer.items()}
        kes = int((cv2.dilate(tum_yeni.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & har).sum())
        rap["Botanical"] = dict(zemin=yon, yerlesim=yer, kapi=kap, susleme_oge_kesisim_px=kes,
                                pass_=bool(all(v["pass_"] for v in kap.values()) and kes == 0 and set(yer) == {"cicek_sag_ust", "cicek_sol_alt"}))
        kayit("Botanical", son, e, "botanical")

    # ---- kontak: her stil eski 8x10 | yeni 12x18, ayni yukseklik
    h = 900
    sat = []
    for ad, s8, s12 in kontak:
        a8 = Image.fromarray(s8).resize((round(2400 * h / 3000), h), Image.LANCZOS)
        a12 = Image.fromarray(s12).resize((round(3600 * h / 5400), h), Image.LANCZOS)
        r = Image.new("RGB", (a8.width + a12.width + 60, h + 20), (230, 230, 230)); r.paste(a8, (20, 10)); r.paste(a12, (a8.width + 40, 10))
        sat.append(r)
    if sat:
        Wk = max(r.width for r in sat)
        kt = Image.new("RGB", (Wk, sum(r.height for r in sat)), (230, 230, 230)); y = 0
        for r in sat:
            kt.paste(r, (0, y)); y += r.height
        kt.save(out / "KONTAK_STIL4.jpg", quality=88)
        kt.resize((kt.width * 1400 // kt.height, 1400), Image.LANCZOS).save(out / "ONIZLEME_KUCUK.jpg", quality=75)
    rap["sonuc"] = "PASS" if all(v.get("pass_") for k, v in rap.items() if isinstance(v, dict) and "pass_" in v) else "FAIL"
    (out / "OLCUM.json").write_text(json.dumps(rap, indent=1, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x)), encoding="utf-8")
    print(json.dumps({k: (v.get("pass_") if isinstance(v, dict) else v) for k, v in rap.items()}, default=str))
    return 0 if rap["sonuc"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
