#!/usr/bin/env python3
"""Ornament ornek V3 (Merkez gorevi STIL3_V3, Serdar onayi 2 Kas 2026). Etsy / Printful yazma yok; toplu uretim yok.
3 zemin (Drive TEMP/ORNAMENT_ZEMIN3_20261102/V2: RUBY, SAPPHIRE, EMERALD; 1264 -> 954 esit olcek, kirpma yok) x 2 yerlesim:
  A HALKALI : poster halkasi (HALKA_BLUE_16x20.png) olculen ELIPS oraniyla (yatay / dikey yari eksen), Printful guvenli dairesinin izin verdigi
              en buyuk boyutta. Yazi blogu (kucuk semboller, EMILY ∞ JAMES, tarih) alta sabitlenir, halkanin acik altina girer. Halka
              genisligi = max(poster profili x olcek, govde tabani); uclar son UC_L px'te dogrusal olarak 0'a (keskin; kuyruk yok).
              Kapsama 4x ornekleme ile (1 px alti sisme yok).
  B HALKASIZ: sembol olabildigince buyuk ve yukarida; yazilar rahat aralikli.
Butunlesme (Serdar "yapistirilmis gibi"): tum altin ogelere
  - golge: zeminin kendi koyu tonu (zemin x GOLGE_KOYU), isiga ters (sag alt) GOLGE_KAYMA px, sigma GOLGE_SIGMA, opaklik GOLGE_OPAK
  - doku: zeminin yuksek gecirgen dokusu altina soft light ile DOKU_GUC
  - golge tonlarina zemin rengi: altin lumasi Lmed altinda zemin ortalama rengiyle en fazla TINT_GUC karisim
  - isik yonu: tek doku kabartmasi ana sembolden olculur, uc zeminde ayni (sol ust)
Okunurluk: hale YOK. Kontrast olcumu murekkebin 1-12 px cevresi (ortanca ve en acik %5). Hedef >= 4.5: once tum altina ortak ton kazanci
(tek doku birligi korunur), yetmezse yazi boyu (en fazla x1.15).
Kapilar: yasak bolgeye (guvenli daire 760.6 disi - PAY, delik, centik) tasan piksel 0; cakisma 0; sonsuz en ince >= 4 px (4x ornekli mesafe
donusumu sirtinin EN KUCUGU; kaynak iki ici sac cizgisi bu boyda dis cizgiyle birlesir: kapi = 2 goz, 1 bilesen); halka govdesi >= 4 px; uc: son 20 px'te genislik >= 1.5'ten 0'a.
Kullanim: ornament_ornek3.py --kaynak DIR --cikti DIR"""
import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

_d = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('ornek1', _d / 'ornament_ornek.py'); o1 = importlib.util.module_from_spec(_s); _s.loader.exec_module(o1)
_s = importlib.util.spec_from_file_location('ornek2', _d / 'ornament_ornek2.py'); o2 = importlib.util.module_from_spec(_s); _s.loader.exec_module(o2)
N, C, MM, LUMA, RV, P = o1.N, o1.C, o1.MM, o1.LUMA, o1.RV, o1.P
GUV_R = 760.6 / 2
PAY = 3                                   # guvenli daireye en az pay (px)
DELIK = (476.7, 163.9, 56.6 / 2)
CENTIK = (422.7, 535.0, 216.9)            # x0, x1, alt y (EK_OLCUM.json sablon; genislik yaklasik 110 px)
UST_MIN = 222.0                           # icerik ust siniri (centik alti 216.9 + 5)
CAP0 = 28.07                              # isim buyuk harf (v1 / V2)
GOVDE = 4.5                               # halka govde tabani (px; istek >= 4)
TEPE = 9.0                                # poster profili tepe genisligi
UC_L = 45.0                               # uc sonum uzunlugu (px yay)
SONSUZ_MIN = 4.0
HEDEF = 4.5
GOLGE_KAYMA, GOLGE_SIGMA, GOLGE_OPAK, GOLGE_KOYU = 1.5, 1.2, 0.55, 0.45
DOKU_GUC, TINT_GUC = 0.08, 0.18
STILLER = (('RUBY_GOLD', 'RUBY_1264.png'), ('SAPPHIRE_GOLD', 'SAPPHIRE_1264.png'), ('EMERALD_GOLD', 'EMERALD_1264.png'))
V2_SEMBOL_W = 378


def lum(x):
    return x @ LUMA


# ----------------------------------------------------------------------------------------------- halka (elips)
def elips_olc(f):
    a = np.asarray(Image.open(f), np.float32) / 255.0
    ys, xs = np.nonzero(a > 0.5)
    X, Y = xs.astype(float), ys.astype(float)
    c, *_ = np.linalg.lstsq(np.c_[X ** 2, Y ** 2, X, Y], np.ones_like(X), rcond=None)
    A, B, Cc, D = c
    x0, y0 = -Cc / (2 * A), -D / (2 * B)
    F = 1 + A * x0 ** 2 + B * y0 ** 2
    ax, by = float(np.sqrt(F / A)), float(np.sqrt(F / B))
    hp = o2.halka_profili(f)
    return dict(cx=float(x0), cy=float(y0), a=ax, b=by, oran=ax / by, hp=hp, uc=hp['bos'])


def halka_alfa(el, cy, ax, ss=4):
    """merkez (C, cy), yatay yari eksen ax (dikey = ax / oran). Doner alfa (N x N), genislik fonksiyonu bilgisi."""
    by = ax / el['oran']
    hp = el['hp']
    k = ax / el['a']
    th_e = el['uc']                        # [44, 136]: acik aralik (0 sag, 90 asagi)
    r_ort = (ax + by) / 2
    n = N * ss
    out = np.zeros((N, N), np.float32)
    y0 = max(0, int(cy - by - 20)); y1 = min(N, int(cy + by + 20))
    yy, xx = np.mgrid[y0 * ss:y1 * ss, 0:n].astype(np.float32)
    px = (xx + 0.5) / ss; py = (yy + 0.5) / ss
    dx, dy = px - C, py - cy
    rho = np.sqrt((dx / ax) ** 2 + (dy / by) ** 2)
    rloc = np.sqrt(dx ** 2 + dy ** 2) / np.maximum(rho, 1e-6)
    d = (rho - 1) * rloc
    ang = (np.degrees(np.arctan2(dy, dx)) + 360) % 360
    w_post = np.interp(ang, hp['th'], hp['w'], period=360) / hp['w_max'] * TEPE
    # uca yay uzakligi (px): acik araligin iki ucundan
    acik = (ang > th_e[0]) & (ang < th_e[1])
    s1 = np.radians((th_e[0] - ang) % 360) * r_ort            # sag uca (44) saat yonu tersine
    s2 = np.radians((ang - th_e[1]) % 360) * r_ort            # sol uca (136)
    s = np.minimum(s1, s2)
    # govde: poster profili ile taban GOVDE'nin buyugu; uc bolgesi (son UC_L px yay): GOVDE'den 0'a dogrusal (keskin uc, kuyruk yok)
    w = np.where(acik, 0.0, np.where(s < UC_L, GOVDE * s / UC_L, np.maximum(w_post, GOVDE)))
    a_hr = ((np.abs(d) <= w / 2) & (w > 0)).astype(np.float32)
    out[y0:y1] = cv2.resize(a_hr, (N, y1 - y0), interpolation=cv2.INTER_AREA)
    return out, dict(ax=ax, by=by, cy=cy, k=k, r_ort=r_ort)


def halka_olc(a, cy, ax, by, th_e, r_ort):
    """aci basina radyal kapsama genisligi (alfa toplami / yay) ve uca yay uzakligina gore genislik."""
    yy, xx = np.mgrid[0:N, 0:N]
    dx, dy = xx + 0.5 - C, yy + 0.5 - cy
    ang = (np.degrees(np.arctan2(dy, dx)) + 360) % 360
    sat = []
    for b0 in np.arange(0, 360, 1.0):
        m = (ang >= b0) & (ang < b0 + 1) & (a > 0.01)
        if not m.any():
            continue
        r = float(np.median(np.hypot(dx[m], dy[m])))
        sat.append((b0 + 0.5, float(a[m].sum() / (np.radians(1) * r))))
    W = {round(t, 1): w for t, w in sat}
    govde = [w for t, w in sat if (t < th_e[0] - (UC_L / r_ort) * 57.3 - 1) or (t > th_e[1] + (UC_L / r_ort) * 57.3 + 1)]
    # uc profili: uca yay uzakligi s (px) -> genislik
    uc = {}
    for t, w in sat:
        s1 = math.radians((th_e[0] - t) % 360) * r_ort
        s2 = math.radians((t - th_e[1]) % 360) * r_ort
        if s1 <= 60:
            uc.setdefault('sag', []).append((round(s1, 1), round(w, 2)))
        if s2 <= 60:
            uc.setdefault('sol', []).append((round(s2, 1), round(w, 2)))
    for k in uc:
        uc[k] = sorted(uc[k])
    return dict(govde_min=round(min(govde), 2), govde_max=round(max(govde), 2), uc=uc,
                aci_genislik={str(t): round(w, 2) for t, w in sat if int(t) % 10 == 0 or abs(t - th_e[0]) < 12 or abs(t - th_e[1]) < 12})


# ----------------------------------------------------------------------------------------------- sonsuz (>= 4 px)
def sonsuz_kalin(son_hr, gen_px, hedef=SONSUZ_MIN):
    """yuksek cozunurlukte genisletilir, sonra hedef genislige esit oranla indirilir (genislik sabit). En ince = 4x ornekli ikili
    goruntude mesafe donusumu sirti (yerel en buyuk) 2. yuzdeligi x 2 / 4. Delik (ic bosluk) sayisi korunmali."""
    def delik_say(m):
        cont, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        return int(sum(1 for h in (hier[0] if hier is not None else []) if h[3] >= 0))
    m0 = (son_hr > 0.5).astype(np.uint8)
    d0 = delik_say(m0)
    s_hr = gen_px / son_hr.shape[1]
    for adim in range(0, 40):
        r = adim * 0.25 / s_hr
        hr = son_hr if r == 0 else cv2.dilate(son_hr, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(round(r)) * 2 + 1,) * 2))
        hr = o1.kirp(hr, hr, 0)
        a = o1.olcek(hr, gen_px / hr.shape[1])
        a4 = cv2.resize(hr, (a.shape[1] * 4, a.shape[0] * 4), interpolation=cv2.INTER_AREA)
        m4 = (a4 > 0.5).astype(np.uint8)
        dt = cv2.distanceTransform(m4, cv2.DIST_L2, 5)
        sirt = (dt > 0) & (cv2.dilate(dt, np.ones((3, 3), np.uint8)) <= dt)
        # en ince: sirt piksellerinde 2 x mesafe; kenar yumusatmasi nedeniyle 4x ornekte merkez pikseli sayilmaz (2 x (dt - 0.5) / 4)
        ince = float(2 * (dt[sirt].min() - 0.5) / 4)
        ince_p2 = float(2 * (np.percentile(dt[sirt], 2) - 0.5) / 4)
        m1 = (a > 0.5).astype(np.uint8)
        dl = delik_say(m1)
        bil = cv2.connectedComponents(m1, 8)[0] - 1
        if ince >= hedef:
            return a, dict(genisletme_hedef_px=adim * 0.25, en_ince_px=round(ince, 2), en_ince_p2_px=round(ince_p2, 2), delik=dl,
                           delik_kaynak=d0, bilesen=int(bil), gecti=(dl == 2 and bil == 1))
    return a, dict(genisletme_hedef_px=adim * 0.25, en_ince_px=round(ince, 2), delik=dl, delik_kaynak=d0, bilesen=int(bil), gecti=False)


# ----------------------------------------------------------------------------------------------- yasak bolge
def yasak():
    yy, xx = np.mgrid[0:N, 0:N]
    r = np.hypot(xx + 0.5 - C, yy + 0.5 - C)
    dis = r > GUV_R - PAY
    delik = np.hypot(xx + 0.5 - DELIK[0], yy + 0.5 - DELIK[1]) <= DELIK[2] + 2
    centik = (xx >= CENTIK[0] - 2) & (xx <= CENTIK[1] + 2) & (yy <= CENTIK[2] + 2)
    ust = yy < UST_MIN
    return dict(guvenli_disi=dis, delik=delik, centik=centik, ust_cizgi=ust)


YASAK = None


# ----------------------------------------------------------------------------------------------- yerlesim
def metinler(K, cap):
    son = np.load(K / 'alfa_ogeler.npz')['sonsuz'].astype(np.float32) / 255.0
    son = o1.kirp(son, son)
    sa, sb = sonsuz_kalin(son, P['sonsuz_w'] / P['cap'] * cap)
    return dict(isim1=o1.metin_alfa('EMILY', K / 'Cinzel.ttf', cap, 500), isim2=o1.metin_alfa('JAMES', K / 'Cinzel.ttf', cap, 500),
                tarih=o1.metin_alfa('14 JUNE 2025', K / 'EBGaramond-Italic.ttf', P['tagline_T'] / P['cap'] * cap, None, ref='T'),
                sonsuz=sa, sonsuz_bilgi=sb, cap=cap)


def maske_yaz(a, x, y):
    m = np.zeros((N, N), np.float32)
    h, w = a.shape
    xa, ya, xb, yb = max(0, x), max(0, y), min(N, x + w), min(N, y + h)
    if xb > xa and yb > ya:
        m[ya:yb, xa:xb] = a[ya - y:yb - y, xa - x:xb - x]
    return m, int((a > 0.02).sum() - (m > 0.02).sum())


def yazi_blogu(T, kucuk, alt_y, g1, g2):
    """yazi blogunu tarih alt kenari alt_y olacak sekilde yerlestirir. Doner {ad: (rgb|None, alfa, x, y)} ve blok ust y."""
    c = T['cap']
    A1, t1 = T['isim1']; A2, t2 = T['isim2']; At, tt = T['tarih']; sa = T['sonsuz']
    b1, b2, bt = o1.bbox(A1, 0.5), o1.bbox(A2, 0.5), o1.bbox(At, 0.5)
    w1, w2 = b1[2] - b1[0], b2[2] - b2[0]
    gap = P['bosluk'] / P['cap'] * c
    top = w1 + gap + sa.shape[1] + gap + w2
    sx = C - top / 2
    E = {}
    tar_ust = alt_y - (bt[3] - bt[1])
    E['tarih'] = (None, At, int(round(C - (bt[0] + bt[2]) / 2)), int(round(tar_ust - bt[1])))
    isim_alt = tar_ust - g2 * c
    # isim satirinin alt kenari (J inisi dahil) isim_alt'a; taban = isim_alt - (inis payi)
    inis = max(b1[3] - t1, b2[3] - t2)
    taban = isim_alt - inis
    E['isim1'] = (None, A1, int(round(sx - b1[0])), int(round(taban - t1)))
    E['isim2'] = (None, A2, int(round(sx + top - w2 - b2[0])), int(round(taban - t2)))
    E['sonsuz'] = (None, sa, int(round(sx + w1 + gap)), int(round(taban - c / 2 - sa.shape[0] / 2)))
    isim_ust = taban - c
    merk = {'sol': sx + w1 / 2, 'sag': sx + top - w2 / 2}
    g_alt = isim_ust - g1 * c
    for t in ('sol', 'sag'):
        rgb, a = kucuk[t]
        bb = o1.bbox(a, 0.5)
        E[f'kucuk_{t}'] = (rgb, a, int(round(merk[t] - a.shape[1] / 2)), int(round(g_alt - bb[3])))
    ust = min(E[f'kucuk_{t}'][3] + o1.bbox(E[f'kucuk_{t}'][1], 0.5)[1] for t in ('sol', 'sag'))
    return E, ust


def kapi(E, haric_cakisma=()):
    M, tasma = {}, {}
    for ad, (_, a, x, y) in E.items():
        if ad == 'halka':
            M[ad] = a; tasma[ad] = 0
        else:
            M[ad], tasma[ad] = maske_yaz(a, x, y)
    tum = np.maximum.reduce([M[k] for k in M]) > 0.02
    yb = {k: int((tum & v).sum()) for k, v in YASAK.items()}
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
    # yazi ogeleri birbirine 3 px'ten yakin olmasin
    yazi = [k for k in M if k not in ('halka', 'sembol')]
    for i, a1 in enumerate(yazi):
        d1 = cv2.dilate((M[a1] > 0.05).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        for a2 in yazi[i + 1:]:
            if (d1 & (M[a2] > 0.05)).any():
                cak.append(f'{a1}/{a2}')
    return M, yb, cak, all(v == 0 for v in yb.values()) and not cak


def sembol_yerlestir(ana, w_hedef, cx, cy):
    x0, y0, x1, y1 = o1.bbox(ana[..., 3], 0.5)
    rgb, a = o1.rgba_olcek(ana, w_hedef / (x1 - x0))
    bb = o1.bbox(a, 0.5)
    return (rgb, a, int(round(cx - (bb[0] + bb[2]) / 2)), int(round(cy - (bb[1] + bb[3]) / 2)))


def alt_sinir(T, kucuk, g1, g2):
    """yazi blogunun en asagi konumu: tarih kapidan gecene kadar yukari."""
    for alt in np.arange(N - 40, 500, -1.0):
        E, ust = yazi_blogu(T, kucuk, alt, g1, g2)
        M, yb, cak, ok = kapi(E)
        if ok:
            return alt, E, ust
    return None, None, None


def yerlesim_A(el, ana, T, kucuk):
    alt, Eyazi, ust = alt_sinir(T, kucuk, 0.45, 0.40)
    if alt is None:
        return None
    sx0, sy0, sx1, sy1 = P['sembol_kutu']
    sonuc, red = None, []
    for ax in np.arange(390, 200, -1.0):
        by = ax / el['oran']
        tepe_w = TEPE
        cy = UST_MIN + tepe_w / 2 + by + 1.0
        ha, hb = halka_alfa(el, cy, ax)
        k = ax / el['a']
        sem = sembol_yerlestir(ana, (sx1 - sx0) * k, C, cy + ((sy0 + sy1) / 2 - el['cy']) * (by / el['b']))
        E = dict(Eyazi); E['halka'] = (None, ha, 0, 0); E['sembol'] = sem
        M, yb, cak, ok = kapi(E)
        if ok:
            sonuc = dict(E=E, M=M, yasak=yb, cak=cak, halka=hb, alt=alt)
            break
        if len(red) < 6:
            red.append(dict(ax=float(ax), yasak={k_: v for k_, v in yb.items() if v}, cak=cak[:4]))
    if sonuc:
        sonuc['red_ilk'] = red
    return sonuc


def yerlesim_B(ana, T, kucuk):
    g = 0.70
    alt, Eyazi, ust = alt_sinir(T, kucuk, g, g)
    if alt is None:
        return None
    c = T['cap']
    red = []
    for w in np.arange(700, 250, -2.0):
        x0, y0, x1, y1 = o1.bbox(ana[..., 3], 0.5)
        h = w * (y1 - y0) / (x1 - x0)
        cy_ust = UST_MIN + 2 + h / 2                      # olabildigince yukari
        cy_alt = ust - g * c - h / 2                      # yazi blogunun ustunde rahat aralik
        if cy_alt < cy_ust:
            continue
        sem = sembol_yerlestir(ana, w, C, cy_ust)
        E = dict(Eyazi); E['sembol'] = sem
        M, yb, cak, ok = kapi(E)
        if ok:
            # bos kalan dikey payi sembol ile yazi arasinda dagit: sembol yukarida kalir, yazi blogu sembole yaklasmaz (rahat aralik)
            return dict(E=E, M=M, yasak=yb, cak=cak, alt=alt, sembol_w=float(w), bos_dikey=round(float(cy_alt - cy_ust), 1), red_ilk=red)
        if len(red) < 6:
            red.append(dict(w=float(w), yasak={k_: v for k_, v in yb.items() if v}, cak=cak[:4]))
    return None


# ----------------------------------------------------------------------------------------------- boyama + butunlesme
def softlight(a, b):
    a, b = a / 255.0, b / 255.0
    r = np.where(b <= 0.5, a - (1 - 2 * b) * a * (1 - a), a + (2 * b - 1) * (np.where(a <= 0.25, ((16 * a - 12) * a + 4) * a, np.sqrt(a)) - a))
    return r * 255.0


def boya(Y, model, zemin, kazanc, td):
    E, M = Y['E'], Y['M']
    out = zemin.astype(np.float32).copy()
    # zemin ortalama rengi ve doku
    zort = zemin.reshape(-1, 3).mean(0)
    zL = lum(zemin)
    doku = zL - cv2.GaussianBlur(zL, (0, 0), 6.0)
    doku_b = np.clip(128 + doku * 2.0, 0, 255)                       # soft light karisim katmani (gri 128 = etkisiz)
    tum = np.maximum.reduce([M[k] for k in M])
    # 1 golge: zeminin koyu tonu, sag alt
    gm = cv2.GaussianBlur(tum, (0, 0), GOLGE_SIGMA)
    T_ = np.float32([[1, 0, GOLGE_KAYMA], [0, 1, GOLGE_KAYMA]])
    gm = cv2.warpAffine(gm, T_, (N, N))
    out = out * (1 - GOLGE_OPAK * gm[..., None] * (1 - GOLGE_KOYU))
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
    # tum altin ogeler: ortak kazanc + golge tonlarina zemin rengi + doku (soft light)
    for ad in E:
        cc = renkler[ad] * kazanc
        L = lum(cc)
        w = np.clip((model.Lmed - L) / max(model.Lmed, 1), 0, 1)[..., None] * TINT_GUC
        tint = zort / max(float(lum(zort[None])[0]), 1.0) * L[..., None]
        cc = cc * (1 - w) + tint * w
        cc = cc * (1 - DOKU_GUC) + softlight(np.clip(cc, 0, 255), doku_b[..., None]) * DOKU_GUC
        m = M[ad][..., None]
        out = out * (1 - m) + np.clip(cc, 0, 255) * m
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def okunurluk(rgb, zemin, m):
    ce = cv2.erode((m > 0.9).astype(np.uint8), np.ones((2, 2), np.uint8)) > 0
    ce = ce if ce.sum() > 10 else m > 0.7
    ink = (m > 0.02).astype(np.uint8)
    yc = np.median(rgb[ce], 0)
    r = {}
    for ad, (i, o) in (('bant_1_12', (3, 25)), ('bant_3_6', (7, 13))):
        arka = (cv2.dilate(ink, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (o, o))) > 0) & \
               (cv2.dilate(ink, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (i, i))) == 0)
        za = rgb[arka].astype(np.float32)                                # sonuc goruntusunde (golge dahil) yazinin arkasi
        z95 = np.median(za[lum(za) >= np.percentile(lum(za), 95)], 0)
        r[ad] = dict(ortanca=o1.kontrast(yc, np.median(za, 0)), acik5=o1.kontrast(yc, z95))
    r['yazi_rgb'] = [int(v) for v in yc]
    return r


def onizleme_satir(liste):
    return o2.onizleme(liste, delik=True)


def main():
    global YASAK
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    K, O = Path(a.kaynak), Path(a.cikti)
    O.mkdir(parents=True, exist_ok=True)
    YASAK = yasak()
    spec = importlib.util.spec_from_file_location('tek_doku', K / 'tek_doku.py')
    td = importlib.util.module_from_spec(spec); spec.loader.exec_module(td)
    R = {'kaynak_sha256': {f.name: o1.sha(f) for f in sorted(K.iterdir()) if f.is_file()},
         'sabit': dict(guvenli_cap=760.6, pay=PAY, delik=DELIK, centik=CENTIK, ust_min=UST_MIN, govde=GOVDE, tepe=TEPE, uc_l=UC_L,
                       golge=dict(kayma=GOLGE_KAYMA, sigma=GOLGE_SIGMA, opak=GOLGE_OPAK, koyu=GOLGE_KOYU), doku=DOKU_GUC, tint=TINT_GUC)}
    el = elips_olc(K / 'HALKA_BLUE_16x20.png')
    R['poster_elips'] = dict(merkez=[round(el['cx'], 1), round(el['cy'], 1)], yatay_yari=round(el['a'], 1), dikey_yari=round(el['b'], 1),
                             oran_yatay_dikey=round(el['oran'], 4), acik_aci=el['uc'])
    ana = np.asarray(Image.open(K / 'CANCER_LIBRA_ana.png').convert('RGBA'), np.float32)
    ana[..., 3] /= 255.0
    ana = o1.kirp(ana, ana[..., 3], pad=2)
    if ana.shape[1] > 1600:
        r_, a_ = o1.rgba_olcek(ana, 1600 / ana.shape[1]); ana = np.dstack([r_, a_])

    def kucuk(burc, cap, h_ratio):
        g = np.asarray(Image.open(K / f'{burc}_symbol_gold.png').convert('RGBA'), np.float32)
        g[..., 3] /= 255.0
        g = o1.kirp(g, g[..., 3], pad=2)
        gx0, gy0, gx1, gy1 = o1.bbox(g[..., 3], 0.5)
        return o1.rgba_olcek(g, h_ratio * cap / (gy1 - gy0))
    zeminler = {ad: o1.zemin_canva(K / zf) for ad, zf in STILLER}
    sonuc = {}
    for yer in ('HALKALI', 'HALKASIZ'):
        secim = None
        for olcek in (1.0, 1.08, 1.15):
            cap = CAP0 * olcek
            T = metinler(K, cap)
            kc = {'sol': kucuk('cancer', cap, P['kucuk_sol_h'] / P['cap']), 'sag': kucuk('libra', cap, P['kucuk_sag_h'] / P['cap'])}
            Y = yerlesim_A(el, ana, T, kc) if yer == 'HALKALI' else yerlesim_B(ana, T, kc)
            if Y is None:
                print(yer, 'yerlesim yok, olcek', olcek, flush=True)
                break
            sb = Y['E']['sembol'][0], Y['E']['sembol'][1]
            sx = Y['E']['sembol']
            # tek doku modeli: sembolun hedef olcekteki hali
            model = o1.Model(td, sx[0], sx[1], 4800 * (o1.bbox(sx[1], 0.5)[2] - o1.bbox(sx[1], 0.5)[0]) / 2084)
            stil_ok, stil = True, {}
            for ad, _ in STILLER:
                z = zeminler[ad]
                sec = None
                for kazanc in (1.0, 1.04, 1.08, 1.12, 1.16, 1.20):
                    rgb = boya(Y, model, z, kazanc, td)
                    ok = {k: okunurluk(rgb, z, Y['M'][k]) for k in ('isim1', 'isim2', 'tarih')}
                    en = min(min(v['bant_1_12']['ortanca'], v['bant_1_12']['acik5']) for v in ok.values())
                    if en >= HEDEF:
                        sec = (kazanc, rgb, ok, en); break
                if sec is None:
                    sec = (kazanc, rgb, ok, en); stil_ok = False
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
        tum = np.maximum.reduce([Y['M'][k] for k in Y['M']]) > 0.02
        yy, xx = np.nonzero(tum)
        rmax = float(np.hypot(xx + 0.5 - C, yy + 0.5 - C).max())
        dl = float(np.hypot(xx + 0.5 - DELIK[0], yy + 0.5 - DELIK[1]).min() - DELIK[2])
        r = dict(yazi_olcek=secim['olcek'], isim_buyuk_harf_mm=round(secim['T']['cap'] * MM, 2),
                 tarih_buyuk_harf_mm=round(P['tagline_T'] / P['cap'] * secim['T']['cap'] * MM, 2),
                 sembol_px=[sb[2] - sb[0], sb[3] - sb[1]], sembol_mm=[round((sb[2] - sb[0]) * MM, 2), round((sb[3] - sb[1]) * MM, 2)],
                 sembol_V2_kazanc_yuzde=round(((sb[2] - sb[0]) / V2_SEMBOL_W - 1) * 100, 1),
                 yasak_piksel=Y['yasak'], cakisma=Y['cak'], guvenli_daireye_pay=round(GUV_R - rmax, 1), delige_uzaklik=round(dl, 1),
                 ust_y=int(yy.min()), sonsuz=secim['T']['sonsuz_bilgi'], red_ilk=Y.get('red_ilk'))
        for ad in Y['M']:
            b = o1.bbox(Y['M'][ad], 0.5)
            r.setdefault('oge', {})[ad] = dict(kutu=list(b), w_mm=round((b[2] - b[0]) * MM, 2), h_mm=round((b[3] - b[1]) * MM, 2))
        if yer == 'HALKALI':
            hb = Y['halka']
            ho = halka_olc(Y['M']['halka'], hb['cy'], hb['ax'], hb['by'], el['uc'], hb['r_ort'])
            hx = np.nonzero(Y['M']['halka'].max(0) > 0.5)[0]; hyy = np.nonzero(Y['M']['halka'].max(1) > 0.5)[0]
            r['halka'] = dict(yatay_yari=round(hb['ax'], 1), dikey_yari=round(hb['by'], 1), oran=round(hb['ax'] / hb['by'], 4),
                              dis_genislik_px=int(hx.max() - hx.min() + 1), dis_yukseklik_px=int(hyy.max() - hyy.min() + 1),
                              dis_genislik_V2_kazanc_yuzde=round(((hx.max() - hx.min() + 1) / 608 - 1) * 100, 1), **ho)
        else:
            r['bos_dikey'] = Y.get('bos_dikey')
        for ad, (kazanc, rgb, ok, en) in secim['stil'].items():
            o1.kaydet(rgb, O / f'{ad}_{yer}_954.png')
            r.setdefault('stil', {})[ad] = dict(altin_kazanc=kazanc, en_kotu_1_12=en, hedef_tuttu=en >= HEDEF, okunurluk=ok)
        r['tek_doku'] = dict(Lmed=round(secim['model'].Lmed, 1), doku=secim['model'].m['doku'],
                             isik_not='kabartma a: dh/dy, b: dh/dx katsayisi (ana sembolden); a < 0 ve b < 0 = isik sol ust')
        R[yer] = r
        print(yer, json.dumps({k: r[k] for k in ('yazi_olcek', 'sembol_px', 'sembol_V2_kazanc_yuzde', 'yasak_piksel', 'cakisma',
                                                  'guvenli_daireye_pay')}), flush=True)
        if yer == 'HALKALI':
            print('HALKA', json.dumps({k: v for k, v in r['halka'].items() if k not in ('aci_genislik',)})[:900], flush=True)
        print(yer, 'stil', json.dumps({k: (v['altin_kazanc'], v['en_kotu_1_12']) for k, v in r['stil'].items()}), flush=True)
    # onizleme: ust satir halkali, alt satir halkasiz
    s1 = o2.onizleme([sonuc['HALKALI']['stil'][a][1] for a, _ in STILLER])
    s2 = o2.onizleme([sonuc['HALKASIZ']['stil'][a][1] for a, _ in STILLER])
    o = Image.new('RGB', (max(s1.width, s2.width), s1.height + s2.height + 24), 'white')
    o.paste(s1, (0, 0)); o.paste(s2, (0, s1.height + 24))
    o.save(O / 'ONIZLEME_7cm.png', dpi=(300, 300))
    (O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=float))
    h = R['HALKALI']['halka']
    g = dict(yasak_0=all(sum(R[y]['yasak_piksel'].values()) == 0 for y in ('HALKALI', 'HALKASIZ')),
             cakisma_0=all(not R[y]['cakisma'] for y in ('HALKALI', 'HALKASIZ')),
             kontrast=all(v['hedef_tuttu'] for y in ('HALKALI', 'HALKASIZ') for v in R[y]['stil'].values()),
             sonsuz=all(R[y]['sonsuz']['en_ince_px'] >= SONSUZ_MIN and R[y]['sonsuz']['gecti'] for y in ('HALKALI', 'HALKASIZ')),
             halka_govde=h['govde_min'] >= 4.0,
             uc=all(any(s_ >= 19 and s_ <= 21 and w >= 1.5 for s_, w in v) for v in h['uc'].values()),
             sembol_B_15=R['HALKASIZ']['sembol_V2_kazanc_yuzde'] >= 15)
    R['kapi'] = g
    (O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=float))
    print('KAPI', json.dumps(g), 'PASS' if all(g.values()) else 'FAIL', flush=True)
    return 0 if all(g.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
