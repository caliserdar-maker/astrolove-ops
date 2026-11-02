#!/usr/bin/env python3
"""Ornament ornek V4 (Merkez gorevi STIL3_V4, Serdar onayi 2 Kas 2026). Etsy / Printful yazma yok; toplu uretim yok.
Duzen V3 ile ayni (sembol ortada buyuk, kucuk burc sembolleri altta iki yanda, isim satiri ortasinda logo, en altta tarih).
Degisenler (V3'e gore):
  1 HALKA: tepe merkez cizgisi delik merkezinden (476, 163) gecer. y < 221 / delik r 34 kurali YALNIZ halka icin kalkar; halka guvenli
    daire icinde en buyuk boyutta (oran 0.987 korunur). Sembol halkayla ayni oranda buyur (posterdeki konum / oran).
  2 HALKA PROFILI: posterden (HALKA_BLUE_16x20.png) elips normali boyunca 0.05 derece adimla olculen genislik W(aci). Genislik =
    GOVDE_MED x W / medyan(W) (posterle ayni goreli profil: tepe kalinlasmasi ve uc incelmesi birebir). Uctan yayin %20'sinden uzak
    govdede taban GOVDE_MIN (>= 4 px). Uclar posterdeki gibi son %15-20'de incelir, kil inceliginde biter.
  3 LOGO: LOGO_1.png sag yarisi (siyah zemin uzerinde beyaz), alfa = parlaklik. YALNIZ olcek + altin renk; kalinlastirma / birlestirme /
    yeniden cizim YOK. En ince cizgi ve kaynaga IoU olculur (hedef >= 2 px tutmazsa raporda 3 oneri).
  4 BUTUNLESME: gomulu kenar (sol ust ic kenar ince koyu, sag alt ic kenar ince acik; zeminin kendi tonunda; ince cizgili ogelerde
    (isim, tarih, logo) opaklik x GOMU_YAZI: tam opaklikta kontrast 4.5 tutmuyor, CELISKI Merkez kararinda), disa sicak altin isik tasmasi
    (4-10 px, dusuk opaklik), zemin dokusu (oge basina gorunen %4-6), golge tonlarina (oge murekkep ortancasindan koyu tonlar) zemin rengi %28,
    isik sol ust. V3'teki dis golge (sag alt) kaldirildi.
Kapilar: son goruntude (|goruntu - zemin| > 1) guvenli daire (476, 477) r 380 disi 0; delik r 34 / y < 221 icinde halka bolgesi disinda 0;
cakisma 0; kontrast >= 4.5 (kati olcut); halka govde >= 4 px; oge basina gorunen doku %4-6; isik tasmasi p95 >= 4, en fazla <= 10 px.
Kullanim: ornament_ornek4.py --kaynak DIR --cikti DIR"""
import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

_d = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('ornek3', _d / 'ornament_ornek3.py'); o3 = importlib.util.module_from_spec(_s); _s.loader.exec_module(o3)
o1, o2 = o3.o1, o3.o2
N, C, MM, P = o1.N, o1.C, o1.MM, o1.P
CX, CY = 476.0, 477.0                     # Printful 900 sablonu guvenli daire / kesim merkezi (inceleme 9: eski 477, 477)
o3.C = CX                                 # yazi blogu yatay merkezi (o3.yazi_blogu)
# Printful resmi 900 Circle sablonu (CeramicOrnaments_Template_Circle.psd, 954 x 954; Merkez olcumu 2 Kas, Serdar):
GUV_R = 380.0                             # guvenli alan (kirmizi kesikli daire) yaricapi; eski 380.3 (v2 Circle.png olcumu)
DELIK = (476.0, 163.0, 34.0)              # delik merkezi ve yasak yaricap (siyah halka dis r 34, ic r 25); eski (476.7, 163.9, 28.3)
DELIK_IC = 25.0                           # deligin kendisi (onizlemede beyaz)
UST_YASAK = 221                           # delik alti kirmizi yay en alt y 220: yasak y < 221; eski y < 217 (centik alti 216.9)
UST_MIN = UST_YASAK
KESIM_R = 38.0 * 300 / 25.4   # fiziksel cap 7.6 cm -> kesim dairesi r 448.8 px (hesap); eski 413.5 (7 cm, 881)
ESKI = dict(guvenli_r=380.3, delik=[476.7, 163.9, 28.3], ust_yasak='y < 217 (+ centik x 422.7-535.0, y <= 216.9)', kesim_r=413.5,
            kesim_kaynak='881 aciklamasi 7 cm (yanlis urun)')
PAY = 3                                   # guvenli daireye en az pay (px); isik tasmasi ayrica GLOW_R ile sayilir
TEPE_Y = DELIK[1]                         # halka tepe merkez cizgisi = delik merkezi y
GOVDE_MED, GOVDE_MIN = 4.4, 4.2           # halka govde: poster medyani -> 4.4 px, govde tabani 4.2 px (olcum >= 4)
UC_BOLGE = 0.20                           # uctan yayin bu orani icinde taban uygulanmaz (poster incelmesi %15-20'de basliyor)
CAP0 = o3.CAP0
LOGO_H = 1.0                              # logo yuksekligi / isim buyuk harf
HEDEF = 4.5
GOMU_KOYU, GOMU_ACIK = 0.55, 0.40         # gomulu kenar opaklik (koyu sol ust, acik sag alt)
GOMU_KAYMA, GOMU_SIGMA = 1.0, 0.6
GOMU_YAZI = 0.20                          # ince cizgili ogelerde (isim, tarih, logo) gomulu kenar opaklik carpani (kontrast)
YAZI_OGE = ('isim1', 'isim2', 'tarih', 'sonsuz')
GLOW_SIGMA, GLOW_OPAK, GLOW_R = 3.0, 0.16, 8   # inceleme 7: gorunen uzanim ~5 px (p95), en fazla 8.4; kapi payi 10 -> 8
GLOW_RGB = np.array([255, 196, 110], np.float32)   # sicak altin
TINT_GUC = 0.28
DOKU_ADAY = (0.14, 0.17, 0.20, 0.23, 0.26, 0.30)   # overlay katman opakligi; gorunen %4-6 icin secilir
DOKU_HEDEF = (4.0, 6.0)
STILLER = o3.STILLER
V3_HALKA_W, V3_SEMBOL_W = 640, 397


def lum(x):
    return x @ o1.LUMA


# ----------------------------------------------------------------------------------------------- poster halka profili
def poster_profil(f):
    el = o3.elips_olc(f)
    a = np.asarray(Image.open(f), np.float32) / 255.0
    ax, by, cx, cy = el['a'], el['b'], el['cx'], el['cy']
    T = np.arange(0, 360, 0.05)
    W = np.zeros_like(T)
    u = np.arange(-40, 40.0001, 0.1)
    for i, t in enumerate(T):
        tr = math.radians(t); c_, s_ = math.cos(tr), math.sin(tr)
        rr = 1 / math.sqrt((c_ / ax) ** 2 + (s_ / by) ** 2); px, py = cx + rr * c_, cy + rr * s_
        nx, ny = (px - cx) / ax ** 2, (py - cy) / by ** 2; nn = math.hypot(nx, ny); nx, ny = nx / nn, ny / nn
        v = cv2.remap(a, (px + u * nx - 0.5).astype(np.float32)[None], (py + u * ny - 0.5).astype(np.float32)[None], cv2.INTER_LINEAR, borderValue=0)[0]
        W[i] = v.sum() * 0.1
    z = np.nonzero(W <= 0.02)[0]
    # acik aralik: alt yarida (0-180) sifir olan en genis aralik
    zz = T[z][(T[z] > 0) & (T[z] < 180)]
    t1, t2 = float(zz.min()), float(zz.max())
    r_ort = (ax + by) / 2
    L = math.radians(360 - (t2 - t1)) * r_ort
    s = np.minimum(np.radians((t1 - T) % 360) * r_ort, np.radians((T - t2) % 360) * r_ort)
    acik = (T > t1) & (T < t2)
    W[acik] = 0.0
    govde = W[(s > 0.25 * L) & ~acik]
    med = float(np.median(govde))
    tablo = {}
    for fr in (0.25, 0.20, 0.15, 0.12, 0.10, 0.08, 0.06, 0.05, 0.04, 0.03, 0.02, 0.01, 0.005, 0.0):
        tablo[str(fr)] = [round(float(W[np.argmin(np.abs(np.radians((t1 - T) % 360) * r_ort - fr * L))] / med), 3),
                          round(float(W[np.argmin(np.abs(np.radians((T - t2) % 360) * r_ort - fr * L))] / med), 3)]
    return dict(el=el, T=T, W=W, t1=t1, t2=t2, L=L, med=med, govde_min=float(govde.min()), tepe=float(W.max()),
                tepe_aci=float(T[W.argmax()]), tablo_uc_sag_sol=tablo)


def genislik(pp, ang):
    """aci (0 sag, 90 asagi) -> halka genisligi (px). Posterin goreli profili; govdede taban."""
    w = np.interp(ang, pp['T'], pp['W'], period=360) / pp['med'] * GOVDE_MED
    T1, T2 = pp['t1'], pp['t2']
    r = (pp['el']['a'] + pp['el']['b']) / 2
    s = np.minimum(np.radians((T1 - ang) % 360), np.radians((ang - T2) % 360)) * r / pp['L']
    acik = (ang > T1) & (ang < T2)
    w = np.where(acik, 0.0, np.where(s >= UC_BOLGE, np.maximum(w, GOVDE_MIN), w))
    return w, s


def halka_alfa(pp, cy, ax, ss=4):
    el = pp['el']
    by = ax / el['oran']
    out = np.zeros((N, N), np.float32)
    y0 = max(0, int(cy - by - 20)); y1 = min(N, int(cy + by + 20))
    yy, xx = np.mgrid[y0 * ss:y1 * ss, 0:N * ss].astype(np.float32)
    dx, dy = (xx + 0.5) / ss - CX, (yy + 0.5) / ss - cy
    rho = np.sqrt((dx / ax) ** 2 + (dy / by) ** 2)
    d = (rho - 1) * np.sqrt(dx ** 2 + dy ** 2) / np.maximum(rho, 1e-6)
    ang = (np.degrees(np.arctan2(dy, dx)) + 360) % 360
    w, _ = genislik(pp, ang)
    a_hr = ((np.abs(d) <= w / 2) & (w > 0)).astype(np.float32)
    out[y0:y1] = cv2.resize(a_hr, (N, y1 - y0), interpolation=cv2.INTER_AREA)
    return out, dict(ax=ax, by=by, cy=cy, r_ort=(ax + by) / 2)


def halka_olc(a, hb, pp):
    ax, by, cy = hb['ax'], hb['by'], hb['cy']
    sat = []
    u = np.arange(-15, 15.0001, 0.1)
    for t in np.arange(0, 360, 0.25):
        tr = math.radians(t); c_, s_ = math.cos(tr), math.sin(tr)
        rr = 1.0 / math.sqrt((c_ / ax) ** 2 + (s_ / by) ** 2)
        px, py = CX + rr * c_, cy + rr * s_
        nx, ny = (px - CX) / ax ** 2, (py - cy) / by ** 2; nn = math.hypot(nx, ny); nx, ny = nx / nn, ny / nn
        v = cv2.remap(a, (px + u * nx - 0.5).astype(np.float32)[None], (py + u * ny - 0.5).astype(np.float32)[None], cv2.INTER_LINEAR, borderValue=0)[0]
        sat.append((t, float(v.sum() * 0.1)))
    T = np.array([x[0] for x in sat]); Wm = np.array([x[1] for x in sat])
    _, s = genislik(pp, T)
    acik = (T > pp['t1']) & (T < pp['t2'])
    govde = (s >= UC_BOLGE) & ~acik
    med_k = float(np.median(Wm[govde]))
    uc = {}
    for ad, ss_ in (('sag', np.radians((pp['t1'] - T) % 360)), ('sol', np.radians((T - pp['t2']) % 360))):
        ss_ = ss_ * (hb['r_ort'] if False else (pp['el']['a'] + pp['el']['b']) / 2) / pp['L']
        uc[ad] = {str(fr): round(float(Wm[np.argmin(np.abs(ss_ - fr))] / med_k), 3) for fr in (0.20, 0.15, 0.10, 0.08, 0.05, 0.02, 0.01, 0.0)}
    return dict(yontem='elips normali, 0.25 derece, 0.1 px bilineer', govde_min=round(float(Wm[govde].min()), 2),
                govde_min_aci=float(T[govde][Wm[govde].argmin()]), govde_medyan=round(med_k, 2), tepe=round(float(Wm.max()), 2),
                tepe_aci=float(T[Wm.argmax()]), uc_oran_govde_medyanina=uc,
                poster_uc_oran=pp['tablo_uc_sag_sol'])


# ----------------------------------------------------------------------------------------------- logo (birebir)
def logo_kaynak(f):
    a = np.asarray(Image.open(f).convert('RGB'), np.float32)
    sag = a[:, a.shape[1] // 2:].mean(2) / 255.0
    ys, xs = np.nonzero(sag > 0.1)
    al = sag[ys.min() - 2:ys.max() + 3, xs.min() - 2:xs.max() + 3]
    return al


def sirt_genislik(m_bin, ss):
    """ikili maske (ss kat ornekli) -> sirt genislikleri (asil px)."""
    dt = cv2.distanceTransform(m_bin, cv2.DIST_L2, 5)
    r = (dt > 0) & (cv2.dilate(dt, np.ones((3, 3), np.uint8)) <= dt)
    return 2 * (dt[r] - 0.5) / ss


def delik_say(m):
    cont, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    return int(sum(1 for h in (hier[0] if hier is not None else []) if h[3] >= 0))


def logo_olc(src, a):
    """src: kaynak alfa, a: hedef boyda alfa. Olcek, en ince cizgi (kaynak x olcek ve hedefte gorunen), IoU, kayip."""
    k = a.shape[1] / src.shape[1]
    ms = (src > 0.5).astype(np.uint8)
    wk = sirt_genislik(cv2.resize(ms * 255, (ms.shape[1] * 4, ms.shape[0] * 4), interpolation=cv2.INTER_NEAREST).__gt__(127).astype(np.uint8), 4)
    geri = cv2.resize(a, (src.shape[1], src.shape[0]), interpolation=cv2.INTER_CUBIC)
    mg = geri > 0.5
    iou = float((mg & (ms > 0)).sum() / max(((mg | (ms > 0))).sum(), 1))
    a4 = cv2.resize(a, (a.shape[1] * 4, a.shape[0] * 4), interpolation=cv2.INTER_CUBIC)
    wh = sirt_genislik((a4 > 0.5).astype(np.uint8), 4)
    kayip = float(((ms > 0) & ~mg).sum() / max(ms.sum(), 1))
    return dict(kaynak_px=[int(src.shape[1]), int(src.shape[0])], hedef_px=[int(a.shape[1]), int(a.shape[0])], olcek=round(k, 4),
                kaynak_en_ince=round(float(wk.min()), 2), kaynak_p1=round(float(np.percentile(wk, 1)), 2),
                kaynak_p5=round(float(np.percentile(wk, 5)), 2), kaynak_medyan=round(float(np.median(wk)), 2),
                hedefte_geometrik_en_ince=round(float(wk.min() * k), 3), hedefte_geometrik_p1=round(float(np.percentile(wk, 1) * k), 3),
                hedefte_geometrik_medyan=round(float(np.median(wk) * k), 2),
                hedefte_gorunen_en_ince_alfa05=round(float(wh.min()), 2) if wh.size else None,
                hedefte_gorunen_medyan=round(float(np.median(wh)), 2) if wh.size else None,
                iou_kaynak=round(iou, 4), kaynak_murekkep_kaybi_yuzde=round(kayip * 100, 2),
                ic_bosluk_kaynak=delik_say(ms), ic_bosluk_hedef=delik_say((a > 0.5).astype(np.uint8)),
                bilesen_hedef=int(cv2.connectedComponents((a > 0.5).astype(np.uint8), 8)[0] - 1),
                iki_px_icin_gereken_genislik_p1=int(round(src.shape[1] * 2 / max(np.percentile(wk, 1), 1e-6))),
                iki_px_icin_gereken_genislik_en_ince=int(round(src.shape[1] * 2 / max(wk.min(), 1e-6))))


def logo_oneri(src, gen):
    """oneri 1 (kalinlastirilmis kucuk boy): en ince cizgi baskida >= 2 px icin kaynakta gereken genisletme ve sekle etkisi."""
    k = gen / src.shape[1]
    hedef_kaynak = 2.0 / k
    ms = (src > 0.5).astype(np.uint8)
    r = []
    for rad in range(1, 16):
        md = cv2.dilate(ms, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rad + 1,) * 2))
        w = sirt_genislik(cv2.resize(md * 255, (md.shape[1] * 2, md.shape[0] * 2), interpolation=cv2.INTER_NEAREST).__gt__(127).astype(np.uint8), 2)
        iou = float((md & ms).sum() / max((md | ms).sum(), 1))
        r.append(dict(genisletme_kaynak_px=rad, en_ince_kaynak=round(float(np.percentile(w, 0.5)), 2), en_ince_hedef=round(float(np.percentile(w, 0.5) * k), 2),
                      iou_kaynak=round(iou, 3), ic_bosluk=delik_say(md), bilesen=int(cv2.connectedComponents(md, 8)[0] - 1)))
        if np.percentile(w, 0.5) >= hedef_kaynak:
            break
    return dict(hedef_genislik_px=round(gen, 1), olcek=round(k, 4), kaynakta_gereken_en_ince=round(hedef_kaynak, 1), adimlar=r)


# ----------------------------------------------------------------------------------------------- yasak bolge
def yasak_m():
    yy, xx = np.mgrid[0:N, 0:N]
    r = np.hypot(xx + 0.5 - CX, yy + 0.5 - CY)
    return dict(guvenli_disi=r > GUV_R - PAY,
                delik=np.hypot(xx + 0.5 - DELIK[0], yy + 0.5 - DELIK[1]) <= DELIK[2] + 1,
                ust_cizgi=yy < UST_YASAK + 1)


YASAK = None
GLOW_K = None
TINT_OLC = None
# V5 kancalari (varsayilan None: V4 davranisi degismez)
RENK_DONUSUM = None                       # f(cc, model) -> cc: altin -> bronz (acik zeminler)
SON_KIRP = None                           # f(cc) -> cc: doku sonrasi (bronz acik ucu siniri)
DIS_GOLGE = None                          # dict(kayma, sigma, opak, koyu): zemin tonlu dis golge (acik zeminler)


def kapi(E):
    """halka: yalniz guvenli daire. Diger ogeler: tum yasaklar. Isik tasmasi icin maske GLOW_R genisletilir."""
    M, tasma = {}, {}
    for ad, (_, a, x, y) in E.items():
        if ad == 'halka':
            M[ad] = a; tasma[ad] = 0
        else:
            M[ad], tasma[ad] = o3.maske_yaz(a, x, y)
    yb = {k: 0 for k in YASAK}
    for ad, m in M.items():
        mg = cv2.dilate((m > 0.02).astype(np.uint8), GLOW_K) > 0
        for k, v in YASAK.items():
            if ad == 'halka' and k != 'guvenli_disi':
                continue
            yb[k] += int((mg & v).sum())
    yb['tuval_disi'] = int(sum(tasma.values()))
    cak = []
    ref = [r for r in ('halka', 'sembol') if r in M]
    for r in ref:
        rm = cv2.dilate((M[r] > 0.05).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
        for ad in M:
            if ad not in ref and (rm & (M[ad] > 0.05)).any():
                cak.append(f'{r}/{ad}')
    if len(ref) == 2 and ((cv2.dilate((M['halka'] > 0.05).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0) & (M['sembol'] > 0.05)).any():
        cak.append('halka/sembol')
    yazi = [k for k in M if k not in ('halka', 'sembol')]
    for i, a1 in enumerate(yazi):
        d1 = cv2.dilate((M[a1] > 0.05).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        for a2 in yazi[i + 1:]:
            if (d1 & (M[a2] > 0.05)).any():
                cak.append(f'{a1}/{a2}')
    return M, yb, cak, all(v == 0 for v in yb.values()) and not cak


def alt_sinir(T, kucuk, g1, g2):
    for alt in np.arange(N - 40, 500, -1.0):
        E, ust = o3.yazi_blogu(T, kucuk, alt, g1, g2)
        M, yb, cak, ok = kapi(E)
        if ok:
            return alt, E, ust
    return None, None, None


def yerlesim_A(pp, ana, T, kucuk):
    el = pp['el']
    alt, Eyazi, ust = alt_sinir(T, kucuk, 0.45, 0.40)
    if alt is None:
        return None
    sx0, sy0, sx1, sy1 = P['sembol_kutu']
    red = []
    for ax in np.arange(365, 250, -1.0):
        by = ax / el['oran']
        cy = TEPE_Y + by                                    # tepe merkez cizgisi delik merkezinden gecer
        ha, hb = halka_alfa(pp, cy, ax)
        k = ax / el['a']
        sem = o3.sembol_yerlestir(ana, (sx1 - sx0) * k, CX, cy + ((sy0 + sy1) / 2 - el['cy']) * (by / el['b']))
        E = dict(Eyazi); E['halka'] = (None, ha, 0, 0); E['sembol'] = sem
        M, yb, cak, ok = kapi(E)
        if ok:
            return dict(E=E, M=M, yasak=yb, cak=cak, halka=hb, alt=alt, red_son=red[-3:])
        red.append(dict(ax=float(ax), yasak={k_: v for k_, v in yb.items() if v}, cak=cak[:4]))
    return None


def yerlesim_B(ana, T, kucuk):
    g = 0.70
    alt, Eyazi, ust = alt_sinir(T, kucuk, g, g)
    if alt is None:
        return None
    c = T['cap']
    x0, y0, x1, y1 = o1.bbox(ana[..., 3], 0.5)
    for w in np.arange(700, 250, -2.0):
        h = w * (y1 - y0) / (x1 - x0)
        cy_ust = UST_YASAK + GLOW_R + 2 + h / 2
        cy_alt = ust - g * c - h / 2
        if cy_alt < cy_ust:
            continue
        sem = o3.sembol_yerlestir(ana, w, CX, cy_ust)
        E = dict(Eyazi); E['sembol'] = sem
        M, yb, cak, ok = kapi(E)
        if ok:
            return dict(E=E, M=M, yasak=yb, cak=cak, alt=alt, sembol_w=float(w), bos_dikey=round(float(cy_alt - cy_ust), 1))
    return None


# ----------------------------------------------------------------------------------------------- boyama + butunlesme
def boya(Y, model, zemin, kazanc, td, doku_guc, doku_kapali=False, butunlesme=True):
    E, M = Y['E'], Y['M']
    z = zemin.astype(np.float32)
    out = z.copy()
    zort = z.reshape(-1, 3).mean(0)
    zL = lum(z)
    doku = zL - cv2.GaussianBlur(zL, (0, 0), 6.0)
    doku_b = np.full_like(zL, 128.0) if doku_kapali else np.clip(128 + o3.DOKU_GENLIK * doku / max(float(doku.std()), 1e-3), 0, 255)
    tum = np.maximum.reduce([M[k] for k in M])
    if butunlesme and DIS_GOLGE is not None:
        gm = cv2.GaussianBlur(tum, (0, 0), DIS_GOLGE['sigma'])
        gm = cv2.warpAffine(gm, np.float32([[1, 0, DIS_GOLGE['kayma']], [0, 1, DIS_GOLGE['kayma']]]), (N, N))
        out = out * (1 - DIS_GOLGE['opak'] * gm[..., None] * (1 - DIS_GOLGE['koyu']))
    if butunlesme and GLOW_OPAK > 0:
        # 1 sicak altin isik tasmasi (disa, 4-10 px): yalniz ogelerin disinda, GLOW_R icinde; screen
        g = cv2.GaussianBlur(tum, (0, 0), GLOW_SIGMA)
        bolge = cv2.dilate((tum > 0.02).astype(np.uint8), GLOW_K).astype(np.float32)
        g = np.clip(g * bolge * (1 - tum), 0, 1)[..., None] * GLOW_OPAK
        out = out + (255 - out) * (GLOW_RGB / 255.0) * g
    renkler = {}
    for ad, (rgb, a, x, y) in E.items():
        if ad == 'sembol':
            col = rgb
        elif ad == 'halka':
            col = np.broadcast_to(td.renk(np.full((1, 1), model.Lmed, np.float32), model.egri), (N, N, 3)).astype(np.float32)
        elif ad.startswith('kucuk'):
            col, _ = model.boya(lum(rgb), a)
        else:
            col, _ = model.duz(a)
        cc = np.zeros((N, N, 3), np.float32)
        if ad == 'halka':
            cc = col.copy()
        else:
            h, w = a.shape
            xa, ya, xb, yb = max(0, x), max(0, y), min(N, x + w), min(N, y + h)
            cc[ya:yb, xa:xb] = col[ya - y:yb - y, xa - x:xb - x]
        renkler[ad] = cc
    koyu_t = z * o3.GOLGE_KOYU
    acik_t = np.clip(z * 1.9 + 18, 0, 255)
    for ad in E:
        cc = renkler[ad] * kazanc
        if RENK_DONUSUM is not None:
            cc = RENK_DONUSUM(cc, model)
        L = lum(cc)
        m = M[ad]
        # golge tonu (inceleme 1): ogenin kendi murekkep ortancasindan (Lref) en az %30 koyu tonlarda zemin rengi TINT_GUC (%28),
        # aradaki tonlarda dogrusal. Duz renkli ogelerde (halka, isim, tarih, logo) golge tonu yoktur: w = 0 (raporda).
        ink = m > 0.5
        Lref = float(np.median(L[ink])) if ink.any() else 1.0
        w = (np.clip((0.95 * Lref - L) / max(0.25 * Lref, 1), 0, 1) * TINT_GUC)[..., None]
        tint = zort / max(float(lum(zort[None])[0]), 1.0) * L[..., None]
        cc = cc * (1 - w) + tint * w
        if TINT_OLC is not None and ink.any():
            gt = ink & (L < 0.70 * Lref)
            TINT_OLC[ad] = dict(golge_tonu_payi_yuzde=round(float(gt.sum() / ink.sum() * 100), 1),
                                golge_tonunda_ort_w=round(float(w[..., 0][gt].mean()), 3) if gt.any() else None,
                                tum_murekkep_ort_w=round(float(w[..., 0][ink].mean()), 3))
        dg = doku_guc.get(ad, 0.0) if isinstance(doku_guc, dict) else doku_guc
        cc = cc * (1 - dg) + o3.overlay(np.clip(cc, 0, 255), doku_b[..., None]) * dg
        if SON_KIRP is not None:
            cc = SON_KIRP(cc)
        if butunlesme and (GOMU_KOYU > 0 or GOMU_ACIK > 0):
            # 2 gomulu kenar: oge ici, sol ust kenar koyu (sol ust komsu oge disi), sag alt kenar acik
            sh = lambda a_, d: cv2.warpAffine(a_, np.float32([[1, 0, d], [0, 1, d]]), (N, N))
            ust_sol = np.clip(m - sh(m, GOMU_KAYMA), 0, 1)          # ogenin sol ust ic kenari
            alt_sag = np.clip(m - sh(m, -GOMU_KAYMA), 0, 1)         # sag alt ic kenari
            ust_sol = cv2.GaussianBlur(ust_sol, (0, 0), GOMU_SIGMA) * m
            alt_sag = cv2.GaussianBlur(alt_sag, (0, 0), GOMU_SIGMA) * m
            kk = GOMU_YAZI if ad in YAZI_OGE else 1.0
            gk, ga = GOMU_KOYU * kk, GOMU_ACIK * kk
            cc = cc * (1 - gk * ust_sol[..., None]) + koyu_t * gk * ust_sol[..., None]
            cc = cc * (1 - ga * alt_sag[..., None]) + acik_t * ga * alt_sag[..., None]
        out = out * (1 - m[..., None]) + np.clip(cc, 0, 255) * m[..., None]
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def doku_oge(rgb, rgb0, M):
    L1, L0 = lum(rgb.astype(np.float32)), lum(rgb0.astype(np.float32))
    r = {}
    for k, m in M.items():
        ic = m > 0.9
        if ic.sum() > 20:
            r[k] = round(float((L1[ic] - L0[ic]).std() / max(float(L0[ic].mean()), 1) * 100), 2)
    return r


def doku_ayarla(Y, model, z, kazanc, td, taban=0.20, hedef=5.0):
    """oge basina doku katman opakligi: gorunen %5 (inceleme 4: havuzlanmis olcu oge bazinda tutmuyordu). Overlay karisimi
    opakliga dogrusal; taban olcum + bir duzeltme."""
    r0 = boya(Y, model, z, kazanc, td, 0.0, doku_kapali=True)
    dg = {k: taban for k in Y['M']}
    for _ in range(2):
        olc = doku_oge(boya(Y, model, z, kazanc, td, dg), r0, Y['M'])
        dg = {k: float(np.clip(dg[k] * hedef / max(olc.get(k, hedef), 0.2), 0.03, 0.8)) for k in dg}
    return dg


def goruntu_yasak(rgb, zemin, halka_m):
    fark = np.abs(rgb.astype(np.float32) - zemin.astype(np.float32)).max(2) > 1.0
    hb = cv2.dilate((halka_m > 0.02).astype(np.uint8), GLOW_K) > 0 if halka_m is not None else np.zeros((N, N), bool)
    yy, xx = np.nonzero(fark)
    r = np.hypot(xx + 0.5 - CX, yy + 0.5 - CY)
    hl = hb[yy, xx]
    yb = dict(guvenli_daire_disi=int((r > GUV_R).sum()),
              delik_halka_disi=int(((np.hypot(xx + 0.5 - DELIK[0], yy + 0.5 - DELIK[1]) <= DELIK[2]) & ~hl).sum()),
              y_221_ustu_halka_disi=int(((yy < UST_YASAK) & ~hl).sum()))
    nh = ~hl
    return yb, dict(gercek_pay=round(float(GUV_R - r.max()), 1),
                    ust_y_halka_disi=int(yy[nh].min()) if nh.any() else None,
                    delige_uzaklik_halka_disi=round(float(np.hypot(xx[nh] + 0.5 - DELIK[0], yy[nh] + 0.5 - DELIK[1]).min() - DELIK[2]), 1) if nh.any() else None)


def glow_olc(rgb, rgb0, tum):
    """isik tasmasi: ogelerin disinda butunlesmeli - butunlesmesiz luma farki > 1 olan en uzak mesafe (px)."""
    d = lum(rgb.astype(np.float32)) - lum(rgb0.astype(np.float32))
    dis = tum < 0.02
    dt = cv2.distanceTransform(dis.astype(np.uint8), cv2.DIST_L2, 5)
    m = dis & (d > 1.0)
    bant = dis & (dt >= 1) & (dt <= 4)
    return dict(uzanim_px=round(float(dt[m].max()), 1) if m.any() else 0.0, p95_px=round(float(np.percentile(dt[m], 95)), 1) if m.any() else 0.0,
                luma_artis_1_4px_ortanca=round(float(np.median(d[bant])), 2) if bant.any() else 0.0)


def onizleme(liste, ara=24):
    """76 mm kesim dairesi (r KESIM_R) disi beyaz, delik (ic r 25) beyaz; 300 dpi gercek boy."""
    yy, xx = np.mgrid[0:N, 0:N]
    al = np.clip(KESIM_R - np.hypot(xx - CX + 0.5, yy - CY + 0.5) + 0.5, 0, 1)
    al = al * np.clip(np.hypot(xx + 0.5 - DELIK[0], yy + 0.5 - DELIK[1]) - DELIK_IC + 0.5, 0, 1)
    al = al[..., None]
    y0, y1 = max(0, int(CY - KESIM_R) - 2), min(N, int(CY + KESIM_R) + 3)
    x0, x1 = max(0, int(CX - KESIM_R) - 2), min(N, int(CX + KESIM_R) + 3)
    ims = [np.round(rgb * al + 255 * (1 - al)).astype(np.uint8)[y0:y1, x0:x1] for rgb in liste]
    o = np.full((max(i.shape[0] for i in ims), sum(i.shape[1] for i in ims) + ara * (len(ims) - 1), 3), 255, np.uint8)
    x = 0
    for i in ims:
        o[:i.shape[0], x:x + i.shape[1]] = i; x += i.shape[1] + ara
    return Image.fromarray(o, 'RGB')


def main():
    global YASAK, GLOW_K
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    K, O = Path(a.kaynak), Path(a.cikti)
    O.mkdir(parents=True, exist_ok=True)
    YASAK = yasak_m()
    GLOW_K = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * GLOW_R + 1,) * 2)
    o3.YASAK = YASAK
    spec = importlib.util.spec_from_file_location('tek_doku', K / 'tek_doku.py')
    td = importlib.util.module_from_spec(spec); spec.loader.exec_module(td)
    R = {'kaynak_sha256': {f.name: o1.sha(f) for f in sorted(K.iterdir()) if f.is_file()},
         'sabit': dict(guvenli_r=GUV_R, pay=PAY, delik=DELIK, delik_ic=DELIK_IC, ust_yasak=f'y < {UST_YASAK}', kesim_r=round(KESIM_R, 1),
                      eski=ESKI, kaynak='Printful resmi 900 Circle sablonu (Serdar), Merkez olcumu 2 Kas; kesim r = 38 mm x 11.81 px/mm (hesap)', tepe_y=TEPE_Y, govde_med=GOVDE_MED,
                       govde_min=GOVDE_MIN, uc_bolge=UC_BOLGE, logo_h=LOGO_H,
                       gomu=dict(koyu=GOMU_KOYU, acik=GOMU_ACIK, kayma=GOMU_KAYMA, sigma=GOMU_SIGMA),
                       isik_tasmasi=dict(sigma=GLOW_SIGMA, opak=GLOW_OPAK, r=GLOW_R, rgb=GLOW_RGB.tolist()), tint=TINT_GUC, gomu_yazi=GOMU_YAZI)}
    pp = poster_profil(K / 'HALKA_BLUE_16x20.png')
    el = pp['el']
    R['poster'] = dict(elips=dict(yatay_yari=round(el['a'], 1), dikey_yari=round(el['b'], 1), oran=round(el['oran'], 4)),
                       acik_aci=[pp['t1'], pp['t2']], yay_px=round(pp['L']), govde_medyan=round(pp['med'], 2), govde_min=round(pp['govde_min'], 2),
                       tepe=round(pp['tepe'], 2), tepe_aci=pp['tepe_aci'], uc_oran_sag_sol=pp['tablo_uc_sag_sol'])
    ana = np.asarray(Image.open(K / 'CANCER_LIBRA_ana.png').convert('RGBA'), np.float32)
    ana[..., 3] /= 255.0
    ana = o1.kirp(ana, ana[..., 3], pad=2)
    if ana.shape[1] > 1600:
        r_, a_ = o1.rgba_olcek(ana, 1600 / ana.shape[1]); ana = np.dstack([r_, a_])
    lsrc = logo_kaynak(K / 'LOGO_1.png')

    def kucuk(burc, cap, h_ratio):
        g = np.asarray(Image.open(K / f'{burc}_symbol_gold.png').convert('RGBA'), np.float32)
        g[..., 3] /= 255.0
        g = o1.kirp(g, g[..., 3], pad=2)
        gx0, gy0, gx1, gy1 = o1.bbox(g[..., 3], 0.5)
        return o1.rgba_olcek(g, h_ratio * cap / (gy1 - gy0))

    def metinler(cap):
        h = LOGO_H * cap
        k = h / lsrc.shape[0]
        la = np.clip(cv2.resize(lsrc, (max(1, int(round(lsrc.shape[1] * k))), max(1, int(round(h)))), interpolation=cv2.INTER_AREA), 0, 1)
        return dict(isim1=o1.metin_alfa('EMILY', K / 'Cinzel.ttf', cap, 500), isim2=o1.metin_alfa('JAMES', K / 'Cinzel.ttf', cap, 500),
                    tarih=o1.metin_alfa('14 JUNE 2025', K / 'EBGaramond-Italic.ttf', P['tagline_T'] / P['cap'] * cap, None, ref='T'),
                    sonsuz=la, cap=cap)
    zeminler = {ad: o1.zemin_canva(K / zf) for ad, zf in STILLER}
    sonuc = {}
    for yer in ('HALKALI', 'HALKASIZ'):
        secim = None
        for olcek in (1.0, 1.08, 1.15):
            cap = CAP0 * olcek
            T = metinler(cap)
            kc = {'sol': kucuk('cancer', cap, P['kucuk_sol_h'] / P['cap']), 'sag': kucuk('libra', cap, P['kucuk_sag_h'] / P['cap'])}
            Y = yerlesim_A(pp, ana, T, kc) if yer == 'HALKALI' else yerlesim_B(ana, T, kc)
            if Y is None:
                print(yer, 'yerlesim yok, olcek', olcek, flush=True); break
            sx = Y['E']['sembol']
            model = o1.Model(td, sx[0], sx[1], 4800 * (o1.bbox(sx[1], 0.5)[2] - o1.bbox(sx[1], 0.5)[0]) / 2084)
            tumm = np.maximum.reduce([Y['M'][k] for k in Y['M']]) > 0.9
            stil_ok, stil = True, {}
            for ad, _ in STILLER:
                z = zeminler[ad]
                sec = None
                for kazanc in (1.0, 1.04, 1.08, 1.12, 1.16, 1.20):
                    dg_sec = doku_ayarla(Y, model, z, kazanc, td)
                    rgb = boya(Y, model, z, kazanc, td, dg_sec)
                    ok = {k: o3.okunurluk(rgb, z, Y['M'][k]) for k in ('isim1', 'isim2', 'tarih')}
                    en = min(min(v['bant_1_12']['kati_ortanca'], v['bant_1_12']['kati_acik5']) for v in ok.values())
                    if en >= HEDEF:
                        sec = kazanc; break
                if sec is None:
                    sec = kazanc; stil_ok = False
                sec = (sec, rgb, ok, en, dg_sec)
                stil[ad] = sec
            secim = dict(Y=Y, T=T, olcek=olcek, stil=stil, model=model)
            if stil_ok:
                break
            print(yer, 'olcek', olcek, 'kontrast tutmadi', {k: v[3] for k, v in stil.items()}, flush=True)
        if secim is None:
            print('FAIL', yer, flush=True); return 1
        sonuc[yer] = secim
        Y = secim['Y']
        sb = o1.bbox(Y['M']['sembol'], 0.5)
        r = dict(yazi_olcek=secim['olcek'], isim_buyuk_harf_mm=round(secim['T']['cap'] * MM, 2),
                 tarih_buyuk_harf_mm=round(P['tagline_T'] / P['cap'] * secim['T']['cap'] * MM, 2),
                 sembol_px=[sb[2] - sb[0], sb[3] - sb[1]], sembol_mm=[round((sb[2] - sb[0]) * MM, 2), round((sb[3] - sb[1]) * MM, 2)],
                 yasak_piksel=Y['yasak'], cakisma=Y['cak'], red_son=Y.get('red_son'),
                 logo=logo_olc(lsrc, secim['T']['sonsuz']))
        for ad in Y['M']:
            b = o1.bbox(Y['M'][ad], 0.5)
            r.setdefault('oge', {})[ad] = dict(kutu=list(b), w_mm=round((b[2] - b[0]) * MM, 2), h_mm=round((b[3] - b[1]) * MM, 2))
        if yer == 'HALKALI':
            hb = Y['halka']
            ho = halka_olc(Y['M']['halka'], hb, pp)
            hm = Y['M']['halka']
            hx = np.nonzero(hm.max(0) > 0.5)[0]; hyy = np.nonzero(hm.max(1) > 0.5)[0]
            ys_, xs_ = np.nonzero(hm > 0.5)
            sol, sag = xs_ < CX, xs_ > CX
            r['halka'] = dict(yatay_yari=round(hb['ax'], 1), dikey_yari=round(hb['by'], 1), oran=round(hb['ax'] / hb['by'], 4), merkez_y=round(hb['cy'], 1),
                              tepe_merkez_cizgisi_y=round(hb['cy'] - hb['by'], 1), delik_merkezi=[DELIK[0], DELIK[1]],
                              dis_genislik_px=int(hx.max() - hx.min() + 1), dis_yukseklik_px=int(hyy.max() - hyy.min() + 1),
                              dis_genislik_V3_kazanc_yuzde=round(((hx.max() - hx.min() + 1) / V3_HALKA_W - 1) * 100, 1),
                              simetri=dict(sol_piksel=int(sol.sum()), sag_piksel=int(sag.sum()),
                                           sol_x_min=int(xs_.min()), sag_x_max=int(xs_.max()),
                                           sol_pay=round(float(CX - xs_.min()), 1), sag_pay=round(float(xs_.max() + 1 - CX), 1)),
                              **ho)
            r['sembol_V3_kazanc_yuzde'] = round(((sb[2] - sb[0]) / V3_SEMBOL_W - 1) * 100, 1)
        else:
            r['bos_dikey'] = Y.get('bos_dikey')
            r['sembol_V3_kazanc_yuzde'] = round(((sb[2] - sb[0]) / 459 - 1) * 100, 1)
        tumm = np.maximum.reduce([Y['M'][k] for k in Y['M']])
        for ad, (kazanc, rgb, ok, en, dg) in secim['stil'].items():
            o1.kaydet(rgb, O / f'{ad}_{yer}_954.png')
            gy, gb = goruntu_yasak(rgb, zeminler[ad], Y['M'].get('halka'))
            rgb0 = boya(Y, secim['model'], zeminler[ad], kazanc, td, 0.0, doku_kapali=True)
            rgbb = boya(Y, secim['model'], zeminler[ad], kazanc, td, dg, butunlesme=False)
            global TINT_OLC
            TINT_OLC = {}
            boya(Y, secim['model'], zeminler[ad], kazanc, td, dg)
            tolc, TINT_OLC = TINT_OLC, None
            dk = doku_oge(rgb, rgb0, Y['M'])
            r.setdefault('stil', {})[ad] = dict(altin_kazanc=kazanc, doku_katman={k: round(v, 3) for k, v in dg.items()}, en_kotu_kati_1_12=en,
                                                hedef_tuttu=en >= HEDEF, okunurluk=ok, goruntu_yasak=gy, goruntu=gb,
                                                doku_gorunen=dict(oge_goreli_std_yuzde=dk, en_az=min(dk.values()), en_cok=max(dk.values()),
                                                                  yontem='oge basina (alfa > 0.9): dokulu - dokusuz luma std / dokusuz luma ortalamasi'),
                                                golge_tonu=tolc, isik_tasmasi=glow_olc(rgb, rgbb, tumm))
        R[yer] = r
        print(yer, json.dumps({k: r[k] for k in ('yazi_olcek', 'sembol_px', 'sembol_V3_kazanc_yuzde', 'yasak_piksel', 'cakisma')}), flush=True)
        if yer == 'HALKALI':
            print('HALKA', json.dumps({k: v for k, v in r['halka'].items() if k not in ('poster_uc_oran',)})[:1400], flush=True)
        print(yer, 'LOGO', json.dumps(r['logo']), flush=True)
        print(yer, 'stil', json.dumps({k: (v['altin_kazanc'], v['en_kotu_kati_1_12'], v['goruntu']['gercek_pay'],
                                           (v['doku_gorunen']['en_az'], v['doku_gorunen']['en_cok']), (v['isik_tasmasi']['p95_px'], v['isik_tasmasi']['uzanim_px']), sum(v['goruntu_yasak'].values()))
                                       for k, v in r['stil'].items()}), flush=True)
    R['logo_oneri_1'] = logo_oneri(lsrc, R['HALKALI']['logo']['hedef_px'][0])
    lg = R['HALKALI']['logo']
    R['logo_oneriler'] = [
        dict(no=1, ad='kucuk boy logo (Merkez onerisi)', icerik='sekil birebir, yalniz 2 px altindaki ince cizgiler elle 2 px (0.17 mm) yapilir; '
             'tek tip genisletme (morfoloji) uygun degil: 2 px icin kaynakta 7 px genisletme gerekir, IoU 0.53, 14 sahte ic bosluk (logo_oneri_1)'),
        dict(no=2, ad='logo isim satirinda daha buyuk', icerik=f'2 px icin genislik p1 {lg["iki_px_icin_gereken_genislik_p1"]} px (ornament 954 px); '
             'hicbir boyda tutmaz, yalniz kalin govde (medyan 15 px kaynak) okunur'),
        dict(no=3, ad='sadelestirilmis isaret', icerik='logonun dis silueti dolu (ic sac cizgileri yok) ya da V3 sonsuzu; sekil degisir, Serdar onayi gerekir')]
    s1 = onizleme([sonuc['HALKALI']['stil'][a][1] for a, _ in STILLER])
    s2 = onizleme([sonuc['HALKASIZ']['stil'][a][1] for a, _ in STILLER])
    o = Image.new('RGB', (max(s1.width, s2.width), s1.height + s2.height + 24), 'white')
    o.paste(s1, (0, 0)); o.paste(s2, (0, s1.height + 24))
    o.save(O / 'ONIZLEME_76mm.png', dpi=(300, 300))
    h = R['HALKALI']['halka']
    g = dict(yasak_0=all(sum(R[y]['yasak_piksel'].values()) == 0 for y in ('HALKALI', 'HALKASIZ')),
             cakisma_0=all(not R[y]['cakisma'] for y in ('HALKALI', 'HALKASIZ')),
             kontrast=all(v['hedef_tuttu'] for y in ('HALKALI', 'HALKASIZ') for v in R[y]['stil'].values()),
             goruntu_yasak_0=all(sum(v['goruntu_yasak'].values()) == 0 for y in ('HALKALI', 'HALKASIZ') for v in R[y]['stil'].values()),
             halka_tepe_delik=abs(h['tepe_merkez_cizgisi_y'] - DELIK[1]) < 0.6,
             halka_govde=h['govde_min'] >= 4.0,
             doku_4_6=all(DOKU_HEDEF[0] <= v['doku_gorunen']['en_az'] and v['doku_gorunen']['en_cok'] <= DOKU_HEDEF[1] for y in ('HALKALI', 'HALKASIZ') for v in R[y]['stil'].values()),
             isik_4_10=all(4 <= v['isik_tasmasi']['p95_px'] and v['isik_tasmasi']['uzanim_px'] <= 10 for y in ('HALKALI', 'HALKASIZ') for v in R[y]['stil'].values()))
    g = {k: bool(v) for k, v in g.items()}
    R['kapi'] = g
    R['bilgi_kapisi_degil'] = dict(logo_en_ince_2px=R['HALKALI']['logo']['hedefte_geometrik_en_ince'] >= 2.0,
                                   not_='logo birebir korununca 2 px hedefi tutmaz; olcum ve 3 oneri raporda')
    (O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=float))
    print('KAPI', json.dumps(g), 'PASS' if all(g.values()) else 'FAIL', flush=True)
    return 0 if all(g.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
