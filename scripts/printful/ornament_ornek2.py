#!/usr/bin/env python3
"""Ornament ornek V2: yalniz STIL3 (SAPPHIRE_GOLD, EMERALD_GOLD, RUBY_GOLD). Merkez bagimsiz inceleme + Serdar istekleri (2 Kas 2026).
Toplu uretim YOK; Etsy / Printful yazma yok. v1 yardimcilari (ornament_ornek.py) yeniden kullanilir.

Degisiklikler (v1'e gore):
  0 yerlesim: halka tepesi (dis kenar) y >= 222 (Printful guvenli alan centigi alti 216.9); halka capi kapilar altinda EN BUYUK deger
    (arama); sembol posterdeki oranda; tum icerik Printful guvenli dairesinin (cap 760.6, merkez 477,477) >= 15 px icinde; yazi boyu sabit
    (isim buyuk harf 28.07 px = 2.38 mm, tarih 23.9 px = 2.02 mm; kucuk semboller v1 boyu).
  1-3 halka: poster halkasinin (HALKA_BLUE_16x20.png) OLCULEN merkez cizgisi r(aci) ve genislik profili w(aci) korunur; genislik
    esit oranla en kalin yer (tepe) HALKA_TEPE_PX olacak sekilde buyutulur; uclarda genislik olculen profille 0'a iner (keskin uc,
    yalniz kapsama azalir); renk boru profili (tek doku modeli profil(t)) ile, aci boyunca tek duze (kabartma yok: aci boyunca parlaklik
    kesintisi olmasin).
  4 okunurluk: isim, sonsuz, tarih arkasina yumusak koyu hale (zemin x (1 - s G)); hedef her yazida min(ortanca, en acik %5) >= 5.0.
    s yetmezse yazi altini en fazla %12 acilir. s ve kazanc raporlanir.
  5 sonsuz: en ince cizgi >= 3 px: kaynak alfa yuksek cozunurlukte genisletilir; kapi = 3x3 acma sonrasi kayip <= %2 ve bilesen sayisi ayni.
  6 onizleme: 827 maskeli, koseler beyaz, asma deligi (477,164; cap 56.6) cizili + ayri kilavuz (827 gorunen, 761 guvenli daire, delik).
  7 sekil dogrulama: ham alfa (motor_gpt/girdi78/ana/cancer_libra_alfa.png) ile kullanilan ana katman alfasi, temizlenip esit oranli
    olcek + oteleme aramasiyla hizalanir; IoU, +-2 px toleransli IoU, en / boy, alan ve cizgi kalinligi orani.
Kullanim: ornament_ornek2.py --kaynak DIR --cikti DIR"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

_s = importlib.util.spec_from_file_location('ornek1', Path(__file__).resolve().parent / 'ornament_ornek.py')
o1 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(o1)
N, C, MM, LUMA = o1.N, o1.C, o1.MM, o1.LUMA
RV = o1.RV
GUV_R = 760.6 / 2                    # Printful guvenli daire (EK_OLCUM.json sablon)
GUV_PAY = 15
R_SINIR = GUV_R - GUV_PAY
CENTIK_ALT = 216.9
HALKA_UST_MIN = 222.0
DELIK = (476.7, 163.9, 56.6 / 2)
HALKA_TEPE_PX = 7.0                  # halkanin en kalin yeri (istek >= 6 px)
HEDEF_KONTRAST = {'SAPPHIRE_GOLD': 5.0, 'EMERALD_GOLD': 4.5, 'RUBY_GOLD': 5.0}   # istek: EMERALD >= 4.5, SAPPHIRE / RUBY tarih > 5
CAP_ISIM = 28.07                     # v1 isim buyuk harf (2.38 mm)
P = o1.P
STILLER = (('SAPPHIRE_GOLD', 'SAPPHIRE_1264.png'), ('EMERALD_GOLD', 'EMERALD_1264.png'), ('RUBY_GOLD', 'RUBY_1264.png'))
V1 = dict(halka_dis_cap=554.1, sembol=(344, 327))


def lum(x):
    return x @ LUMA


# ------------------------------------------------------------------ halka profili (poster halkasindan olcum)
def halka_profili(f):
    a = np.asarray(Image.open(f), np.float32) / 255.0
    ys, xs = np.nonzero(a > 0.3)
    w = a[ys, xs]
    A = np.c_[2 * xs, 2 * ys, np.ones_like(xs)]
    c, *_ = np.linalg.lstsq(A * w[:, None], (xs ** 2 + ys ** 2) * w, rcond=None)
    cx, cy = c[0], c[1]
    R = float(np.sqrt(c[2] + cx ** 2 + cy ** 2))
    th = np.arange(0, 360, 1.0)
    rr = np.arange(R - 80, R + 80, 0.5)
    W, OFF = [], []
    for t in np.radians(th):
        x = cx + rr * np.cos(t); y = cy + rr * np.sin(t)
        v = a[np.clip(np.round(y).astype(int), 0, a.shape[0] - 1), np.clip(np.round(x).astype(int), 0, a.shape[1] - 1)]
        s = v.sum() * 0.5
        W.append(s); OFF.append(float((rr * v).sum() / max(v.sum(), 1e-6) - R) if s > 0.05 else np.nan)
    W, OFF = np.array(W), np.array(OFF)
    # dairesel 7 derece medyan (olcum gurultusu / plaka dokusu kesintilerini at)
    def med(v):
        v2 = np.r_[v[-3:], v, v[:3]]
        return np.array([np.nanmedian(v2[i:i + 7]) for i in range(len(v))])
    Ws = med(W)
    Ws[W < 0.05] = 0
    OFFs = med(np.where(np.isnan(OFF), np.nanmedian(OFF), OFF))
    # acik (bos) aci araligi: genislik 0 olan en uzun dairesel aralik
    sifir = Ws <= 0.05
    bos = [int(i) for i in np.nonzero(sifir)[0]]
    return dict(cx=float(cx), cy=float(cy), R=R, th=th, w=Ws, off=OFFs, w_max=float(Ws.max()),
                bos=[min(bos), max(bos)] if bos else None)


def halka_ciz(hp, cy, Rc, tepe_px=HALKA_TEPE_PX):
    """merkez (C, cy), merkez cizgisi yaricapi Rc (poster R'ye esit oranli); genislik = w(aci) / w_max x tepe_px. Doner alfa, t (0 kenar 1 orta)."""
    k = Rc / hp['R']
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    dx, dy = xx + 0.5 - C, yy + 0.5 - cy
    ang = (np.degrees(np.arctan2(dy, dx)) + 360) % 360
    w = np.interp(ang, hp['th'], hp['w'], period=360) / hp['w_max'] * tepe_px
    off = np.interp(ang, hp['th'], hp['off'], period=360) * k
    d = np.hypot(dx, dy) - (Rc + off)
    h = w / 2
    a = np.clip(h - np.abs(d) + 0.5, 0, 1) * (w > 0)
    t = np.clip(1 - np.abs(d) / np.maximum(h, 1e-3), 0, 1)
    return a.astype(np.float32), t.astype(np.float32), dict(k=k)


# ------------------------------------------------------------------ sonsuz kalinlastirma
def sonsuz_hazir(son_hr, gen_px):
    """son_hr: yuksek cozunurluk alfa (0-1). gen_px hedef genislik. 3x3 acmada kayip <= %2 ve bilesen sayisi ayni olana kadar
    kaynak alfa (hedef olcekte 0.25 px adimlarla) genisletilir."""
    s = gen_px / son_hr.shape[1]
    for adim in range(0, 25):
        r_hr = adim * 0.25 / s
        if r_hr > 0:
            k = int(round(r_hr)) * 2 + 1
            hr = cv2.dilate(son_hr, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        else:
            hr = son_hr
        pad = int(np.ceil(r_hr)) + 2
        hr = np.pad(hr, pad)
        a = o1.olcek(hr, gen_px / hr.shape[1])
        m = (a > 0.5).astype(np.uint8)
        ac = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        kayip = 1 - ac.sum() / max(m.sum(), 1)
        n0 = cv2.connectedComponents(m, 8)[0] - 1
        n1 = cv2.connectedComponents(ac, 8)[0] - 1
        if kayip <= 0.02 and n0 == n1:
            dt = cv2.distanceTransform(m, cv2.DIST_L2, 3)
            return a, dict(genisletme_hedef_px=adim * 0.25, acma3_kayip=round(float(kayip), 4), bilesen=int(n0),
                           en_ince_tahmin_px=round(float(2 * np.percentile(dt[(dt > 0) & (cv2.dilate(dt, np.ones((3, 3))) == dt)], 2)), 2))
    return a, dict(hata='3 px saglanamadi', acma3_kayip=round(float(kayip), 4))


# ------------------------------------------------------------------ sekil dogrulama (ham alfa / ana alfa)
def temiz_alfa(a):
    m = (a > 0.5).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return m
    buyuk = st[1:, cv2.CC_STAT_AREA].max()
    tut = np.isin(lab, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= 0.001 * buyuk])
    return tut.astype(np.uint8)


def sekil_dogrula(ham_f, ana_f, W=1200):
    ham = np.asarray(Image.open(ham_f), np.float32) / 255.0
    ana = np.asarray(Image.open(ana_f).convert('RGBA'), np.float32)[..., 3] / 255.0
    out = {}
    hm, am = temiz_alfa(ham), temiz_alfa(ana)
    for ad, m, ham_a in (('ham', hm, ham), ('ana', am, ana)):
        x0, y0, x1, y1 = o1.bbox(m.astype(np.float32), 0.5)
        dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
        cevre = sum(len(c) for c in cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)[0])
        out[ad] = dict(boyut=[int(ham_a.shape[1]), int(ham_a.shape[0])], kutu=[x0, y0, x1, y1], en_boy=round((x1 - x0) / (y1 - y0), 4),
                       alan_kutu_orani=round(float(m.sum() / ((x1 - x0) * (y1 - y0))), 4),
                       kalinlik_kutu_genisligine=round(float(2 * m.sum() / max(cevre, 1)) / (x1 - x0), 5),
                       kucuk_bilesen_atilan=int((ham_a > 0.5).sum() - m.sum()))
    def norm(m):
        x0, y0, x1, y1 = o1.bbox(m.astype(np.float32), 0.5)
        c = m[y0:y1, x0:x1].astype(np.float32)
        return cv2.resize(c, (W, round(c.shape[0] * W / c.shape[1])), interpolation=cv2.INTER_AREA)
    A, B = norm(am), norm(hm)                                         # A ana (referans), B ham
    en = None
    for s in np.arange(0.95, 1.0501, 0.0025):
        Bs = cv2.resize(B, (round(B.shape[1] * s), round(B.shape[0] * s)), interpolation=cv2.INTER_AREA)
        pad = 60
        Ap = np.pad(A, pad)
        if Bs.shape[0] > Ap.shape[0] or Bs.shape[1] > Ap.shape[1]:
            continue
        r = cv2.matchTemplate(Ap, Bs, cv2.TM_CCORR_NORMED)
        _, v, _, loc = cv2.minMaxLoc(r)
        if en is None or v > en[0]:
            en = (v, s, loc, Bs)
    v, s, (lx, ly), Bs = en
    H = max(A.shape[0] + 120, ly + Bs.shape[0]); Wd = max(A.shape[1] + 120, lx + Bs.shape[1])
    Ab = np.zeros((H, Wd), np.float32); Bb = np.zeros((H, Wd), np.float32)
    Ab[60:60 + A.shape[0], 60:60 + A.shape[1]] = A
    Bb[ly:ly + Bs.shape[0], lx:lx + Bs.shape[1]] = Bs
    a5, b5 = Ab > 0.5, Bb > 0.5
    iou = (a5 & b5).sum() / max((a5 | b5).sum(), 1)
    k = np.ones((5, 5), np.uint8)
    ad, bd = cv2.dilate(a5.astype(np.uint8), k) > 0, cv2.dilate(b5.astype(np.uint8), k) > 0
    tol = ((a5 & bd).sum() + (b5 & ad).sum()) / max(a5.sum() + b5.sum(), 1)    # +-2 px icinde kalan murekkep orani
    out['hizali'] = dict(calisma_genisligi=W, olcek=round(float(s), 4), oteleme=[int(lx - 60), int(ly - 60)], ncc=round(float(v), 4),
                         iou=round(float(iou), 4), tolerans2px_ortusme=round(float(tol), 4),
                         ham_fazla=round(float((b5 & ~ad).sum() / max(b5.sum(), 1)), 4),
                         ana_fazla=round(float((a5 & ~bd).sum() / max(a5.sum(), 1)), 4))
    return out


# ------------------------------------------------------------------ yerlesim + uretim
def yerlesim(K, hp, Rc, kaynak):
    """Rc: halka merkez cizgisi yaricapi. cy halka tepesi (dis kenar) = HALKA_UST_MIN olacak sekilde. Doner ogeler ve kapi sonucu."""
    k = Rc / hp['R']
    tepe_off = float(np.interp(270, hp['th'], hp['off'])) * k
    cy = HALKA_UST_MIN + HALKA_TEPE_PX / 2 + Rc + tepe_off + 0.5
    ha, ht, _ = halka_ciz(hp, cy, Rc)
    E = {'halka': (None, ha, 0, 0)}
    # sembol: posterdeki oran (kutu genisligi / halka merkez cizgisi capi; merkez dy / R)
    s_rgb_hr, s_a_hr = kaynak['ana']
    sx0, sy0, sx1, sy1 = P['sembol_kutu']
    s_w = (sx1 - sx0) * k
    x0, y0, x1, y1 = o1.bbox(s_a_hr, 0.5)
    s_rgb, s_a = o1.rgba_olcek(np.dstack([s_rgb_hr, s_a_hr]), s_w / (x1 - x0))
    s_cy = cy + ((sy0 + sy1) / 2 - hp['cy']) * k
    E['sembol'] = (s_rgb, s_a, int(round(C - s_a.shape[1] / 2)), int(round(s_cy - s_a.shape[0] / 2)))
    c = CAP_ISIM
    A1, t1 = kaynak['isim1']; A2, t2 = kaynak['isim2']; sa = kaynak['sonsuz']; At, tt = kaynak['tarih']
    b1, b2, bt = o1.bbox(A1, 0.5), o1.bbox(A2, 0.5), o1.bbox(At, 0.5)
    w1, w2 = b1[2] - b1[0], b2[2] - b2[0]
    gap = P['bosluk'] / P['cap'] * c
    top = w1 + gap + sa.shape[1] + gap + w2
    sx = C - top / 2
    gl = kaynak['kucuk']
    sym_alt = E['sembol'][3] + o1.bbox(s_a)[3]
    g_ust = sym_alt + 0.30 * c
    g_h = max(a.shape[0] for _, a in gl.values())
    g_mid = g_ust + g_h / 2
    isim_ust = g_ust + max(o1.bbox(a, 0.5)[3] - o1.bbox(a, 0.5)[1] for _, a in gl.values()) + 0.55 * c
    taban = isim_ust + c
    merk = {'sol': sx + w1 / 2, 'sag': sx + top - w2 / 2}
    E['isim1'] = (None, A1, int(round(sx - b1[0])), int(round(taban - t1)))
    E['isim2'] = (None, A2, int(round(sx + top - w2 - b2[0])), int(round(taban - t2)))
    E['sonsuz'] = (None, sa, int(round(sx + w1 + gap)), int(round(taban - c / 2 - sa.shape[0] / 2)))
    for t in ('sol', 'sag'):
        rgb, a = gl[t]
        E[f'kucuk_{t}'] = (rgb, a, int(round(merk[t] - a.shape[1] / 2)), int(round(g_mid - a.shape[0] / 2)))
    isim_alt = max(E['isim1'][3] + o1.bbox(A1, 0.5)[3], E['isim2'][3] + o1.bbox(A2, 0.5)[3])
    ct = P['tagline_T'] / P['cap'] * c
    tar_ust = isim_alt + 0.45 * c
    E['tarih'] = (None, At, int(round(C - (bt[0] + bt[2]) / 2)), int(round(tar_ust - bt[1])))
    # kapilar
    yy, xx = np.mgrid[0:N, 0:N]
    rr = np.hypot(xx - C + 0.5, yy - C + 0.5)
    maske, ihlal = {}, {}
    for ad, (_, a, x, y) in E.items():
        m = np.zeros((N, N), np.float32)
        h, w = a.shape
        xa, ya, xb, yb = max(0, x), max(0, y), min(N, x + w), min(N, y + h)
        m[ya:yb, xa:xb] = a[ya - y:yb - y, xa - x:xb - x]
        maske[ad] = m
        ic = m > 0.02
        ihlal[ad] = bool((a > 0.02).sum() - ic.sum() > 0 or (rr[ic] > R_SINIR).any() or (yy[ic] < HALKA_UST_MIN).any())
    cak = []
    for ref in ('halka', 'sembol'):
        rm = cv2.dilate((maske[ref] > 0.05).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
        for ad in E:
            if ad not in ('halka', 'sembol') and (rm & (maske[ad] > 0.05)).any():
                cak.append(f'{ref}/{ad}')
    if (cv2.dilate((maske['halka'] > 0.05).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0)[maske['sembol'] > 0.05].any():
        cak.append('halka/sembol')
    return dict(E=E, maske=maske, ihlal=ihlal, cak=cak, gecti=not any(ihlal.values()) and not cak, cy=cy, Rc=Rc, k=k, ht=ht, ct=ct)


def okunurluk(rgb, zemin, maske, ad):
    m = maske[ad]
    ce = cv2.erode((m > 0.9).astype(np.uint8), np.ones((2, 2), np.uint8)) > 0
    ce = ce if ce.sum() > 10 else m > 0.7
    # yazinin arkasi = murekkebin 3-6 px cevresindeki bant (deneme 1: kutu + 6 px, J inisi yuzunden harflerden 25-30 px uzak zemini de
    # kapsiyordu; okunurlugu belirleyen harf cevresidir). Once / sonra ayni yontemle olculur.
    ink = (m > 0.02).astype(np.uint8)
    arka = (cv2.dilate(ink, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))) > 0) & \
           (cv2.dilate(ink, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))) == 0)
    yc = np.median(rgb[ce], 0)
    za = zemin[arka]
    zc = np.median(za, 0)
    z95 = np.median(za[lum(za) >= np.percentile(lum(za), 95)], 0)
    return dict(yazi_rgb=[int(v) for v in yc], zemin_rgb=[int(v) for v in zc], kontrast=o1.kontrast(yc, zc),
                kontrast_acik5=o1.kontrast(yc, z95))


def boya_bindir(Y, model, zemin, hale_s, kazanc, ht):
    out = zemin.astype(np.float32).copy()
    yazi = ('isim1', 'isim2', 'sonsuz', 'tarih')
    if hale_s > 0:
        tm = np.maximum.reduce([Y['maske'][a] for a in yazi])
        # deneme 1 (kosu 41435681741): 5 px + sigma 3 hale olcum bolgesinin (yazi kutusu + 6 px) disini koyulastirmiyordu, EMERALD 3.31
        g = cv2.GaussianBlur(cv2.dilate((tm > 0.02).astype(np.float32), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))), (0, 0), 2.5)
        g = g / max(float(g.max()), 1e-6)
        out = out * (1 - hale_s * g[..., None])
    zemin_hale = out.copy()
    for ad, (rgb, a, x, y) in Y['E'].items():
        if ad == 'sembol':
            col = rgb
        elif ad == 'halka':
            # tek renk (tek doku modelinin Lmed rengi): deneme 1'de boru profili ince bolgelerde tepe uretmiyor, govde parlakligi 151-184
            col = np.broadcast_to(model.td.renk(np.full((1, 1), model.Lmed, np.float32), model.egri), (N, N, 3)).astype(np.float32)
        elif ad.startswith('kucuk'):
            col, _ = model.boya(lum(rgb), a)
        else:
            col, _ = model.duz(a)
            if ad in yazi and kazanc != 1.0:
                col = np.clip(model.td.renk(lum(col) * kazanc, model.egri), 0, 255)
        m = Y['maske'][ad][..., None]
        cc = np.zeros((N, N, 3), np.float32)
        if ad == 'halka':
            cc = col
        else:
            h, w = a.shape
            xa, ya, xb, yb = max(0, x), max(0, y), min(N, x + w), min(N, y + h)
            cc[ya:yb, xa:xb] = col[ya - y:yb - y, xa - x:xb - x]
        out = out * (1 - m) + cc * m
    return np.clip(np.round(out), 0, 255).astype(np.uint8), zemin_hale


def halka_olc(rgb, a, cy):
    """aci boyunca (2 derece) halka genisligi (radyal alfa toplami) ve parlaklik (alfa > 0.9 piksellerin en buyuk lumasi)."""
    yy, xx = np.mgrid[0:N, 0:N]
    ang = (np.degrees(np.arctan2(yy + 0.5 - cy, xx + 0.5 - C)) + 360) % 360
    L = lum(rgb.astype(np.float32))
    sat = []
    for b0 in range(0, 360, 2):
        m = (ang >= b0) & (ang < b0 + 2) & (a > 0.02)
        if not m.any():
            continue
        r = np.hypot(xx[m] + 0.5 - C, yy[m] + 0.5 - cy)
        yay = np.radians(2) * float(np.median(r))
        gen = float(a[m].sum() / max(yay, 1e-6))
        tam = m & (a > 0.99)
        sat.append(dict(aci=b0 + 1, genislik_px=round(gen, 2), parlaklik=round(float(L[tam].max()), 1) if tam.any() else None,
                        renk_ort_kapsamli=round(float((L[m] * a[m]).sum() / a[m].sum()), 1)))
    return sat


def onizleme(liste, delik=True, kilavuz=False, ara=24):
    ims = []
    for rgb in liste:
        im = Image.fromarray(rgb).convert('RGB')
        d = ImageDraw.Draw(im)
        if delik:
            x, y, r = DELIK
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255))
        if kilavuz:
            for rr, renk in ((RV, (255, 255, 255)), (GUV_R, (0, 230, 255))):
                d.ellipse([C - rr, C - rr, C + rr, C + rr], outline=renk, width=1)
            x, y, r = DELIK
            d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 80, 80), width=1)
            d.line([C - 60, o1.Y_UST - 0, C + 60, o1.Y_UST], fill=(255, 255, 255))
            d.line([C - 60, CENTIK_ALT, C + 60, CENTIK_ALT], fill=(0, 230, 255))
        a = np.asarray(im)
        if not kilavuz:
            yy, xx = np.mgrid[0:N, 0:N]
            al = np.clip(RV - np.hypot(xx - C + 0.5, yy - C + 0.5) + 0.5, 0, 1)[..., None]
            a = np.round(a * al + 255 * (1 - al)).astype(np.uint8)
            a = a[int(C - RV) - 2:int(C + RV) + 3, int(C - RV) - 2:int(C + RV) + 3]
        ims.append(a)
    h = max(i.shape[0] for i in ims)
    w = sum(i.shape[1] for i in ims) + ara * (len(ims) - 1)
    o = np.full((h, w, 3), 255, np.uint8)
    x = 0
    for i in ims:
        o[:i.shape[0], x:x + i.shape[1]] = i
        x += i.shape[1] + ara
    return Image.fromarray(o, 'RGB')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    K, O = Path(a.kaynak), Path(a.cikti)
    O.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('tek_doku', K / 'tek_doku.py')
    td = importlib.util.module_from_spec(spec); spec.loader.exec_module(td)
    R = {'kaynak_sha256': {f.name: o1.sha(f) for f in sorted(K.iterdir()) if f.is_file()},
         'sabit': dict(guvenli_r=GUV_R, guvenli_pay=GUV_PAY, halka_ust_min=HALKA_UST_MIN, halka_tepe_px=HALKA_TEPE_PX, hedef_kontrast=HEDEF_KONTRAST)}
    hp = halka_profili(K / 'HALKA_BLUE_16x20.png')
    R['poster_halka'] = dict(merkez=[round(hp['cx'], 1), round(hp['cy'], 1)], R=round(hp['R'], 1), w_max=round(hp['w_max'], 2), bos_aci=hp['bos'],
                             genislik_ornek={str(t): round(float(hp['w'][t]), 2) for t in (270, 300, 330, 0, 20, 30, 35, 40, 140, 145, 150, 160, 180, 210, 240)})
    # kaynaklar
    ana = np.asarray(Image.open(K / 'CANCER_LIBRA_ana.png').convert('RGBA'), np.float32)
    ana[..., 3] /= 255.0
    ana = o1.kirp(ana, ana[..., 3], pad=2)
    if ana.shape[1] > 1600:                                                       # arama hizi: tek seferlik esit oranli on kucultme
        rgb_, a_ = o1.rgba_olcek(ana, 1600 / ana.shape[1])
        ana = np.dstack([rgb_, a_])
    kaynak = {'ana': (ana[..., :3], ana[..., 3])}
    kaynak['isim1'] = o1.metin_alfa('EMILY', K / 'Cinzel.ttf', CAP_ISIM, 500)
    kaynak['isim2'] = o1.metin_alfa('JAMES', K / 'Cinzel.ttf', CAP_ISIM, 500)
    kaynak['tarih'] = o1.metin_alfa('14 JUNE 2025', K / 'EBGaramond-Italic.ttf', P['tagline_T'] / P['cap'] * CAP_ISIM, None, ref='T')
    son = np.load(K / 'alfa_ogeler.npz')['sonsuz'].astype(np.float32) / 255.0
    son = o1.kirp(son, son)
    sa, R['sonsuz'] = sonsuz_hazir(son, P['sonsuz_w'] / P['cap'] * CAP_ISIM)
    kaynak['sonsuz'] = sa
    def kucuk(burc, h_hedef):
        g = np.asarray(Image.open(K / f'{burc}_symbol_gold.png').convert('RGBA'), np.float32)
        g[..., 3] /= 255.0
        g = o1.kirp(g, g[..., 3], pad=2)
        gx0, gy0, gx1, gy1 = o1.bbox(g[..., 3], 0.5)
        return o1.rgba_olcek(g, h_hedef / (gy1 - gy0))
    kaynak['kucuk'] = {'sol': kucuk('cancer', P['kucuk_sol_h'] / P['cap'] * CAP_ISIM), 'sag': kucuk('libra', P['kucuk_sag_h'] / P['cap'] * CAP_ISIM)}
    # en buyuk halka: Rc azalan arama (1 px), ilk gecen
    Y, denenen = None, []
    for Rc in np.arange(360, 200, -1.0):
        y_ = yerlesim(K, hp, float(Rc), kaynak)
        if y_['gecti']:
            Y = y_
            break
        if len(denenen) < 400:
            denenen.append(dict(Rc=float(Rc), ihlal=[k for k, v in y_['ihlal'].items() if v], cak=y_['cak']))
    if Y is None:
        print('FAIL: yerlesim bulunamadi', json.dumps(denenen[-5:]), flush=True)
        return 1
    R['arama_son_red'] = denenen[-3:]
    # model (sembolun hedef olcekteki hali)
    s_rgb, s_a = Y['E']['sembol'][0], Y['E']['sembol'][1]
    model = o1.Model(td, s_rgb, s_a, 4800 * Y['k'])
    # olcu
    tum = np.maximum.reduce([Y['maske'][k] for k in Y['maske']]) > 0.02
    yy, xx = np.nonzero(tum)
    rmax = float(np.hypot(xx - C + 0.5, yy - C + 0.5).max())
    hy, hx = np.nonzero(Y['maske']['halka'] > 0.02)
    dis_cap = float(hx.max() - hx.min() + 1)
    sb = o1.bbox(Y['maske']['sembol'], 0.5)
    R['yerlesim'] = dict(halka_merkez_y=round(Y['cy'], 1), halka_Rc=Y['Rc'], halka_dis_cap_px=dis_cap, halka_dis_cap_mm=round(dis_cap * MM, 2),
                         halka_dis_cap_v1=V1['halka_dis_cap'], halka_kazanc_yuzde=round((dis_cap / V1['halka_dis_cap'] - 1) * 100, 1),
                         halka_ust_y=int(hy.min()), centik_alt=CENTIK_ALT,
                         sembol_px=[sb[2] - sb[0], sb[3] - sb[1]], sembol_mm=[round((sb[2] - sb[0]) * MM, 2), round((sb[3] - sb[1]) * MM, 2)],
                         sembol_kazanc_yuzde=round(((sb[2] - sb[0]) / V1['sembol'][0] - 1) * 100, 1),
                         en_dis_r=round(rmax, 1), guvenli_daireye_pay=round(GUV_R - rmax, 1), ust_min_y=int(yy.min()),
                         kenar_payi_gorunen=round(RV - rmax, 1), ihlal=Y['ihlal'], cakisma=Y['cak'])
    for ad in Y['maske']:
        x0, y0, x1, y1 = o1.bbox(Y['maske'][ad], 0.5)
        R['yerlesim'].setdefault('oge', {})[ad] = dict(kutu=[x0, y0, x1, y1], w_mm=round((x1 - x0) * MM, 2), h_mm=round((y1 - y0) * MM, 2))
    R['yerlesim']['isim_buyuk_harf_mm'] = round(CAP_ISIM * MM, 2)
    R['yerlesim']['tarih_buyuk_harf_mm'] = round(Y['ct'] * MM, 2)
    # stiller
    cikti = []
    for ad, zf in STILLER:
        zemin = o1.zemin_canva(K / zf)
        once = None
        sec = None
        hedef = HEDEF_KONTRAST[ad]
        for s in np.arange(0, 0.751, 0.05):                          # en hafif hale once; her hale icin altin en fazla %12 acilir
            for kazanc in (1.0, 1.04, 1.08, 1.12):
                rgb, zh = boya_bindir(Y, model, zemin, float(s), kazanc, Y['ht'])
                ok = {k: okunurluk(rgb, zh, Y['maske'], k) for k in ('isim1', 'isim2', 'tarih')}
                if once is None:
                    once = ok
                en_kotu = min(min(v['kontrast'], v['kontrast_acik5']) for v in ok.values())
                if en_kotu >= hedef:
                    sec = (float(s), kazanc, rgb, ok, en_kotu)
                    break
            if sec:
                break
        if sec is None:
            sec = (float(s), kazanc, rgb, ok, en_kotu)
        s, kazanc, rgb, ok, en_kotu = sec
        o1.kaydet(rgb, O / f'{ad}_954.png')
        cikti.append(rgb)
        ho = halka_olc(rgb, Y['maske']['halka'], Y['cy'])
        govde = [h for h in ho if h['genislik_px'] >= 1.0 and h['parlaklik'] is not None]
        R.setdefault('stil', {})[ad] = dict(hale_s=round(s, 2), altin_kazanc=kazanc, en_kotu_kontrast=en_kotu, hedef=hedef, hedef_tuttu=en_kotu >= hedef,
                                            okunurluk_once=once, okunurluk=ok,
                                            halka_parlaklik_govde=dict(min=min(h['parlaklik'] for h in govde), max=max(h['parlaklik'] for h in govde)),
                                            halka_aci=ho)
        print(ad, json.dumps({k: R['stil'][ad][k] for k in ('hale_s', 'altin_kazanc', 'en_kotu_kontrast', 'halka_parlaklik_govde')}), flush=True)
    onizleme(cikti).save(O / 'STIL3_V2_ONIZLEME_7cm.png', dpi=(300, 300))
    onizleme(cikti, kilavuz=True).save(O / 'STIL3_V2_KILAVUZ.png', dpi=(300, 300))
    if (K / 'cancer_libra_alfa.png').exists():
        R['sekil'] = sekil_dogrula(K / 'cancer_libra_alfa.png', K / 'CANCER_LIBRA_ana.png')
        print('SEKIL', json.dumps(R['sekil']['hizali']), flush=True)
    (O / 'OLCUM_V2.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=float))
    print('YERLESIM', json.dumps({k: v for k, v in R['yerlesim'].items() if k != 'oge'}), flush=True)
    print('SONSUZ', json.dumps(R['sonsuz']), flush=True)
    gecti = all(v['hedef_tuttu'] for v in R['stil'].values()) and 'hata' not in R['sonsuz']
    print('KAPI', 'PASS' if gecti else 'FAIL', flush=True)
    return 0 if gecti else 1


if __name__ == '__main__':
    sys.exit(main())
