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
  (Layers B Serdar 1 Kas F 3. kosu karariyla birakildi.)
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
KORELASYON, KAZANC, KAYMA, AFIN = 0.98, (0.95, 1.05), 0.5, 0.01
YAKIN = {"Timeless": [(0, 4800), (3000, 4800), (1500, 500)], "FirstPage": [(0, 0), (3000, 4800)], "Botanical": [(2900, 100), (100, 4600)]}
KIRP_ORAN = 0.01       # ONERI (Serdar onayi yok): susleme piksellerinin en cok %1'i 255'te kirpilabilir
PROFIL_FARK = 0.05     # ONERI: cerceve en koyu oran farki (kanal) <= 0,05 ve FWHM farki <= 1 px @8x10 (yerel vekil olcum 0,019)
PROFIL_ORNEK = 0.08    # ONERI (G1, d2a38e47; tahmin): cerceve profili ofset basina oran farki (kanal) <= 0,08
DIS_ORAN = 0.02        # ONERI: maske disinda kalan susleme koyuluk kutlesi maske icinin en cok %2'si
KAGIT_KENAR = 31       # Botanical maske disi halka: kagit maskesi 31x31 cekirdekle (yaricap 15 px) asindirilir (yirtik kenar bandi; TAHMIN)


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
        # inceleme 1 Kas bulgu 12: son secenek sessizce dal_sag_alt'a katiyordu; atanamayan buyuk parca "diger" olur ve kapi FAIL verir
        ad = ("yay" if w > 1200 else "dal_sol_ust" if cx < 1200 and cy < 1500 else "dal_sol_alt" if cx < 1200 and cy >= 1500
              else "dal_sag_alt" if cx >= 1200 and cy >= 1500 else "diger")
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
    # inceleme 1 Kas E5: kutu = gercek kenar; orta %60'lik satir / sutunlarda ilk / son kagit pikselinin MEDYANI (tirtik ortalanir)
    sat_ = np.arange(int(H * 0.2), int(H * 0.8)); sut_ = np.arange(int(W * 0.2), int(W * 0.8))
    sol = np.median([np.argmax(k[y]) for y in sat_]); sag = np.median([W - 1 - np.argmax(k[y][::-1]) for y in sat_])
    ust = np.median([np.argmax(k[:, x]) for x in sut_]); alt = np.median([H - 1 - np.argmax(k[:, x][::-1]) for x in sut_])
    return k, [int(round(sol)), int(round(ust)), int(round(sag)), int(round(alt))]


def botanical_parcalar(e):
    km, kk = kagit(e)
    # inceleme 1 Kas E4: koyuluk yalniz KAGIT zeminine gore (medyan 61 px adacayi karisiyordu); kagit ici 7 px asindirma (31 px dallari
    # kenarda 16 px iceride duz kesiyordu)
    d = lum(YR.yerel_zemin(e, ~km).clip(0, 255)) - lum(e)
    sat = e.max(2).astype(np.float32) - e.min(2)
    s0 = float(np.median(sat[km]))
    # yerel deneme 1 Kas: kagidin tirtikli kenari / adacayi zemin maskeye karisiyordu (sol alt kutu x 19..2357) -> yalniz kagit ici
    ic = cv2.erode(km.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
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
    # inceleme 1 Kas E3: maske icinde kagit gibi pikseller (|R - 1| kagit dokusu duzeyinde) eski kagit liflerini tasimasin:
    # sapma kagidin (maske ve haric disi) |R - 1| p50..p99 araliginda yumusakca 0'a cekilir
    kag = ~(cv2.dilate(har.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0)
    sap = np.abs(R - 1).max(2)
    t1, t2 = (float(np.percentile(sap[kag], 50)), float(np.percentile(sap[kag], 99))) if kag.any() else (0.0, 0.0)
    g = np.clip((sap - t1) / max(t2 - t1, 1e-6), 0, 1)[..., None]
    w = cv2.GaussianBlur(cv2.dilate(maske.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32), (0, 0), 1.5)
    oran.son = dict(kagit_sapma_p50=round(t1, 4), kagit_sapma_p99=round(t2, 4),
                    maskede_kagit_gibi_oran=round(float(((sap < t2) & maske).sum() / max(maske.sum(), 1)), 4))
    # F 3. kosu (Serdar 1 Kas "Timeless 255 kirpma"; inceleme: yayda cikti doygun 0,0134, eski 0,0055): kagittan PARLAK piksel (R > 1)
    # carpimla yeni (daha parlak) kagitta 255'i asiyordu. Parlak kanal artik kagidin 255'e kalan payina gore tasinir (S = (255 - eski) /
    # (255 - eski zemin); cikti = 255 - (255 - yeni) x S): eski zeminde tam eski degeri verir, 255'i asamaz, eskide 255 olan 255 kalir.
    S = np.clip((255.0 - e.astype(np.float32)) / np.maximum(255.0 - z, 1.0), 0, 1.5)
    gw = g * w[..., None]
    return (1 + (R - 1) * gw, 1 + (S - 1) * gw, (R > 1).astype(np.float32)), w


def kutu(m, pay=24):
    """goruntu sinirina KIRPILMIS kutu (yerel deneme 1 Kas: sinir disina tasan kutu kesik diziyi tek yonde esnetiyordu; SIFT sy 1,559)"""
    ys, xs = np.where(m)
    H, W = m.shape
    x0, y0 = max(0, int(xs.min()) - pay), max(0, int(ys.min()) - pay)
    x1, y1 = min(W, int(xs.max()) + pay + 1), min(H, int(ys.max()) + pay + 1)
    # cift koordinat: x 1,5 tam sayi olur (yerel deneme: (3000 - 2351) x 1,5 = 973,5 yuvarlamasi 0,5 px kayma veriyordu)
    return [x0 - x0 % 2, y0 - y0 % 2, min(W, x1 + x1 % 2), min(H, y1 + y1 % 2)]


def carp(dst, L, kt, X, Y):
    """oran katmanlarini (R carpim, S parlak pay, H parlak secici) kt kutusundan esit olcek K ile buyutup dst'ye (X, Y) sol ust kosesinden
    uygular; koyu kanal dst x R, parlak kanal 255 - (255 - dst) x S, H ile yumusak secim; tuval disi kirpilir."""
    R, S, Hs = L
    x0, y0, x1, y1 = kt
    w, h = round((x1 - x0) * K), round((y1 - y0) * K)
    r = cv2.resize(R[y0:y1, x0:x1], (w, h), interpolation=cv2.INTER_LANCZOS4)
    s_ = cv2.resize(S[y0:y1, x0:x1], (w, h), interpolation=cv2.INTER_LANCZOS4)
    hs = np.clip(cv2.resize(Hs[y0:y1, x0:x1], (w, h), interpolation=cv2.INTER_LINEAR), 0, 1)
    H, W = dst.shape[:2]
    a0, b0 = max(0, -X), max(0, -Y); a1, b1 = min(w, W - X), min(h, H - Y)
    d = dst[Y + b0:Y + b1, X + a0:X + a1]
    hh = hs[b0:b1, a0:a1]
    dst[Y + b0:Y + b1, X + a0:X + a1] = (1 - hh) * d * r[b0:b1, a0:a1] + hh * (255.0 - (255.0 - d) * s_[b0:b1, a0:a1])
    return [X, Y, X + w, Y + h], [X + a0, Y + b0, X + a1, Y + b1]


# ------------------------------------------------------------------ kapilar
def koyuluk(a, haric):
    z = YR.yerel_zemin(a, haric)
    return np.clip(1 - lum(a) / np.maximum(lum(z.clip(0, 255)), 1.0), 0, 1)


def faz(a, b, up=50):
    """numpy faz korelasyonu (Hann pencere). Denetim 1 Kas (F 3. kosu): 3 nokta parabol alt piksel kestirimi S bicimli yanliydi
    (oz-test: 0,25 -> 0,08-0,14; 0,55 -> 0,62-0,74; inceleme bulgu 9). Simdi tam sayi tepe etrafinda +-0,75 px bolge, 1/up px adimla
    ters DFT dogrudan hesaplanir (Guizar-Sicairos 2008 yontemi). cv2.phaseCorrelate kullanilmaz: OpenCV 5.0.0.93'te kirpim boyunun
    getOptimalDFTSize karsiligi tek sayi olan eksende ozdes girdide 0,50 px veriyor (650 -> 675, 1842 -> 1875)."""
    a = a.astype(np.float64); b = b.astype(np.float64); h, w = a.shape
    hn = np.outer(np.hanning(h), np.hanning(w))
    A = np.fft.fft2((a - a.mean()) * hn); B = np.fft.fft2((b - b.mean()) * hn)
    R = np.conj(A) * B; R /= np.maximum(np.abs(R), 1e-12)
    r = np.real(np.fft.ifft2(R))
    iy, ix = np.unravel_index(int(np.argmax(r)), r.shape)
    n = int(1.5 * up) + 1
    ys = iy + (np.arange(n) - n // 2) / up; xs = ix + (np.arange(n) - n // 2) / up
    Ey = np.exp(2j * np.pi * np.outer(ys, np.fft.fftfreq(h))); Ex = np.exp(2j * np.pi * np.outer(np.fft.fftfreq(w), xs))
    c = np.real(Ey @ R @ Ex)
    jy, jx = np.unravel_index(int(np.argmax(c)), c.shape)
    py, px = ys[jy], xs[jx]
    py = py - h if py > h / 2 else py; px = px - w if px > w / 2 else px
    return float(px), float(py), float(c[jy, jx] / (h * w))


def fourier_kaydir(a, dx, dy):
    h, w = a.shape
    return np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-2j * np.pi * (np.fft.fftfreq(w)[None, :] * dx + np.fft.fftfreq(h)[:, None] * dy))))


FAZ_TEST = (0.0, 0.25, 0.45, 0.5, 0.55, 1.0, 2.0)
FAZ_TEST_HATA = 0.05   # oz-test gecerlilik siniri (tahmin): bilinen kaymada en buyuk mutlak hata


def faz_oztest(De):
    """kapinin AYNI kirpimi ve AYNI koyuluk haritasi uzerinde bilinen kaymalar (x ve y); en buyuk hata"""
    hata = 0.0; satir = []
    for k in FAZ_TEST:
        for yon in ("x", "y"):
            dx, dy = (k, 0.0) if yon == "x" else (0.0, k)
            mx, my, _ = faz(De, fourier_kaydir(De, dx, dy))
            e_ = max(abs(mx - dx), abs(my - dy)); hata = max(hata, e_)
            satir.append([yon, k, round(mx, 3), round(my, 3)])
    return dict(en_buyuk_hata=round(hata, 4), esik=FAZ_TEST_HATA, pass_=bool(hata <= FAZ_TEST_HATA), olcumler=satir)


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


def susleme_kapi(e, out, maske_e, kt, X, Y, haric_out, kagit_ic=None):
    """bagimsiz: eski ve cikti koyulugu (1 - lum / yerel zemin) ayni yontemle; cikti kirpimi 1/1,5 INTER_AREA; maske >= 0,5 pikseller.
    kagit_ic (Botanical): maske disi halka yalniz kagit icinde olculur (F 3. kosu: halka kutlesinin cogu kagidin yirtik kenari / adacayi
    zemin; kagit disi px 2770 / 5137 ve 4728 / 5972, olcum 1 Kas)."""
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
    fz = faz_oztest(De)
    sift = sift_afin(lum(e[y0:y1, x0:x1]), lum(out[Y:Y + round(h * K), X:X + round(w * K)]))
    # E2: mutlak renk (Lab dE76) susleme cekirdeginde (koyuluk > 0,10) ve 255 kirpilan susleme pikseli; E4: maske DISINDA kalan susleme
    # (eski koyuluk > 0,08, maskeye 30 px yakin) koyuluk kutlesi / maske ici kutle
    o_k = cv2.resize(out[Y:Y + round(h * K), X:X + round(w * K)], (w, h), interpolation=cv2.INTER_AREA)
    lab = lambda a: cv2.cvtColor(a.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32) * [100 / 255, 1, 1] - [0, 128, 128]  # noqa: E731
    cek = maske_e[y0:y1, x0:x1] & (De > 0.10)
    dE = np.linalg.norm(lab(e[y0:y1, x0:x1]) - lab(o_k), axis=2)[cek] if cek.any() else np.zeros(1)
    mt = cv2.resize(maske_e[y0:y1, x0:x1].astype(np.uint8), (round(w * K), round(h * K)), interpolation=cv2.INTER_NEAREST) > 0
    o_t = out[Y:Y + round(h * K), X:X + round(w * K)]
    # inceleme 1 Kas (3. kosu oncesi): Lanczos taban ringing ile 255'e tasip doygun sayiliyordu; kanal bazinda DOGRUSAL taban.
    # Yeni kirpma = herhangi bir kanalda cikti >= 254 iken eskide AYNI kanal < 250 (eskide 250-253 bandindaki kanal da artik sayilir).
    eski_b = cv2.resize(e[y0:y1, x0:x1], (round(w * K), round(h * K)), interpolation=cv2.INTER_LINEAR)
    kirp = int((((o_t >= 254) & (eski_b < 250)).any(2) & mt).sum())
    # F 3. kosu (Serdar 1 Kas, "Timeless 255 kirpma"): ESKI tanim (ciktida >= 254 olan tum maske pikseli) eskinin KENDI doygun altin
    # parlakligini da sayiyordu (eski 8x10 susleme maskesinde >= 254 orani %0,5-2,7, olcum 1 Kas). Kapi: (a) yeni doyan px orani
    # <= KIRP_ORAN ve (b) cikti doygun orani - eski doygun orani (ayni maske, eski x1,5 Lanczos) <= KIRP_ORAN. ESKI tanim bilgi olarak yazilir.
    doy_o = float((o_t >= 254).any(2)[mt].mean()) if mt.any() else 0.0
    doy_e = float((eski_b >= 254).any(2)[mt].mean()) if mt.any() else 0.0
    me = maske_e[y0:y1, x0:x1]
    yak = (cv2.dilate(me.astype(np.uint8), np.ones((61, 61), np.uint8)) > 0) & ~(cv2.dilate(me.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0)
    dis_eski_tanim = float(De[yak & (De > 0.08)].sum() / max(De[me].sum(), 1e-6))     # G1 tanimi (bilgi): taban yok, kagit disi dahil
    ki = kagit_ic[y0:y1, x0:x1] if kagit_ic is not None else np.ones_like(me)
    yak &= ki
    # taban: ayni yogunluk olcusu maskeden 120-180 px uzak (yalniz kagit lifi / kirinti); asim = yakin - taban (alan oranli)
    uzak = (cv2.dilate(me.astype(np.uint8), np.ones((361, 361), np.uint8)) > 0) & ~(cv2.dilate(me.astype(np.uint8), np.ones((241, 241), np.uint8)) > 0) & ki
    yog = lambda b: float(De[b & (De > 0.08)].sum() / max(b.sum(), 1))  # noqa: E731
    dis = max(0.0, (yog(yak) - (yog(uzak) if uzak.any() else 0.0))) * float(yak.sum()) / max(float(De[me].sum()), 1e-6)
    d = dict(korelasyon=round(float(np.corrcoef(xe, xo)[0, 1]), 4), kazanc=round(float((xe * xo).sum() / max((xe * xe).sum(), 1e-9)), 4),
             ort_mutlak_fark=round(float(np.abs(xo - xe).mean()), 4), px=int(m.sum()), kayma=[round(dx, 3), round(dy, 3)], faz_tepe=round(r, 3),
             faz_oztest=fz,
             sift=sift, dE76_cekirdek=dict(medyan=round(float(np.median(dE)), 2), p95=round(float(np.percentile(dE, 95)), 2)),
             kirpilan_255_px=kirp, kirpilan_255_oran=round(kirp / max(int(mt.sum()), 1), 5),
             doygun_oran_cikti=round(doy_o, 5), doygun_oran_eski=round(doy_e, 5), doygun_fazla=round(doy_o - doy_e, 5),
             kirp_eski_tanim_bilgi=round(doy_o, 5),
             maske_disi_susleme_kutle_orani=round(dis, 4), maske_disi_eski_tanim_bilgi=round(dis_eski_tanim, 4))
    d["pass_"] = bool(d["korelasyon"] >= KORELASYON and KAZANC[0] <= d["kazanc"] <= KAZANC[1] and max(abs(dx), abs(dy)) < KAYMA
                      and sift.get("pass_", False) and d["kirpilan_255_oran"] <= KIRP_ORAN and d["doygun_fazla"] <= KIRP_ORAN and dis <= DIS_ORAN
                      and fz["pass_"])
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
        if ad == "diger":
            continue
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
                       kutu_yeni=carp(out, R, kt, X, Y)[0], oran_katmani=dict(oran.son))
    out = np.clip(out, 0, 255).astype(np.uint8)
    son, fark = ogeli_tum(bp, "timeless", out, S)
    return son, fark, p, yer


def ogeli_tum(bp, fn, img, S):
    son = img.copy()
    b, fark = ogeli_blok(bp, fn, img[OY:OY + 4500], S)
    son[OY:OY + 4500] = b
    f = np.zeros(img.shape[:2], bool); f[OY:OY + 4500] = fark
    return son, f


PROFIL_T = 14          # 8x10 px: cizgi merkezinden +-14 profil (olcum 1 Kas: cizgi FWHM 7-8, hale +-10'a kadar)


def yan_profil(img, yan, ara, uz):
    """img'de bir kenar cizgisinin ortalama profili: ara = (bas, son) arama araligi (kenara dik), uz = (bas, son) cizgi boyunca orta
    kisim. Donus: alt piksel merkez (goruntu koordinati), kagit rengi, oran profili (ofset -> RGB oran) fonksiyonu icin ornekler."""
    a = img.astype(np.float32)
    if yan in ("sol", "sag"):
        bant = a[uz[0]:uz[1], ara[0]:ara[1]].mean(0)
    else:
        bant = a[ara[0]:ara[1], uz[0]:uz[1]].mean(1)
    g = bant @ np.float32([0.299, 0.587, 0.114])
    kag = np.median(np.r_[bant[:6], bant[-6:]], 0)
    pr = lum(kag[None])[0] - g; i = int(np.argmax(pr))
    w = np.where(pr >= pr[i] / 2, pr, 0); c = ara[0] + (w * np.arange(len(g))).sum() / w.sum()
    ofs = ara[0] + np.arange(len(g)) - c
    return float(c), kag, ofs, bant / kag[None]


def cerceve_olc(e):
    H, W = e.shape[:2]
    r = {}
    for yan, ara, uz in (("sol", (60, 180), (600, 2400)), ("sag", (2220, 2340), (600, 2400)), ("ust", (60, 180), (500, 1900)),
                         ("alt", (2820, 2940), (500, 1900))):
        c, kag, ofs, oran_ = yan_profil(e, yan, ara, uz)
        uzak = c if yan in ("sol", "ust") else ((W - 1 - c) if yan == "sag" else (H - 1 - c))
        m = np.abs(ofs) <= PROFIL_T
        r[yan] = dict(merkez=round(c, 2), kenar_uzaklik=round(float(uzak), 2), ofs=ofs[m].round(3).tolist(), oran=oran_[m].round(4).tolist(),
                      en_koyu_oran=oran_[m].min(0).round(4).tolist(), kagit=kag.round(1).tolist())
    r["yan_pay"] = round((r["sol"]["kenar_uzaklik"] + r["sag"]["kenar_uzaklik"]) / 2, 2)
    r["kose_tasma_8x10"] = kose_tasma(e, (r["sol"]["merkez"], r["sag"]["merkez"]), (r["ust"]["merkez"], r["alt"]["merkez"]), 1.0)      # Serdar 1 Kas: 12x18 kose = 0 ve eski 8x10 ile ayni (8x10 = 0 olmali)
    return r


def cerceve_ciz(img, olc):
    """Her kenarin OLCULEN 8x10 oran profili (ofset x 1,5, dogrusal ara deger; acik kabartma omuzlari > 1 DAHIL). F 3. kosu (Serdar 1 Kas):
    2. kosuda (a) cizgiler koseden profil penceresi kadar (~21 px) uzayip "+" yapiyordu, (b) np.minimum oran > 1 omuzlari atiyordu
    (ornek basina profil farki 0,08-0,12, omuz ofsetlerinde). Simdi her piksel icin dikdortgene isaretli L-sonsuz uzaklik
    s = max(m - x, x - xs, m - y, y - ya) (icerde < 0, disarida > 0; disarida kose KARE) ve s'yi veren kenarin profili uygulanir:
    cizgi hicbir yerde dik cizginin disina tasmaz. Dort kenar payi esit = 8x10 yan payi x 1,5."""
    H, W = img.shape[:2]
    m = olc["yan_pay"] * K
    xs_, ya_ = W - 1 - m, H - 1 - m
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.stack([m - xx, xx - xs_, m - yy, yy - ya_])            # sol, sag, ust, alt
    k = np.argmax(d, 0); s_ = np.take_along_axis(d, k[None], 0)[0]
    R = np.ones((H, W, 3), np.float32)
    KG = np.full((H, W, 3), 230.0, np.float32)                      # 8x10 kagit rengi (kenar basina; parlak omuz payi icin)
    yari = PROFIL_T * K
    bolge = np.abs(s_) <= yari
    for i, yan in enumerate(("sol", "sag", "ust", "alt")):
        ofs = np.array(olc[yan]["ofs"]) * K; orn = np.array(olc[yan]["oran"])
        sec = bolge & (k == i)
        o = (-s_[sec]) if yan in ("sol", "ust") else s_[sec]           # yan_profil ofseti: koordinat artan yonde (sol / ust icin iceri)
        for c in range(3):
            R[..., c][sec] = np.interp(o, ofs, orn[:, c], left=1, right=1)
            KG[..., c][sec] = olc[yan]["kagit"][c]
    # parlak kabartma omzu (oran > 1): carpim yeni kagitta 255'i asiyordu (inceleme: R kanali bandin %2,5'inde >= 254); 8x10'daki
    # 255'e kalan pay orani korunur: cikti = 255 - (255 - yeni) x (255 - kagit x oran) / (255 - kagit)
    a = img.astype(np.float32)
    S = np.clip((255.0 - KG * R) / np.maximum(255.0 - KG, 1.0), 0, 1)
    son = np.where(R > 1, 255.0 - (255.0 - a) * S, a * R)
    return np.clip(son, 0, 255).astype(np.uint8), dict(pay_px=round(m, 2), profil="olculen 8x10 (kenar basina, omuz dahil)",
                                                                                kose="L-sonsuz (kare), tasma yok")


KOSE_PEN, KOSE_CEKIRDEK, KOSE_KOYU = 40, 7, 25   # 8x10 px: kose penceresi, cizgi koyu cekirdegi yari genisligi (profil: oran ofset +-5,4'te
#                                                  ~1'e doner, olcum 1 Kas), kagittan koyu esigi (lum). 12x18'de x1,5.


def kose_tasma(img, xs, ys, olcek=1.0):
    """dort kosede, cizgi koyu cekirdeginin DISINDA (kenar ve kose yonunde) kagittan KOSE_KOYU kadar koyu piksel sayisi. Serdar 1 Kas:
    kapi = 0 ve eski 8x10 ile ayni."""
    L = lum(img)
    pen, ck = KOSE_PEN * olcek, KOSE_CEKIRDEK * olcek
    r = {}
    # inceleme: merkez her kenarin OLCULEN cizgi merkezi (8x10 ust / alt 116,89 / 119,53; yan_pay ortalamasi 2 px kaydiriyordu)
    (xl, xr), (yu, ya) = xs, ys
    for ad, (cx, cy, sx, sy) in (("sol_ust", (xl, yu, -1, -1)), ("sag_ust", (xr, yu, 1, -1)), ("sol_alt", (xl, ya, -1, 1)),
                                 ("sag_alt", (xr, ya, 1, 1))):
        x0, x1 = int(round(cx - pen)), int(round(cx + pen)) + 1; y0, y1 = int(round(cy - pen)), int(round(cy + pen)) + 1
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        dis = ((xx - cx) * sx > ck) | ((yy - cy) * sy > ck)              # dik cizgilerden en az birinin disinda
        ic = ((xx - cx) * -sx > 2 * ck) & ((yy - cy) * -sy > 2 * ck)     # kagit referansi: cerceve ici kose bolgesi
        P = L[y0:y1, x0:x1]
        kag = float(np.median(P[ic]))
        r[ad] = int(((P < kag - KOSE_KOYU) & dis).sum())
    r["toplam"] = sum(r.values())
    return r


def cerceve_kapi(img, olc=None, ara=60):
    """dort kenar payi (cizgi merkezi, alt piksel) esit mi; olc verilirse cizgi profili 8x10 ile kiyas (ofset / 1,5'te oran farki)."""
    H, W = img.shape[:2]
    m = olc["yan_pay"] * K if olc else 180
    r = {}; prof = {}
    for yan, a_, uz in (("sol", (int(m - ara), int(m + ara)), (900, 4500)), ("sag", (int(W - 1 - m - ara), int(W - 1 - m + ara)), (900, 4500)),
                        ("ust", (int(m - ara), int(m + ara)), (800, 2800)), ("alt", (int(H - 1 - m - ara), int(H - 1 - m + ara)), (800, 2800))):
        c, kag, ofs, oran_ = yan_profil(img, yan, a_, uz)
        r[yan] = round(float(c if yan in ("sol", "ust") else ((W - 1 - c) if yan == "sag" else (H - 1 - c))), 2)
        if olc:
            o8 = np.array(olc[yan]["ofs"]); r8 = np.array(olc[yan]["oran"])
            r12 = np.stack([np.interp(o8 * K, ofs, oran_[:, k]) for k in range(3)], 1)
            ince = np.arange(o8.min(), o8.max(), 0.05)
            def fwhm(o, r):
                k = 1 - np.interp(ince, o, r @ np.float32([0.299, 0.587, 0.114])); return float((k >= k.max() / 2).sum() * 0.05)
            prof[yan] = dict(oran_fark_max_bilgi=round(float(np.abs(r12 - r8).max()), 4), en_koyu_8x10=r8.min(0).round(3).tolist(),
                             en_koyu_12x18=r12.min(0).round(3).tolist(), en_koyu_fark=round(float(np.abs(r12.min(0) - r8.min(0)).max()), 4),
                             fwhm_8x10=round(fwhm(o8, r8), 2), fwhm_12x18_olcekli=round(fwhm(ofs / K, oran_), 2))
    r["fark_max"] = round(max(r[k] for k in ("sol", "sag", "ust", "alt")) - min(r[k] for k in ("sol", "sag", "ust", "alt")), 3)
    r["beklenen_fark_max"] = round(max(abs(r[k] - m) for k in ("sol", "sag", "ust", "alt")), 3) if olc else None   # inceleme bulgu: her kenar
    r["profil"] = prof
    r["kose_tasma_px"] = kose_tasma(img, (r["sol"], W - 1 - r["sag"]), (r["ust"], H - 1 - r["alt"]), K)
    if olc:
        r["kose_tasma_8x10_px"] = olc.get("kose_tasma_8x10")
    # F 3. kosu: G1 ornek basina profil farki <= PROFIL_ORNEK (onceki adiyla oran_fark_max) yeniden kapida; en koyu + FWHM de kalir
    r["pass_"] = bool(r["fark_max"] <= 1.0 and (r["beklenen_fark_max"] is None or r["beklenen_fark_max"] <= 1.0)
                      and r["kose_tasma_px"]["toplam"] == 0
                      and (not prof or all(v["oran_fark_max_bilgi"] <= PROFIL_ORNEK and v["en_koyu_fark"] <= PROFIL_FARK
                                           and abs(v["fwhm_12x18_olcekli"] - v["fwhm_8x10"]) <= 1.0 for v in prof.values())))
    return r


def kemer_maske(a, duz, esik=25):
    return np.abs(a.astype(np.float32) - np.float32(duz)).max(2) > esik


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
    rap = dict(hizli_yerel=a.hizli, by_scale=S, esik=dict(korelasyon=KORELASYON, kazanc=KAZANC, kayma=KAYMA, afin_xy=AFIN, cerceve_px=1.0,
                                                           kirp_oran_oneri=KIRP_ORAN, dis_oran_oneri=DIS_ORAN, profil_fark_oneri=PROFIL_FARK,
                                                           profil_ornek_oneri=PROFIL_ORNEK, faz_test_hata_oneri=FAZ_TEST_HATA,
                                                           kose=dict(pencere=KOSE_PEN, cekirdek=KOSE_CEKIRDEK, koyu_lum=KOSE_KOYU, tasma_px=0),
                                                           botanical_kagit_kenar_asindirma_cekirdek=KAGIT_KENAR),
               olcum_kaynakli_sabitler=dict(botanical_yesil="G-R yaprak -9..-14, kirinti -21..-31",
                                            oneri_sabitler="histerezis 10/4 (Timeless), 25/10, 18/20 (Botanical), alan 3000 / 600, yakinlik 450, "
                                                           "asindirma 7, kemer 25, rampa 120: olcumle turetilmedi (oneri)"))
    yakin = []
    eski = lambda n: np.asarray(Image.open(Path(a.kod, Z, f"{n}_8x10_300ppi.png")).convert("RGB"))  # noqa: E731
    kontak = []
    stiller = a.stiller.split(",")
    t0 = time.time()

    def kayit(ad, img, e, fn, fark=None):
        Image.fromarray(img).save(out / f"{ad}_12x18.jpg", quality=95, subsampling=0, dpi=(300, 300))
        for (x, y) in YAKIN.get(ad, []):
            yakin.append((f"{ad} ({x},{y})", img[y:y + 600, x:x + 600]))
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
        rap["Timeless"] = dict(zemin=yon, yerlesim=yer, kapi=kap, susleme_oge_kesisim_px=kes, atanamayan_parca_px=int(p["diger"].sum()) if "diger" in p else 0,
                               pass_=bool(all(v["pass_"] for v in kap.values()) and kes == 0 and "diger" not in p
                                          and set(yer) == {"yay", "dal_sol_ust", "dal_sol_alt", "dal_sag_alt"}))
        kayit("Timeless", son, e, "timeless")

    if "FirstPage" in stiller:
        e = eski("3_FirstPage")
        zem, yon = doku(Path(a.doku_dizin, "3_FirstPage_2x3_kaynak.png"), a.esrgan, a.hizli)
        o = cerceve_olc(e)
        z, rc = cerceve_ciz(zem, o)
        son, fark = ogeli_tum(bp, "first_page", z, S)
        kc = cerceve_kapi(son, o)
        on_d = yan_profil(zem, "sol", (100, 260), (900, 4500)); on_k = round(float(1 - on_d[3].min()), 4)
        rap["FirstPage"] = dict(zemin=yon, cerceve_8x10={k: (v if k == "yan_pay" else {x: v[x] for x in v if x not in ("ofs", "oran")})
                                                        for k, v in o.items()}, cerceve=rc, cerceve_kapi_12x18=kc,
                                doku_onceden_cizgi_kontrast_sol=on_k,
                                beklenen_pay=round(o["yan_pay"] * K, 2),
                                pass_=bool(kc["pass_"] and o["kose_tasma_8x10"]["toplam"] == 0))
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
        # Layers B (yeni duz doku + kemer uste sabit): Serdar 1 Kas F 3. kosu karari ile BIRAKILDI; yalniz A uretilir.
        yakin.append(("Layers_A sol kirpim", A[1500:2100, 0:600]))
        s8 = ogeler(bp1, e, "layers")
        kontak.append(("Layers_A", s8, A))
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
            yer[ad] = dict(kutu_eski=kt, X=X, Y=Y, kagit_eski=kk_e, kagit_yeni=kk_n, kutu_yeni=carp(out_, R, kt, X, Y)[0],
                           oran_katmani=dict(oran.son))
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
        ki_e = cv2.erode(km_e.astype(np.uint8), np.ones((KAGIT_KENAR, KAGIT_KENAR), np.uint8)) > 0
        kap = {ad: susleme_kapi(e, son, p[ad], y["kutu_eski"], y["X"], y["Y"], har_o, ki_e) for ad, y in yer.items()}
        kes = int((cv2.dilate(tum_yeni.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & har).sum())
        # bilgi (kapi degil; inceleme 1 Kas): eski 8x10'da dallarin kagit kenarini gecip ADACAYI uzerinde suren uclari aktarilmiyor
        # (maske kagit ici). Adacayi zeminine gore Lab farki > adacayi gurultusu p99,9 (13,5; olcum 1 Kas) olan, maskeye 100 px yakin px.
        kmd = cv2.dilate(km_e.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
        zs = YR.yerel_zemin(e, kmd)
        lab_ = lambda a_: cv2.cvtColor(np.clip(a_, 0, 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32) * [100 / 255, 1, 1]  # noqa: E731
        dEs = np.linalg.norm(lab_(e) - lab_(zs), axis=2)
        ada = {ad: int(((cv2.dilate(m_.astype(np.uint8), np.ones((201, 201), np.uint8)) > 0) & ~kmd & (dEs > 13.5)).sum()) for ad, m_ in p.items()}
        rap["Botanical"] = dict(zemin=yon, yerlesim=yer, kapi=kap, susleme_oge_kesisim_px=kes, adacayi_ustu_aktarilmayan_px_bilgi=ada,
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
    if yakin:   # inceleme E8: kontakta gorunmeyen kenar / gecis / kose yakin planlari (gercek piksel, 600x600)
        Wy = 3 * 620; Hy = ((len(yakin) + 2) // 3) * 640
        yk = Image.new("RGB", (Wy, Hy), (230, 230, 230))
        for i, (ad_, k_) in enumerate(yakin):
            yk.paste(Image.fromarray(np.ascontiguousarray(k_)), ((i % 3) * 620 + 10, (i // 3) * 640 + 30))
        yk.save(out / "YAKIN_STIL4.jpg", quality=88)
        rap["yakin_plan_sirasi"] = [a_ for a_, _ in yakin]
    rap["sonuc"] = "PASS" if all(v.get("pass_") for k, v in rap.items() if isinstance(v, dict) and "pass_" in v) else "FAIL"
    (out / "OLCUM.json").write_text(json.dumps(rap, indent=1, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x)), encoding="utf-8")
    print(json.dumps({k: (v.get("pass_") if isinstance(v, dict) else v) for k, v in rap.items()}, default=str))
    return 0 if rap["sonuc"] == "PASS" else 3   # 3 = kapi FAIL (1 = Python hatasi / SystemExit ile karismasin)


if __name__ == "__main__":
    sys.exit(main())
