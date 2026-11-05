#!/usr/bin/env python3
"""YENI DUZEN (Serdar 4 Kas aksam; KARARLAR_20261104_2, ORNAMENT_YERLESIM78_SECIM) geometri modulu. Motor (ornament_motor.py, YENI_DUZEN=1)
ve yerel test (yeni_duzen_yerel_test.py) AYNI fonksiyonlari cagirir. Eski davranis bu modulu cagirmaz (varsayilan YENI_DUZEN=0).

Asama 1b (Serdar 4 Kas gece "katilıyorum"; PLAN_YENI_DUZEN.md 8. bolum bulgulari):
  K2  dikey cizgiler SABIT referans metinden (EMILY / JAMES / JUNE 14, 2025) BIR KEZ hesaplanir; her siparisin isim ve tarihi
      referansin TABAN CIZGISINE oturur (harf kutusuna degil). Boylece J / Q inisi sembol yerini oynatmaz.
  K3  kapilar sabit beklenen degerlere (SABIT) baglanir; kodun o an kurdugu cizgiye degil. Referans cizgi SABIT'ten saparsa ref_cizgi_sabit FAIL.
  K1  B3 olcegi CIZILEN piksellerle bulunur (render ile ikili arama, O2); kapi yerlestirme sozlugunu okumaz: en buyuk olcegi yeniden
      hesaplar, x 0,85'te beklenen sembolu yeniden cizer ve CIZILEN sembolun kutusuyla (h, w) karsilastirir (1 px).
  D2  isim satiri = isim1 + isim2 + logo (sonsuz) birlesimi (karar 2 "isim + logo satiri").
  D8  yatay merkez 475,5 (halka ic dairesi merkezi; Serdar karari 3).
  O6  H_MAX nominal degerin yukari yuvarlanmisi; kucuk isaret ustu sabit cizginin ustune cikamaz (kapi).
  O5  hedef_kapat yeni yolda da uygulanir (kapat parametresi).
Tanimlar (954 px tuval, 11,8 px/mm):
  kutu        = alfa > 0,5 sinir kutusu (piksel indeksi + 1 = alt / sag)
  halka ic    = merkez (475,5, 504), r 336; alt noktasi y 840
  karar 1     referans tarihin kutu alti = 795 (840 - 45)
  karar 2     referans metinde: tarih ustu - isim satiri alti = 32; isim satiri ustu - kucuk satir alti = 32
  karar 3     kucuk satir USTU SABIT = kucuk alt - H_MAX; sembol alt siniri = ust cizgi - 32
  karar 4     sembol yatayda ortali; ust >= 230, alt <= sinir, halka payi >= 30 (r <= 306); B3 = Y3'te sigan en buyuk x 0,85; Y2 = bos dikeyin %75'i ustte
  karar 5     tarih "JUNE 14, 2025" (TARIH_YENI)"""
import math

import numpy as np

N = 954
HALKA_C = (475.5, 504.0)
HALKA_R = 336.0
HALKA_PAY = 30.0
TARIH_ALT = 795
BOSLUK = 32
UST_MIN = 230
CX = 475.5                                                                 # Serdar 4 Kas gece karar 3 (D8): halka merkezi
B3_KAT = 0.85
Y2_UST_ORAN = 0.75
TARIH_YENI = 'JUNE 14, 2025'
TARIH_ESKI = '14 JUNE 2025'
REF_ISIM = ('EMILY', 'JAMES')
TOL_PX = 1.0
RENDER_ADIM = 18                                                           # ikili arama adimi (aralik s0; 2^-18 goreli, piksel altinda)
# K3: referans cizgilerin beklenen degerleri (asama 1b yerel olcumu, yeni_duzen_yerel_test.py; motor ve test bunlara karsi denetler).
# Bu degerler degisirse kapi FAIL verir; degistirmek ayri karar (gevsetme degil, yeni olcum + Serdar onayi).
SABIT = dict(tarih_alt=795, tarih_ust=764, tarih_taban=787.5, isim_ust=695, isim_alt=732, isim_taban=724.0, isim_taban_esit=True,
             sonsuz_y=696, kucuk_alt=663, kucuk_ust_sabit=594, sembol_alt_sinir=562, h_max=69)   # 4 Kas gece yerel olcum, Pillow 11.0.0 (is akisi surumu; 12.3.0'da tarih_taban 787.75: surum farki kapida yakalanir)


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


def kaydir_x(E, adlar, dx):
    for ad in adlar:
        rgb, a, x, y = E[ad]
        E[ad] = (rgb, a, int(x + dx), y)


def halka_max_r(a, x, y, esik=0.5):
    """alfa > esik murekkep piksellerinin halka ic dairesi merkezine en buyuk uzakligi (piksel merkezi)."""
    ys, xs = np.nonzero(a > esik)
    if not len(xs):
        return 0.0
    return float(np.sqrt(((xs + x + 0.5) - HALKA_C[0]) ** 2 + ((ys + y + 0.5) - HALKA_C[1]) ** 2).max())


def h_max_12(h_oran, cap, burclar):
    """karar 3 (O6): 12 kucuk isaretin nominal en yuksegi (h_oran x cap), yukari yuvarlanmis tam sayi. Gercek isaret bu cizgiyi
    en fazla TOL_PX asabilir (kapi kucuk_ust_ge_sabit)."""
    return int(math.ceil(max(h_oran(b) * cap for b in burclar) - 1e-9))


ISIM_SATIRI = ('isim1', 'isim2', 'sonsuz')                                 # D2: karar 2 "isim + logo satiri"


def referans_cizgi(yazi_blogu, T_ref, kc, h_max):
    """K2: referans metinle (EMILY / JAMES / JUNE 14, 2025) dikey cizgiler. Kutu tabanli yerlesim yalniz BURADA, bir kez.
    Doner dict: tarih_alt, tarih_ust, tarih_taban, isim_ust, isim_alt, isim_taban, sonsuz_y, kucuk_alt, kucuk_ust_sabit, sembol_alt_sinir, h_max."""
    E, _ = yazi_blogu(T_ref, kc, TARIH_ALT, 0.45, 0.40)
    t = kutu_E(E, 'tarih')
    kaydir(E, ('tarih',), TARIH_ALT - t[3])
    t = kutu_E(E, 'tarih')
    i0, i1 = satir_E(E, ISIM_SATIRI)
    kaydir(E, ISIM_SATIRI, (t[1] - BOSLUK) - i1)
    i0, i1 = satir_E(E, ISIM_SATIRI)
    k_alt = i0 - BOSLUK
    ust = int(k_alt - h_max)
    taban1 = E['isim1'][3] + T_ref['isim1'][1]
    taban2 = E['isim2'][3] + T_ref['isim2'][1]
    return dict(tarih_alt=int(t[3]), tarih_ust=int(t[1]), tarih_taban=round(float(E['tarih'][3] + T_ref['tarih'][1]), 3),
                isim_ust=int(i0), isim_alt=int(i1), isim_taban=round(float(taban1), 3), isim_taban_esit=abs(taban1 - taban2) < 1e-6,
                sonsuz_y=int(E['sonsuz'][3]), kucuk_alt=int(k_alt), kucuk_ust_sabit=ust, sembol_alt_sinir=ust - BOSLUK, h_max=int(h_max))


def yazi_yerlestir(yazi_blogu, T, kc, ref):
    """karar 1-3 (K2): yataylar yazi_blogu'ndan (karar 3: boy ve yatay yer degismez); dikeyler referans taban cizgisinden.
    Doner (E, tabanlar) tabanlar = {ad: E koordinatinda taban y}."""
    E, _ = yazi_blogu(T, kc, TARIH_ALT, 0.45, 0.40)
    tab = {}
    for ad, ref_t in (('tarih', ref['tarih_taban']), ('isim1', ref['isim_taban']), ('isim2', ref['isim_taban'])):
        rgb, a, x, _ = E[ad]
        E[ad] = (rgb, a, x, int(round(ref_t - T[ad][1])))
        tab[ad] = E[ad][3] + T[ad][1]
    rgb, a, x, _ = E['sonsuz']
    E['sonsuz'] = (rgb, a, x, int(ref['sonsuz_y']))
    for ad in ('kucuk_sol', 'kucuk_sag'):
        b = kutu_E(E, ad)
        kaydir(E, (ad,), ref['kucuk_alt'] - b[3])                          # satirin altina yasli
    return E, tab


def _uyar(pts_x, pts_y, bcx, bcy, s, cx, cy):
    """kaynak murekkep noktalari (kutu merkezine gore) -> 954 konum (merkez cx, cy) olcek s."""
    return cx + (pts_x - bcx) * s, cy + (pts_y - bcy) * s


def b3_olcek(ana_a, sinir_alt, ust_min=UST_MIN):
    """YERLESTIRME: Y3 (alanin dikey ortasi, yatay CX) yerlesiminde sigan en buyuk olcek (ikili arama, murekkep alfa > 0,5 noktalariyla,
    surekli model): ust >= ust_min, alt <= sinir_alt, halka payi >= 30 (r <= 306). Doner (s_max, ayrinti)."""
    ys, xs = np.nonzero(ana_a > 0.5)
    if not len(xs) or sinir_alt <= ust_min:                                 # D7: bos sembol ya da ters alan
        return 0.0, dict(kaynak_kutu=None, y3_merkez=None, hata='bos sembol ya da alan')
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


def y3_sigar(ana_rgba, sinir_alt, olcekle, s, ust_min=UST_MIN):
    """olcek s'de cizilen sembol Y3 (alanin dikey ortasi) + yatay CX tam sayi konumda: ust >= ust_min, alt <= sinir_alt, halka payi >= 30."""
    cy = (ust_min + sinir_alt) / 2.0
    rgb, a = olcekle(ana_rgba, s)
    b = kutu(a)
    if b is None:
        return False
    h = b[3] - b[1]
    x = int(round(CX - (b[0] + b[2]) / 2.0)); y = int(round(cy - h / 2.0 - b[1]))
    if y + b[1] < ust_min or y + b[3] > sinir_alt:
        return False
    return halka_max_r(a, x, y) <= HALKA_R - HALKA_PAY


def b3_olcek_render(ana_rgba, sinir_alt, olcekle, s0, ust_min=UST_MIN, adim=RENDER_ADIM):
    """B3 (O2): sembol gercekten olceklenip (olcekle) tam sayi konuma Y3 + yatay CX ile konur; ust, alt ve halka payi CIZILEN alfa ile
    olculur. s0 (nokta modeli b3_olcek) yalniz arama araligini verir: [0,5 s0, 1,5 s0]; sonuc aralik kenarindaysa 'kenar' True (kapi FAIL).
    Doner (s_max_render, ayrinti)."""
    if s0 <= 0:
        return 0.0, dict(kenar=True)

    def sigar(s):
        return y3_sigar(ana_rgba, sinir_alt, olcekle, s, ust_min)
    lo, hi = 0.5 * s0, 1.5 * s0
    if not sigar(lo):
        return 0.0, dict(kenar=True)
    for _ in range(adim):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if sigar(m) else (lo, m)
    return lo, dict(kenar=bool(hi >= 1.5 * s0 * (1 - 1e-6)), aralik=[round(0.5 * s0, 6), round(1.5 * s0, 6)])


def sembol_yerlestir(ana_rgba, sinir_alt, olcekle, ust_min=UST_MIN, b3_kat=B3_KAT, y2=Y2_UST_ORAN, kapat=None):
    """karar 4: B3 + Y2. olcekle(rgba, s) -> (rgb, a) (motor: o1.rgba_olcek). kapat(rgb, a) -> (rgb, a, n) (O5; motor: o5.hedef_kapat, n dict: alfa_lt_09, degisen_alfa_gt_002, degisen_alfa_gt_03).
    Doner ((rgb, a, x, y), ayrinti)."""
    a0 = ana_rgba[..., 3]
    s_p, d = b3_olcek(a0, sinir_alt, ust_min)
    s_max, d_r = b3_olcek_render(ana_rgba, sinir_alt, olcekle, s_p, ust_min)
    d.update(s_nokta_max=round(s_p, 6), render_kenar=d_r.get('kenar'))
    s = s_max * b3_kat
    rgb, a = olcekle(ana_rgba, s)
    if kapat is not None:
        rgb, a, n_ = kapat(rgb, a)
        d['hedef_kapatilan'] = n_ if isinstance(n_, dict) else int(n_)   # o5.hedef_kapat dict doner (eski yol da dict yazar: ornament_ornek5.py:384)
    b = kutu(a)
    h, w = b[3] - b[1], b[2] - b[0]
    bos = (sinir_alt - ust_min) - h
    ust = ust_min + y2 * bos
    x = int(round(CX - (b[0] + b[2]) / 2.0))
    y = int(round(ust - b[1]))
    d.update(s_max=round(s_max, 6), s=round(s, 6), b3_kat=b3_kat, y2_ust_oran=y2, h=int(h), w=int(w), bos_dikey=round(float(bos), 2),
             ust_hedef=round(float(ust), 2))
    return (rgb, a, x, y), d


def kapilar(E, ana_rgba, olcekle, tabanlar, sabit, ref_metin, kapat=None):
    """yeni duzen kapilari. K3: cizgiler 'sabit'ten (SABIT), yerlestirme sozlugunden degil. K1: B3 olcegi yeniden hesaplanir (sabit sinirla),
    beklenen sembol x 0,85'te yeniden cizilir (kapat dahil) ve CIZILEN sembolun kutusu (h, w) ile 1 px icinde karsilastirilir.
    ref_metin True ise (motorun EMILY / JAMES / JUNE 14, 2025 ornegi) murekkep kutusu kapilari da (tarih alt 795, 32 / 32). Doner (kapi: bool, olcum)."""
    s = kutu_E(E, 'sembol')
    _, a, x, y = E['sembol']
    r_max = halka_max_r(a, x, y)
    sinir = sabit['sembol_alt_sinir']
    h_d, w_d = s[3] - s[1], s[2] - s[0]
    s_p, _ = b3_olcek(ana_rgba[..., 3], sinir)
    s_r, d_r = b3_olcek_render(ana_rgba, sinir, olcekle, s_p)
    be = None
    if s_r > 0:
        rgb_e, a_e = olcekle(ana_rgba, s_r * B3_KAT)
        if kapat is not None:
            rgb_e, a_e, _ = kapat(rgb_e, a_e)
        be = kutu(a_e)
    h_e, w_e = (be[3] - be[1], be[2] - be[0]) if be else (None, None)
    en_buyuk = bool(s_r > 0 and y3_sigar(ana_rgba, sinir, olcekle, s_r) and not y3_sigar(ana_rgba, sinir, olcekle, s_r * 1.01))   # B3 tanimi: sigan en buyuk
    bos = (sinir - UST_MIN) - h_d
    ust_hedef = UST_MIN + Y2_UST_ORAN * bos
    k = {ad: kutu_E(E, ad) for ad in ('kucuk_sol', 'kucuk_sag')}
    olc = dict(sembol_kutu=list(s), sembol_ust=s[1], sembol_alt=s[3], sembol_alt_sinir=sinir, halka_r_max=round(r_max, 2),
               halka_pay=round(HALKA_R - r_max, 2), yatay_merkez=(s[0] + s[2]) / 2.0, sembol_hw=[int(h_d), int(w_d)], beklenen_hw=[h_e, w_e],
               olcek_render_max=round(s_r, 6), olcek_nokta_max=round(s_p, 6), render_nokta_orani=round(s_r / s_p, 6) if s_p else None,
               render_kenar=d_r.get('kenar'), ust_hedef_y2=round(ust_hedef, 2),
               tabanlar={kk: round(float(v), 3) for kk, v in tabanlar.items()}, sonsuz_y=int(E['sonsuz'][3]),
               kucuk_alt=[b[3] for b in k.values()], kucuk_ust=[b[1] for b in k.values()], kucuk_ust_sabit=sabit['kucuk_ust_sabit'])
    g = dict(ust_ge_230=s[1] >= UST_MIN,
             halka_pay_ge_30=(HALKA_R - r_max) >= HALKA_PAY,
             sembol_alt_le_sinir=s[3] <= sinir,
             yatay_orta=abs((s[0] + s[2]) / 2.0 - CX) <= TOL_PX,
             b3_olcek=(be is not None) and not d_r.get('kenar') and abs(h_d - h_e) <= TOL_PX and abs(w_d - w_e) <= TOL_PX,
             b3_en_buyuk=en_buyuk,
             y2_ust=abs(s[1] - ust_hedef) <= TOL_PX,
             tarih_taban=abs(tabanlar['tarih'] - sabit['tarih_taban']) <= 0.5 + 1e-6,
             isim_taban=all(abs(tabanlar[ad] - sabit['isim_taban']) <= 0.5 + 1e-6 for ad in ('isim1', 'isim2')),
             sonsuz_y=int(E['sonsuz'][3]) == sabit['sonsuz_y'],
             kucuk_alta_yasli=all(abs(b[3] - sabit['kucuk_alt']) <= TOL_PX for b in k.values()),
             kucuk_ust_ge_sabit=all(b[1] >= sabit['kucuk_ust_sabit'] - TOL_PX for b in k.values()))
    if ref_metin:
        t = kutu_E(E, 'tarih')
        i0, i1 = satir_E(E, ISIM_SATIRI)
        olc.update(tarih_kutu=list(t), tarih_alt=t[3], bosluk_tarih_isim=t[1] - i1, bosluk_isim_kucuk=i0 - max(b[3] for b in k.values()))
        g.update(tarih_alt_795=abs(t[3] - TARIH_ALT) <= TOL_PX,
                 bosluk_32_32=abs((t[1] - i1) - BOSLUK) <= TOL_PX and abs((i0 - max(b[3] for b in k.values())) - BOSLUK) <= TOL_PX)
    return {kk: bool(v) for kk, v in g.items()}, olc


def ref_esit(ref, sabit):
    """K3: o an hesaplanan referans cizgiler SABIT ile birebir mi (tam sayilar esit, tabanlar 0,01 px)."""
    if sabit is None:
        return False
    for kk, v in sabit.items():
        if kk not in ref:
            return False
        if isinstance(v, float):
            if abs(ref[kk] - v) > 0.01:
                return False
        elif ref[kk] != v:
            return False
    return True


def yeni_yerlesim(yazi_blogu, olcekle, T, kc, ana_rgba, h_max, T_ref=None, kapat=None, sabit=None):
    """tam yeni yerlesim (motor ve yerel test ayni yol). T_ref None ise T referans metindir (motor ornegi).
    Doner (E, cizgi, d_sembol, kapi, olcum)."""
    ref_metin = T_ref is None
    ref = referans_cizgi(yazi_blogu, T if ref_metin else T_ref, kc, h_max)
    sabit_ = sabit if sabit is not None else (SABIT if SABIT is not None else ref)
    E, tab = yazi_yerlestir(yazi_blogu, T, kc, ref)
    sem, d = sembol_yerlestir(ana_rgba, ref['sembol_alt_sinir'], olcekle, kapat=kapat)
    E['sembol'] = sem
    g, olc = kapilar(E, ana_rgba, olcekle, tab, sabit_, ref_metin, kapat=kapat)
    g['ref_cizgi_sabit'] = bool(ref_esit(ref, SABIT if sabit is None else sabit))
    olc['ref_cizgi'] = ref
    return E, ref, d, g, olc
