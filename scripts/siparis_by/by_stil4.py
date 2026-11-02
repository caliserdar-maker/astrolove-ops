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
  (Layers B Serdar 1 Kas F 3. kosu karariyla birakildi; F5'te B'ye donuldu.)
  Layers B2 (F6, Serdar 2 Kas: B yerlesimi RED, icerik yukari toplanmis): eski 8x10 x1,5 kemerin duz bolumunden (8x10 satir 1250) ikiye
            ayrilir, alt parca 900 satir iner, arada kemer uzatma bandi (sutun medyani + yeni doku; eski piksel degil); ogeler uc dikey
            grupta tasinir (YEAR ONE 0, buyuk sembol 450, alttakiler 900). Kapi: icerik kutusu alt / ust bosluk orani eski 8x10 +-%10.
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
HT = 5400   # F7 (Serdar 2 Kas): aile tuvali yuksekligi (genislik 3600). tuval(ht) HT ve OY'yi (ogeler blogu = eski 8x10 x1,5 = 4500 satir, dikey ortali) degistirir
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
# F6 (Serdar 2 Kas: Layers B yeni 12x18 RED, icerik yukari toplanmis, alt ~1/5 bos; eski 8x10'da kemer asagi iner, baslik + tarih alta yakin)
UZAT = round(5400 - 3000 * K)   # 900: kemer uzatma bandi (12x18 px) = tuval - eski 8x10 x1,5; tuval tam dolar (eklenen yeni doku bandi yok)
UZAT_Y8 = 1250         # kesim satiri (eski 8x10): kemerin DUZ bolumu ic kemer cy 1037 ile on duzlemin en ust noktasi 1463 (sol kenar) arasi
#                        (olcum 2 Kas kemer_geo); 1060-1440 satirlarinda kemer sutun medyani satirdan satira en cok 8-12 seviye (doku), ic kemer 5
UZAT_KAYNAK = 300      # F7 it. 2: ayna doseme kaynagi, kesim satirinin ustunde 300 satir (12x18; kemer duz bolumu 1555-2194, ys 1875)
UZAT_ORT = 45          # uzatma bandi sutun rengi: kesim satirinin +-45 satiri (12x18) sutun medyani (ONERI)
UZAT_GECIS = 180       # bant <-> eski piksel gecisi (12x18 satir, smoothstep; ONERI). F6 it. 1 (yerel) 60: eski kemer dokusu (burusuk) ile
#                        sentez dokusu (yeni kagit) arasi sinir yakin planda seciliyordu (kapilar PASS); it. 2: 180 (~0,6 inc) yumusak gecis
OGE_ORTA = 0.5         # buyuk sembol kaymasi = UZAT x 0,5 (ust grup YEAR ONE 0, alt gruplar UZAT; ONERI, Serdar onayi yok)
BOSLUK_TOL = 0.10      # gorev metni F6: icerik kutusu alt / ust bosluk orani eski 8x10 oraninin +-%10'u


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
            X, Y = round(x0 * K), round(HT - (3000 - y0) * K)
        else:
            X, Y = round(3600 - (2400 - x0) * K), round(HT - (3000 - y0) * K)
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


def uzat_y8(H, olcek, ys, D):
    """F6 Layers B2: tuval satiri -> eski 8x10 satiri (parcali): Y < ys ust parca (Y / olcek), ys <= Y < ys + D uzatma bandi (sabit = kesim
    satiri; kemerin duz bolumu), Y >= ys + D alt parca (Y - D) / olcek. Piksel merkezi kurali kemer_geo_maske ile ayni."""
    Y = np.arange(H, dtype=np.float64)
    Yk = np.where(Y < ys, Y, np.where(Y < ys + D, ys, Y - D))
    return (Yk + 0.5) / olcek - 0.5


def bosluk_orani(m):
    """F6 icerik kutusu dikey dengesi: oge maskesinin (True = oge pikseli) ust bosluk = ilk oge satiri, alt bosluk = H - 1 - son oge satiri;
    oran = alt / ust. Oge yoksa None."""
    r = np.where(m.any(1))[0]
    if not r.size:
        return dict(ust=None, alt=None, oran=None)
    u, a_ = int(r.min()), int(m.shape[0] - 1 - r.max())
    return dict(ust=u, alt=a_, oran=round(a_ / max(u, 1), 4))


def kemer_geo_maske(g, H, W, olcek, oy=0, y8=None):
    """geometrik kemer maskesi (True = kemer katmani) H x W tuvalde; piksel merkezi -> eski 8x10: x8 = (X + 0,5) / olcek - 0,5.
    y8 verilirse (F6 uzat_y8) satir eslemesi ondan alinir."""
    k = g["ic_kemer"]; sl, sg = g["on_duzlem"]["sol"], g["on_duzlem"]["sag"]
    x8 = ((np.arange(W, dtype=np.float64) + 0.5) / olcek - 0.5)[None, :]
    y8 = ((np.arange(H, dtype=np.float64) - oy + 0.5) / olcek - 0.5)[:, None] if y8 is None else np.asarray(y8, np.float64)[:, None]
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
# ------------------------------------------------------------------ F7 (Serdar 2 Kas): 14 boy, her en-boy oraninda yeniden yerlesim
# Wall art yontemi (siparis_dijital/tek_jpg.py, by_boy.py): oran AILESI basina tek sayfa, ailedeki boylar o sayfanin yeniden orneklenmesi.
# F7'de 5x7 da kendi ailesi (Serdar: dikey ortali kirpma YASAK; wall art 5x7'yi A ailesinden <= %1,5 kirpar, burada kirpma yok).
# Aile sayfasi: genislik 3600, yukseklik H = 3600 / oran. Ogeler blogu (eski 8x10 x1,5 = 3600x4500) dikey ortali (OY = (H - 4500) / 2);
# 2:3 (H 5400) = onayli 12x18 ile ayni yol. Zemin: 3600x5400 doku (ESRGAN) ORTADAN kisaltilir (orta_kes): ust ve alt kenar bantlari
# (Botanical tirtikli kagit kenari, FirstPage / Starlit kenar) aynen kalir, ortadan 5400 - H satir cikar; birlesim en kucuk hata dikisi.
AILE7 = {"4x5": 4500, "11x14": round(3600 * 14 / 11), "3x4": 4800, "2x3": 5400, "A": round(3600 * 297 / 210), "5x7": 5040}
BOY_AILE7 = {"5x7": "5x7", "8x10": "4x5", "16x20": "4x5", "24x30": "4x5", "11x14": "11x14", "12x16": "3x4", "18x24": "3x4",
             "12x18": "2x3", "16x24": "2x3", "20x30": "2x3", "24x36": "2x3", "A4": "A", "A3": "A", "A2": "A"}
KES_ORT = 200          # orta_kes bindirme satiri (3600 genislik; ONERI)
KES_YUMUSAK = 8        # dikis cevresi yumusak gecis (+- satir; ONERI)
KES_SIGMA = 25.0       # dikis dusuk frekans ayrimi Gauss sigma (px; ONERI)
KES_ARA = 400          # F7 it. 2: kesim yeri arama araligi (+- satir, ht/2 cevresi; ONERI). Ust / alt 600 satir (kenar bantlari) dokunulmaz
KENAR_PAY = 0.04       # Serdar 2 Kas: tum ogeler kenardan en az %4 iceride (ust / alt yukseklige, sol / sag genislige gore)
LAYERS_SINIR = (463, 1660, 2134)   # Layers oge gruplari (eski 8x10 satir): YEAR ONE | sembol | isaret + isim | baslik + tarih.
#   Olcum 2 Kas, 78 cift by_poster olcek 1: YEAR ONE 297-379, sembol 547-1626, isaret+isim 1695-2096, baslik+tarih 2173-2834 (en genis
#   araliklar); sinirlar gruplar arasi bosluklarin ortasi. Her kosuda dogrulanir: sinirin +-SINIR_BOS satirinda oge pikseli yok, her bant dolu.
SINIR_BOS = 30
LAYERS_KAYMA = (0.0, 0.5, 1.0, 1.0)   # grup kaymasi = D x katsayi (D = H - 4500). Baslik ve tarih BIRLIKTE (ayni kayma)
BT_TOL = 2.0           # baslik-tarih arasi bosluk (aile px) = eski 8x10 x 1,5 +- 2 px (yeniden ornekleme payi; ONERI)


def tuval(ht):
    global HT, OY
    if ht < 4500:
        raise SystemExit(f"DUR: aile yuksekligi {ht} < 4500")
    HT, OY = int(ht), (int(ht) - 4500) // 2


def orta_kes(z, ht, c=None):
    """3600x5400 zemini ortadan ht satira kisaltir. Ust parca [0, c + O/2), alt parca [c - O/2 + R, H) (R = H - ht); O satirlik
    bindirmede iki parcanin RGB kare farkinin soldan saga en kucuk toplamli yolu (komsu sutunda +-1 satir) secilir; yolun ustu ust parca,
    alti alt parca, +-KES_YUMUSAK satir smoothstep. Donus: (zemin, bilgi)."""
    H, W = z.shape[:2]
    if ht == H:
        return z, dict(kesim=0)
    R, O = H - ht, KES_ORT
    c = ht // 2 if c is None else int(c)
    a0 = c - O // 2
    A = z[a0:a0 + O].astype(np.float32); B_ = z[a0 + R:a0 + R + O].astype(np.float32)
    E = ((A - B_) ** 2).sum(2)
    E[:KES_YUMUSAK + 2] += 1e9; E[-KES_YUMUSAK - 2:] += 1e9
    C = E.copy(); gk = np.zeros(E.shape, np.int8); ar = np.arange(O)
    for x in range(1, W):
        p = C[:, x - 1]
        st = np.stack([np.r_[np.inf, p[:-1]], p, np.r_[p[1:], np.inf]])
        k = st.argmin(0); C[:, x] += st[k, ar]; gk[:, x] = k - 1
    y = np.empty(W, int); y[-1] = int(C[:, -1].argmin())
    for x in range(W - 1, 0, -1):
        y[x - 1] = y[x] + gk[y[x], x]
    t = np.clip((ar[:, None] - y[None, :] + KES_YUMUSAK) / (2 * KES_YUMUSAK), 0, 1); t = t * t * (3 - 2 * t)
    # F7 yerel deneme 1 (4:5 dikis cizgisi 1,311 > taban 1,105): iki parcanin aydinlik (dusuk frekans) farki dikiste basamak yapiyordu.
    # Dusuk frekans (sigma KES_SIGMA, tum zeminde) bindirme boyunca smoothstep ile karisir; yuksek frekans (doku) en kucuk hata dikisiyle.
    zl = cv2.GaussianBlur(z.astype(np.float32), (0, 0), KES_SIGMA)
    lA, lB = zl[a0:a0 + O], zl[a0 + R:a0 + R + O]
    u = (ar.astype(np.float32) + 0.5) / O; u = (u * u * (3 - 2 * u))[:, None, None]
    orta = lA * (1 - u) + lB * u + (A - lA) * (1 - t[..., None]) + (B_ - lB) * t[..., None]
    out = np.concatenate([z[:a0], np.clip(np.round(orta), 0, 255).astype(np.uint8), z[a0 + R + O:]], 0)
    assert out.shape[0] == ht
    yol_fark = np.sqrt(E[y, np.arange(W)] / 3)
    return out, dict(kesim=R, kesim_merkez=int(c), bindirme=[int(a0), int(a0 + O)], dikis_satir=[int(a0 + y.min()), int(a0 + y.max())],
                     dikis_rgb_fark_ort=round(float(yol_fark.mean()), 2), dikis_rgb_fark_p99=round(float(np.percentile(yol_fark, 99)), 2))


def orta_kes_sec(z, ht):
    """F7 it. 2 (kosu 41418784010: Botanical 3:4 dikis 1,008 > esik 1,0): kesim merkezi ht/2 + k x 100 (k = -4..4; ust / alt 600 satir
    kenar bandi dokunulmaz) adaylarindan dikis kapisinin PAYI (esik - olcum) en buyuk olan secilir. Kapi ve esik degismez."""
    if ht == z.shape[0]:
        zem, b = orta_kes(z, ht)
        return zem, b, kesim_kapi(z, zem, b)
    R, O = z.shape[0] - ht, KES_ORT
    en = None; aday = []
    for k in range(-KES_ARA // 100, KES_ARA // 100 + 1):
        c = ht // 2 + 100 * k
        if c - O // 2 < 600 or c + O // 2 + R > z.shape[0] - 600:
            continue
        zem, b = orta_kes(z, ht, c); kk = kesim_kapi(z, zem, b)
        pay = kk["esik"] - kk["dikis_cizgi_max"]; aday.append([c, round(pay, 3)])
        if en is None or pay > en[0]:
            en = (pay, zem, b, kk)
    en[3]["aday_kesim_pay"] = aday
    return en[1], en[2], en[3]


def kesim_kapi(zem5400, zem, bilgi):
    """orta_kes dikisi: yatay cizgi dedektoru (F5, 240 px) cikti bindirme satirlarinda; taban = ayni dedektor kesilmemis dokunun IKI kaynak
    bandinda (ust parca bindirmesi ve alt parca karsiligi; cikti satirlari ikisinden gelir). Yerel olcum 2 Kas: cikti en buyugu dikiste
    degil alt kaynak bandinin kendi dokusunda (Timeless 4:5 cikti 1,294 = alt kaynak 1,311 yakin; doku 200 satirlik bantlarda medyan 1,26).
    Kapi: cikti <= max(CIZGI_ESIK, ust taban, alt taban) (ONERI)."""
    if not bilgi.get("kesim"):
        return dict(kesim=0, pass_=True)
    a0, a1 = bilgi["bindirme"]; R = bilgi["kesim"]
    det = lambda X: yatay_cizgi(lum(X), np.ones(X.shape[:2], bool), CIZGI_PEN)[0]  # noqa: E731
    (m, y_, _), (mu, _, _), (ma, _, _) = det(zem[a0:a1]), det(zem5400[a0:a1]), det(zem5400[a0 + R:a1 + R])
    esik = max(CIZGI_ESIK, mu, ma)
    return dict(bilgi, dikis_cizgi_max=round(m, 3), dikis_satir=a0 + y_, taban_ust=round(mu, 3), taban_alt=round(ma, 3),
                esik=round(esik, 3), pass_=bool(m <= esik + 1e-6))


def kenar_olc(m):
    """oge maskesi: kenara en yakin oge pikseli (px ve oran), kenara degen piksel."""
    H, W = m.shape
    r = np.where(m.any(1))[0]; c = np.where(m.any(0))[0]
    if not r.size:
        return dict(bos=True, pass_=False)
    u, a_, s_, g_ = int(r.min()), int(H - 1 - r.max()), int(c.min()), int(W - 1 - c.max())
    oran = dict(ust=round(u / H, 4), alt=round(a_ / H, 4), sol=round(s_ / W, 4), sag=round(g_ / W, 4))
    deg = int(m[0].sum() + m[-1].sum() + m[:, 0].sum() + m[:, -1].sum())
    return dict(px=dict(ust=u, alt=a_, sol=s_, sag=g_), oran=oran, en_kucuk=min(oran.values()), kenara_degen_px=deg,
                pass_=bool(min(oran.values()) >= KENAR_PAY and deg == 0))


def ogeli_olcek(bp, fn, img, S):
    """ogeler blogu boy cozunurlugunde: genislik W, yukseklik round(1,25 W), dikey ortali (aile kurali ile ayni)."""
    Ht, Wt = img.shape[:2]
    hb = round(Wt * 1.25); oy = (Ht - hb) // 2
    son = img.copy()
    b, fark = ogeli_blok(bp, fn, img[oy:oy + hb], S)
    son[oy:oy + hb] = b
    f = np.zeros(img.shape[:2], bool); f[oy:oy + hb] = fark
    return son, f


def susleme_tasi(e, zem, p, yerle, haric_fn):
    """Timeless / Botanical ortak: oran katmanlariyla susleme aktarimi; yerle(ad, kt) -> (X, Y). Donus out (float), yer, tum_yeni maske,
    susleme_kesilen_px (tuval disi)."""
    out = zem.astype(np.float32); yer = {}
    tum = np.zeros(e.shape[:2], bool)
    for v in p.values():
        tum |= v
    tum_yeni = np.zeros(zem.shape[:2], bool); kesilen = 0
    for ad, m in p.items():
        if ad == "diger":
            continue
        R, _ = oran(e, m, haric_ek=haric_fn(tum, m))
        kt = kutu(m); x0, y0, x1, y1 = kt
        X, Y = yerle(ad, kt)
        ku, kk = carp(out, R, kt, X, Y)
        yer[ad] = dict(kutu_eski=kt, X=X, Y=Y, kenar_uzaklik_eski=dict(sol=x0, ust=y0, sag=2400 - x1, alt=3000 - y1),
                       kutu_yeni=ku, oran_katmani=dict(oran.son))
        X0, Y0, X1, Y1 = ku
        mm = cv2.resize(m[y0:y1, x0:x1].astype(np.uint8), (X1 - X0, Y1 - Y0), interpolation=cv2.INTER_NEAREST) > 0
        a0, b0 = max(0, -X0), max(0, -Y0); a1, b1 = min(X1 - X0, zem.shape[1] - X0), min(Y1 - Y0, zem.shape[0] - Y0)
        ic = mm[b0:b1, a0:a1]
        tum_yeni[Y0 + b0:Y0 + b1, X0 + a0:X0 + a1] |= ic
        kesilen += int(mm.sum() - ic.sum())
        yer[ad]["kenar_uzaklik_yeni"] = dict(sol=X0, ust=Y0, sag=zem.shape[1] - X1, alt=zem.shape[0] - Y1)
    return out, yer, tum_yeni, kesilen


def timeless_aile(e, zem, bp, S, p):
    def yerle(ad, kt):
        x0, y0 = kt[0], kt[1]
        if ad == "yay":
            return round(x0 * K), round(y0 * K + OY)
        if ad == "dal_sol_ust":
            return round(x0 * K), round(y0 * K)
        if ad == "dal_sol_alt":
            return round(x0 * K), round(HT - (3000 - y0) * K)
        return round(3600 - (2400 - x0) * K), round(HT - (3000 - y0) * K)
    out, yer, tum_yeni, kesilen = susleme_tasi(e, zem, p, yerle, lambda tum, m: tum & ~m)
    son, fark = ogeli_tum(bp, "timeless", np.clip(out, 0, 255).astype(np.uint8), S)
    har = cv2.dilate(fark.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    har_o = (cv2.dilate(tum_yeni.astype(np.uint8), np.ones((21, 21), np.uint8)) > 0) | har
    kap = {ad: susleme_kapi(e, son, p[ad], y["kutu_eski"], y["X"], y["Y"], har_o) for ad, y in yer.items()}
    kes = int((cv2.dilate(tum_yeni.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & har).sum())
    r = dict(yerlesim=yer, kapi=kap, susleme_oge_kesisim_px=kes, susleme_tuval_disi_px_bilgi=kesilen,
             atanamayan_parca_px=int(p["diger"].sum()) if "diger" in p else 0)
    r["pass_"] = bool(all(v["pass_"] for v in kap.values()) and kes == 0 and "diger" not in p
                      and set(yer) == {"yay", "dal_sol_ust", "dal_sol_alt", "dal_sag_alt"})
    return son, fark, r


CICEK_KAYMA_MAX = 150   # F7 it. 2 (kosu 41418784010: Botanical 4:5 kesisim 463 px, A 55 px): cicek ogeye degmeyene kadar DISARI kayar
CICEK_KAYMA_ADIM = 6    # (sag ust yukari, sol alt asagi), en cok 150 px (12x18 olcegi, 0,5 inc; ONERI). Kayma rapora yazilir.


def botanical_aile(e, zem, bp, S, p, km_e, kk_e):
    km_n, kk_n = kagit(zem)
    _, fark0 = ogeli_tum(bp, "botanical", zem, S)                      # oge konumlari zeminden bagimsiz (yalniz kaydirma olcumu)
    yasak = cv2.dilate(fark0.astype(np.uint8), np.ones((17, 17), np.uint8)) > 0   # kapidaki iki 9x9 genisletmenin birlesimi
    kayma = {}

    def degiyor(m, kt, X, Y):
        x0, y0, x1, y1 = kt
        w, h = round((x1 - x0) * K), round((y1 - y0) * K)
        mm = cv2.resize(m[y0:y1, x0:x1].astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0
        H_, W_ = yasak.shape
        a0, b0 = max(0, -X), max(0, -Y); a1, b1 = min(w, W_ - X), min(h, H_ - Y)
        return int((mm[b0:b1, a0:a1] & yasak[Y + b0:Y + b1, X + a0:X + a1]).sum())

    def yerle(ad, kt):
        x0, y0 = kt[0], kt[1]
        if ad == "cicek_sag_ust":
            X, Y, yon = round(kk_n[2] - (kk_e[2] - x0) * K), round(kk_n[1] + (y0 - kk_e[1]) * K), -1
        else:
            X, Y, yon = round(kk_n[0] + (x0 - kk_e[0]) * K), round(kk_n[3] - (kk_e[3] - y0) * K), 1
        d, n0 = 0, degiyor(p[ad], kt, X, Y)
        while d < CICEK_KAYMA_MAX and degiyor(p[ad], kt, X, Y + yon * d):
            d += CICEK_KAYMA_ADIM
        kayma[ad] = dict(kayma_px=yon * d, ilk_kesisim_px=n0, son_kesisim_px=degiyor(p[ad], kt, X, Y + yon * d))
        return X, Y + yon * d
    out, yer, tum_yeni, kesilen = susleme_tasi(e, zem, p, yerle, lambda tum, m: (tum & ~m) | ~km_e)
    son, fark = ogeli_tum(bp, "botanical", np.clip(out, 0, 255).astype(np.uint8), S)
    har = cv2.dilate(fark.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    har_o = (cv2.dilate(tum_yeni.astype(np.uint8), np.ones((21, 21), np.uint8)) > 0) | har | ~km_n
    ki_e = cv2.erode(km_e.astype(np.uint8), np.ones((KAGIT_KENAR, KAGIT_KENAR), np.uint8)) > 0
    kap = {ad: susleme_kapi(e, son, p[ad], y["kutu_eski"], y["X"], y["Y"], har_o, ki_e) for ad, y in yer.items()}
    kes = int((cv2.dilate(tum_yeni.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & har).sum())
    kd = int((fark & ~km_n).sum())                       # F7 KAPI: oge pikseli kagit disinda (adacayi ustunde) = 0
    r = dict(yerlesim=yer, kagit_yeni=kk_n, kapi=kap, susleme_oge_kesisim_px=kes, oge_kagit_disi_px=kd, susleme_tuval_disi_px_bilgi=kesilen,
             cicek_kayma=kayma)
    r["pass_"] = bool(all(v["pass_"] for v in kap.values()) and kes == 0 and kd == 0 and set(yer) == {"cicek_sag_ust", "cicek_sol_alt"})
    return son, fark, r


def starlit_hazir(kod):
    eski = np.asarray(Image.open(Path(kod, B3.ESKI)).convert("RGB"))
    o = B3.olc(eski)
    yol = B3.YO.eski_yol(eski, B3.YOL_SEED)
    isik, maske, bilgi = YR.katman(eski, yol)
    return dict(eski=eski, o=o, yol=yol, isik=isik, maske=maske, bilgi=bilgi)


def starlit_aile(zem, bp, S, st):
    """by_ornek3 12x18 yolu (cerceve kodla, yay eski 8x10 isik katmani x1,5 ogeler bloguna, ogeler) aile tuvalinde."""
    z, rc = B3.cerceve(zem, K, st["o"])
    z, ry = YR.ekle(z, st["isik"], K, OY)
    son, fark = ogeli_tum(bp, "starlit", z, S)
    ogem = cv2.dilate(fark.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    yay = np.zeros(fark.shape, bool)
    yay[OY:OY + 4500] = cv2.resize(st["maske"], (3600, 4500), interpolation=cv2.INTER_LINEAR) > 0.05
    kes = int((ogem & yay).sum())
    son, yz = yazi_yildiz(son, fark, yay)
    return son, fark, dict(cerceve=rc, yay=ry, yay_oge_kesisim_px=kes, yazi_yildiz=yz, pass_=bool(kes == 0 and yz["pass_"]))


YILDIZ_ESIK = 20.0     # F7 it. 2 (Merkez 2 Kas, Starlit 12x18 x=1652 y=3736 "nokta"): yerel medyandan (31 px) bu kadar parlak (lum) zemin
YILDIZ_PAY = 0.5       # pikseli yildiz; yazi kutusu cevresi pay = yazi satiri yuksekligi x 0,5 (Merkez). Esik ONERI (olcumle turetilmedi).
YAZI_KORU = 25         # yazinin kendi isiltisi korunur: oge maskesi 25x25 genisletilir, bu alana dokunulmaz


def yazi_yildiz(img, fark, yay):
    """yazi satirlari (oge satir gruplari, en buyuk alanli grup = sembol HARIC) cevresinde (pay = satir yuksekligi x YILDIZ_PAY) zemin
    yildizlarini temizler (cv2.inpaint TELEA, 5 px genisletilmis maske). Kapi: temizlik sonrasi ayni olcumle yildiz bileseni 0."""
    r8 = np.where(fark.any(1))[0]
    if not r8.size:
        return img, dict(pass_=False, neden="oge yok")
    bl = np.split(r8, np.where(np.diff(r8) > 30)[0] + 1)
    alan = [int(fark[b[0]:b[-1] + 1].sum()) for b in bl]
    sembol = int(np.argmax(alan))
    koru = (cv2.dilate(fark.astype(np.uint8), np.ones((YAZI_KORU, YAZI_KORU), np.uint8)) > 0) | (cv2.dilate(yay.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0)
    bolge = np.zeros(fark.shape, bool); kutular = []
    for i, b in enumerate(bl):
        if i == sembol:
            continue
        y0, y1 = int(b[0]), int(b[-1]); c = np.where(fark[y0:y1 + 1].any(0))[0]
        x0, x1 = int(c.min()), int(c.max()); p = int(round((y1 - y0 + 1) * YILDIZ_PAY))
        Y0, Y1, X0, X1 = max(0, y0 - p), min(fark.shape[0], y1 + p + 1), max(0, x0 - p), min(fark.shape[1], x1 + p + 1)
        bolge[Y0:Y1, X0:X1] = True; kutular.append([X0, Y0, X1, Y1])

    def yildiz(a):
        L = lum(a)
        Y0, X0 = np.where(bolge.any(1))[0], np.where(bolge.any(0))[0]
        y0, y1, x0, x1 = Y0.min(), Y0.max() + 1, X0.min(), X0.max() + 1
        Lm = np.zeros_like(L)
        Lm[y0:y1, x0:x1] = cv2.medianBlur(np.clip(L[y0:y1, x0:x1], 0, 255).astype(np.uint8), 31).astype(np.float32)
        m = (L - Lm > YILDIZ_ESIK) & bolge & ~koru
        n, _, st_, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
        return m, n - 1
    m, n0 = yildiz(img)
    out = img
    if n0:
        mk = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8))
        mk[koru] = 0
        out = cv2.inpaint(np.ascontiguousarray(img), mk, 5, cv2.INPAINT_TELEA)
    _, n1 = yildiz(out)
    return out, dict(once_yildiz=int(n0), sonra_yildiz=int(n1), temizlenen_px=int(m.sum()), kutu=kutular, esik=YILDIZ_ESIK, pay=YILDIZ_PAY,
                     pass_=bool(n1 == 0))


SERIT_STD = (0.8, 1.25)   # F7 it. 2 serit doku kapisi (ONERI): uzatilan / kaynak yuksek frekans std orani
SERIT_GRAD = 0.20         # ONERI: (dikey / yatay gradyan) orani uzatilan bolgede kaynaga gore en cok +-%20 farkli


def serit_doku(B, mask, ys, D):
    """Layers kemer seritleri (sol x < 1800, sag x >= 1800; kemer ici, oge disi): UZATILAN bolge [ys, ys + D) ile KAYNAK [ys - D', ys)
    (D' = min(D, 300)) arasinda yuksek frekans std (lum - Gauss 6) ve ortalama |dy| / ortalama |dx| oranlari. D = 0 ise uzatma yok."""
    if D <= 0:
        return dict(uzatma=0, pass_=True)
    Lb = lum(B); hp = Lb - cv2.GaussianBlur(Lb, (0, 0), 6)
    gy = np.zeros_like(Lb); gy[1:] = np.abs(np.diff(Lb, axis=0)); gx = np.zeros_like(Lb); gx[:, 1:] = np.abs(np.diff(Lb, axis=1))
    Dk = min(D, 300); r = {}; ok = True
    for yan, sl in (("sol", slice(0, 1800)), ("sag", slice(1800, 3600))):
        olc = {}
        for ad, (a0, a1) in (("kaynak", (ys - Dk, ys)), ("uzatilan", (ys, ys + D))):
            m = mask[a0:a1, sl]
            if m.sum() < 1000:
                olc[ad] = None; continue
            olc[ad] = dict(px=int(m.sum()), std=round(float(hp[a0:a1, sl][m].std()), 3),
                           grad_orani=round(float(gy[a0:a1, sl][m].mean() / max(gx[a0:a1, sl][m].mean(), 1e-6)), 3))
        if olc["kaynak"] and olc["uzatilan"]:
            so = olc["uzatilan"]["std"] / max(olc["kaynak"]["std"], 1e-6)
            go = olc["uzatilan"]["grad_orani"] / max(olc["kaynak"]["grad_orani"], 1e-6)
            p_ = SERIT_STD[0] <= so <= SERIT_STD[1] and abs(go - 1) <= SERIT_GRAD
            olc.update(std_orani=round(so, 3), grad_orani_bagil=round(go, 3), pass_=bool(p_))
        else:
            olc["pass_"] = False
        ok = ok and olc["pass_"]; r[yan] = olc
    r.update(esik=dict(std=list(SERIT_STD), grad=SERIT_GRAD), pass_=bool(ok))
    return r


def layers_aile(e, zemB, bp, S, s8, f8, out, etiket, yakin):
    """Layers B (F7): F6 B2 yontemi aile yuksekliginde. D = HT - 4500 (4:5'te 0: eski 8x10 x1,5 aynen, uzatma bandi yok).
    Oge gruplari ALANA gore degil SAYFADAKI SIRAYA gore (LAYERS_SINIR): YEAR ONE 0, sembol D/2, isaret + isim D, baslik + tarih D."""
    duz = np.median(e[2600:2950, 800:1600].reshape(-1, 3), 0)
    km = kemer_maske(e, duz)
    ys = round(UZAT_Y8 * K); D = HT - 4500
    ust0 = cv2.resize(e, (3600, 4500), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
    ust = np.full((HT, 3600, 3), np.nan, np.float32)
    ust[:ys] = ust0[:ys]; ust[ys + D:] = ust0[ys:]
    if D > 0:
        # F7 it. 2 (Merkez incelemesi 2 Kas, KRITIK): F6 bandi (sutun medyani + yeni doku yuksek frekansi) kemer seritlerinde dokuyu
        # silip dikey cizgiye ceviriyordu (doku sapmasi 2,5 -> 0,8; dikey / yatay gradyan 1,0 -> 0,5). Yeni: bant, kesim satirinin
        # hemen ustundeki ESKI kemer satirlarindan (UZAT_KAYNAK satir, kemerin duz bolumu) AYNA doseme ile dolar (Serdar onayi:
        # "gercek dokudan dose ya da yansit"); ust birlesim aynada kesintisiz, alt birlesim UZAT_GECIS satir smoothstep.
        Lk = UZAT_KAYNAK
        kay_ = ust0[ys - Lk:ys]
        n_ = D + UZAT_GECIS
        i_ = np.arange(n_) % (2 * Lk)
        sira = np.where(i_ < Lk, Lk - 1 - i_, i_ - Lk)
        sent = kay_[sira]
        s0, s1 = ys, ys + n_
        tt = np.ones(n_, np.float32)
        r_ = np.arange(UZAT_GECIS, dtype=np.float32) / UZAT_GECIS; sm = r_ * r_ * (3 - 2 * r_)
        tt[-UZAT_GECIS:] = sm[::-1]
        eskiler = np.where(np.isnan(ust[s0:s1]), sent, ust[s0:s1])
        ust[s0:s1] = eskiler * (1 - tt[:, None, None]) + sent * tt[:, None, None]
    else:
        s0 = s1 = ys
    nan_px = int(np.isnan(ust).any(2).sum())
    ust = np.nan_to_num(ust)
    g = kemer_geo(e)
    y8 = uzat_y8(HT, K, ys, D)
    Mg = kemer_geo_maske(g, HT, 3600, K, y8=y8)
    Mp = cv2.dilate(Mg.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * KEMER_PAY + 1, 2 * KEMER_PAY + 1)))
    uz = cv2.distanceTransform((1 - Mp).astype(np.uint8), cv2.DIST_L2, 5)
    t_ = np.clip(1 - uz / KEMER_RAMPA, 0, 1); w2 = t_ * t_ * (3 - 2 * t_)
    Bz = np.clip(ust * w2[..., None] + zemB.astype(np.float32) * (1 - w2[..., None]), 0, 255).astype(np.uint8)
    # oge gruplari: sayfa sirasi (sabit sinirlar), her kosuda dogrulanir
    sin = (0,) + LAYERS_SINIR + (3000,)
    sat = f8.any(1)
    dolu = [bool(sat[sin[i]:sin[i + 1]].any()) for i in range(4)]
    sinir_temiz = [bool(not sat[b - SINIR_BOS:b + SINIR_BOS].any()) for b in LAYERS_SINIR]
    if not (all(dolu) and all(sinir_temiz)):
        raise SystemExit(f"DUR: Layers oge gruplari sinirlara uymuyor (dolu {dolu}, sinir temiz {sinir_temiz})")
    kay = [round(D * k_) for k_ in LAYERS_KAYMA]
    s12 = [0] + [round(b * K) for b in LAYERS_SINIR] + [4500]
    bantlar = [(s12[i], s12[i + 1], kay[i]) for i in range(4)]
    C = np.zeros((4500, 3600, 3), np.uint8)
    for a0, a1, s_ in bantlar:
        C[a0:a1] = Bz[a0 + s_:a1 + s_]
    Cb, fC = ogeli_blok(bp, "layers", C, S)
    B = Bz.copy(); fBt = np.zeros((HT, 3600), bool); dBt = np.zeros((HT, 3600), bool); kayip = 0
    for a0, a1, s_ in bantlar:
        d_ = (Cb[a0:a1] != C[a0:a1]).any(2)                              # aktarilan (yumusak kenar dahil) pikseller
        B[a0 + s_:a1 + s_][d_] = Cb[a0:a1][d_]
        dBt[a0 + s_:a1 + s_] = d_
        fBt[a0 + s_:a1 + s_] = fC[a0:a1]                                  # oge maskesi: ham fark (> 2), diger stillerle ayni tanim
        kayip += int(d_.sum()) - int(dBt[a0 + s_:a1 + s_].sum())
    ogesiz = ~(cv2.dilate(dBt.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0)
    ky, kx = np.where(km)
    X_, Y_ = (kx + 0.5) * K, (ky + 0.5) * K
    Y_ = np.where(Y_ >= ys, Y_ + D, Y_)
    kes = int(((X_ < 0) | (X_ >= 3600) | (Y_ < 0) | (Y_ >= HT)).sum())
    bant = np.zeros(HT, bool); bant[s0:s1] = True
    cek = (w2 >= 0.999) & Mg & ogesiz & ~bant[:, None]
    cek_fark = np.abs(B.astype(np.float32) - ust)[cek] if cek.any() else np.zeros(1)
    Lb = lum(B)
    gecerli = ~(Mp > 0) & ogesiz
    (c_max, c_y, c_x), _ = yatay_cizgi(Lb, gecerli, CIZGI_PEN)
    Mi = cv2.erode(Mg.astype(np.uint8), np.ones((2 * KEMER_PAY + 1, 2 * KEMER_PAY + 1), np.uint8)) > 0
    if D > 0:
        kb = np.zeros(HT, bool); kb[s0 - 1:s1 + 1] = True
        (k_max, k_y, k_x), _ = yatay_cizgi(Lb, Mi & ogesiz & kb[:, None], CIZGI_PEN)
    else:
        k_max, k_y, k_x = 0.0, -1, -1
    # F7 it. 2: bant artik ESKI kemer satirlarinin aynasi; ayni dedektor eski kemer x1,5'te (kesim satiri +-360, F6 tabani) 1,144
    # olcuyordu (eski dokunun kendisi). Esik = max(CIZGI_ESIK, bu taban); taban ayni kosuda olculur. KAPI DEGISIKLIGI (Merkez'e raporlanir).
    Mg0 = kemer_geo_maske(g, 4500, 3600, K)
    Mi0 = cv2.erode(Mg0.astype(np.uint8), np.ones((2 * KEMER_PAY + 1, 2 * KEMER_PAY + 1), np.uint8)) > 0
    kb0 = np.zeros(4500, bool); kb0[ys - 360:ys + 360] = True
    (k0_max, k0_y, _), _ = yatay_cizgi(lum(ust0), Mi0 & kb0[:, None], CIZGI_PEN)
    k_esik = max(CIZGI_ESIK, k0_max)
    dk = dikis_yerel(B, uz, ogesiz, KEMER_RAMPA / 2, 20)
    Lz2 = lum(zemB)
    gB = cv2.Sobel(Lb, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(Lb, cv2.CV_32F, 0, 1) ** 2
    gZ = cv2.Sobel(Lz2, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(Lz2, cv2.CV_32F, 0, 1) ** 2
    kenar = (w2 > 0.3) & (w2 < 0.7) & ogesiz
    g_or = float(np.sqrt(np.percentile(gB[kenar], 99)) / max(np.sqrt(np.percentile(gZ, 99)), 1e-6)) if kenar.any() else None
    bo8, bo = bosluk_orani(f8), bosluk_orani(fBt)
    bo_ok = bool(bo["oran"] is not None and abs(bo["oran"] / bo8["oran"] - 1) <= BOSLUK_TOL)
    # baslik-tarih arasi bosluk (Serdar 2 Kas): son grubun (baslik + tarih) satir alt gruplari (> 20 satir bosluk); son iki alt grup arasi
    def bt(m, a0, a1):
        r = np.where(m[a0:a1].any(1))[0] + a0
        bl = np.split(r, np.where(np.diff(r) > 20)[0] + 1)
        return (int(bl[-1][0] - bl[-2][-1] - 1), [[int(b_[0]), int(b_[-1])] for b_ in bl]) if len(bl) >= 2 else (None, [])
    bt8, bt8_g = bt(f8, LAYERS_SINIR[2], 3000)
    bt12, bt12_g = bt(fBt, s12[3] + kay[3], HT)
    bt_ok = bool(bt8 is not None and bt12 is not None and abs(bt12 - bt8 * K) <= BT_TOL)
    # ara bosluklar (bilgi): gruplar arasi (aile px) ve eski x1,5
    def gr_sinir(m, kayma_):
        r_ = []
        for i, (a0, a1, _) in enumerate(bantlar):
            rr = np.where(m[a0 + kayma_[i]:a1 + kayma_[i]].any(1))[0]
            r_.append((int(rr[0] + a0 + kayma_[i]), int(rr[-1] + a0 + kayma_[i])))
        return r_
    g12 = gr_sinir(fBt, kay)
    g8 = []
    for i in range(4):
        rr = np.where(f8[sin[i]:sin[i + 1]].any(1))[0] + sin[i]
        g8.append((round(rr[0] * K), round(rr[-1] * K)))
    ara = dict(yeni=[g12[i + 1][0] - g12[i][1] - 1 for i in range(3)], eski_x1_5=[g8[i + 1][0] - g8[i][1] - 1 for i in range(3)])
    oge_kemer = int((fBt & Mg).sum())
    sd = serit_doku(B, Mi & ogesiz, ys, D)
    su = sift_afin(lum(e[:UZAT_Y8]), lum(B[:ys]))
    sa = sift_afin(lum(e[UZAT_Y8:DUZ_Y]), lum(B[ys + D:round(DUZ_Y * K) + D]))
    r = dict(D=D, uzatma=dict(kesim_satiri_12x18=ys, bant_satir=D, sentez_gecis_satir=[s0, s1]),
             oge_gruplari=dict(sinir_8x10=list(LAYERS_SINIR), dolu=dolu, sinir_temiz=sinir_temiz, kayma=kay,
                               bantlar=[dict(satir=[a0, a1], kayma=s_) for a0, a1, s_ in bantlar], grup_satir_yeni=g12, ara_bosluk_bilgi=ara),
             baslik_tarih=dict(eski_8x10=bt8, eski_alt_grup=bt8_g, yeni=bt12, yeni_alt_grup=bt12_g, beklenen=round(bt8 * K, 1) if bt8 else None,
                               tol=BT_TOL, pass_=bt_ok),
             kaynaksiz_tuval_px=nan_px, oge_aktarim_kayip_px=kayip,
             kemer_kesim=dict(kemer_px_8x10=int(km.sum()), kesilen_px=kes),
             kemer_cekirdek=dict(px=int(cek.sum()), fark_max=round(float(cek_fark.max()), 3)),
             yatay_cizgi=dict(max=round(c_max, 3), satir=c_y, esik=CIZGI_ESIK),
             kemer_ici_cizgi=dict(max=round(k_max, 3), satir=k_y, esik=round(k_esik, 3), taban_eski_kemer=round(k0_max, 3), taban_satir=k0_y),
             dikis_yerel=dk, kenar_gradyan_orani_p99=round(g_or, 3) if g_or else None,
             bosluk=dict(eski_8x10=bo8, yeni=bo, tolerans=BOSLUK_TOL, oran_bagil=round(bo["oran"] / bo8["oran"], 4) if bo["oran"] else None, pass_=bo_ok),
             oge_kemer_kesisim_px=oge_kemer, sift_ust=su, sift_alt=sa, serit_doku=sd)
    r["pass_"] = bool(kes == 0 and nan_px == 0 and kayip == 0 and float(cek_fark.max()) <= 1.0 and oge_kemer == 0
                      and su.get("pass_", False) and sa.get("pass_", False) and c_max <= CIZGI_ESIK and k_max <= k_esik + 1e-6
                      and dk["max"] is not None and dk["max"] <= DIKIS_YEREL_ESIK and g_or is not None and g_or <= DIKIS_GRAD
                      and bo_ok and bt_ok and sd["pass_"])
    if D > 0:
        yakin.append((f"Layers_B {etiket} alt gecis (sol)", B[s1 - 400:s1 + 200, 0:600]))
    return B, fBt, r


def firstpage_boy(zem_aile, o, bp, S, Wt, Ht):
    """F5 onayli yol, kirpma yerine aile zemini: aile zemini boy pikseline LANCZOS, cerceve BOYUN cozunurlugunde (olcek K x Wt / 3600),
    ogeler boy cozunurlugunde, JPEG q95 4:4:4 gidis-donus, kose tasma olcumu."""
    z = np.asarray(Image.fromarray(zem_aile).resize((Wt, Ht), Image.LANCZOS))
    olcek = K * Wt / 3600
    img, rc = cerceve_ciz(z, o, olcek)
    img, fark = ogeli_olcek(bp, "first_page", img, S)
    img = _jpeg_gidis_donus(img)
    mt = o["yan_pay"] * olcek
    r = kose_tasma(img, (mt, Wt - 1 - mt), (mt, Ht - 1 - mt), olcek)
    return img, fark, dict(kose_tasma=r, olcek=round(olcek, 4), bosluk_cekilen_px=rc["bosluk_cekilen_px"], kirpilan_px=rc["kirpilan_px"],
                           pass_=bool(r["toplam"] == 0))


def boy_px(ad):
    import by_boy as BB
    wi, hi = BB.BOY[ad]
    return round(wi * 300), round(hi * 300)


def karo(img, ad, h=620):
    a = Image.fromarray(img) if not isinstance(img, Image.Image) else img
    a = a.resize((max(1, round(a.width * h / a.height)), h), Image.LANCZOS)
    k = Image.new("RGB", (a.width + 20, h + 56), (236, 236, 236)); k.paste(a, (10, 46))
    from PIL import ImageDraw
    ImageDraw.Draw(k).text((10, 8), ad, fill=(20, 20, 20), font=_font(30))
    return k


def _font(n):
    from PIL import ImageFont
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        if Path(f).exists():
            return ImageFont.truetype(f, n)
    return ImageFont.load_default()


def kontak_yaz(stil, karolar, yol):
    """stil basina tek sayfa: 14 boy, gercek en-boy orani, ayni yukseklik, 2 sira x 7."""
    sira = [karolar[i:i + 7] for i in range(0, len(karolar), 7)]
    W = max(sum(k.width for k in s) for s in sira) + 20
    Hh = sum(max(k.height for k in s) for s in sira) + 90
    kt = Image.new("RGB", (W, Hh), (236, 236, 236))
    from PIL import ImageDraw
    ImageDraw.Draw(kt).text((14, 18), f"F7 {stil}: 14 boy (her boy kendi en-boy oraninda; ayni yukseklikte gosterim)", fill=(0, 0, 0), font=_font(36))
    y = 80
    for s in sira:
        x = 10
        for k in s:
            kt.paste(k, (x, y)); x += k.width
        y += max(k.height for k in s)
    kt.save(yol, quality=85)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kod", required=True); ap.add_argument("--doku-dizin", required=True); ap.add_argument("--esrgan", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--pair", default="CANCER_LIBRA")
    ap.add_argument("--n1", default="EMMA"); ap.add_argument("--n2", default="JAMES"); ap.add_argument("--hizli", action="store_true")
    ap.add_argument("--stiller", default="Starlit,Timeless,FirstPage,Layers,Botanical")
    ap.add_argument("--aileler", default=",".join(AILE7)); ap.add_argument("--boylar", default="")
    ap.add_argument("--zemin-dizin", default="", help="onceden kaydedilmis ZEMIN_<stil>_3600x5400.png (ESRGAN tekrar yok)")
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    S = B3.BY_SCALE
    bp = B3.by_poster(a.kod, S, a.pair, a.n1, a.n2)
    bp1 = B3.by_poster(a.kod, 1, a.pair, a.n1, a.n2)
    aileler = a.aileler.split(",")
    boylar = [b for b in (a.boylar.split(",") if a.boylar else BOY_AILE7) if BOY_AILE7[b] in aileler]
    rap = dict(gorev="F7 (Serdar 2 Kas)", hizli_yerel=a.hizli, by_scale=S, aile_yukseklik={k: AILE7[k] for k in aileler},
               boy_aile={b: BOY_AILE7[b] for b in boylar}, esik=dict(kenar_pay=KENAR_PAY, oge_kesim=0, bosluk_tol_layers=BOSLUK_TOL,
                                                                     baslik_tarih_tol_px=BT_TOL, kes_bindirme=KES_ORT, kes_yumusak=KES_YUMUSAK, kes_sigma=KES_SIGMA),
               yontem=("aile sayfasi (genislik 3600, H = 3600 / oran), ogeler blogu (eski 8x10 x1,5) dikey ortali, zemin ortadan kisaltilir "
                       "(en kucuk hata dikisi); boy = aile sayfasi hedef piksele LANCZOS (FirstPage: cerceve ve ogeler boy cozunurlugunde, "
                       "F5 onayli yol). Kirpma yok (5x7 dahil)."), stiller={})
    eski = lambda n: np.asarray(Image.open(Path(a.kod, Z, f"{n}_8x10_300ppi.png")).convert("RGB"))  # noqa: E731
    yakin = []
    t0 = time.time()
    KAYNAK = {"Starlit": ("1_Starlit", "starlit"), "Timeless": ("2_Timeless", "timeless"), "FirstPage": ("3_FirstPage", "first_page"),
              "Layers": ("4_Layers", "layers"), "Botanical": ("5_Botanical", "botanical")}
    toplam_is = len(a.stiller.split(",")) * len(boylar); bitti = 0
    for stil in a.stiller.split(","):
        ad_, fn = KAYNAK[stil]
        hz = Path(a.zemin_dizin, f"ZEMIN_{stil}_3600x5400.png") if a.zemin_dizin else None
        if hz and hz.exists():
            zem5400, yon = np.asarray(Image.open(hz).convert("RGB")), f"hazir {hz.name}"
        else:
            zem5400, yon = doku(Path(a.doku_dizin, f"{ad_}_2x3_kaynak.png"), a.esrgan, a.hizli)
            Image.fromarray(zem5400).save(out / f"ZEMIN_{stil}_3600x5400.png")
        e = eski(ad_) if stil != "Starlit" else None
        st = starlit_hazir(a.kod) if stil == "Starlit" else None
        e8 = e if e is not None else st["eski"]
        s8 = ogeler(bp1, e8, fn)
        f8 = np.abs(s8.astype(np.int16) - e8.astype(np.int16)).max(2) > 2
        R = dict(zemin=yon, eski_8x10_kenar=kenar_olc(f8), eski_8x10_bosluk=bosluk_orani(f8), aile={}, boy={})
        if stil == "Timeless":
            pT = timeless_parcalar(e)
        if stil == "Botanical":
            pB, km_e, kk_e = botanical_parcalar(e)
        if stil == "FirstPage":
            oF = cerceve_olc(e)
        karolar = []
        for aile in aileler:
            tuval(AILE7[aile])
            zem, kb, kk_ = orta_kes_sec(zem5400, HT)
            RA = dict(H=HT, OY=OY, zemin_kesim=kk_)
            if kb.get("kesim"):
                a0_ = kb["bindirme"][0]
                yakin.append((f"{stil} {aile} dikis sol", zem[a0_ - 200:a0_ + 400, 0:600]))
            if stil == "FirstPage":
                sayfa, fark = None, None
            elif stil == "Starlit":
                sayfa, fark, RA["stil"] = starlit_aile(zem, bp, S, st)
            elif stil == "Timeless":
                sayfa, fark, RA["stil"] = timeless_aile(e, zem, bp, S, pT)
            elif stil == "Botanical":
                sayfa, fark, RA["stil"] = botanical_aile(e, zem, bp, S, pB, km_e, kk_e)
            else:
                sayfa, fark, RA["stil"] = layers_aile(e, zem, bp, S, s8, f8, out, aile, yakin)
            if fark is not None:
                RA["kenar"] = kenar_olc(fark); RA["bosluk"] = bosluk_orani(fark)
                RA["bosluk_bagil_bilgi"] = round(RA["bosluk"]["oran"] / R["eski_8x10_bosluk"]["oran"], 4) if RA["bosluk"]["oran"] else None
                if aile == "2x3":
                    Image.fromarray(sayfa).save(out / f"F7_{stil}_2x3_3600x5400.jpg", quality=95, subsampling=0, dpi=(300, 300))
                if stil == "Layers" and aile == "2x3":
                    h_ = 1400
                    a8_ = Image.fromarray(s8).resize((round(2400 * h_ / 3000), h_), Image.LANCZOS)
                    a12_ = Image.fromarray(sayfa).resize((round(3600 * h_ / 5400), h_), Image.LANCZOS)
                    yy_ = Image.new("RGB", (a8_.width + a12_.width + 60, h_ + 90), (236, 236, 236))
                    yy_.paste(a8_, (20, 70)); yy_.paste(a12_, (a8_.width + 40, 70))
                    from PIL import ImageDraw
                    ImageDraw.Draw(yy_).text((20, 16), "Layers B: eski 8x10 | yeni 12x18 (F7, gercek oran)", fill=(0, 0, 0), font=_font(34))
                    yy_.save(out / "F7_LAYERS_B_ESKI_YENI.jpg", quality=88)
            R["aile"][aile] = RA
            for boy in [b for b in boylar if BOY_AILE7[b] == aile]:
                Wt, Ht = boy_px(boy)
                if stil == "FirstPage":
                    img, fb, RB = firstpage_boy(zem, oF, bp, S, Wt, Ht)
                else:
                    img = np.asarray(Image.fromarray(sayfa).resize((Wt, Ht), Image.LANCZOS))
                    fb = cv2.resize(fark.astype(np.uint8), (Wt, Ht), interpolation=cv2.INTER_AREA) > 0
                    RB = dict(pass_=True)
                RB.update(boyut=[int(img.shape[1]), int(img.shape[0])], hedef=[Wt, Ht], kenar=kenar_olc(fb),
                          oran_hata=round(abs(img.shape[1] / img.shape[0] - Wt / Ht), 6))
                RB["pass_"] = bool(RB["pass_"] and RB["boyut"] == [Wt, Ht] and RB["kenar"]["pass_"])
                R["boy"][boy] = RB
                if boy == "11x14":                                       # Merkez 2 Kas: tam cozunurluk dikisli bir boy
                    Image.fromarray(img).save(out / f"F7_{stil}_11x14_{Wt}x{Ht}.jpg", quality=95, subsampling=0, dpi=(300, 300))
                karolar.append((list(BOY_AILE7).index(boy), karo(img, f"{boy}  {Wt}x{Ht}  {'PASS' if RB['pass_'] else 'FAIL'}")))
                del img, fb
                bitti += 1
                g_ = time.time() - t0
                print(f"ETA {bitti}/{toplam_is} {stil} {boy} gecen {g_:.0f}s kalan ~{g_ / bitti * (toplam_is - bitti):.0f}s "
                      f"%{100 * bitti / toplam_is:.0f}", flush=True)
            del sayfa, fark, zem
        kontak_yaz(stil if stil != "Layers" else "Layers B", [k for _, k in sorted(karolar, key=lambda x: x[0])], out / f"F7_{stil if stil != 'Layers' else 'Layers_B'}.jpg")
        R["pass_"] = bool(all(v["pass_"] for v in R["boy"].values()) and len(R["boy"]) == len(boylar)
                          and all(v.get("stil", {}).get("pass_", True) and v["zemin_kesim"]["pass_"]
                                  and v.get("kenar", {}).get("pass_", True) for v in R["aile"].values()))
        rap["stiller"][stil] = R
        print(f"{stil} tamam ({time.time() - t0:.0f}s) pass={R['pass_']}", flush=True)
        del zem5400
    if yakin:
        Wy = 3 * 620; Hy = ((len(yakin) + 2) // 3) * 680
        yk = Image.new("RGB", (Wy, Hy), (236, 236, 236))
        from PIL import ImageDraw
        dr = ImageDraw.Draw(yk)
        for i, (ad_, k_) in enumerate(yakin):
            yk.paste(Image.fromarray(np.ascontiguousarray(k_)), ((i % 3) * 620 + 10, (i // 3) * 680 + 60))
            dr.text(((i % 3) * 620 + 10, (i // 3) * 680 + 20), ad_, fill=(0, 0, 0), font=_font(24))
        yk.save(out / "F7_YAKIN.jpg", quality=88)
    rap["sonuc"] = "PASS" if all(v["pass_"] for v in rap["stiller"].values()) else "FAIL"
    oz = []                                                             # F7 tani: FAIL veren kapilar (LOG + F7_OZET.txt; gorsel degismez)

    def fail_yol(d, yol):
        if isinstance(d, dict):
            if d.get("pass_") is False:
                alt = [k for k, v in d.items() if isinstance(v, dict) and v.get("pass_") is False]
                if not alt:
                    oz.append(f"FAIL {yol}: " + json.dumps({k: v for k, v in d.items() if not isinstance(v, (dict, list))}, default=str)[:600])
            for k, v in d.items():
                if isinstance(v, dict):
                    fail_yol(v, f"{yol}/{k}")
    fail_yol(rap["stiller"], "")
    (out / "F7_OZET.txt").write_text("\n".join(oz) or "FAIL yok", encoding="utf-8")
    print("\n".join(oz[:40]), flush=True)
    (out / "F7_OLCUM.json").write_text(json.dumps(rap, indent=1, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x)), encoding="utf-8")
    print(json.dumps({k: v["pass_"] for k, v in rap["stiller"].items()}), rap["sonuc"], flush=True)
    return 0 if rap["sonuc"] == "PASS" else 3


if __name__ == "__main__":
    sys.exit(main())
