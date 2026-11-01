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
KOSE_YUZDE = 99        # F 4. kosu: cizgi dis koyu siniri = cizgi boyunca koyulugun p99'u >= KOSE_KOYU olan en uzak ofset (cizginin kendi
#                        ulastigi nokta; p99,9 kagit lekeleriyle sisiyordu: eski 8x10 ust 13,89 px, p99 9,89; olcum 1 Kas)
DUZ_Y = 2100           # Layers: eski 8x10'da kemer katmanlari satir 2050'de biter (olcum 1 Kas: satir 2050+ duz renkten > 25 sapan piksel 0)
KEMER_ESIK = 12        # Layers B kemer maskesi: duz seftaliden > 12 sapma (golgeler dahil), 9 px genisletme
KEMER_RAMPA = 120      # F5 it. 2 (kosu 41339810943: yerel dikis max 2,332 > 2,3 oneri; ESRGAN dokusunda rampa uclari arasi dE ort 3,12):
#                        gecis 60 -> 120 px; ayni renk farki iki kat mesafeye yayilir (kapi degismedi). Onceki not: Layers B (F 4. kosu):
#                        kemer disinda eski duz seftaliden yeni dokuya gecis rampasi (12x18 px; 2. kosu sigma 3 dikisi
#                        gradyan orani 1,615 > 1,5 veriyordu); kemer cekirdegi (w = 1) eski piksel x1,5 AYNEN (Serdar 1 Kas: kemer orijinal)
KEMER_PAY = 9          # F5: geometrik kemer maskesi disa 9 px (12x18) genisletilir: kenar gecisi eski 8x10'da 3-6 px (olcum 1 Kas,
#                        ic kemer sol kenar y 1300: -115 -> -4,6 lum 3 px'te; on duzlem x 150: 6 px), x1,5
CIZGI_PEN = 240        # F5 yatay cizgi dedektoru pencere genisligi (12x18 px). Olcum 1 Kas (4. kosu ciktisi): 240 px'te satir 4500 kesimi 2,98,
#                        temiz yeni doku 0,53; tam satir (3600) ortalamasi ayni kesimi 0,61 ile KACIRIYOR (daha siki tanim secildi)
CIZGI_ESIK = 1.0       # ONERI (gorev metni F5): yatay cizgi <= 1,0 lum
DIKIS_YEREL_ESIK = 2.3   # ONERI (Serdar onayi yok): yerel dikis karo dE76 EN BUYUK <= 2,3 (CIE76 fark edilebilirlik esigi; 3. taraf:
#                          Mahy vd. 1994 / Sharma 2003). Yerel olcum 1 Kas (hizli doku): cikti p95 1,38 max 1,95; yeni doku tabani p95 0,93,
#                          eski doku tabani p95 0,75 (taban esik olarak kullanilmadi: iki farkli kagidin gecisi tabandan buyuk olmak zorunda)
DIKIS_DE, DIKIS_GRAD = 3.0, 1.5   # ONERI (Serdar onayi yok): dikis renk basamagi dE76 <= 3; kenar gradyani p99 <= 1,5 x yeni doku p99


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
        r[yan] = dict(_yan=yan, merkez=round(c, 2), kenar_uzaklik=round(float(uzak), 2), ofs=ofs[m].round(3).tolist(), oran=oran_[m].round(4).tolist(),
                      en_koyu_oran=oran_[m].min(0).round(4).tolist(), kagit=kag.round(1).tolist())
    r["yan_pay"] = round((r["sol"]["kenar_uzaklik"] + r["sag"]["kenar_uzaklik"]) / 2, 2)
    r["kose_tasma_8x10"] = kose_tasma(e, (r["sol"]["merkez"], r["sag"]["merkez"]), (r["ust"]["merkez"], r["alt"]["merkez"]), 1.0)      # Serdar 1 Kas: 12x18 kose = 0 ve eski 8x10 ile ayni (8x10 = 0 olmali)
    return r


def cerceve_ciz(img, olc, olcek=K):
    """Her kenarin OLCULEN 8x10 oran profili (ofset x olcek, dogrusal ara deger; acik kabartma omuzlari > 1 DAHIL). F 3. kosu (Serdar 1 Kas):
    2. kosuda (a) cizgiler koseden profil penceresi kadar (~21 px) uzayip "+" yapiyordu, (b) np.minimum oran > 1 omuzlari atiyordu
    (ornek basina profil farki 0,08-0,12, omuz ofsetlerinde). Simdi her piksel icin dikdortgene isaretli L-sonsuz uzaklik
    s = max(m - x, x - xs, m - y, y - ya) (icerde < 0, disarida > 0; disarida kose KARE) ve s'yi veren kenarin profili uygulanir:
    cizgi hicbir yerde dik cizginin disina tasmaz. Dort kenar payi esit = 8x10 yan payi x olcek.
    F5 (Serdar 1 Kas karar b): (1) cerceve her boyda KENDI cozunurlugunde cizilir (olcek = K x boy genisligi / 3600; buyutulen / kucultulen
    sayfada kuyruk sutunu esigin cevresine dusuyordu); yalniz kenar seritleri islenir (24x36 bellek). (2) dis kose ceyreginde secilen
    cizgi, DIK cizginin analitik koyu siniri - KOSE_KIRP'te biter. (3) DIS kuyrukta nominal koyuluk (KOYU_BOSLUK) araligina dusmez:
    esik (KOSE_KOYU) altindaysa alt uca, ustundeyse ust uca cekilir (oran farki <= 15 / 228 ~ 0,066 < PROFIL_ORNEK 0,08)."""
    H, W = img.shape[:2]
    m = olc["yan_pay"] * olcek
    yari = PROFIL_T * olcek
    T = int(np.ceil(m + yari)) + 2
    e_an = {yan: dis_sinir_analitik(olc[yan]) * olcek - KOSE_KIRP * olcek / K for yan in ("sol", "sag", "ust", "alt")}
    out = img.copy(); say = dict(kirpilan_px=0, bosluk_cekilen_px=0)
    for (y0, y1, x0, x1) in ((0, T, 0, W), (H - T, H, 0, W), (T, H - T, 0, T), (T, H - T, W - T, W)):
        if y1 > y0 and x1 > x0:
            out[y0:y1, x0:x1] = _cerceve_parca(img[y0:y1, x0:x1], olc, m, W, H, y0, x0, olcek, e_an, say)
    return out, dict(pay_px=round(m, 2), olcek=round(olcek, 4), profil="olculen 8x10 (kenar basina, omuz dahil)",
                     kose="L-sonsuz (kare); dis kose ceyreginde dik cizginin koyu siniri - KOSE_KIRP'te biter; dis kuyrukta koyuluk boslugu",
                     kose_kirp_px=round(KOSE_KIRP * olcek / K, 3), koyu_bosluk=list(KOYU_BOSLUK), **say,
                     dis_sinir_analitik_px={k: round(v + KOSE_KIRP * olcek / K, 2) for k, v in e_an.items()})


def _cerceve_parca(img, olc, m, W, H, y0, x0, olcek, e_an, say):
    h, w = img.shape[:2]
    xs_, ya_ = W - 1 - m, H - 1 - m
    yy, xx = np.mgrid[y0:y0 + h, x0:x0 + w].astype(np.float32)
    d = np.stack([m - xx, xx - xs_, m - yy, yy - ya_])            # sol, sag, ust, alt
    k = np.argmax(d, 0); s_ = np.take_along_axis(d, k[None], 0)[0]
    R = np.ones((h, w, 3), np.float32)
    KG = np.full((h, w, 3), 230.0, np.float32)                      # 8x10 kagit rengi (kenar basina; parlak omuz payi icin)
    yari = PROFIL_T * olcek
    bolge = np.abs(s_) <= yari
    for i, yan in enumerate(("sol", "sag", "ust", "alt")):
        ofs = np.array(olc[yan]["ofs"]) * olcek; orn = np.array(olc[yan]["oran"])
        sec = bolge & (k == i)
        o = (-s_[sec]) if yan in ("sol", "ust") else s_[sec]           # yan_profil ofseti: koordinat artan yonde (sol / ust icin iceri)
        for c in range(3):
            R[..., c][sec] = np.interp(o, ofs, orn[:, c], left=1, right=1)
            KG[..., c][sec] = olc[yan]["kagit"][c]
    # (3) dis kuyruk koyuluk boslugu (yalniz cizgi merkezinin DISI, koyu taraf)
    wl = np.float32([0.299, 0.587, 0.114])
    kl = KG @ wl; dn = kl - (KG * R) @ wl
    lo, hi = KOYU_BOSLUK
    bs = bolge & (s_ > 0) & (dn > lo) & (dn < hi)
    if bs.any():
        hedef = np.where(dn[bs] < KOSE_KOYU, lo, hi)
        R[bs] = 1 - (1 - R[bs]) * (hedef / dn[bs])[:, None]
        say["bosluk_cekilen_px"] += int(bs.sum())
    # (2) dis kose ceyregi
    dv = np.maximum(d[0], d[1]); dh = np.maximum(d[2], d[3])
    e_h = np.where(d[2] > d[3], e_an["ust"], e_an["alt"]); e_v = np.where(d[0] > d[1], e_an["sol"], e_an["sag"])
    kirp = (dv > 0) & (dh > 0) & (((dv >= dh) & (dh > e_h)) | ((dh > dv) & (dv > e_v)))
    R[kirp] = 1.0
    say["kirpilan_px"] += int(kirp.sum())
    # parlak kabartma omzu (oran > 1): carpim yeni kagitta 255'i asiyordu (inceleme: R kanali bandin %2,5'inde >= 254); 8x10'daki
    # 255'e kalan pay orani korunur: cikti = 255 - (255 - yeni) x (255 - kagit x oran) / (255 - kagit)
    a = img.astype(np.float32)
    S = np.clip((255.0 - KG * R) / np.maximum(255.0 - KG, 1.0), 0, 1)
    son = np.where(R > 1, 255.0 - (255.0 - a) * S, a * R)
    return np.clip(son, 0, 255).astype(np.uint8)


def dis_sinir_analitik(o8):
    """bir kenar profilinin (8x10 ofset / oran / kagit) dis yondeki koyuluk >= KOSE_KOYU olan en uzak ofseti (8x10 px, 0,005 adim)."""
    ofs = np.array(o8["ofs"]); orn = np.array(o8["oran"]); kg = np.array(o8["kagit"], np.float64)
    w = np.array([0.299, 0.587, 0.114]); dk = kg @ w - (kg * orn) @ w
    yan_dis = -ofs if o8["_yan"] in ("sol", "ust") else ofs          # dis yon: sol / ust icin ofset eksi
    i = np.argsort(yan_dis); f = np.arange(0, 14, 0.005); dd = np.interp(f, yan_dis[i], dk[i])
    k = np.where(dd >= KOSE_KOYU)[0]
    return float(f[k.max()]) if k.size else 0.0


KOSE_KIRP = 1.5       # F5: dis kose ceyreginde kirpma payi (12x18 px). Olcum 1 Kas (4. kosu 12x18): olculen koyu sinir analitikten en cok
#                       0,93 px kucuk (alt: 6,16 / 7,09); pay bunu kapsar
KOYU_BOSLUK = (10.0, 32.0)   # F5: cizgi dis kuyrugunda nominal koyuluk (lum) bu araliga dusmez. Olcum 1 Kas (FirstPage yerel dokusu, kose
#                              120 px pencere, kose medyanina gore): kagit koyulugu p99 10, p99,9 13, en cok 16 -> esik 25'in altindaki kuyruk
#                              10'a (10 + 16 = 26 yalniz en kotu tek pikselde); ustu 32'ye (kendi parcasinda p99 >= 25 kalir). Profil farki
#                              (yerel) ust 0,0706 -> 0,0768 (PROFIL_ORNEK 0,08)
KOSE_PEN, KOSE_CEKIRDEK, KOSE_KOYU = 40, 7, 25   # 8x10 px: kose penceresi, cizgi koyu cekirdegi yari genisligi (profil: oran ofset +-5,4'te
#                                                  ~1'e doner, olcum 1 Kas), kagittan koyu esigi (lum). 12x18'de x1,5.


def cizgi_dis_sinir(L, dikey, c, kag, isaret, bolge):
    """Bir cizgi PARCASININ dis yondeki en uzak koyu siniri. dikey: dikey cizgi (x = c) mi; isaret: dis yon (-1 sol / ust, +1 sag / alt);
    bolge = (bas, son) cizgi boyunca parca. Her dis ofset sutunu / satiri icin koyuluk (kag - lum) yuzdeligi KOSE_YUZDE; >= KOSE_KOYU olan
    en uzak ofset (px): cizginin kendisinin bu parcada ulastigi en dis nokta."""
    H, W = L.shape
    b0, b1 = max(0, int(bolge[0])), min(H if dikey else W, int(bolge[1]))
    if b1 - b0 < 5:
        return 0.0
    lim = W if dikey else H
    ix = np.arange(max(0, int(c - 60)), min(lim, int(c + 61)))
    o = (ix - float(c)) * isaret
    blok = L[b0:b1][:, ix] if dikey else L[ix][:, b0:b1].T
    dk = np.percentile(kag - blok, KOSE_YUZDE, axis=0)
    k = (dk >= KOSE_KOYU) & (o >= 0)
    return float(o[k].max()) if k.any() else 0.0


def kose_tasma(img, xs, ys, olcek=1.0, L=None):
    """dort kosede KOSE DISI koyu piksel sayisi (F 4. kosu, Serdar 1 Kas: esik yok, 10 px alti tasma da sayilir). Her kose YEREL:
    kagit = kose ici bolgenin medyani; iki cizginin dis koyu siniri O KOSEYE BITISIK parcadan (kose penceresinin hemen disi, pencere x2
    uzunluk) ayni kagitla olculur; pencerede iki cizgiden en az birinin dis sinirinin otesindeki koyu piksel = tasma (kapi 0).
    F5 (Serdar 1 Kas karar b): iterasyon 1 tanimina DONULDU. Iterasyon 2'nin "cizginin iki ucundaki parcalarin buyugu" tanimi
    kapiyi gevsetiyordu (eski 8x10 sol_ust 4,89 -> 9,89 px; 33 px tasma 0 gorunuyordu) ve KULLANILMAZ."""
    L = lum(img) if L is None else L
    pen = KOSE_PEN * olcek
    (xl, xr), (yu, ya) = xs, ys
    H, W = L.shape
    r, ds, ham = {}, {}, {}
    for ad, (cx, cy, sx, sy) in (("sol_ust", (xl, yu, -1, -1)), ("sag_ust", (xr, yu, 1, -1)), ("sol_alt", (xl, ya, -1, 1)),
                                 ("sag_alt", (xr, ya, 1, 1))):
        x0, x1 = max(0, int(round(cx - pen))), min(W, int(round(cx + pen)) + 1)
        y0, y1 = max(0, int(round(cy - pen))), min(H, int(round(cy + pen)) + 1)
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float64)   # float64: sinir ustundeki piksel (ofset = dis sinir) float32'de "oteye" dusuyordu
        ic = ((xx - cx) * -sx > 2 * KOSE_CEKIRDEK * olcek) & ((yy - cy) * -sy > 2 * KOSE_CEKIRDEK * olcek)
        P = L[y0:y1, x0:x1]
        kag = float(np.median(P[ic]))
        # bitisik parcalar: dikey cizgi koseden iceri (y yonu -sy) pen..3pen; yatay cizgi (x yonu -sx) pen..3pen
        by = sorted((cy - sy * pen, cy - sy * 3 * pen)); bx = sorted((cx - sx * pen, cx - sx * 3 * pen))
        dx = cizgi_dis_sinir(L, True, cx, kag, sx, by)
        dy = cizgi_dis_sinir(L, False, cy, kag, sy, bx)
        dis = ((xx - cx) * sx > dx + 1e-6) | ((yy - cy) * sy > dy + 1e-6)
        r[ad] = int(((P < kag - KOSE_KOYU) & dis).sum())
        ds[ad] = [round(dx, 2), round(dy, 2)]; ham[ad] = (dx, dy)
    r["toplam"] = sum(r[a] for a in ("sol_ust", "sag_ust", "sol_alt", "sag_alt"))
    r["dis_sinir_px"] = ds
    kose_tasma.ham = ham
    return r


def kose_oztest_gercek(img, xs, ys, olcek, tasmalar=(1, 5)):
    """F5 (Serdar 1 Kas): GERCEK dokulu oz-test. Ciktinin sol_ust kosesinde yatay (ust) cizgi, dikey (sol) cizginin OLCULEN dis sinirinin
    otesine t px uzatilir: hedef sutunlar (dis sinir < ofset <= dis sinir + t) yatay cizginin kendi parcasindaki bir referans sutunun
    oranlariyla (referans / ayni sutunun kagidi) carpilir. Kapi her t icin > 0 bulmali. Donus: t -> sol_ust sayimi."""
    L0 = lum(img)
    taban = kose_tasma(img, xs, ys, olcek, L0)
    dx = kose_tasma.ham["sol_ust"][0]                                  # yuvarlanmamis (F5: 2 ondalik yuvarlama 1 px sutunu kaciriyordu)
    cx, cy = xs[0], ys[0]
    pen = KOSE_PEN * olcek
    xr = int(round(cx + 2 * pen))                                     # referans sutun: ust cizginin koseye bitisik parcasi
    yb0, yb1 = int(cy - 3 * KOSE_CEKIRDEK * olcek), int(cy + 3 * KOSE_CEKIRDEK * olcek) + 1
    a = img.astype(np.float32)
    kag_ref = np.median(np.r_[a[yb1:yb1 + 20, xr - 5:xr + 6].reshape(-1, 3), a[max(0, yb0 - 20):yb0, xr - 5:xr + 6].reshape(-1, 3)], 0)
    oran_ = a[yb0:yb1, xr] / np.maximum(kag_ref, 1)
    sonuc = {"0": taban["sol_ust"]}
    for t in tasmalar:
        b = a.copy()
        xs_ = [x for x in range(int(cx - dx - t - 2), int(cx) + 1) if dx + 1e-6 < (cx - x) <= dx + t + 1e-6]
        for x in xs_:
            b[yb0:yb1, x] = b[yb0:yb1, x] * oran_
        bb = np.clip(b, 0, 255).astype(np.uint8)
        sonuc[str(t)] = kose_tasma(bb, xs, ys, olcek)["sol_ust"]
    return dict(sol_ust_sayim=sonuc, dis_sinir_dikey_px=round(dx, 3), pass_=bool(sonuc["0"] == 0 and all(sonuc[str(t)] > 0 for t in tasmalar)))


def kose_oztest(olcek=1.5):
    """Yapay L kose (sentetik cizgi, FWHM ~ 8 x olcek) + bilinen tasma: 0, 1, 2, 3, 5, 8, 12 px. Gecer: tasmasizda 0, her tasmada > 0."""
    H = W = 1200                                                      # kose kenar ortasi olcum bandinin (%20-80) disinda kalmali
    c = 90.0; sig = 3.4 * olcek
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    def ciz(tasma):
        k = np.exp(-0.5 * (np.maximum(c - xx, c - yy) / sig) ** 2)      # kare kose (L-sonsuz), cerceve_ciz ile ayni bicim
        if tasma:   # yatay cizgi, dikey cizginin koyu dis sinirinin (koyuluk 25 / 150) otesine tasma px uzar
            e0 = sig * np.sqrt(2 * np.log(150 / KOSE_KOYU))
            uz = (xx < c - e0) & (xx >= c - e0 - tasma)
            k = np.maximum(k, np.exp(-0.5 * ((yy - c) / sig) ** 2) * uz)
        return np.clip(230 - 150 * k[..., None], 0, 255).astype(np.uint8).repeat(3, 2)
    sonuc = {}
    for t in (0, 1, 2, 3, 5, 8, 12):
        a = ciz(t)
        r = kose_tasma(a, (c, W - 1 - 90), (c, H - 1 - 90), olcek)
        sonuc[t] = r["sol_ust"]
    return dict(tasma_px_sayim=sonuc, pass_=bool(sonuc[0] == 0 and all(v > 0 for k, v in sonuc.items() if k)))


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


def _jpeg_gidis_donus(img):
    import io
    bf = io.BytesIO(); Image.fromarray(img).save(bf, "JPEG", quality=95, subsampling=0); bf.seek(0)
    return np.asarray(Image.open(bf).convert("RGB"))


def firstpage_boylar(zem, o):
    """F5 (Serdar 1 Kas): FirstPage 14 boy kose kapisi. Her boy: zemin (3600x5400) boy oranina dikey ortali kirpilir, hedef piksele
    (inc x 300; A mm; by_boy.BOY) LANCZOS; cerceve O BOYUN cozunurlugunde cizilir (olcek = K x Wt / 3600, dort pay esit). Olcum JPEG
    q95 4:4:4 gidis-donusten sonra. Donus: boy -> kose_tasma, ve 8x10 icin (goruntu, xs, ys, olcek)."""
    import by_boy as BB
    sonuc, sakla = {}, {}
    for boy_ad, (wi, hi) in BB.BOY.items():
        Wt, Ht = round(wi * 300), round(hi * 300)
        Hc = min(zem.shape[0], round(zem.shape[1] * Ht / Wt)); y0 = (zem.shape[0] - Hc) // 2
        z = np.asarray(Image.fromarray(np.ascontiguousarray(zem[y0:y0 + Hc])).resize((Wt, Ht), Image.LANCZOS))
        olcek = K * Wt / 3600
        img, rc = cerceve_ciz(z, o, olcek)
        img = _jpeg_gidis_donus(img)
        mt = o["yan_pay"] * olcek
        xs, ys = (mt, Wt - 1 - mt), (mt, Ht - 1 - mt)
        r = kose_tasma(img, xs, ys, olcek)
        r["boyut"] = [Wt, Ht]; r["olcek"] = round(olcek, 4); r["bosluk_cekilen_px"] = rc["bosluk_cekilen_px"]; r["kirpilan_px"] = rc["kirpilan_px"]
        sonuc[boy_ad] = r
        if boy_ad == "8x10":
            sakla["8x10"] = (img, xs, ys, olcek)
        del img, z
    return sonuc, sakla


def kose_yakin(out, e, o, son, xs12, ys12, b8):
    """FirstPage 4 kose yakin plani x2: satir 1 eski 8x10 kaynak, satir 2 yeni 8x10, satir 3 yeni 12x18 (pencere +-60 px @8x10 olcegi)."""
    satir = []
    for img, xs, ys, olcek, ad in ((e, (o["sol"]["merkez"], o["sag"]["merkez"]), (o["ust"]["merkez"], o["alt"]["merkez"]), 1.0, "eski 8x10"),
                                   (b8[0], b8[1], b8[2], b8[3], "yeni 8x10"), (son, xs12, ys12, K, "yeni 12x18")):
        h = 60; parca = []                                                 # 120 px kesit -> 240 = x2
        for cx, cy in ((xs[0], ys[0]), (xs[1], ys[0]), (xs[0], ys[1]), (xs[1], ys[1])):
            cx, cy = int(round(cx)), int(round(cy))
            k = img[max(0, cy - h):cy + h, max(0, cx - h):cx + h]
            parca.append(Image.fromarray(np.ascontiguousarray(k)).resize((240, 240), Image.NEAREST))
        r = Image.new("RGB", (4 * 250 + 10, 250), (230, 230, 230))
        for i, p_ in enumerate(parca):
            r.paste(p_, (10 + i * 250, 5))
        from PIL import ImageDraw
        dr = ImageDraw.Draw(r)
        for i, k_ in enumerate(("sol_ust", "sag_ust", "sol_alt", "sag_alt")):
            dr.rectangle([12 + i * 250, 7, 12 + i * 250 + 150, 21], fill=(255, 255, 255)); dr.text((14 + i * 250, 8), f"{ad} {k_} x2", fill=(0, 0, 0))
        satir.append(r)
    t = Image.new("RGB", (satir[0].width, 3 * 250), (230, 230, 230))
    for i, r in enumerate(satir):
        t.paste(r, (0, i * 250))
    t.save(out / "FP_KOSE_YAKIN.jpg", quality=92)


def _super_elips_uydur(P, p0, n_iter=60):
    """|x-cx|/a ^ n + |y-cy|/b ^ n = 1 egrisine en kucuk kareler (Levenberg-Marquardt, sayisal Jacobian; scipy yok). P: (N, 2) x, y."""
    def art(p):
        cx, cy, a_, b_, n_ = p
        return (np.abs((P[:, 0] - cx) / a_) ** n_ + np.abs((P[:, 1] - cy) / b_) ** n_) ** (1 / n_) - 1
    p = np.array(p0, np.float64); lam = 1e-3; f = art(p); c = (f ** 2).sum()
    for _ in range(n_iter):
        J = np.stack([(art(p + dp) - f) / 1e-4 for dp in np.eye(5) * 1e-4], 1)
        A_ = J.T @ J; g_ = J.T @ f
        dp = -np.linalg.solve(A_ + lam * np.diag(np.diag(A_)), g_)
        f2 = art(p + dp); c2 = (f2 ** 2).sum()
        if c2 < c:
            p, f, c, lam = p + dp, f2, c2, lam / 3
        else:
            lam *= 5
    return p, f


def kemer_geo(e):
    """F5 (Serdar 1 Kas karar b): Layers kemer katmanlarinin GEOMETRISI (eski 8x10 px). Kemer bolgesi = on duzlemin ust kenari (iki dogru)
    ustu, ic kemer (alt yari dikdortgen + ust super-elips) disi. Olcum (1 Kas): ic kemer kenar noktalari, esik 12 maskesinin satir < 2000
    ic bilesen sinirindan (keskin kenar, kontrast > 40 lum; leke yok); on duzlem dogrulari esik 25 maskesinin sutun basina en alt satirindan
    (sol: x 0..xl-25, sag: xr+25..xr+225; sag acik yan duzlem x > xr+235 esik 25'in altinda kaldigi icin disarida). Olcum 1 Kas: super-elips
    artik p95 1,97 / en cok 3,99 px; kesik kagit kenari dogrudan en cok 3,57 (sol) / 2,55 (sag) px sapar (2. derece egri p95'i dusurmuyor).
    Uyum kapisi: super-elips p95 <= 3, dogru p95 <= 4; her artik maske payinin (KEMER_PAY / K = 6 px) altinda (asilirsa DUR: kaynak degismis)."""
    duz = np.median(e[2600:2950, 800:1600].reshape(-1, 3), 0)
    d = np.abs(e.astype(np.float32) - np.float32(duz)).max(2)
    m12 = d > KEMER_ESIK; m12[DUZ_Y:] = False
    n_, lab = cv2.connectedComponents((~m12[:2000]).astype(np.uint8), connectivity=4)
    ic = lab == lab[1000, 1200]                                         # tohum: ic kemer ortasi (eski 8x10)
    sol_, sag_ = [], []
    for y in range(120, 1950):
        xs = np.where(ic[y])[0]
        if xs.size:
            sol_.append((xs.min(), y)); sag_.append((xs.max(), y))
    sol_ = np.array(sol_, np.float64); sag_ = np.array(sag_, np.float64)
    yan = lambda Q: Q[(Q[:, 1] > 1150) & (Q[:, 1] < 1400)][:, 0]     # noqa: E731
    xl, xr = float(np.median(yan(sol_))), float(np.median(yan(sag_)))
    P = np.r_[sol_[sol_[:, 1] < 1000], sag_[sag_[:, 1] < 1000]]
    p, f = _super_elips_uydur(P, [(xl + xr) / 2, 1000, (xr - xl) / 2, 850, 2.0])
    cx, cy, a_, b_, n_s = p
    rad = np.abs(f) * a_
    m25 = d > 25
    def alt(x):
        r_ = np.where(m25[:DUZ_Y, x])[0]; return r_.max() if r_.size else -1
    dog = {}
    for ad, X in (("sol", np.arange(0, int(xl) - 25)), ("sag", np.arange(int(xr) + 25, int(xr) + 225))):
        Y = np.array([alt(x) for x in X], np.float64); k = Y > 0
        q = np.polyfit(X[k], Y[k], 1); r_ = np.abs(Y[k] - np.polyval(q, X[k]))
        dog[ad] = dict(egim=round(float(q[0]), 5), kesisim=round(float(q[1]), 2), artik_p95=round(float(np.percentile(r_, 95)), 2),
                       artik_max=round(float(r_.max()), 2))
    g = dict(ic_kemer=dict(cx=round(float(cx), 2), cy=round(float(cy), 2), a=round(float(a_), 2), b=round(float(b_), 2), n=round(float(n_s), 4),
                           yan_x_olculen=[xl, xr], artik_p95=round(float(np.percentile(rad, 95)), 2), artik_max=round(float(rad.max()), 2)),
             on_duzlem=dog, birim="eski 8x10 px")
    pay8 = KEMER_PAY / K                                                # maske payi (eski 8x10 px): her artik bunun altinda kalmali
    if (g["ic_kemer"]["artik_p95"] > 3 or g["ic_kemer"]["artik_max"] >= pay8
            or any(v["artik_p95"] > 4 or v["artik_max"] >= pay8 for v in dog.values())):
        raise SystemExit(f"kemer geometri uyumu FAIL: {g}")
    return g


def kemer_geo_maske(g, H, W, olcek, oy=0):
    """geometrik kemer maskesi (True = kemer katmani) H x W tuvalde; piksel merkezi -> eski 8x10: x8 = (X + 0,5) / olcek - 0,5."""
    k = g["ic_kemer"]; sl, sg = g["on_duzlem"]["sol"], g["on_duzlem"]["sag"]
    x8 = ((np.arange(W, dtype=np.float64) + 0.5) / olcek - 0.5)[None, :]
    y8 = ((np.arange(H, dtype=np.float64) - oy + 0.5) / olcek - 0.5)[:, None]
    ux = np.abs((x8 - k["cx"]) / k["a"]); uy = np.abs((y8 - k["cy"]) / k["b"])
    ic = ((y8 >= k["cy"]) & (ux <= 1)) | ((ux ** k["n"] + uy ** k["n"]) <= 1)
    cizgi = np.where(x8 < k["cx"], sl["egim"] * x8 + sl["kesisim"], sg["egim"] * x8 + sg["kesisim"])
    return ~ic & ~(y8 > cizgi)


def yatay_cizgi(L, gecerli, pen=240, en_az=0.5):
    """F5 yatay cizgi dedektoru: ardisik satir (y, y+1) lum farki, pen sutunluk pencerede iki satirda da gecerli sutunlarin ortalamasi
    (pencerenin en az %50'si gecerli); tum satir ve pencerelerde en buyuk mutlak deger. Donus: (deger, satir, pencere x), satir profili."""
    H, W = L.shape
    D = L[1:] - L[:-1]; G = gecerli[1:] & gecerli[:-1]
    en = (0.0, -1, -1); prof = np.zeros(H - 1, np.float32)
    for x0 in range(0, W, pen):
        g_ = G[:, x0:x0 + pen]; n_ = g_.sum(1); s_ = (D[:, x0:x0 + pen] * g_).sum(1)
        ok = n_ >= en_az * g_.shape[1]; m_ = np.abs(np.where(ok, s_ / np.maximum(n_, 1), 0))
        prof = np.maximum(prof, m_); i = int(np.argmax(m_))
        if m_[i] > en[0]:
            en = (float(m_[i]), i, x0)
    return en, prof


def cizgi_grafik(prof, yol, esik, y_max):
    """satir basina en buyuk pencere farki (y ekseni, lum) - satir (x ekseni) grafigi; esik ve eski 4500 satiri isaretli."""
    from PIL import ImageDraw
    Wg, Hg, pd = 1400, 360, 40
    ust_ = max(3.0, float(prof.max()) * 1.1)
    im = Image.new("RGB", (Wg, Hg), (255, 255, 255)); dr = ImageDraw.Draw(im)
    X = lambda y: pd + (Wg - 2 * pd) * y / len(prof)                    # noqa: E731
    Y = lambda v: Hg - pd - (Hg - 2 * pd) * v / ust_                    # noqa: E731
    dr.line([(pd, Hg - pd), (Wg - pd, Hg - pd)], fill=(0, 0, 0)); dr.line([(pd, pd), (pd, Hg - pd)], fill=(0, 0, 0))
    dr.line([(pd, Y(esik)), (Wg - pd, Y(esik))], fill=(200, 0, 0))
    dr.line([(X(4500), pd), (X(4500), Hg - pd)], fill=(0, 0, 200))
    adim = max(1, len(prof) // (Wg - 2 * pd))
    pts = [(X(i), Y(float(prof[i:i + adim].max()))) for i in range(0, len(prof), adim)]
    dr.line(pts, fill=(0, 0, 0))
    dr.text((pd + 5, 5), f"yatay cizgi: satir basina en buyuk pencere farki (lum); kirmizi esik {esik}; mavi satir 4500; max {prof.max():.2f} @ {y_max}", fill=(0, 0, 0))
    for v in range(0, int(ust_) + 1):
        dr.text((5, Y(v) - 6), str(v), fill=(0, 0, 0))
    for y in range(0, len(prof) + 1, 900):
        dr.text((X(y) - 10, Hg - pd + 5), str(y), fill=(0, 0, 0))
    im.save(yol)


def dikis_yerel(img, uz, gecerli, merkez, yari, uc=False, karo=64):
    """F5 yerel dikis: kemer payindan uzaklik (uz) ile iki bant: A = [merkez - yari, merkez), B = (merkez, merkez + yari]
    (uc=True: A = [0, 20), B = [60, 80] rampa uclari). karo x karo bloklarda iki yanda en az 100 px varsa iki ortalama Lab farki (dE76)."""
    lab = cv2.cvtColor(np.ascontiguousarray(img), cv2.COLOR_RGB2LAB).astype(np.float32) * [100 / 255, 1, 1] - [0, 128, 128]
    H, W = uz.shape
    if uc:
        A = (uz >= 0.5) & (uz < 20) & gecerli; B_ = (uz >= 60) & (uz <= 80) & gecerli
    else:
        A = (uz >= merkez - yari) & (uz < merkez) & gecerli; B_ = (uz > merkez) & (uz <= merkez + yari) & gecerli
    ntx = (W + karo - 1) // karo
    tid = (np.arange(H)[:, None] // karo) * ntx + (np.arange(W)[None, :] // karo)
    nt = tid.max() + 1
    def ort(M):
        ids = tid[M]; n_ = np.bincount(ids, minlength=nt)
        return n_, np.stack([np.bincount(ids, weights=lab[..., c][M], minlength=nt) for c in range(3)], 1) / np.maximum(n_, 1)[:, None]
    nA, mA = ort(A); nB, mB = ort(B_)
    ok = (nA >= 100) & (nB >= 100)
    dE = np.linalg.norm(mA[ok] - mB[ok], axis=1)
    if not dE.size:
        return dict(karo=0, ort=None, p95=None, max=None)
    return dict(karo=int(ok.sum()), ort=round(float(dE.mean()), 3), p95=round(float(np.percentile(dE, 95)), 3), max=round(float(dE.max()), 3))


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
                                                           kose=dict(pencere=KOSE_PEN, cekirdek=KOSE_CEKIRDEK, koyu_lum=KOSE_KOYU, dis_sinir_yuzde=KOSE_YUZDE, tasma_px=0),
                                                           layers_b=dict(kemer_esik=KEMER_ESIK, rampa=KEMER_RAMPA, dikis_dE=DIKIS_DE, dikis_grad=DIKIS_GRAD, kemer_kesilen=0, kemer_cekirdek_fark=1.0),
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
        boy, boy_img = firstpage_boylar(zem, o)
        xs12 = (kc["sol"], 3599 - kc["sag"]); ys12 = (kc["ust"], 5399 - kc["alt"])
        og12 = kose_oztest_gercek(son, xs12, ys12, K)
        og8 = kose_oztest_gercek(boy_img["8x10"][0], boy_img["8x10"][1], boy_img["8x10"][2], boy_img["8x10"][3])
        boy_ok = all(v["toplam"] == 0 for v in boy.values()) and len(boy) == 14
        rap["FirstPage"] = dict(zemin=yon, cerceve_8x10={k: (v if k == "yan_pay" else {x: v[x] for x in v if x not in ("ofs", "oran")})
                                                        for k, v in o.items()}, cerceve=rc, cerceve_kapi_12x18=kc,
                                doku_onceden_cizgi_kontrast_sol=on_k,
                                beklenen_pay=round(o["yan_pay"] * K, 2), kose_oztest_12x18=kose_oztest(K), kose_oztest_8x10=kose_oztest(1.0),
                                kose_oztest_gercek_12x18=og12, kose_oztest_gercek_8x10=og8, kose_tasma_14_boy=boy,
                                kose_tasma_14_boy_not="aile sayfasi (W 3600, zemin + kodla cerceve, esit pay) -> boy pikseli LANCZOS -> JPEG q95 4:4:4 "
                                                      "-> olcum; 5x7 A sayfasindan dikey ortali kirpma. Ogeler (isim / yazi) yalniz 12x18'de; kose penceresinde oge yok",
                                kose_tasma_eski_8x10_kaynak_bilgi=o["kose_tasma_8x10"],
                                pass_=bool(kc["pass_"] and kose_oztest(K)["pass_"] and kose_oztest(1.0)["pass_"] and og12["pass_"] and og8["pass_"] and boy_ok))
        kayit("FirstPage", son, e, "first_page")
        kose_yakin(out, e, o, son, xs12, ys12, boy_img["8x10"])

    if "Layers" in stiller:
        e = eski("4_Layers")
        duz = np.median(e[2600:2950, 800:1600].reshape(-1, 3), 0)
        km = kemer_maske(e, duz)                                        # kemer (esik 25): kesim kapisi bununla (degismedi)
        # B USTE SABIT (Serdar 1 Kas karar b): zemin = YENI duz seftali doku (4_Layers_2x3_kaynak.png, ESRGAN, esit olcek); kemer katmanlari
        # ESKI 8x10 pikseli x1,5 uste sabit (oy = 0), tam genislik; yazilar ayni donusumle.
        # F5 (Serdar 1 Kas karar b): (a) karisim TUM yukseklikte (eski [:4500] siniri kalkti; 4. kosu satir 4500'de yatay kesim), (b) kemer
        # maskesi renk farkindan degil GEOMETRIDEN (kemer_geo: ic kemer super-elips + iki on duzlem dogrusu), kagit lekeleri maskeye girmez.
        zemB, yonB = doku(Path(a.doku_dizin, "4_Layers_2x3_kaynak.png"), a.esrgan, a.hizli)
        ust = np.zeros((5400, 3600, 3), np.float32)
        ust[:4500] = cv2.resize(e, (3600, 4500), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
        g = kemer_geo(e)
        Mg = kemer_geo_maske(g, 5400, 3600, K)
        Mp = cv2.dilate(Mg.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * KEMER_PAY + 1, 2 * KEMER_PAY + 1)))
        uz = cv2.distanceTransform((1 - Mp).astype(np.uint8), cv2.DIST_L2, 5)
        t_ = np.clip(1 - uz / KEMER_RAMPA, 0, 1); w2 = t_ * t_ * (3 - 2 * t_)
        eski_yok = int((w2[4500:] > 0).sum())                          # eski goruntu 4500 satir; altinda eski piksel YOK (0 olmali)
        Bz = np.clip(ust * w2[..., None] + zemB.astype(np.float32) * (1 - w2[..., None]), 0, 255).astype(np.uint8)
        b, fB = ogeli_blok(bp, "layers", Bz[:4500], S)
        B = Bz.copy(); B[:4500] = b
        fBt = np.zeros((5400, 3600), bool); fBt[:4500] = fB
        ogesiz = ~(cv2.dilate(fBt.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0)
        # KEMER KESIM KAPISI (Serdar 1 Kas): eski kemer (esik 25) pikselleri x1,5 ile tuvale tasinir; tuval disina dusen = kesilen (0 olmali)
        ky, kx = np.where(km)
        X_, Y_ = (kx + 0.5) * K, (ky + 0.5) * K
        kes = int(((X_ < 0) | (X_ >= 3600) | (Y_ < 0) | (Y_ >= 5400)).sum())
        # geometrik maske de tuvalde mi (eski 8x10 tum alani x1,5 = 3600x4500 icinde; kesilen 0)
        # kemer cekirdegi orijinal mi: w = 1, geometrik maske ve oge disi pikselde |B - eski x1,5| (kayit oncesi, uint8 yuvarlama)
        cek = (w2 >= 0.999) & Mg & ogesiz
        cek[4500:] = False
        cek_fark = np.abs(B.astype(np.float32) - ust)[cek] if cek.any() else np.zeros(1)
        # leke bilgisi: eski renk maskesi (esik 12) ile geometrik maske farki (leke / acik yan duzlem pikselleri; 12x18 px)
        km12 = cv2.resize(kemer_maske(e, duz, KEMER_ESIK).astype(np.uint8), (3600, 4500), interpolation=cv2.INTER_NEAREST) > 0
        leke_disarida = int((km12 & ~Mp[:4500].astype(bool)).sum())
        # YATAY CIZGI DEDEKTORU (F5): tum yukseklik, zemin bolgesi (geometrik kemer + pay disi, oge disi)
        Lb = lum(B)
        gecerli = ~(Mp > 0) & ogesiz
        (c_max, c_y, c_x), c_prof = yatay_cizgi(Lb, gecerli, CIZGI_PEN)
        (c_tam, c_ty, _), _ = yatay_cizgi(Lb, gecerli, 3600)
        (z_max, z_y, z_x), _ = yatay_cizgi(lum(zemB), gecerli, CIZGI_PEN)   # taban: yeni doku tek basina, ayni bolge
        cizgi_grafik(c_prof, out / "CIZGI_KESIT_Layers_B.png", CIZGI_ESIK, c_y)
        # YEREL DIKIS (F5): eski -> yeni doku gecisinin ortasi (w = 0,5) cevresinde +-20 px iki bant, 64 px karolarda dE76
        dk = dikis_yerel(B, uz, ogesiz, KEMER_RAMPA / 2, 20)
        dk_taban = dikis_yerel(zemB, uz, ogesiz, KEMER_RAMPA / 2, 20)
        dk_eski = dikis_yerel(np.clip(ust, 0, 255).astype(np.uint8), uz, ogesiz & (np.arange(5400)[:, None] < 4500), KEMER_RAMPA / 2, 20)
        dk_uc = dikis_yerel(B, uz, ogesiz, KEMER_RAMPA / 2, 20, uc=True)
        # kenar gradyani (onceki kapi, kalir): rampa ortasinda B gradyan p99 / yeni doku gradyan p99
        gB = cv2.Sobel(Lb, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(Lb, cv2.CV_32F, 0, 1) ** 2
        Lz = lum(zemB); gZ = cv2.Sobel(Lz, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(Lz, cv2.CV_32F, 0, 1) ** 2
        kenar = (w2 > 0.3) & (w2 < 0.7) & ogesiz
        g_or = float(np.sqrt(np.percentile(gB[kenar], 99)) / max(np.sqrt(np.percentile(gZ, 99)), 1e-6)) if kenar.any() else None
        tasarim = np.where(fBt)
        zr = np.median(zemB.reshape(-1, 3), 0)
        rap["Layers_B"] = dict(ust_olcek=1.5, zemin=yonB, yeni_doku_medyan_rgb=zr.round(1).tolist(), eski_duz_rgb=np.asarray(duz).round(1).tolist(),
                               kemer_geometri=g, kemer_pay_px=KEMER_PAY, kemer_rampa_px=KEMER_RAMPA,
                               eski_piksel_4500_alti_px=eski_yok, leke_px_maske_disinda_bilgi=leke_disarida,
                               kemer_kesim=dict(kemer_px_8x10=int(km.sum()), kesilen_px=kes, kesilen_oran=round(kes / max(int(km.sum()), 1), 6),
                                                geometrik_maske_px_12x18=int(Mg.sum()), geometrik_4500_alti_px=int(Mg[4500:].sum())),
                               kemer_cekirdek=dict(px_12x18=int(cek.sum()), fark_max=round(float(cek_fark.max()), 3), fark_p99=round(float(np.percentile(cek_fark, 99)), 3)),
                               yatay_cizgi=dict(tanim=f"ardisik satir lum farki, {CIZGI_PEN} px sutun penceresinde gecerli (zemin, oge disi) sutun ortalamasi; tum yukseklik",
                                                max=round(c_max, 3), satir=c_y, pencere_x=c_x, esik_oneri=CIZGI_ESIK,
                                                tam_satir_3600_max_bilgi=round(c_tam, 3), tam_satir_satir=c_ty,
                                                taban_yeni_doku_max=round(z_max, 3), taban_satir=z_y, kesit_grafik="CIZGI_KESIT_Layers_B.png"),
                               dikis_yerel=dict(tanim="w = 0,5 cizgisinin (kemer payindan 30 px) +-20 px iki yani, 64 px karo, karo basina iki yan ortalama Lab farki dE76",
                                                cikti=dk, taban_yeni_doku=dk_taban, taban_eski_doku=dk_eski, rampa_uclari_0_20_vs_60_80_bilgi=dk_uc,
                                                esik_oneri=DIKIS_YEREL_ESIK),
                               kenar_gradyan_orani_p99=round(g_or, 3) if g_or else None, esik_gradyan=DIKIS_GRAD,
                               eklenen_bant=[4500, 5400], eklenen_bantta_oge_px=int(fBt[4500:].sum()),
                               tasarim_kutu=[int(tasarim[1].min()), int(tasarim[0].min()), int(tasarim[1].max()), int(tasarim[0].max())],
                               tasarim_alt_bosluk_px=int(5400 - 1 - tasarim[0].max()),
                               sift_ust=sift_afin(lum(e[:DUZ_Y]), lum(B[:round(DUZ_Y * K)])))
        L_ = rap["Layers_B"]
        L_["pass_"] = bool(kes == 0 and eski_yok == 0 and float(cek_fark.max()) <= 1.0 and L_["eklenen_bantta_oge_px"] == 0
                           and L_["sift_ust"].get("pass_", False) and c_max <= CIZGI_ESIK
                           and dk["max"] is not None and dk["max"] <= DIKIS_YEREL_ESIK
                           and g_or is not None and g_or <= DIKIS_GRAD)
        Image.fromarray(B).save(out / "Layers_B_12x18.jpg", quality=95, subsampling=0, dpi=(300, 300))
        # yakin planlar: eski 4500 bolgesi x2 (satir 4200-4800, sol 600 px) ve kemer alt ucu rampa x2
        yakin.append(("Layers_B 4500 bolgesi", B[4350:4650, 0:300]))
        ys_, xs_ = np.where((w2 > 0.3) & (w2 < 0.7))
        if ys_.size:
            j_ = int(np.argmax(ys_)); cy_, cx_ = int(ys_[j_]), int(xs_[j_])
            yakin.append(("Layers_B rampa alt uc", B[max(0, cy_ - 150):cy_ + 150, max(0, cx_ - 150):cx_ + 150]))
        Image.fromarray(np.ascontiguousarray(B[4200:4800, 0:600])).resize((1200, 1200), Image.NEAREST).save(out / "LB_4500_YAKIN_x2.jpg", quality=92)
        s8 = ogeler(bp1, e, "layers")
        kontak.append(("Layers_B", s8, B))
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
