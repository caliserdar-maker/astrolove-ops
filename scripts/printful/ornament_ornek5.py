#!/usr/bin/env python3
"""Ornament ornek V5 (Merkez gorevi STIL3_V5, Serdar 2 Kas aksam kararlari). Etsy / Printful yazma yok. YALNIZ HALKALI.
Renkler: RUBY (altin, V4 butunlesmesi) + BEIGE, AGED_PAPYRUS (dal gecici/ornament-sembol-renk 2877495 zemin_acik/, sha kontrollu;
tum ogeler koyu bronz). Sutunlar: V4 (V4 duzeni) | A-T1 | A-T2.
A (madde 6-8):
  6 ACIK LEKE: kaynak sembollerin alfa delikleri kapatilir (kapali maske icinde alfa 1, renk inpaint). Acik zeminde isik tasmasi ve
    gomulu kenar KAPALI; yalniz zemin tonlu dis golge. Kapi: kapanisli oge maskesi (1 px ice) icinde (a) alfa < 0.9 = 0,
    (b) bronz acik ucundan acik piksel = 0 (yalniz bronz).
  7 HALKA UCLARI: halka KILITLI (ax 341, by 345.6, merkez y 508.6, tepe y 163 = delik merkezi; acik acilar V4). Govde V4 ile ayni
    (poster profili x 4.4 / medyan, taban 4.2). Uctan yayin T1 %30 / T2 %40'inda kosinus incelme baslar, uc 0 px; taban incelme
    bolgesinde uygulanmaz (basamak yok).
  8 SEMBOL ALTI: uc bosluk (sembol -> kucuk burc -> isim -> tarih; alfa >= 0.5 kutulari, J dahil) = ceil(0.70 x isim buyuk harf).
    Yazi blogu en asagi gecerli konumda; sembol V4 boyunda (halka 341 orani), yalniz YUKARI tasinir. Sigmazsa FAIL + gereken kucultme.
Kontrast (bronz): V4 kati olcut (ortanca ve zeminin acik %5'i) + zeminin koyu %5'i (koyu yazi icin en kotu durum); tarih ve halka uclari
dahil; >= 4.5 icin ana ton koyulastirilir (carpan yazilir).
Kullanim: ornament_ornek5.py --kaynak DIR --cikti DIR"""
import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

_d = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('ornek4', _d / 'ornament_ornek4.py'); o4 = importlib.util.module_from_spec(_s); _s.loader.exec_module(o4)
o1, o3 = o4.o1, o4.o3
N, MM, P, CX, CY = o4.N, o4.MM, o4.P, o4.CX, o4.CY
lum = o4.lum
HALKA_AX = 341.0
HALKA_CY = 508.6
UC_T = {'T1': 0.30, 'T2': 0.40}
BOSLUK_ORAN = 0.70
ZEMINLER = (('RUBY', 'RUBY_1264.png', 'koyu'), ('BEIGE', 'BEIGE_1264.png', 'acik'), ('AGED_PAPYRUS', 'AGED_PAPYRUS_1264.png', 'acik'))
ZEMIN_SHA = {'BEIGE_1264.png': 'a55e7703f65ca3bdaeba6ff5055517f0d4f2ecb2920ee3e5b04d021bbf58d29b',
             'AGED_PAPYRUS_1264.png': '0dfe2f2db5c1996bae7268c77d463b311d85c2b0f7f24d03dc4b2d13b2dd3988'}
BRONZ = dict(koyu=np.array([40, 24, 6], np.float32), ana=np.array([84, 54, 14], np.float32), acik=np.array([140, 98, 40], np.float32))
BRONZ_CARPAN = (1.0, 0.92, 0.85, 0.78, 0.70, 0.62)
ALTIN_KAZANC = (1.0, 1.04, 1.08, 1.12, 1.16, 1.20)
ACIK_GOLGE = dict(kayma=1.5, sigma=1.2, opak=0.55, koyu=0.45)
ISIM = ('isim1', 'isim2', 'sonsuz')
KUCUK = ('kucuk_sol', 'kucuk_sag')


# ----------------------------------------------------------------------------------------------- kaynak alfa delikleri (madde 6)
def delik_kapat(rgba, k=9):
    """alfa > 0.5 maskesi kapanis (k x k elips), 1 px ice; icinde alfa 1, renk inpaint. Doner (rgba, kapatilan piksel)."""
    a = rgba[..., 3]
    m = (a > 0.5).astype(np.uint8)
    c = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    ic = cv2.erode(c, np.ones((3, 3), np.uint8)) > 0
    hedef = ic & (a < 0.999)
    out = rgba.copy()
    if hedef.any():
        rgb8 = np.clip(rgba[..., :3], 0, 255).astype(np.uint8)
        maske = (ic & (a < 0.9)).astype(np.uint8)
        rgbi = cv2.inpaint(rgb8, maske, 5, cv2.INPAINT_TELEA).astype(np.float32) if maske.any() else rgb8.astype(np.float32)
        out[..., :3] = np.where(maske[..., None] > 0, rgbi, rgba[..., :3])
        out[..., 3] = np.where(ic, 1.0, a)
    return out, int(hedef.sum())


def leke_kapisi(M, rgb, bronz_acik_L=None):
    """oge basina: kapanisli (3x3) alfa > 0.5 maskesi 1 px ice; (a) alfa < 0.9, (b) luma > bronz acik ucu + 2."""
    L = lum(rgb.astype(np.float32))
    r = {}
    for k, m in M.items():
        b = (m > 0.5).astype(np.uint8)
        c = cv2.morphologyEx(b, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
        ic = cv2.erode(c, np.ones((3, 3), np.uint8)) > 0
        r[k] = dict(alfa_lt_09=int((ic & (m < 0.9)).sum()), ic_piksel=int(ic.sum()),
                    acik_piksel=int((ic & (L > bronz_acik_L + 2)).sum()) if bronz_acik_L is not None else None)
    return r


# ----------------------------------------------------------------------------------------------- bronz (madde 5)
def bronz_fonk(carpan):
    k, a_, c = BRONZ['koyu'] * carpan, BRONZ['ana'] * carpan, BRONZ['acik'] * carpan

    def f(cc, model):
        L = lum(cc)
        r = np.clip(L / max(model.Lmed, 1.0), 0.5, 1.5)
        t1 = np.clip((r - 0.5) / 0.5, 0, 1)[..., None]
        t2 = np.clip((r - 1.0) / 0.5, 0, 1)[..., None]
        return np.where(r[..., None] <= 1.0, k + (a_ - k) * t1, a_ + (c - a_) * t2)
    Lc = float(lum(c[None])[0])

    def kirp(cc):
        L = lum(cc)
        s = np.where(L > Lc, Lc / np.maximum(L, 1e-3), 1.0)[..., None]
        return cc * s
    return f, kirp, Lc


def ayarla(tur, carpan=None):
    """o4 boyama kancalari: koyu zemin = V4; acik zemin = bronz, isik tasmasi / gomulu kenar kapali, zemin tonlu dis golge."""
    if tur == 'koyu':
        o4.RENK_DONUSUM = o4.SON_KIRP = o4.DIS_GOLGE = None
        o4.GLOW_OPAK, o4.GOMU_KOYU, o4.GOMU_ACIK = 0.16, 0.55, 0.40
        return None
    f, kirp, Lc = bronz_fonk(carpan)
    o4.RENK_DONUSUM, o4.SON_KIRP, o4.DIS_GOLGE = f, kirp, ACIK_GOLGE
    o4.GLOW_OPAK, o4.GOMU_KOYU, o4.GOMU_ACIK = 0.0, 0.0, 0.0
    return Lc


# ----------------------------------------------------------------------------------------------- halka (madde 7)
def halka_T(pp, s0, ss=4):
    el = pp['el']
    ax = HALKA_AX
    by = ax / el['oran']
    cy = HALKA_CY
    out = np.zeros((N, N), np.float32)
    y0 = max(0, int(cy - by - 20)); y1 = min(N, int(cy + by + 20))
    yy, xx = np.mgrid[y0 * ss:y1 * ss, 0:N * ss].astype(np.float32)
    dx, dy = (xx + 0.5) / ss - CX, (yy + 0.5) / ss - cy
    rho = np.sqrt((dx / ax) ** 2 + (dy / by) ** 2)
    d = (rho - 1) * np.sqrt(dx ** 2 + dy ** 2) / np.maximum(rho, 1e-6)
    ang = (np.degrees(np.arctan2(dy, dx)) + 360) % 360
    w = genislik_T(pp, ang, s0)
    a_hr = ((np.abs(d) <= w / 2) & (w > 0)).astype(np.float32)
    out[y0:y1] = cv2.resize(a_hr, (N, y1 - y0), interpolation=cv2.INTER_AREA)
    return out, dict(ax=ax, by=by, cy=cy, r_ort=(ax + by) / 2)


def genislik_T(pp, ang, s0):
    """govde = V4 (poster x GOVDE_MED / medyan, taban GOVDE_MIN); uctan yay orani s < s0: x 0.5 (1 - cos(pi s / s0)); uc 0."""
    w = np.interp(ang, pp['T'], pp['W'], period=360) / pp['med'] * o4.GOVDE_MED
    r = (pp['el']['a'] + pp['el']['b']) / 2
    s = np.minimum(np.radians((pp['t1'] - ang) % 360), np.radians((ang - pp['t2']) % 360)) * r / pp['L']
    acik = (ang > pp['t1']) & (ang < pp['t2'])
    govde = np.maximum(w, o4.GOVDE_MIN)
    f = np.where(s >= s0, 1.0, 0.5 * (1 - np.cos(np.pi * np.clip(s / s0, 0, 1))))
    return np.where(acik, 0.0, govde * f)


def halka_uc_olc(a, hb, pp):
    """elips normali boyunca genislik (0.05 derece); her uc icin genislik < 2 px ve < 1 px kalan yay boyu (px, mm)."""
    ax, by, cy = hb['ax'], hb['by'], hb['cy']
    T = np.arange(0, 360, 0.05)
    W = np.zeros_like(T)
    u = np.arange(-15, 15.0001, 0.1)
    for i, t in enumerate(T):
        tr = math.radians(t); c_, s_ = math.cos(tr), math.sin(tr)
        rr = 1.0 / math.sqrt((c_ / ax) ** 2 + (s_ / by) ** 2)
        px, py = CX + rr * c_, cy + rr * s_
        nx, ny = (px - CX) / ax ** 2, (py - cy) / by ** 2; nn = math.hypot(nx, ny); nx, ny = nx / nn, ny / nn
        v = cv2.remap(a, (px + u * nx - 0.5).astype(np.float32)[None], (py + u * ny - 0.5).astype(np.float32)[None], cv2.INTER_LINEAR, borderValue=0)[0]
        W[i] = v.sum() * 0.1
    # yay boyu (gercek elips): ardisik noktalar arasi
    tr = np.radians(T)
    rr = 1.0 / np.sqrt((np.cos(tr) / ax) ** 2 + (np.sin(tr) / by) ** 2)
    X, Y = rr * np.cos(tr), rr * np.sin(tr)
    ds = np.hypot(np.diff(np.r_[X, X[0]]), np.diff(np.r_[Y, Y[0]]))
    acik = (T > pp['t1']) & (T < pp['t2'])
    L = float(ds[~acik].sum())
    r = dict(yay_toplam_px=round(L, 1), yay_toplam_mm=round(L * MM, 1))
    # sag uc: t1'den geriye (azalan aci), sol uc: t2'den ileri
    for ad, sira in (('sag', np.r_[np.nonzero(T <= pp['t1'])[0][::-1], np.nonzero(T >= pp['t2'])[0][::-1]]),
                     ('sol', np.r_[np.nonzero(T >= pp['t2'])[0], np.nonzero(T <= pp['t1'])[0]])):
        s_cum = np.cumsum(ds[sira])
        w_s = W[sira]
        def uzunluk(esik):
            k = np.nonzero(w_s >= esik)[0]
            return float(s_cum[k[0]]) if len(k) else None
        r[ad] = dict(ince_2px_px=round(uzunluk(2.0), 1), ince_2px_mm=round(uzunluk(2.0) * MM, 2),
                     ince_1px_mm=round(uzunluk(1.0) * MM, 2),
                     profil={str(f): round(float(w_s[np.argmin(np.abs(s_cum - f * L))]), 2) for f in (0.0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5)})
    govde = W[~acik & (W > 0)]
    r['govde_max'] = round(float(W.max()), 2)
    return r


# ----------------------------------------------------------------------------------------------- yerlesim (madde 8)
def kutu(E, ad):
    rgb, a, x, y = E[ad]
    b = o1.bbox(a, 0.5)
    return (x + b[0], y + b[1], x + b[2], y + b[3])


def satir(E, adlar):
    k = [kutu(E, a) for a in adlar]
    return min(b[1] for b in k), max(b[3] for b in k)


def kaydir(E, adlar, dy):
    for ad in adlar:
        rgb, a, x, y = E[ad]
        E[ad] = (rgb, a, x, int(y + dy))


def bosluklar(E):
    s = kutu(E, 'sembol')
    k0, k1 = satir(E, KUCUK)
    i0, i1 = satir(E, ('isim1', 'isim2'))
    t = kutu(E, 'tarih')
    return [int(k0 - s[3]), int(i0 - k1), int(t[1] - i1)]


def blok(T, kucuk, alt, G):
    E, _ = o3.yazi_blogu(T, kucuk, alt, 0.45, 0.40)
    t0 = kutu(E, 'tarih')[1]
    kaydir(E, ISIM, (t0 - G) - satir(E, ('isim1', 'isim2'))[1])
    kaydir(E, KUCUK, (satir(E, ('isim1', 'isim2'))[0] - G) - satir(E, KUCUK)[1])
    return E


def yerlesim_V5(pp, ana, T, kucuk, halka_a, hb, G):
    """yazi blogu: bosluklar G, en asagi gecerli konum (halka dahil kapi). Sembol: V4 boyu (halka 341 orani), merkez V4 formulu;
    bosluk G icin gerekiyorsa yalniz yukari. Doner Y ya da hata (gereken kucultme)."""
    el = pp['el']
    sx0, sy0, sx1, sy1 = P['sembol_kutu']
    k = HALKA_AX / el['a']
    sem4 = o3.sembol_yerlestir(ana, (sx1 - sx0) * k, CX, hb['cy'] + ((sy0 + sy1) / 2 - el['cy']) * (hb['by'] / el['b']))
    secilen = None
    for alt in np.arange(N - 40, 500, -1.0):
        E = blok(T, kucuk, alt, G)
        E['halka'] = (None, halka_a, 0, 0)
        M, yb, cak, ok = o4.kapi(E)
        if ok:
            secilen = (alt, E); break
    if secilen is None:
        return None, dict(hata='yazi blogu halka ile sigmiyor')
    alt, E = secilen
    E['sembol'] = sem4
    s4 = kutu(E, 'sembol')
    k0 = satir(E, KUCUK)[0]
    hedef_alt = k0 - G
    dy = min(0, hedef_alt - s4[3])                                    # yalniz yukari
    kaydir(E, ('sembol',), dy)
    M, yb, cak, ok = o4.kapi(E)
    bilgi = dict(alt=float(alt), sembol_kaldir_px=int(-dy), sembol_V4_ust=s4[1])
    if not ok:
        # sembol en fazla ne kadar yukari cikabilir; eksik = gereken kucultme
        en = None
        for d in range(0, int(-dy) + 1):
            E2 = dict(E); rgb, a, x, y = sem4; E2['sembol'] = (rgb, a, x, y - d)
            if o4.kapi(E2)[3]:
                en = d
        bilgi.update(hata='sembol sigmiyor', yasak=yb, cakisma=cak, en_fazla_kaldir=en,
                     gereken_kucultme_px=int(-dy) - (en or 0))
        return None, bilgi
    return dict(E=E, M=M, yasak=yb, cak=cak, halka=hb), bilgi


# ----------------------------------------------------------------------------------------------- olcum
def okunurluk5(rgb, m):
    ce = cv2.erode((m > 0.9).astype(np.uint8), np.ones((2, 2), np.uint8)) > 0
    yt = np.median(rgb[m > 0.5], 0) if (m > 0.5).any() else np.median(rgb[ce], 0)
    ink = (m > 0.02).astype(np.uint8)
    arka = (cv2.dilate(ink, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))) > 0) & \
           (cv2.dilate(ink, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))) == 0)
    za = rgb[arka].astype(np.float32)
    Lz = lum(za)
    z95 = np.median(za[Lz >= np.percentile(Lz, 95)], 0)
    z05 = np.median(za[Lz <= np.percentile(Lz, 5)], 0)
    return dict(ortanca=o1.kontrast(yt, np.median(za, 0)), acik5=o1.kontrast(yt, z95), koyu5=o1.kontrast(yt, z05),
                yazi_rgb=[int(v) for v in yt])


def uc_maske(pp, s0):
    """halka uc bolgesi (uctan yay orani < s0) maske; halka ucu kontrasti icin."""
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    by = HALKA_AX / pp['el']['oran']
    ang = (np.degrees(np.arctan2(yy + 0.5 - HALKA_CY, xx + 0.5 - CX)) + 360) % 360
    r = (pp['el']['a'] + pp['el']['b']) / 2
    s = np.minimum(np.radians((pp['t1'] - ang) % 360), np.radians((ang - pp['t2']) % 360)) * r / pp['L']
    return (s < s0) & ~((ang > pp['t1']) & (ang < pp['t2']))


def isim_guvenli(E):
    """isim satiri (isim1, logo, isim2) murekkebinin guvenli daireye en yakin uzakligi (px)."""
    d = 1e9
    for ad in ISIM:
        rgb, a, x, y = E[ad]
        ys, xs = np.nonzero(a > 0.02)
        r = np.hypot(xs + x + 0.5 - CX, ys + y + 0.5 - CY)
        d = min(d, float(o4.GUV_R - r.max()))
    return round(d, 1)


def boya_sec(Y, model, z, tur, td, pp, s0):
    """koyu: altin kazanci; acik: bronz carpani. Kontrast: isim1, isim2, tarih (kati: ortanca / acik %5; bronzda + koyu %5) ve halka uclari."""
    adaylar = ALTIN_KAZANC if tur == 'koyu' else BRONZ_CARPAN
    um = uc_maske(pp, s0) if 'halka' in Y['M'] else None
    for c in adaylar:
        Lc = ayarla(tur, c)
        kaz = c if tur == 'koyu' else 1.0
        dg = o4.doku_ayarla(Y, model, z, kaz, td)
        rgb = o4.boya(Y, model, z, kaz, td, dg)
        ok = {k: okunurluk5(rgb, Y['M'][k]) for k in ('isim1', 'isim2', 'tarih')}
        if um is not None:
            ok['halka_uclari'] = okunurluk5(rgb, Y['M']['halka'] * um)
        anahtar = ('ortanca', 'acik5') if tur == 'koyu' else ('ortanca', 'acik5', 'koyu5')
        en = min(v[k] for v in ok.values() for k in anahtar)
        if en >= o4.HEDEF:
            break
    return dict(deger=c, rgb=rgb, ok=ok, en=en, dg=dg, Lc=Lc, kazanc=kaz)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    K, O = Path(a.kaynak), Path(a.cikti)
    O.mkdir(parents=True, exist_ok=True)
    for f, h in ZEMIN_SHA.items():
        if o1.sha(K / f) != h:
            print('FAIL zemin sha', f, flush=True); return 1
    o4.YASAK = o4.yasak_m()
    o4.GLOW_K = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * o4.GLOW_R + 1,) * 2)
    o3.YASAK = o4.YASAK
    spec = importlib.util.spec_from_file_location('tek_doku', K / 'tek_doku.py')
    td = importlib.util.module_from_spec(spec); spec.loader.exec_module(td)
    pp = o4.poster_profil(K / 'HALKA_BLUE_16x20.png')
    ana0 = np.asarray(Image.open(K / 'CANCER_LIBRA_ana.png').convert('RGBA'), np.float32)
    ana0[..., 3] /= 255.0
    ana0 = o1.kirp(ana0, ana0[..., 3], pad=2)
    if ana0.shape[1] > 1600:
        r_, a_ = o1.rgba_olcek(ana0, 1600 / ana0.shape[1]); ana0 = np.dstack([r_, a_])
    ana5, ana_kapatilan = delik_kapat(ana0)
    lsrc = o4.logo_kaynak(K / 'LOGO_1.png')
    kapatilan = {'ana_1600px': ana_kapatilan}

    def kucuk(burc, cap, h_ratio, kapat):
        g = np.asarray(Image.open(K / f'{burc}_symbol_gold.png').convert('RGBA'), np.float32)
        g[..., 3] /= 255.0
        g = o1.kirp(g, g[..., 3], pad=2)
        if kapat:
            g, n = delik_kapat(g); kapatilan[burc] = n
        gx0, gy0, gx1, gy1 = o1.bbox(g[..., 3], 0.5)
        return o1.rgba_olcek(g, h_ratio * cap / (gy1 - gy0))

    def metinler(cap, ad1='EMILY', ad2='JAMES', isim_olcek=1.0):
        k = cap * o4.LOGO_H / lsrc.shape[0]
        la = np.clip(cv2.resize(lsrc, (max(1, int(round(lsrc.shape[1] * k))), max(1, int(round(cap * o4.LOGO_H)))), interpolation=cv2.INTER_AREA), 0, 1)
        return dict(isim1=o1.metin_alfa(ad1, K / 'Cinzel.ttf', cap * isim_olcek, 500), isim2=o1.metin_alfa(ad2, K / 'Cinzel.ttf', cap * isim_olcek, 500),
                    tarih=o1.metin_alfa('14 JUNE 2025', K / 'EBGaramond-Italic.ttf', P['tagline_T'] / P['cap'] * cap, None, ref='T'), sonsuz=la, cap=cap)
    cap = o4.CAP0
    G = int(math.ceil(BOSLUK_ORAN * cap))
    T = metinler(cap)
    kc4 = {'sol': kucuk('cancer', cap, P['kucuk_sol_h'] / P['cap'], False), 'sag': kucuk('libra', cap, P['kucuk_sag_h'] / P['cap'], False)}
    kc5 = {'sol': kucuk('cancer', cap, P['kucuk_sol_h'] / P['cap'], True), 'sag': kucuk('libra', cap, P['kucuk_sag_h'] / P['cap'], True)}
    zem = {ad: (o1.zemin_canva(K / f), tur) for ad, f, tur in ZEMINLER}
    R = {'kaynak_sha256': {f.name: o1.sha(f) for f in sorted(K.iterdir()) if f.is_file()},
         'sabit': dict(halka=dict(ax=HALKA_AX, by=round(HALKA_AX / pp['el']['oran'], 2), cy=HALKA_CY, tepe_y=round(HALKA_CY - HALKA_AX / pp['el']['oran'], 2),
                                  acik_aci=[pp['t1'], pp['t2']], govde_med=o4.GOVDE_MED, govde_min=o4.GOVDE_MIN),
                       uc_T=UC_T, bosluk_hedef_px=G, bosluk_tanimi=f'ceil({BOSLUK_ORAN} x isim buyuk harf {cap} px); alfa >= 0.5 kutulari, J dahil',
                       bronz={k: v.tolist() for k, v in BRONZ.items()}, acik_golge=ACIK_GOLGE, kapatilan_alfa_piksel=kapatilan,
                       not_halka='V4 kosusu 41485011606 halkasi ax 343 / cy 510.6; Merkez kilidi ax 341 / cy 508.6 (V4 deneme 1) uygulandi')}
    # V4 duzeni (karsilastirma): V4 betigi, kaynak delikleri kapatilmadan
    Y4 = o4.yerlesim_A(pp, ana0, T, kc4)
    secenek = {'V4': (Y4, None)}
    yer = {}
    for ad, s0 in UC_T.items():
        ha, hb = halka_T(pp, s0)
        Y, bilgi = yerlesim_V5(pp, ana5, T, kc5, ha, hb, G)
        yer[ad] = bilgi
        if Y is None:
            print('FAIL yerlesim', ad, json.dumps(bilgi, default=str), flush=True)
            R['yerlesim'] = yer
            (O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str))
            return 1
        secenek['A-' + ad] = (Y, s0)
    R['yerlesim'] = yer
    sonuc, rgbler = {}, {}
    for zad, (z, tur) in zem.items():
        for sad, (Y, s0) in secenek.items():
            sx = Y['E']['sembol']
            model = o1.Model(td, sx[0], sx[1], 4800 * (o1.bbox(sx[1], 0.5)[2] - o1.bbox(sx[1], 0.5)[0]) / 2084)
            b = boya_sec(Y, model, z, tur, td, pp, s0 if s0 is not None else 0.20)
            rgb = b['rgb']
            ayarla(tur, b['deger'])
            rgb0 = o4.boya(Y, model, z, b['kazanc'], td, 0.0, doku_kapali=True)
            rgbb = o4.boya(Y, model, z, b['kazanc'], td, b['dg'], butunlesme=False)
            tumm = np.maximum.reduce([Y['M'][k] for k in Y['M']])
            gy, gb = o4.goruntu_yasak(rgb, z, Y['M'].get('halka'))
            r = dict(tur=tur, ton=('altin kazanci ' if tur == 'koyu' else 'bronz carpani ') + str(b['deger']),
                     bronz_ana_rgb=[round(float(v), 1) for v in BRONZ['ana'] * b['deger']] if tur == 'acik' else None,
                     en_kotu_kontrast=round(b['en'], 2), hedef_tuttu=b['en'] >= o4.HEDEF,
                     kontrast={k: {kk: (round(vv, 2) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in b['ok'].items()},
                     bosluk_px=bosluklar(Y['E']), sembol_kutu=list(kutu(Y['E'], 'sembol')),
                     sembol_px=[kutu(Y['E'], 'sembol')[2] - kutu(Y['E'], 'sembol')[0], kutu(Y['E'], 'sembol')[3] - kutu(Y['E'], 'sembol')[1]],
                     isim_guvenli_daireye_px=isim_guvenli(Y['E']), yasak_piksel=Y['yasak'], cakisma=Y['cak'],
                     goruntu_yasak=gy, goruntu=gb, doku_oge=o4.doku_oge(rgb, rgb0, Y['M']),
                     isik=o4.glow_olc(rgb, rgbb, tumm) if tur == 'koyu' else 'kapali (acik zemin)',
                     leke=leke_kapisi(Y['M'], rgb, b['Lc']))
            if 'halka' in Y['M'] and s0 is not None:
                r['halka_uc'] = halka_uc_olc(Y['M']['halka'], Y['halka'], pp)
            elif sad == 'V4':
                r['halka_uc'] = halka_uc_olc(Y['M']['halka'], Y['halka'], pp)
                r['halka_V4'] = dict(ax=Y['halka']['ax'], cy=round(Y['halka']['cy'], 1))
            sonuc.setdefault(zad, {})[sad] = r
            rgbler[(zad, sad)] = rgb
            if sad != 'V4':
                o1.kaydet(rgb, O / f'{zad}_{sad}_954.png')
            lk = r['leke']
            print(zad, sad, r['ton'], 'kontrast', r['en_kotu_kontrast'], 'bosluk', r['bosluk_px'], 'sembol', r['sembol_kutu'],
                  'yasak', sum(gy.values()), 'cak', r['cakisma'], 'leke a', sum(v['alfa_lt_09'] for k_, v in lk.items() if k_ in ('sembol',) + KUCUK),
                  'leke b', sum((v['acik_piksel'] or 0) for v in lk.values()), 'doku', min(r['doku_oge'].values()), max(r['doku_oge'].values()),
                  'uc2px_mm', (r.get('halka_uc') or {}).get('sag', {}).get('ince_2px_mm'), flush=True)
    R['sonuc'] = sonuc
    # onizleme 3 x 3 + etiket
    font = ImageFont.truetype(str(K / 'EBGaramond-Italic.ttf'), 30)
    satirlar = []
    for zad, _, _ in ZEMINLER:
        im = o4.onizleme([rgbler[(zad, s)] for s in secenek], ara=24)
        tile = (im.width - 48) // 3
        b = Image.new('RGB', (im.width, im.height + 100), 'white'); b.paste(im, (0, 0)); d = ImageDraw.Draw(b)
        for i, s in enumerate(secenek):
            r = sonuc[zad][s]
            t = (f'{zad} {s}: bosluk {r["bosluk_px"][0]}/{r["bosluk_px"][1]}/{r["bosluk_px"][2]} px, sembol ust y {r["sembol_kutu"][1]}\n'
                 f'{r["ton"]}, kontrast {r["en_kotu_kontrast"]}, uc <2px {(r.get("halka_uc") or {}).get("sag", {}).get("ince_2px_mm")} mm')
            for j, line in enumerate(t.split('\n')):
                d.text((i * (tile + 24) + 6, im.height + 8 + j * 34), line, fill=(20, 20, 20), font=font)
        satirlar.append(b)
    o = Image.new('RGB', (max(s.width for s in satirlar), sum(s.height for s in satirlar) + 24 * 2), 'white')
    y = 0
    for s in satirlar:
        o.paste(s, (0, y)); y += s.height + 24
    o.save(O / 'ONIZLEME_76mm_SECENEK.png', dpi=(300, 300))
    # uc yakin cekim (sag uc, 2x): RUBY ve BEIGE x V4 / T1 / T2
    t1 = math.radians(pp['t1'])
    hb = Y4['halka']
    ux = int(CX + hb['ax'] * math.cos(t1)); uy = int(hb['cy'] + hb['by'] * math.sin(t1))
    kx0, ky0 = max(0, ux - 150), max(0, uy - 330)
    kirp = (kx0, ky0, min(N, kx0 + 200), min(N, ky0 + 360))
    parcalar = []
    for zad in ('RUBY', 'BEIGE'):
        sat = []
        for s in secenek:
            im = Image.fromarray(rgbler[(zad, s)]).crop(kirp)
            im = im.resize((im.width * 2, im.height * 2), Image.NEAREST)
            c = Image.new('RGB', (im.width, im.height + 44), 'white'); c.paste(im, (0, 0))
            ImageDraw.Draw(c).text((6, im.height + 6), f'{zad} {s}', fill=(20, 20, 20), font=font)
            sat.append(c)
        parcalar.append(sat)
    W = sum(c.width for c in parcalar[0]) + 24 * 2
    H = sum(row[0].height for row in parcalar) + 24
    u = Image.new('RGB', (W, H), 'white')
    y = 0
    for row in parcalar:
        x = 0
        for c in row:
            u.paste(c, (x, y)); x += c.width + 24
        y += row[0].height + 24
    u.save(O / 'UC_T1_T2.png')
    R['uc_kirp_kutu'] = kirp
    # uzun isim testi (bilgi): RUBY A-T1, CAGLAYANGUL / MAXIMILIAN, yazi boyu degismez
    z, tur = zem['RUBY']
    ha, hb1 = halka_T(pp, UC_T['T1'])
    TU = metinler(cap, 'ÇAĞLAYANGÜL', 'MAXIMILIAN')
    tasma = {}
    for ad_, isim in (('isim1', 'ÇAĞLAYANGÜL'), ('isim2', 'MAXIMILIAN')):
        A_, t_ = TU[ad_]
        bb = o1.bbox(A_, 0.5)
        tasma[isim] = dict(genislik_px=bb[2] - bb[0], ust_buyuk_harf_ustu_px=int(round((t_ - cap) - bb[1])), alt_taban_alti_px=int(round(bb[3] - t_)),
                           not_='ust > 0: aksan (Ğ breve, Ü nokta) buyuk harf ustune tasar; alt > 0: Ç cengeli taban altina iner')
    YU, bu = yerlesim_V5(pp, ana5, TU, kc5, ha, hb1, G)
    uz = dict(isimler=['ÇAĞLAYANGÜL', 'MAXIMILIAN'], olcek_1_sigar=YU is not None, bilgi=bu, aksan=tasma)
    if YU is None:
        gerek = None
        for sc in np.arange(0.99, 0.60, -0.01):
            Ts = metinler(cap, 'ÇAĞLAYANGÜL', 'MAXIMILIAN', isim_olcek=float(sc))
            Ys, _ = yerlesim_V5(pp, ana5, Ts, kc5, ha, hb1, G)
            if Ys is not None:
                gerek = round(float(sc), 2); break
        uz['gereken_isim_olcegi'] = gerek
        uz['gereken_isim_buyuk_harf_mm'] = round(cap * gerek * MM, 2) if gerek else None
        # gorsel: olcek 1 (tasma gorunur), kapisiz yerlesim
        E = blok(TU, kc5, float(yer['T1']['alt']), G)
        E['halka'] = (None, ha, 0, 0)
        E['sembol'] = secenek['A-T1'][0]['E']['sembol']
        M = {}
        for k_, (_, a_, x_, y_) in E.items():
            M[k_] = a_ if k_ == 'halka' else o3.maske_yaz(a_, x_, y_)[0]
        YU = dict(E=E, M=M, yasak=None, cak=None, halka=hb1)
    else:
        uz['bosluk_px'] = bosluklar(YU['E'])
        uz['isim_guvenli_daireye_px'] = isim_guvenli(YU['E'])
    sx = YU['E']['sembol']
    model = o1.Model(td, sx[0], sx[1], 4800 * (o1.bbox(sx[1], 0.5)[2] - o1.bbox(sx[1], 0.5)[0]) / 2084)
    ayarla('koyu')
    rgbu = o4.boya(YU, model, z, 1.08, td, 0.2)
    R['uzun_isim'] = uz
    im = o4.onizleme([rgbu], ara=0)
    b = Image.new('RGB', (im.width, im.height + 120), 'white'); b.paste(im, (0, 0)); d = ImageDraw.Draw(b)
    msg = (f'RUBY A-T1, olcek 1.0: {"sigar" if uz["olcek_1_sigar"] else "SIGMAZ"}' +
           (f'; gereken isim olcegi {uz.get("gereken_isim_olcegi")} (buyuk harf {uz.get("gereken_isim_buyuk_harf_mm")} mm)' if not uz['olcek_1_sigar'] else ''))
    d.text((8, im.height + 8), msg, fill=(20, 20, 20), font=font)
    d.text((8, im.height + 46), 'aksan: ' + ', '.join(f'{k} ust {v["ust_buyuk_harf_ustu_px"]} px alt {v["alt_taban_alti_px"]} px' for k, v in tasma.items()),
           fill=(20, 20, 20), font=font)
    b.save(O / 'UZUN_ISIM.png', dpi=(300, 300))
    print('UZUN', json.dumps(uz, ensure_ascii=False, default=str)[:600], flush=True)
    # kapilar (A secenekleri)
    A = [sonuc[z_][s] for z_ in sonuc for s in sonuc[z_] if s != 'V4']
    g = dict(yasak_0=all(sum(r['yasak_piksel'].values()) == 0 for r in A), cakisma_0=all(not r['cakisma'] for r in A),
             goruntu_yasak_0=all(sum(r['goruntu_yasak'].values()) == 0 for r in A), kontrast=all(r['hedef_tuttu'] for r in A),
             bosluk_ge_hedef=all(min(r['bosluk_px']) >= BOSLUK_ORAN * cap for r in A),
             leke_a_0=all(sum(v['alfa_lt_09'] for k_, v in r['leke'].items() if k_ in ('sembol',) + KUCUK) == 0 for r in A),
             leke_b_0=all(sum((v['acik_piksel'] or 0) for v in r['leke'].values()) == 0 for r in A),
             doku_4_6=all(4.0 <= min(r['doku_oge'].values()) and max(r['doku_oge'].values()) <= 6.0 for r in A),
             isik_4_10_koyu=all(4 <= r['isik']['p95_px'] and r['isik']['uzanim_px'] <= 10 for r in A if r['tur'] == 'koyu'),
             halka_kilit=abs(R['sabit']['halka']['tepe_y'] - o4.DELIK[1]) < 0.6)
    g = {k: bool(v) for k, v in g.items()}
    R['kapi'] = g
    R['kapi_not'] = 'leke (a) kapisi kaynak goruntulu ogelerde (sembol, kucuk burclar); yazi / logo / halka vektor kenar yumusatmasi raporda (OLCUM leke)'
    (O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=float))
    print('KAPI', json.dumps(g), 'PASS' if all(g.values()) else 'FAIL', flush=True)
    return 0 if all(g.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
