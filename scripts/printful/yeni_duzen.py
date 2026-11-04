#!/usr/bin/env python3
"""YENI DUZEN (Serdar 4 Kas aksam; KARARLAR_20261104_2, ORNAMENT_YERLESIM78_SECIM) geometri modulu. Motor (ornament_motor.py, YENI_DUZEN=1)
ve yerel test (yeni_duzen_yerel_test.py) AYNI fonksiyonlari cagirir. Eski davranis bu modulu cagirmaz (varsayilan YENI_DUZEN=0).
Tanimlar (954 px tuval, 11,8 px/mm):
  kutu        = alfa > 0,5 sinir kutusu (ornament_ornek5.kutu ile ayni; tarih kutusu virgul dahil, ust ve alt dahil, piksel indeksi + 1 = alt)
  halka ic    = merkez (475,5, 504), r 336; alt noktasi y 840
  karar 1     tarih kutu alt = 795 (840 - 45)
  karar 2     isim satiri (isim1 + isim2 kutularinin birlesimi; logo isim grubuyla birlikte kayar) alt = tarih ust - 32;
              kucuk burc satiri alt = isim satiri ust - 32 (her kucuk isaret satirin altina yasli)
  karar 3     kucuk burc satiri UST CIZGISI SABIT = satir alt - H_MAX (12 kucuk isaretin en yuksegi); sembol alt siniri = ust cizgi - 32
  karar 4     sembol yatayda ortali (kutu merkezi x 476); alan: ust >= 230, alt <= sinir, halka icine >= 30 px pay (murekkep r <= 306)
              B3: Y3 (alanin dikey ortasi) yerlesiminde sigan en buyuk olcek x 0,85; Y2: bos dikey alanin %75'i sembolun ustunde
  karar 5     tarih "JUNE 14, 2025" (TARIH_YENI); en genis tarih ayri olculur
Yatay yerler (kucuk isaret, isim, logo, tarih) ornament_ornek3.yazi_blogu ile AYNEN (karar 3: boy ve yatay yer degismez)."""
import math

import numpy as np

N = 954
HALKA_C = (475.5, 504.0)
HALKA_R = 336.0
HALKA_PAY = 30.0
TARIH_ALT = 795
BOSLUK = 32
UST_MIN = 230
CX = 476.0
B3_KAT = 0.85
Y2_UST_ORAN = 0.75
TARIH_YENI = 'JUNE 14, 2025'
TARIH_ESKI = '14 JUNE 2025'
TOL_PX = 1.0
TOL_OLCEK = 0.005


def kutu(a, x=0, y=0, esik=0.5):
    ys, xs = np.nonzero(a > esik)
    if not len(xs):
        return None
    return (int(x + xs.min()), int(y + ys.min()), int(x + xs.max() + 1), int(y + ys.max() + 1))


def kutu_E(E, ad):
    _, a, x, y = E[ad]
    return kutu(a, x, y)


def satir_E(E, adlar):
    k = [kutu_E(E, a) for a in adlar]
    return min(b[1] for b in k), max(b[3] for b in k)


def kaydir(E, adlar, dy):
    for ad in adlar:
        rgb, a, x, y = E[ad]
        E[ad] = (rgb, a, x, int(y + dy))


def halka_max_r(a, x, y, esik=0.5):
    """alfa > esik murekkep piksellerinin halka ic dairesi merkezine en buyuk uzakligi (piksel merkezi)."""
    ys, xs = np.nonzero(a > esik)
    if not len(xs):
        return 0.0
    return float(np.sqrt(((xs + x + 0.5) - HALKA_C[0]) ** 2 + ((ys + y + 0.5) - HALKA_C[1]) ** 2).max())


def yazi_yerlestir(yazi_blogu, T, kc, h_max):
    """karar 1-3: dikey konumlar; yataylar yazi_blogu'ndan. Doner (E, cizgi) cizgi = dict(tarih_alt, isim_ust, isim_alt, kucuk_alt, kucuk_ust_sabit, sembol_alt_sinir)."""
    E, _ = yazi_blogu(T, kc, TARIH_ALT, 0.45, 0.40)                        # yataylar (karar 3); dikeyler asagida yeniden
    t = kutu_E(E, 'tarih')
    kaydir(E, ('tarih',), TARIH_ALT - t[3])
    t = kutu_E(E, 'tarih')
    i0, i1 = satir_E(E, ('isim1', 'isim2'))
    kaydir(E, ('isim1', 'isim2', 'sonsuz'), (t[1] - BOSLUK) - i1)
    i0, i1 = satir_E(E, ('isim1', 'isim2'))
    k_alt = i0 - BOSLUK
    for ad in ('kucuk_sol', 'kucuk_sag'):
        b = kutu_E(E, ad)
        kaydir(E, (ad,), k_alt - b[3])                                     # satirin altina yasli
    ust = int(k_alt - h_max)
    return E, dict(tarih_alt=t[3], tarih_ust=t[1], isim_ust=i0, isim_alt=i1, kucuk_alt=k_alt, kucuk_ust_sabit=ust, sembol_alt_sinir=ust - BOSLUK,
                   h_max=int(h_max))


def _uyar(pts_x, pts_y, bcx, bcy, s, cx, cy):
    """kaynak murekkep noktalari (kutu merkezine gore) -> 954 konum (merkez cx, cy) olcek s."""
    return cx + (pts_x - bcx) * s, cy + (pts_y - bcy) * s


def b3_olcek(ana_a, sinir_alt, ust_min=UST_MIN):
    """Y3 (alanin dikey ortasi, yatay 476) yerlesiminde sigan en buyuk olcek (ikili arama, murekkep alfa > 0,5 noktalariyla):
    ust >= ust_min, alt <= sinir_alt, halka ic dairesine pay >= 30 (r <= 306). Doner (s_max, ayrinti)."""
    ys, xs = np.nonzero(ana_a > 0.5)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    bcx, bcy = (x0 + x1) / 2, (y0 + y1) / 2
    px, py = xs + 0.5, ys + 0.5
    if len(px) > 400000:                                                   # hiz: kenar noktalari yeterli (ic noktalar sinira ulasmaz)
        import cv2
        k = cv2.morphologyEx((ana_a > 0.5).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
        yy, xx = np.nonzero(k); px, py = xx + 0.5, yy + 0.5
    cy = (ust_min + sinir_alt) / 2.0
    lo, hi = 0.0, 4.0 * (sinir_alt - ust_min) / max(1, (y1 - y0))

    def sigar(s):
        X, Yy = _uyar(px, py, bcx, bcy, s, CX, cy)
        h = (y1 - y0) * s
        if cy - h / 2 < ust_min or cy + h / 2 > sinir_alt:
            return False
        return float(np.sqrt((X - HALKA_C[0]) ** 2 + (Yy - HALKA_C[1]) ** 2).max()) <= HALKA_R - HALKA_PAY
    for _ in range(40):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if sigar(m) else (lo, m)
    return lo, dict(kaynak_kutu=[int(x0), int(y0), int(x1), int(y1)], y3_merkez=cy)


def sembol_yerlestir(ana_rgba, sinir_alt, olcekle, ust_min=UST_MIN, b3_kat=B3_KAT, y2=Y2_UST_ORAN):
    """karar 4: B3 + Y2. olcekle(rgba, s) -> (rgb, a) (motor: o1.rgba_olcek). Doner ((rgb, a, x, y), ayrinti)."""
    a0 = ana_rgba[..., 3]
    s_max, d = b3_olcek(a0, sinir_alt, ust_min)
    s = s_max * b3_kat
    rgb, a = olcekle(ana_rgba, s)
    b = kutu(a)
    h, w = b[3] - b[1], b[2] - b[0]
    bos = (sinir_alt - ust_min) - h
    ust = ust_min + y2 * bos
    x = int(round(CX - (b[0] + b[2]) / 2.0))
    y = int(round(ust - b[1]))
    d.update(s_max=round(s_max, 6), s=round(s, 6), b3_kat=b3_kat, y2_ust_oran=y2, h=int(h), w=int(w), bos_dikey=round(float(bos), 2),
             ust_hedef=round(float(ust), 2))
    return (rgb, a, x, y), d


def kapilar(E, cizgi, d_sembol, h_max_gercek=None):
    """yeni duzen kapilari (olculur esik; tolerans TOL_PX / TOL_OLCEK). Doner (kapi: bool, olcum)."""
    s = kutu_E(E, 'sembol'); t = kutu_E(E, 'tarih')
    i0, i1 = satir_E(E, ('isim1', 'isim2')); k = [kutu_E(E, ad) for ad in ('kucuk_sol', 'kucuk_sag')]
    _, a, x, y = E['sembol']
    r_max = halka_max_r(a, x, y)
    bos = (cizgi['sembol_alt_sinir'] - UST_MIN) - (s[3] - s[1])
    ust_hedef = UST_MIN + Y2_UST_ORAN * bos
    olc = dict(sembol_kutu=list(s), sembol_ust=s[1], sembol_alt=s[3], sembol_alt_sinir=cizgi['sembol_alt_sinir'], halka_r_max=round(r_max, 2),
               halka_pay=round(HALKA_R - r_max, 2), yatay_merkez=(s[0] + s[2]) / 2.0, tarih_kutu=list(t), tarih_alt=t[3],
               bosluk_tarih_isim=t[1] - i1, bosluk_isim_kucuk=i0 - max(b[3] for b in k), kucuk_alt=[b[3] for b in k],
               kucuk_ust_sabit=cizgi['kucuk_ust_sabit'], olcek_orani=round(d_sembol['s'] / d_sembol['s_max'], 6) if d_sembol['s_max'] else None,
               ust_hedef_y2=round(ust_hedef, 2))
    g = dict(ust_ge_230=s[1] >= UST_MIN,
             halka_pay_ge_30=(HALKA_R - r_max) >= HALKA_PAY,
             sembol_alt_le_sinir=s[3] <= cizgi['sembol_alt_sinir'],
             yatay_orta=abs((s[0] + s[2]) / 2.0 - CX) <= TOL_PX,
             b3_y2_oran=(abs(d_sembol['s'] / d_sembol['s_max'] - B3_KAT) <= TOL_OLCEK) and abs(s[1] - ust_hedef) <= TOL_PX,
             tarih_alt_795=abs(t[3] - TARIH_ALT) <= TOL_PX,
             bosluk_32_32=abs((t[1] - i1) - BOSLUK) <= TOL_PX and abs((i0 - max(b[3] for b in k)) - BOSLUK) <= TOL_PX,
             kucuk_alta_yasli=max(b[3] for b in k) - min(b[3] for b in k) <= TOL_PX)
    return {kk: bool(v) for kk, v in g.items()}, olc


def h_max_12(h_oran, cap, burclar):
    """karar 3: 12 kucuk isaretin en yuksegi (nominal: h_oran x cap; motor gercek alfa kutusundan da olcer)."""
    return max(h_oran(b) * cap for b in burclar)


def yeni_yerlesim(yazi_blogu, olcekle, T, kc, ana_rgba, h_max):
    """tam yeni yerlesim (motor ve yerel test ayni yol). Doner (E, cizgi, d_sembol, kapi, olcum)."""
    E, cizgi = yazi_yerlestir(yazi_blogu, T, kc, h_max)
    sem, d = sembol_yerlestir(ana_rgba, cizgi['sembol_alt_sinir'], olcekle)
    E['sembol'] = sem
    g, olc = kapilar(E, cizgi, d)
    return E, cizgi, d, g, olc
