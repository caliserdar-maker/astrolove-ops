#!/usr/bin/env python3
"""Seramik yuvarlak ornament ORNEK baski dosyasi (Serdar 2 Kas 2026; yalniz CANCER_LIBRA, toplu uretim YOK). Etsy / Printful yok.

Urun (Printful API, dal docs/ornament/ham): 881/900 Circle printfile 954x954 px, 300 dpi; urun capi 7 cm (2.76") ~ 827 px.
Gorunen alan: merkezde 827 px daire; disi kesim payi (zemin tasar).

Kaynaklar (hepsi oldugu gibi, yalniz esit oranli olcek; yapay zeka yok, sekil degismez):
  ana sembol   Drive ANA_SEMBOL78_KATMAN_20261008/CANCER_LIBRA_ana.png (RGBA, 78 tek dokulu altin)
  kucuk sembol Drive ARCHIVE/LEGACY_COMPONENTS/zodiac_symbols_gold/{cancer,libra}_symbol_gold.png (posterdeki tek burc glifleri)
  halka        dal ornek-tek-doku motor/varlik/halka/HALKA_BLUE_16x20.png (MB) / HALKA_16x20.png (CI): poster plakasindan piksel
               olarak ayrilmis orijinal halka (alttan acik, uclara incelen); yeni halka CIZILMEZ
  sonsuz       dal siparis-gpt motor_gpt/alfa_ogeler.npz['sonsuz'] (posterdeki sonsuz alfasi, 652 px)
  yazi tipi    dal ornek-tek-doku motor/font: Cinzel wght 500 (isimler), EB Garamond Italic 400 (tarih = poster tagline yazi tipi)
  tek doku     dal ornek-tek-doku motor/tek_doku.py (egri_olc, doku_olc, duz_l): ana sembolden olculen renk egrisi + boru profili
               + kabartma; halka, kucuk semboller, isimler, sonsuz, tarih bu modelle boyanir (tek doku birligi)
  zemin        MB: BLUE_16x20 plakasinin merkezden disa radyal ortanca profili; CI: MODERN_16x20 ayni yontem;
               STIL3: Canva zeminleri (1264 -> 954 esit olcek, kirpma yok, baska islem yok)
Poster oranlari: sabitler/CANCER_LIBRA_MB_16x20.json (ornek-tek-doku): sembol kutusu, kucuk sembol, isim, sonsuz, tagline.
Kapilar (PASS/FAIL): tum icerik gorunen dairenin >= 40 px icinde; ustte 160 px delik boslugu bos; halka ile diger ogeler cakismaz.
Kullanim: ornament_ornek.py --kaynak DIR --cikti DIR"""
import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
N = 954
C = N / 2.0
RV = 827 / 2.0                     # gorunen daire yaricapi
PAY = 40                           # kenar payi (px)
RIN = RV - PAY
DELIK = 160                        # ust delik boslugu (gorunen dairenin tepesinden)
Y_UST = C - RV                     # gorunen dairenin tepesi (63.5)
Y_MIN = Y_UST + DELIK              # icerik bu satirdan asagida (223.5)
MM = 25.4 / 300
LUMA = np.array([0.299, 0.587, 0.114], np.float32)

# Poster olculeri (CANCER_LIBRA_MB_16x20.json, 4800x6000)
P = dict(sembol_kutu=(1358, 1216, 3442, 3176), kucuk_sol_h=351, kucuk_sag_h=363, cap=(172 + 167) / 2,
         bosluk=269, sonsuz_w=375, tagline_T=144)
HALKA_ORAN = 0.67                  # halka capi / gorunen daire (istek %65-70)
ISIM1, ISIM2, TARIH = "EMILY", "JAMES", "14 JUNE 2025"


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def lum(rgb):
    return rgb @ LUMA


def bbox(a, t=0.02):
    ys, xs = np.nonzero(a > t)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def kirp(arr, a, pad=4):
    x0, y0, x1, y1 = bbox(a)
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    return arr[y0:y1 + pad, x0:x1 + pad]


def olcek(arr, k):
    h, w = arr.shape[:2]
    return cv2.resize(arr, (max(1, round(w * k)), max(1, round(h * k))), interpolation=cv2.INTER_AREA)


def rgba_olcek(rgba, k):
    """on carpilmis RGB ile esit oranli kucultme."""
    a = rgba[..., 3:4]
    pm = olcek(np.concatenate([rgba[..., :3] * a, a], -1), k)
    a2 = pm[..., 3]
    rgb = pm[..., :3] / np.maximum(a2[..., None], 1e-4)
    return np.clip(rgb, 0, 255), np.clip(a2, 0, 1)


def metin_alfa(metin, font_yolu, cap_px, wght=None, ref='H', ss=4):
    """metni ss kat buyuk cizip esit oranli kucultur; buyuk harf yuksekligi (ref) = cap_px."""
    def f_(pt):
        f = ImageFont.truetype(str(font_yolu), max(4, int(round(pt))))
        if wght:
            f.set_variation_by_axes([wght])
        return f
    pt = cap_px * ss * 1.45
    for _ in range(4):
        f = f_(pt)
        b = f.getbbox(ref, anchor='ls')
        pt *= cap_px * ss / max(1, -b[1])
    f = f_(pt)
    b = f.getbbox(metin, anchor='ls')
    pad = 6 * ss
    w, h = b[2] - b[0] + 2 * pad, b[3] - b[1] + 2 * pad
    im = Image.new('L', (w, h), 0)
    ImageDraw.Draw(im).text((pad - b[0], pad - b[1]), metin, font=f, fill=255, anchor='ls')
    A = np.asarray(im, np.float32) / 255.0
    taban = (pad - b[1]) / ss
    A = olcek(A, 1 / ss)
    return A, taban


class Model:
    """tek doku: ana sembolden (hedef olcekte) renk egrisi, Lmed, doku (motor/tek_doku.py)."""

    def __init__(self, td, rgb, a, W_es):
        self.td = td
        ce = a > 0.9
        self.egri = td.egri_olc(rgb[a > 0.98].astype(np.float32))
        self.L = lum(rgb)
        self.Lmed = float(np.median(self.L[ce]))
        self.m = {'egri': self.egri, 'Lmed': self.Lmed, 'doku': td.doku_olc(a, self.L, W_es)}

    def boya(self, l, A):
        """luma dokusu l -> renk; k cekirdek ortancasini Lmed'e esitler (tek doku)."""
        ce = A > 0.9 if (A > 0.9).sum() >= 20 else A > 0.5
        k = self.Lmed / max(float(np.median(l[ce])), 1.0)
        return self.td.renk(l * k, self.egri), round(k, 3)

    def duz(self, A):
        return self.boya(self.td.duz_l(A, self.m), A)


def plaka_profili(f):
    """plakanin merkezden disa radyal ortanca rengi (yildiz / halka ortanca ile disarida kalir). Doner r(0..1) -> RGB."""
    im = np.asarray(Image.open(f).convert('RGB'))
    im = cv2.resize(im, (im.shape[1] // 4, im.shape[0] // 4), interpolation=cv2.INTER_AREA).astype(np.float32)
    H, W = im.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot(xx - W / 2, yy - H / 2) / (W / 2)
    rs = np.linspace(0, 1.4, 29)
    prof = []
    for i in range(len(rs)):
        m = np.abs(r - rs[i]) < (0.025 if i else 0.05)
        prof.append(np.median(im[m], 0) if m.sum() > 20 or not prof else prof[-1])
    return rs, np.array(prof, np.float32)


def zemin_profil(rs, prof):
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    r = np.hypot(xx - C + 0.5, yy - C + 0.5) / C
    z = np.stack([np.interp(r, rs, prof[:, c]) for c in range(3)], -1)
    rng = np.random.default_rng(7)
    return np.clip(z + rng.uniform(-0.5, 0.5, z.shape), 0, 255)      # bant onleme titresimi (+-0.5)


def zemin_canva(f):
    im = np.asarray(Image.open(f).convert('RGB'), np.float32)
    return cv2.resize(im, (N, N), interpolation=cv2.INTER_AREA)


def kontrast(c1, c2):
    def L_(c):
        c = np.asarray(c, np.float64) / 255
        c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    a, b = sorted([L_(c1), L_(c2)])
    return round((b + 0.05) / (a + 0.05), 2)


def render(K, td, zemin, halka_f, isim1, isim2, tarih, kucult_sinir=0.55):
    """Doner: (rgb uint8, olcum dict, ogeler dict)."""
    # --- halka
    ha = np.asarray(Image.open(halka_f), np.float32) / 255.0
    hx0, hy0, hx1, hy1 = bbox(ha, 0.1)
    p_cap = hx1 - hx0
    p_cy = hy0 + p_cap / 2                                     # poster halka merkezi (ust + yaricap)
    D = HALKA_ORAN * 2 * RV
    kr = D / p_cap
    hk = olcek(ha[hy0 - 6:hy1 + 6, hx0 - 6:hx1 + 6], kr)
    ring_ust = Y_MIN + 3
    cy = ring_ust + D / 2
    # --- ana sembol (posterdeki oran: kutu genisligi / halka capi, merkez dy)
    ana = np.asarray(Image.open(K / 'CANCER_LIBRA_ana.png').convert('RGBA'), np.float32)
    ana[..., 3] /= 255.0
    ana = kirp(ana, ana[..., 3], pad=2)
    sx0, sy0, sx1, sy1 = P['sembol_kutu']
    s_w = (sx1 - sx0) * kr
    x0, y0, x1, y1 = bbox(ana[..., 3], 0.5)
    ks = s_w / (x1 - x0)
    s_rgb, s_a = rgba_olcek(ana, ks)
    s_cy = cy + ((sy0 + sy1) / 2 - p_cy) * kr
    W_es = 4800 * kr                                           # tek doku pencere / sigma olcegi (poster tuvali esdegeri)
    model = Model(td, s_rgb, s_a, W_es)

    def kucuk(burc, h_hedef):
        g = np.asarray(Image.open(K / f'{burc}_symbol_gold.png').convert('RGBA'), np.float32)
        g[..., 3] /= 255.0
        g = kirp(g, g[..., 3], pad=2)
        gx0, gy0, gx1, gy1 = bbox(g[..., 3], 0.5)
        return rgba_olcek(g, h_hedef / (gy1 - gy0))

    son = np.load(K / 'alfa_ogeler.npz')['sonsuz'].astype(np.float32) / 255.0
    son = kirp(son, son)

    c0 = P['cap'] * kr                                         # poster oraninda isim buyuk harf yuksekligi
    c, sn = c0, 1.0                                            # c: metin olcegi, sn: isim satiri ek kucultmesi
    for deneme in range(60):
        E = {}                                                 # ad -> (rgb, alfa, x, y)
        E['halka'] = (None, hk, int(round(C - hk.shape[1] / 2)), int(round(ring_ust - 6 * kr - 0)))
        E['sembol'] = (s_rgb, s_a, int(round(C - s_a.shape[1] / 2)), int(round(s_cy - s_a.shape[0] / 2)))
        cn = c * sn
        A1, t1 = metin_alfa(isim1, K / 'Cinzel.ttf', cn, 500)
        A2, t2 = metin_alfa(isim2, K / 'Cinzel.ttf', cn, 500)
        b1, b2 = bbox(A1, 0.5), bbox(A2, 0.5)
        w1, w2 = b1[2] - b1[0], b2[2] - b2[0]
        sa = olcek(son, P['sonsuz_w'] / P['cap'] * cn / son.shape[1])
        gap = P['bosluk'] / P['cap'] * cn
        top = w1 + gap + sa.shape[1] + gap + w2
        sx = C - top / 2
        sym_alt = E['sembol'][3] + bbox(s_a)[3]
        g_h = {'sol': P['kucuk_sol_h'] / P['cap'] * c, 'sag': P['kucuk_sag_h'] / P['cap'] * c}
        gl = {t: kucuk(b, g_h[t]) for t, b in (('sol', 'cancer'), ('sag', 'libra'))}
        g_ust = sym_alt + 0.55 * c
        g_mid = g_ust + max(a.shape[0] for _, a in gl.values()) / 2
        isim_ust = g_ust + max(g_h.values()) + 0.85 * c
        taban = isim_ust + cn
        merk = {'sol': sx + w1 / 2, 'sag': sx + top - w2 / 2}
        E['isim1'] = (None, A1, int(round(sx - b1[0])), int(round(taban - t1)))
        E['isim2'] = (None, A2, int(round(sx + top - w2 - b2[0])), int(round(taban - t2)))
        E['sonsuz'] = (None, sa, int(round(sx + w1 + gap)), int(round(taban - cn / 2 - sa.shape[0] / 2)))
        for t in ('sol', 'sag'):
            rgb, a = gl[t]
            E[f'kucuk_{t}'] = (rgb, a, int(round(merk[t] - a.shape[1] / 2)), int(round(g_mid - a.shape[0] / 2)))
        ct = P['tagline_T'] / P['cap'] * c
        At, tt = metin_alfa(tarih, K / 'EBGaramond-Italic.ttf', ct, None, ref='T')
        bt = bbox(At, 0.5)
        tar_taban = taban + 1.15 * c + ct
        E['tarih'] = (None, At, int(round(C - (bt[0] + bt[2]) / 2)), int(round(tar_taban - tt)))
        # kapilar
        yy, xx = np.mgrid[0:N, 0:N]
        rr = np.hypot(xx - C + 0.5, yy - C + 0.5)
        ihlal, maske = {}, {}
        for ad, (_, a, x, y) in E.items():
            m = np.zeros((N, N), np.float32)
            h, w = a.shape
            xa, ya, xb, yb = max(0, x), max(0, y), min(N, x + w), min(N, y + h)
            m[ya:yb, xa:xb] = a[ya - y:yb - y, xa - x:xb - x]
            dis = (a > 0.02).sum() - (m > 0.02).sum()
            maske[ad] = m
            ic = m > 0.02
            ihlal[ad] = bool(dis > 0 or (rr[ic] > RIN).any() or (yy[ic] < Y_MIN).any())
        cak = []
        hm = cv2.dilate((maske['halka'] > 0.05).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        for ad in E:
            if ad != 'halka' and (hm & (maske[ad] > 0.05)).any():
                cak.append(f'halka/{ad}')
        sm = cv2.dilate((maske['sembol'] > 0.05).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        for ad in ('kucuk_sol', 'kucuk_sag', 'isim1', 'isim2', 'sonsuz', 'tarih'):
            if (sm & (maske[ad] > 0.05)).any():
                cak.append(f'sembol/{ad}')
        ok = not any(ihlal.values()) and not cak
        if ok:
            break
        isim_satiri = ihlal['isim1'] or ihlal['isim2'] or ihlal['sonsuz']
        diger = any(v for k_, v in ihlal.items() if k_ not in ('isim1', 'isim2', 'sonsuz')) or cak
        if isim_satiri and not diger and sn > kucult_sinir:
            sn *= 0.97
        else:
            c *= 0.97
    # --- boyama (tek doku) + bindirme
    out = zemin.astype(np.float32).copy()
    kk = {}
    for ad, (rgb, a, x, y) in E.items():
        if ad == 'sembol':
            col = rgb                                          # posterdeki altin (ana sembol yuzeyi oldugu gibi)
        elif ad.startswith('kucuk'):
            col, kk[ad] = model.boya(lum(rgb), a)
        else:
            col, kk[ad] = model.duz(a)
        m = maske[ad][..., None]
        cc = np.zeros((N, N, 3), np.float32)
        h, w = a.shape
        xa, ya, xb, yb = max(0, x), max(0, y), min(N, x + w), min(N, y + h)
        cc[ya:yb, xa:xb] = col[ya - y:yb - y, xa - x:xb - x]
        out = out * (1 - m) + cc * m
    rgb = np.clip(np.round(out), 0, 255).astype(np.uint8)
    # --- olcumler
    tum = np.maximum.reduce([maske[k] for k in maske]) > 0.02
    yy, xx = np.nonzero(tum)
    rmax = float(np.hypot(xx - C + 0.5, yy - C + 0.5).max())
    O = dict(
        kapi=dict(gecti=bool(ok), ihlal=ihlal, cakisma=cak, deneme=deneme + 1),
        kenar_payi_px=round(RV - rmax, 1), kenar_payi_mm=round((RV - rmax) * MM, 2),
        delik_boslugu_px=round(float(yy.min()) - Y_UST, 1), delik_boslugu_mm=round((float(yy.min()) - Y_UST) * MM, 2),
        halka=dict(cap_px=round(D, 1), cap_mm=round(D * MM, 2), oran_gorunen=round(D / (2 * RV), 3), olcek_poster=round(kr, 4),
                   tepe_kalinlik_px=round(float((maske['halka'][:, int(C)] > 0.5).sum()), 1),
                   tepe_kalinlik_mm=round(float((maske['halka'][:, int(C)] > 0.5).sum()) * MM, 2)),
        metin_olcegi=dict(c_poster_orani_px=round(c0, 2), c_px=round(c, 2), isim_satiri_ek=round(sn, 3)),
        kucuk_sembol_oran={k: v for k, v in kk.items()}, tek_doku=dict(Lmed=round(model.Lmed, 1), doku=model.m['doku']))
    for ad in maske:
        x0, y0, x1, y1 = bbox(maske[ad], 0.5)
        O.setdefault('oge', {})[ad] = dict(kutu=[x0, y0, x1, y1], w_mm=round((x1 - x0) * MM, 2), h_mm=round((y1 - y0) * MM, 2))
    O['isim_buyuk_harf_mm'] = round(c * sn * MM, 2)
    O['tarih_buyuk_harf_mm'] = round(P['tagline_T'] / P['cap'] * c * MM, 2)
    # okunurluk: yazi cekirdek ortanca rengi / yazinin arkasindaki zemin (yazi kutusu +6 px, yazi pikselleri haric) ortancasi
    for ad in ('isim1', 'isim2', 'tarih'):
        m = maske[ad]
        ce = cv2.erode((m > 0.9).astype(np.uint8), np.ones((2, 2), np.uint8)) > 0
        ce = ce if ce.sum() > 10 else m > 0.7
        x0, y0, x1, y1 = bbox(m, 0.02)
        kutu = np.zeros((N, N), bool)
        kutu[max(0, y0 - 6):y1 + 6, max(0, x0 - 6):x1 + 6] = True
        arka = kutu & (cv2.dilate((m > 0.02).astype(np.uint8), np.ones((3, 3), np.uint8)) == 0)
        yc, zc = np.median(rgb[ce], 0), np.median(zemin[arka], 0)
        za = zemin[arka]
        z95 = np.median(za[lum(za) >= np.percentile(lum(za), 95)], 0)      # yazinin arkasindaki en acik %5 zemin
        O.setdefault('okunurluk', {})[ad] = dict(yazi_rgb=[int(v) for v in yc], zemin_rgb=[int(v) for v in zc],
                                                 kontrast_wcag=kontrast(yc, zc),
                                                 kontrast_en_acik_zemin_p95=kontrast(yc, z95),
                                                 zemin_luma_std=round(float(lum(zemin[arka]).std()), 1))
    return rgb, O


def daire_maskeli(rgb):
    yy, xx = np.mgrid[0:N, 0:N]
    a = np.clip(RV - np.hypot(xx - C + 0.5, yy - C + 0.5) + 0.5, 0, 1)
    out = np.dstack([rgb, np.round(a * 255).astype(np.uint8)])
    return out[int(C - RV) - 2:int(C + RV) + 3, int(C - RV) - 2:int(C + RV) + 3]


def yan_yana(liste, ara=24):
    ims = [daire_maskeli(r) for r in liste]
    h = max(i.shape[0] for i in ims)
    w = sum(i.shape[1] for i in ims) + ara * (len(ims) - 1)
    o = np.zeros((h, w, 4), np.uint8)
    x = 0
    for i in ims:
        o[:i.shape[0], x:x + i.shape[1]] = i
        x += i.shape[1] + ara
    return Image.fromarray(o, 'RGBA')


def kaydet(rgb, f):
    Image.fromarray(rgb).save(f, dpi=(300, 300))


def cizgi_bandi(f):
    """RUBY sol kenar dikey cizgi bandi (954 olceginde, zemin baskiya giden haliyle): her satir 61 px yatay kutu ortalamasindan
    cikarilir (yavas gradyan atilir), sutun ortalamasi alinir (s). Gurultu = orta sutunlarin (300-650) |s| MAD x 1.4826.
    Bant (betimleyici) = sol kenardan, 9 sutun kayan ortalamasi -1 gurultunun altinda kaldigi sutunlar; ayrica 2 x gurultu esigi. Gorunen daire x >= 63.5."""
    im = zemin_canva(f)
    L = lum(im)
    hp = L - cv2.blur(L, (61, 1))
    s = hp.mean(0)
    orta = s[300:650]
    gur = float(np.median(np.abs(orta - np.median(orta))) * 1.4826)
    rm = np.convolve(s, np.ones(9) / 9, mode='valid')                   # rm[i] = s[i..i+8] ortalamasi
    esik = 2 * max(gur, 0.05)
    koyu = np.nonzero(np.abs(rm[:N // 4]) > esik)[0]
    x2 = int(koyu.max() + 9) if len(koyu) else 0                        # 2 x gurultu esigini asan bant
    i = 0
    while i < N // 4 and rm[i] < -gur:                                  # betimleyici: 9 sutun ortalamasi -1 gurultunun altinda kaldikca
        i += 1
    x = i + 4 if i else 0
    ort = float(s[:max(x, 1)].mean())
    z = ort / (gur / np.sqrt(max(x, 1)))
    ic = slice(int(np.ceil(C - RV)), int(C))
    return dict(yontem='954 olcek, satir yuksek geciren (61 px) sutun ortalamasi', gurultu_luma=round(gur, 3), esik_luma=round(esik, 3),
                sol_bant_2x_esik_genislik_px=x2, sol_bant_genislik_px=int(x), sol_bant_x=[0, int(x)],
                sol_bant_ortalama_sapma_luma=round(ort, 3), sol_bant_z=round(float(z), 1), sol_bant_en_buyuk_sapma=round(float(s[:max(x, 1)][np.argmax(np.abs(s[:max(x, 1)]))]), 2),
                gorunen_daire_sol_x=round(C - RV, 1), daire_icinde=bool(x > C - RV),
                daire_ici_sol_yari_max_sapma=round(float(np.abs(s[ic]).max()), 2), sutun_0_30=[round(float(v), 2) for v in s[:30]])


def sablon_delik(K):
    """Printful Circle sablon gorseli (Actions'ta indirilebildiyse) uzerinde delik adayi."""
    f = K / 'sablon_Circle.png'
    if not f.exists():
        return {'durum': 'sablon gorseli yok (indirilemedi)'}
    im = Image.open(f)
    a = np.asarray(im.convert('RGBA'), np.float32)
    H, W = a.shape[:2]
    x0, top, pw = 262, 262, 2476                               # mockup_templates role=template print_area (3000x3000)
    k = N / pw
    A = a[..., 3]
    L = lum(a[..., :3])
    bilgi = {'boyut': [W, H], 'mod': im.mode, 'alfa_degerleri': [int(v) for v in np.unique(A)[:6]]}
    adaylar = []
    for ad, m in (('opak_alan', A > 128), ('koyu', (L < 100) & (A > 128))):
        n, lab, st, cen = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
        for i in range(1, n):
            cx, cy = cen[i]
            if abs(cx - 1500) < 300 and top <= cy < top + pw * 0.3 and 30 < st[i, cv2.CC_STAT_AREA] < 60000:
                adaylar.append(dict(tur=ad, merkez_printfile=[round((cx - x0) * k, 1), round((cy - top) * k, 1)],
                                    kutu_printfile=[round((st[i, 0] - x0) * k, 1), round((st[i, 1] - top) * k, 1),
                                                    round((st[i, 0] + st[i, 2] - x0) * k, 1), round((st[i, 1] + st[i, 3] - top) * k, 1)],
                                    alan_px=int(st[i, cv2.CC_STAT_AREA])))
    bilgi['adaylar'] = adaylar[:10]
    bilgi['not'] = 'otomatik aday; gorsel dogrulama gerekir'
    return bilgi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    K, O = Path(a.kaynak), Path(a.cikti)
    (O / 'STIL3').mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('tek_doku', K / 'tek_doku.py')
    td = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(td)
    R = {'kaynak_sha256': {f.name: sha(f) for f in sorted(K.iterdir()) if f.is_file()}, 'sabit': dict(N=N, RV=RV, PAY=PAY, DELIK=DELIK)}
    # ham (renksiz) sembol ile ana sembol alfasi uyumu (sekil degismedi mi): bbox'a esit oranli olcekle IoU
    if (K / 'cancer_libra_alfa.png').exists():
        ham = np.asarray(Image.open(K / 'cancer_libra_alfa.png'), np.float32) / 255
        ana = np.asarray(Image.open(K / 'CANCER_LIBRA_ana.png').convert('RGBA'), np.float32)[..., 3] / 255
        hk, ak = kirp(ham, ham, 0), kirp(ana, ana, 0)
        w = 1000
        hk2 = cv2.resize(hk, (w, round(hk.shape[0] * w / hk.shape[1])), interpolation=cv2.INTER_AREA)
        ak2 = cv2.resize(ak, (w, round(ak.shape[0] * w / ak.shape[1])), interpolation=cv2.INTER_AREA)
        h = min(hk2.shape[0], ak2.shape[0])
        i_ = ((hk2[:h] > 0.5) & (ak2[:h] > 0.5)).sum(); u_ = ((hk2[:h] > 0.5) | (ak2[:h] > 0.5)).sum()
        R['ham_ana_iou'] = dict(iou=round(float(i_ / max(u_, 1)), 4), ham_en_boy=[hk.shape[1], hk.shape[0]], ana_en_boy=[ak.shape[1], ak.shape[0]],
                                aciklama='ham alfa ve ana alfa kendi murekkep kutularina esit oranli olceklenip ust uste konur')
    sonuc = {}
    # ---- Ornek A: MB + CI
    rs, pmb = plaka_profili(K / 'BLUE_16x20.png')
    rs, pci = plaka_profili(K / 'MODERN_16x20.png')
    R['zemin_profili'] = {'MB': {f'{r:.2f}': [round(float(v), 1) for v in p] for r, p in zip(rs[::4], pmb[::4])},
                          'CI': {f'{r:.2f}': [round(float(v), 1) for v in p] for r, p in zip(rs[::4], pci[::4])}}
    zmb, zci = zemin_profil(rs, pmb), zemin_profil(rs, pci)
    for ad, z, hf in (('MB', zmb, 'HALKA_BLUE_16x20.png'), ('CI', zci, 'HALKA_16x20.png')):
        rgb, o = render(K, td, z, K / hf, ISIM1, ISIM2, TARIH)
        kaydet(rgb, O / f'CANCER_LIBRA_{ad}_954.png')
        sonuc[ad] = rgb
        R[ad] = o
        print(ad, json.dumps({k: o[k] for k in ('kapi', 'kenar_payi_px', 'delik_boslugu_px', 'isim_buyuk_harf_mm')}), flush=True)
    yan_yana([sonuc['MB'], sonuc['CI']]).save(O / 'ONIZLEME_7cm.png', dpi=(300, 300))
    rgb, o = render(K, td, zmb, K / 'HALKA_BLUE_16x20.png', 'ALEXANDRINA', 'MAXIMILIANO', TARIH)
    kaydet(rgb, O / 'UZUN_ISIM_TEST_954.png')
    yan_yana([rgb]).save(O / 'UZUN_ISIM_TEST.png', dpi=(300, 300))
    R['UZUN_ISIM'] = o
    print('UZUN', json.dumps({k: o[k] for k in ('kapi', 'metin_olcegi', 'isim_buyuk_harf_mm')}), flush=True)
    # ---- STIL3
    st = []
    for ad, zf in (('SAPPHIRE_GOLD', 'SAPPHIRE_1264.png'), ('EMERALD_GOLD', 'EMERALD_1264.png'), ('RUBY_GOLD', 'RUBY_1264.png')):
        if not (K / zf).exists():
            continue
        z = zemin_canva(K / zf)
        rgb, o = render(K, td, z, K / 'HALKA_BLUE_16x20.png', ISIM1, ISIM2, TARIH)
        kaydet(rgb, O / 'STIL3' / f'{ad}_954.png')
        st.append(rgb)
        R.setdefault('STIL3', {})[ad] = o
        print(ad, json.dumps({k: o[k] for k in ('kapi', 'okunurluk')}), flush=True)
    if st:
        yan_yana(st).save(O / 'STIL3' / 'STIL3_ONIZLEME_7cm.png', dpi=(300, 300))
    if (K / 'RUBY_1264.png').exists():
        R['RUBY_cizgi_bandi'] = cizgi_bandi(K / 'RUBY_1264.png')
        print('RUBY bant', json.dumps(R['RUBY_cizgi_bandi'])[:600], flush=True)
    R['sablon_delik'] = sablon_delik(K)
    (O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=float))
    gecti = all(R[k]['kapi']['gecti'] for k in ('MB', 'CI')) and all(v['kapi']['gecti'] for v in R.get('STIL3', {}).values())
    print('KAPI', 'PASS' if gecti else 'FAIL', '| uzun isim', 'PASS' if R['UZUN_ISIM']['kapi']['gecti'] else 'FAIL', flush=True)
    return 0 if gecti else 1


if __name__ == '__main__':
    sys.exit(main())
