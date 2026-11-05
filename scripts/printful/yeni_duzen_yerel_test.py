#!/usr/bin/env python3
"""YENI DUZEN yerel geometri testi (Serdar 4 Kas aksam; asama 1 D, asama 1b K1-K3 / O3 / O4 / D2 / D5 / D8 ve isim olcumu).
Motor girdisi yalniz Actions'ta: ana sembol yerine motor 6da763a motor_gpt/girdi78/ana/<cift>_alfa.png (poster alfa maskesi; motorun okudugu
<CIFT>_ana.png ile ayni sinir kutusu DOGRULANMADI: acik soru 2). Kucuk isaretler: cancer / libra gercek kaynak (docs/ornament/kaynak),
digerleri motorun hedef yuksekligiyle (h_oran x cap) dikdortgen benzetim. Yazilar motorla ayni (o1.metin_alfa, Cinzel / EBGaramond-Italic
TEK_DOKU 2a08a78; LOGO_1 6da763a). Halka: o5.halka_T (HALKA_BLUE 2a08a78).
Olcer:
  - referans cizgiler (K2) ve SABIT esitligi (K3); SABIT tanimsizsa olculen degerleri yazar ve cikis 3
  - 78/78 yeni_duzen.kapilar + o4.kapi
  - bilinen FAIL: 3 cift (CANCER_LIBRA, LEO_SAGITTARIUS, LIBRA_LIBRA) x her kapi icin bir negatif vaka (O3); vaka CIZIMI degistirir (K1)
  - en genis tarih (12 ay x 31 gun x 2000-2035); sigmazsa cikis 1 (O4)
  - en uzun isim (W x N), verilen isimler, SSA en sik 200 isimle cift sigma orani ve 8 / 10 harf icin gereken isim kuculmesi (Serdar karari 2)
  - KONTAK.jpg (11 cift RUBY benzetim)
Cikis: 0 hepsi PASS ve tum bilinen FAIL beklenen kapidan; 1 degil; 2 cokus; 3 SABIT olculdu (sabitlenmeli).
Kullanim: yeni_duzen_yerel_test.py --cikti DIR [--girdi DIR] [--tarih_hizli]  (girdi: maske ve font; varsayilan /tmp/yd_girdi, dala girmez: D5)"""
import argparse
import csv
import importlib.util
import itertools
import json
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

_d = Path(__file__).resolve().parent
_k = _d.parent.parent
MOTOR_C = '6da763aa5b9820027420f73264fc69d30e120a33'
TEK_C = '2a08a78216ca19dd632e7dedda31c4c53c365c25'
ORNEK11 = ['TAURUS_TAURUS', 'CANCER_TAURUS', 'AQUARIUS_CANCER', 'LIBRA_LIBRA', 'AQUARIUS_AQUARIUS', 'ARIES_SCORPIO', 'LEO_SAGITTARIUS',
           'CAPRICORN_CAPRICORN', 'CANCER_LIBRA', 'AQUARIUS_PISCES', 'GEMINI_VIRGO']
BF_CIFT = ('CANCER_LIBRA', 'LEO_SAGITTARIUS', 'LIBRA_LIBRA')              # O3: dikeyde ve halkada sinirlanan ciftler
BF_VAKA = 15                                                              # cift basina bilinen FAIL vakasi (K-1b-10; uretim78_beklenen 45 ile ayni)
AYLAR = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER']
SSA = _k / 'data/ornament/ssa_century_top100.csv'                          # resmi kaynak: ssa.gov/oact/babynames/decades/century.html (1926-2025)


def git_bayt(rev, yol):
    return subprocess.run(['git', '-C', str(_k), 'show', f'{rev}:{yol}'], capture_output=True, check=True).stdout


def yukle(ad, dosya):
    s = importlib.util.spec_from_file_location(ad, _d / dosya); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--cikti', required=True); ap.add_argument('--girdi', default='/tmp/yd_girdi')
    ap.add_argument('--tarih_hizli', action='store_true')
    ap.add_argument('--yalniz_kapi', action='store_true', help='is akisi hazirlik adimi: yalniz SABIT, 78/78 ve bilinen FAIL (tarih, isim, kontak yok)')
    a = ap.parse_args(); O = Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
    W = Path(a.girdi); W.mkdir(parents=True, exist_ok=True)
    for ad, rev, yol in (('Cinzel.ttf', TEK_C, 'motor/font/Cinzel.ttf'), ('EBGaramond-Italic.ttf', TEK_C, 'motor/font/EBGaramond-Italic.ttf'),
                         ('HALKA_BLUE_16x20.png', TEK_C, 'motor/varlik/halka/HALKA_BLUE_16x20.png'), ('LOGO_1.png', MOTOR_C, 'motor_gpt/girdi/LOGO_1.png')):
        if not (W / ad).exists():
            (W / ad).write_bytes(git_bayt(rev, yol))
    al = yukle('altin', 'ornament_altin.py'); o1, o3, o4, o5, son = al.o1, al.o3, al.o4, al.o5, al.son
    mo = yukle('motor', 'ornament_motor.py'); yd = yukle('yd', 'yeni_duzen.py')
    o4.YASAK = o4.yasak_m(); o3.YASAK = o4.YASAK
    KAPAT = (lambda r_, a_: o5.hedef_kapat(r_, a_)) if o5.KAPAT_HEDEF else None   # K-1b-2: motorla ayni yol (ornament_motor.py kapat_); eskiden test kapatsiz kosuyordu
    o4.GLOW_K = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * o4.GLOW_R + 1,) * 2)
    Pc, cap = o5.P, o4.CAP0
    lsrc = o4.logo_kaynak(W / 'LOGO_1.png')

    def logo():
        kk = cap * o4.LOGO_H / lsrc.shape[0]
        sz = (max(1, int(round(lsrc.shape[1] * kk))), max(1, int(round(cap * o4.LOGO_H))))
        return np.clip(cv2.resize(lsrc, sz, interpolation=cv2.INTER_AREA if kk <= 1 else cv2.INTER_CUBIC), 0, 1)
    tcap = Pc['tagline_T'] / Pc['cap'] * cap

    def T_(i1=yd.REF_ISIM[0], i2=yd.REF_ISIM[1], tarih=yd.TARIH_YENI, isim_k=1.0):
        return dict(isim1=o1.metin_alfa(i1, W / 'Cinzel.ttf', cap * isim_k, 500), isim2=o1.metin_alfa(i2, W / 'Cinzel.ttf', cap * isim_k, 500),
                    tarih=o1.metin_alfa(tarih, W / 'EBGaramond-Italic.ttf', tcap, None, ref='T'), sonsuz=logo(), cap=cap)

    def h_oran(b):
        if b == 'CANCER':
            return Pc['kucuk_sol_h'] / Pc['cap']
        if b == 'LIBRA':
            return Pc['kucuk_sag_h'] / Pc['cap']
        return mo.SPRITE_H[b] * mo.SPRITE_C / Pc['cap']
    gercek = {}

    def kucuk(b, k=1.0):
        hb_ = h_oran(b) * cap * k
        f = _k / 'docs/ornament/kaynak' / f'{b.lower()}_symbol_gold.png'
        if f.exists():
            if b not in gercek:
                g = np.asarray(Image.open(f).convert('RGBA'), np.float32); g[..., 3] /= 255.0
                g = o1.kirp(g, g[..., 3], pad=2); g, _ = o5.delik_kapat(g); gercek[b] = g
            g = gercek[b]; bb = o1.bbox(g[..., 3], 0.5)
            rgb_, a_ = o1.rgba_olcek(g, hb_ / (bb[3] - bb[1]))
            return rgb_, a_
        h = int(round(hb_)); a_ = np.zeros((h + 4, h + 4), np.float32); a_[2:2 + h, 2:2 + h] = 1.0
        return np.zeros(a_.shape + (3,), np.float32), a_
    BURC = sorted(mo.SPRITE_H)
    h_max = yd.h_max_12(h_oran, cap, BURC)
    pp = o4.poster_profil(W / 'HALKA_BLUE_16x20.png')
    ha, hb = o5.halka_T(pp, son.S0)
    CIFT78 = sorted('_'.join(sorted(p)) for p in itertools.combinations_with_replacement(BURC, 2))
    ana_onbellek = {}

    def ana(c):
        if c in ana_onbellek:
            return ana_onbellek[c]
        f = W / f'{c.lower()}_alfa.png'
        if not f.exists():
            f.write_bytes(git_bayt(MOTOR_C, f'motor_gpt/girdi78/ana/{c.lower()}_alfa.png'))
        m = np.asarray(Image.open(f).convert('L'), np.float32) / 255.0
        g = np.dstack([np.full(m.shape + (3,), (212, 170, 90), np.float32), m])
        g = o1.kirp(g, g[..., 3], pad=2)
        if g.shape[1] > 1600:
            r_, a_ = o1.rgba_olcek(g, 1600 / g.shape[1]); g = np.dstack([r_, a_])
        g, _ = o5.delik_kapat(g)
        if c in BF_CIFT:                                                       # bellek: yalniz tekrar kullanilan 3 cift (78 x ~40 MB tasar)
            ana_onbellek[c] = g
        return g

    def o4_kapi(E):
        E2 = dict(E); E2['halka'] = (None, ha, 0, 0)
        _, yb, cak, ok = o4.kapi(E2)
        return bool(ok), yb, cak[:6]
    T0 = T_()
    # --- referans cizgiler ve SABIT (K2, K3) ---
    kc0 = {'sol': kucuk('CANCER'), 'sag': kucuk('LIBRA')}
    REF = yd.referans_cizgi(o3.yazi_blogu, T0, kc0, h_max)
    if yd.SABIT is None:
        (O / 'SABIT_OLCULEN.json').write_text(json.dumps(REF, indent=1, ensure_ascii=False))
        print('SABIT tanimsiz; olculen referans cizgiler:', json.dumps(REF)); return 3
    ref_sabit = yd.ref_esit(REF, yd.SABIT)
    SONUC, E11 = {}, {}
    t0 = time.time()
    for i, c in enumerate(CIFT78):
        b1, b2 = c.split('_')
        kc = {'sol': kucuk(b1), 'sag': kucuk(b2)}
        E, cizgi, d, g, olc = yd.yeni_yerlesim(o3.yazi_blogu, o1.rgba_olcek, T0, kc, ana(c), h_max, kapat=KAPAT)
        ok, yb, cak = o4_kapi(E)
        g['o4_kapi'] = ok
        SONUC[c] = dict(gecti=all(g.values()), kapi=g, olcum=olc, sembol=d, o4=dict(yasak=yb, cakisma=cak))
        if c in ORNEK11:
            E11[c] = E
        if (i + 1) % 13 == 0:
            print(f'ETA {i + 1}/78 gecen {time.time() - t0:.0f} sn kalan~{(time.time() - t0) / (i + 1) * (78 - i - 1):.0f} sn', flush=True)
    fail = sorted(c for c, v in SONUC.items() if not v['gecti'])
    # --- bilinen FAIL (O3): her vaka CIZIMI degistirir, kapi fonksiyonu yerlesim sozlugunu degil cizimi olcer (K1, K3) ---
    BF = []

    def tum(E):
        """kapi + o4 (cizim degismis E icin; tabanlar E'nin kendisinden)."""
        tab_ = {ad: E[ad][3] + T0[ad][1] for ad in ('tarih', 'isim1', 'isim2')}
        g, _ = yd.kapilar(E, A, o1.rgba_olcek, tab_, yd.SABIT, True, kapat=KAPAT)
        g['o4_kapi'] = o4_kapi(E)[0]
        return g

    def vaka(cift, ad, beklenen, E):
        """beklenen: kapi adi ya da adlar (biri FAIL vermeli)."""
        g = tum(E)
        fl = [kk for kk, v in g.items() if not v]
        bk_ = (beklenen,) if isinstance(beklenen, str) else tuple(beklenen)
        BF.append(dict(cift=cift, vaka=ad, beklenen=list(bk_), fail=fl, gecti=any(x in fl for x in bk_)))
    for c in BF_CIFT:
        b1, b2 = c.split('_'); kc = {'sol': kucuk(b1), 'sag': kucuk(b2)}; A = ana(c)
        E, cizgi, d, g, olc = yd.yeni_yerlesim(o3.yazi_blogu, o1.rgba_olcek, T0, kc, A, h_max, kapat=KAPAT)
        s = yd.kutu_E(E, 'sembol')
        e = dict(E); yd.kaydir(e, ('sembol',), 229 - s[1]); vaka(c, 'sembol ustu 229', 'ust_ge_230', e)
        e = dict(E); yd.kaydir(e, ('sembol',), (yd.SABIT['sembol_alt_sinir'] + 2) - s[3]); vaka(c, 'sembol alti sinir + 2', 'sembol_alt_le_sinir', e)
        e = dict(E); yd.kaydir_x(e, ('sembol',), 3); vaka(c, 'sembol 3 px saga', 'yatay_orta', e)
        e = dict(E); yd.kaydir(e, ('sembol',), -4 if s[1] - 4 >= yd.UST_MIN else 4); vaka(c, 'sembol 4 px kaydi (Y2)', 'y2_ust', e)
        for kat, ad in ((0.90, 'B3 0,90 cizildi'), (0.80, 'B3 0,80 cizildi')):
            sem, _ = yd.sembol_yerlestir(A, yd.SABIT['sembol_alt_sinir'], o1.rgba_olcek, b3_kat=kat, kapat=KAPAT)
            e = dict(E); e['sembol'] = sem; vaka(c, ad, 'b3_olcek', e)
        rgb_, a_ = o1.rgba_olcek(A, d['s'] * 1.25); bb = yd.kutu(a_)
        e = dict(E); e['sembol'] = (rgb_, a_, int(round((s[0] + s[2]) / 2 - (bb[0] + bb[2]) / 2)), int(round((s[1] + s[3]) / 2 - (bb[1] + bb[3]) / 2)))
        vaka(c, 'olcek x 1,25 ayni merkez', 'halka_pay_ge_30' if c == 'LIBRA_LIBRA' else ('halka_pay_ge_30', 'ust_ge_230', 'sembol_alt_le_sinir'), e)
        e = dict(E); yd.kaydir(e, ('tarih',), 5); vaka(c, 'tarih 5 px asagi', 'tarih_taban', e)
        e = dict(E); yd.kaydir(e, ('tarih',), 5); vaka(c, 'tarih 5 px asagi (murekkep)', 'tarih_alt_795', e)
        e = dict(E); yd.kaydir(e, ('isim1', 'isim2'), 3); vaka(c, 'isimler 3 px asagi', 'isim_taban', e)
        e = dict(E); yd.kaydir(e, ('isim1', 'isim2', 'sonsuz'), 3); vaka(c, 'isim satiri 3 px asagi', 'bosluk_32_32', e)
        e = dict(E); yd.kaydir(e, ('sonsuz',), 3); vaka(c, 'logo 3 px asagi', 'sonsuz_y', e)
        e = dict(E); yd.kaydir(e, ('kucuk_sag',), -3); vaka(c, 'sag kucuk 3 px yukari', 'kucuk_alta_yasli', e)
        kb = yd.kutu_E(E, 'kucuk_sag'); rgb_, a_ = kucuk(b2, (yd.SABIT['h_max'] + 3) / (kb[3] - kb[1])); e = dict(E); nb = yd.kutu(a_)
        e['kucuk_sag'] = (rgb_, a_, int(round((kb[0] + kb[2]) / 2 - (nb[0] + nb[2]) / 2)), int(kb[3] - nb[3]))
        vaka(c, 'sag kucuk H_MAX + 3 px, alta yasli', 'kucuk_ust_ge_sabit', e)
        e = dict(E); yd.kaydir(e, ('tarih',), 60); vaka(c, 'tarih 60 px asagi (halka)', 'o4_kapi', e)
    bf_hepsi = all(x['gecti'] for x in BF) and len(BF) == BF_VAKA * len(BF_CIFT)   # K-1b-10: eksik ya da fazla vaka da FAIL
    if a.yalniz_kapi:
        R = dict(not_='yalniz kapi (is akisi hazirlik); yerel benzetim: alfa maskesi, kucuk isaretler cancer/libra gercek, digerleri dikdortgen',
                 referans=REF, sabit=yd.SABIT, ref_sabit_esit=ref_sabit, fail=fail, gecen=78 - len(fail), bilinen_fail=BF, bilinen_fail_hepsi=bf_hepsi,
                 bilinen_fail_sayi=len(BF), kapi_ozet={c: [k for k, v in SONUC[c]['kapi'].items() if not v] for c in CIFT78})
        (O / 'YERLESIM78_TEST.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str))
        print('ref = SABIT', ref_sabit, '| 78 cift', 78 - len(fail), 'PASS | FAIL', fail, '| bilinen FAIL', sum(x['gecti'] for x in BF), '/', len(BF))
        return 0 if (ref_sabit and not fail and bf_hepsi) else 1
    # --- en genis tarih (O4: sigmazsa cikis 1) ---
    gun = range(1, 32); yil = range(2000, 2036)
    adaylar = [f'{m} {dd}, {yy}' for m in AYLAR for dd in gun for yy in yil]
    if a.tarih_hizli:                                                      # genislik ay ve gun basamagi ile baskin; yillardan 2000-2035 hepsi korunur
        adaylar = [f'{m} {dd}, {yy}' for m in AYLAR for dd in (1, 10, 11, 20, 22, 28, 30, 31) for yy in yil]
    gen = {}
    for s_ in adaylar:
        al_ = o1.metin_alfa(s_, W / 'EBGaramond-Italic.ttf', tcap, None, ref='T')[0]; b = yd.kutu(al_); gen[s_] = b[2] - b[0]
    en_s = max(gen, key=gen.get)

    def dene(T, c='CANCER_LIBRA'):
        b1, b2 = c.split('_'); kc = {'sol': kucuk(b1), 'sag': kucuk(b2)}
        E, cizgi, d, g, olc = yd.yeni_yerlesim(o3.yazi_blogu, o1.rgba_olcek, T, kc, ana(c), h_max, T_ref=T0, kapat=KAPAT)
        ok, yb, cak = o4_kapi(E)
        r = max(yd.halka_max_r(E[ad][1], E[ad][2], E[ad][3]) for ad in ('isim1', 'isim2', 'sonsuz', 'kucuk_sol', 'kucuk_sag', 'tarih'))
        return E, g, ok, yb, cak, r
    E, g, ok, yb, cak, r = dene(T_(tarih=en_s))
    _, at, xt, yt = E['tarih']; rt = yd.halka_max_r(at, xt, yt)
    tarih_sigar = bool(rt <= yd.HALKA_R and ok and all(g.values()))
    TARIH = dict(aday_sayisi=len(adaylar), tum_bilesim=not a.tarih_hizli, en_genis=en_s, genislik_px=int(gen[en_s]), genislik_mm=round(gen[en_s] / 11.8, 2),
                 ilk10=sorted(gen.items(), key=lambda kv: -kv[1])[:10], ornek=dict(dizgi=yd.TARIH_YENI, px=int(gen.get(yd.TARIH_YENI, -1))),
                 sigar=dict(halka_ic_r_max=round(rt, 2), o4_kapi=ok, yasak=yb, cakisma=cak, kapi=g, gecti=tarih_sigar))
    # --- isim (Serdar karari 2): W x N, verilen ciftler, SSA en sik 200 isim, 8 / 10 harf icin kuculme ---
    def isim_dene(i1, i2, k=1.0):
        E, g, ok, yb, cak, r = dene(T_(i1, i2, isim_k=k))
        b1, b2 = yd.kutu_E(E, 'isim1'), yd.kutu_E(E, 'isim2')
        return dict(isim1=i1, isim2=i2, isim_k=round(k, 4), halka_r_max=round(r, 2), o4_kapi=ok, yasak=yb, cakisma=cak, satir_x=[b1[0], b2[2]],
                    gecti=bool(r <= yd.HALKA_R and ok))
    ISIM = dict(W_testi=[], verilen=[], not_='harf sayisi tire / kesme isareti haric; sinir halka ic dairesi (r 336) + o4.kapi; W en genis buyuk harf (Cinzel); '
                                            'isim boyu karar 3 geregi sabit (isim_k = 1); k < 1 yalniz bilgi')
    N_W = None
    for n in range(3, 15):
        r_ = isim_dene('W' * n, 'W' * n); r_['harf'] = n; ISIM['W_testi'].append(r_)
        if r_['gecti']:
            N_W = n
    for i1, i2 in (('MAXIMILIAN', 'CHRISTOPHER'), ('ALEXANDRIA', 'ANNA'), ('MARY-JANE', "O'NEIL"), ('EMILY', 'JAMES'), ('QUINN', 'JOSEPH')):
        r_ = isim_dene(i1, i2); r_['harf'] = [sum(ch.isalpha() for ch in i1), sum(ch.isalpha() for ch in i2)]; ISIM['verilen'].append(r_)
    ISIM['N_W'] = N_W
    erkek, kadin = [], []
    with open(SSA, newline='') as fh:
        for row in csv.DictReader(fh):
            erkek.append(row['boy'].upper()); kadin.append(row['girl'].upper())
    tum_ad = sorted(set(erkek + kadin))
    gen_ad = {}
    for ad_ in tum_ad:
        A_, _ = o1.metin_alfa(ad_, W / 'Cinzel.ttf', cap, 500); b = yd.kutu(A_); gen_ad[ad_] = b[2] - b[0]
    # sigma yalniz w1 + w2'ye bagli mi: satir C'ye ortali (yazi_blogu), uclar toplam genislikle belirlenir; dogrulama: esik ciftlerinde iki yonde deneme
    ciftler = sorted({(x, y) for x in tum_ad for y in tum_ad}, key=lambda p: gen_ad[p[0]] + gen_ad[p[1]])
    lo, hi = 0, len(ciftler) - 1
    if not isim_dene(*ciftler[lo])['gecti']:
        esik = None
    elif isim_dene(*ciftler[hi])['gecti']:
        esik = gen_ad[ciftler[hi][0]] + gen_ad[ciftler[hi][1]]
    else:
        while hi - lo > 1:
            m = (lo + hi) // 2
            lo, hi = (m, hi) if isim_dene(*ciftler[m])['gecti'] else (lo, m)
        esik = gen_ad[ciftler[lo][0]] + gen_ad[ciftler[lo][1]]
    dogrula = []
    if esik is not None:
        yak = [p for p in ciftler if abs(gen_ad[p[0]] + gen_ad[p[1]] - esik) <= 6]
        for p in yak[::max(1, len(yak) // 12)][:12]:
            r_ = isim_dene(*p); dogrula.append(dict(cift=list(p), toplam=gen_ad[p[0]] + gen_ad[p[1]], gecti=r_['gecti'],
                                                    beklenen=gen_ad[p[0]] + gen_ad[p[1]] <= esik))
    monoton = all(x['gecti'] == x['beklenen'] for x in dogrula)

    def oran(liste):
        if esik is None:
            return 0.0
        return round(100.0 * sum(1 for p in liste if gen_ad[p[0]] + gen_ad[p[1]] <= esik) / max(1, len(liste)), 1)
    ek_ciftler = [(x, y) for x in erkek for y in kadin]
    tek = {ad_: dict(harf=len(ad_), px=gen_ad[ad_]) for ad_ in tum_ad}
    harf_tablosu = {}
    for n in range(3, 12):
        adlar = [ad_ for ad_ in tum_ad if len(ad_) == n]
        if adlar:
            en_gen = max(adlar, key=lambda z: gen_ad[z])
            harf_tablosu[n] = dict(ad_sayisi=len(adlar), en_genis=en_gen, px=gen_ad[en_gen],
                                   iki_en_genis_sigar=esik is not None and 2 * gen_ad[en_gen] <= esik)
    kucultme = {}
    for n in (8, 10):
        adlar = [ad_ for ad_ in tum_ad if len(ad_) == n]
        if not adlar:
            kucultme[n] = dict(not_='SSA listesinde bu uzunlukta ad yok'); continue
        en_gen = max(adlar, key=lambda z: gen_ad[z])
        lo_k, hi_k = 0.3, 1.0
        if isim_dene(en_gen, en_gen, 1.0)['gecti']:
            kucultme[n] = dict(ad=en_gen, gereken_k=1.0, kuculme_yuzde=0.0); continue
        for _ in range(14):
            m = (lo_k + hi_k) / 2
            lo_k, hi_k = (m, hi_k) if isim_dene(en_gen, en_gen, m)['gecti'] else (lo_k, m)
        kucultme[n] = dict(ad=en_gen, iki_isim=f'{en_gen} / {en_gen}', gereken_k=round(lo_k, 3), kuculme_yuzde=round(100 * (1 - lo_k), 1),
                           not_='bilgi; karar 3 geregi isim boyu degismez (Serdar karari olcumden sonra)')
    ISIM['ssa'] = dict(kaynak='ssa.gov/oact/babynames/decades/century.html (1926-2025, ilk 100 erkek + ilk 100 kadin; resmi kaynak)',
                       ad_sayisi=len(tum_ad), esik_toplam_px=esik, esik_monoton_dogrulama=dogrula, monoton=monoton,
                       oran_erkek_kadin_yuzde=oran(ek_ciftler), oran_tum_ciftler_yuzde=oran(ciftler),
                       tek_isim_sigar_yuzde_ayni_genislikte_es=round(100.0 * sum(1 for z in tum_ad if esik is not None and 2 * gen_ad[z] <= esik) / len(tum_ad), 1),
                       harf_tablosu=harf_tablosu, kucultme=kucultme, genislik=tek)
    # --- kontak (benzetim) ---
    tiles = []
    fnt = ImageFont.load_default()
    for c in ORNEK11:
        E = E11[c]; im = np.zeros((954, 954, 3), np.float32)
        yy, xx = np.mgrid[0:954, 0:954]; im[np.hypot(xx - 476, yy - 477) <= 449] = (110, 18, 30)
        for ad, (_, a_, x, y) in E.items():
            m, _ = o3.maske_yaz(a_, x, y); im = im * (1 - m[..., None]) + np.array((212, 170, 90), np.float32) * m[..., None]
        t = Image.fromarray(np.clip(im, 0, 255).astype(np.uint8)); dr = ImageDraw.Draw(t)
        dr.ellipse((475.5 - 336, 504 - 336, 475.5 + 336, 504 + 336), outline=(120, 120, 120))
        dr.line((0, yd.SABIT['sembol_alt_sinir'], 954, yd.SABIT['sembol_alt_sinir']), fill=(90, 90, 90))
        dr.line((0, 230, 954, 230), fill=(90, 90, 90))
        t = t.resize((400, 400), Image.LANCZOS); dr = ImageDraw.Draw(t)
        dr.text((6, 6), f'{c} BENZETIM {"PASS" if SONUC[c]["gecti"] else "FAIL"}', fill=(255, 255, 255), font=fnt)
        tiles.append(t)
    K = Image.new('RGB', (4 * 404, 3 * 404), (255, 255, 255))
    for i, t in enumerate(tiles):
        K.paste(t, ((i % 4) * 404, (i // 4) * 404))
    K.save(O / 'KONTAK.jpg', quality=85)
    R = dict(not_='YEREL BENZETIM: ana sembol = motor 6da763a girdi78 alfa maskesi (motor <CIFT>_ana.png kullanir; sinir kutusu esitligi dogrulanmadi). '
                  'Kucuk isaretler: cancer/libra gercek, digerleri h_oran x cap dikdortgen. Kapi gevsetme yok.',
             sabitler=dict(halka_c=yd.HALKA_C, halka_r=yd.HALKA_R, pay=yd.HALKA_PAY, tarih_alt=yd.TARIH_ALT, bosluk=yd.BOSLUK, ust_min=yd.UST_MIN,
                           cx=yd.CX, b3=yd.B3_KAT, y2=yd.Y2_UST_ORAN, h_max_12=h_max, tarih=yd.TARIH_YENI, tol_px=yd.TOL_PX, render_adim=yd.RENDER_ADIM),
             referans=REF, sabit=yd.SABIT, ref_sabit_esit=ref_sabit,
             cift=SONUC, fail=fail, gecen=78 - len(fail), bilinen_fail=BF, bilinen_fail_hepsi=bf_hepsi, bilinen_fail_sayi=len(BF))
    R['ozet_11'] = {c: dict(w=SONUC[c]['sembol']['w'], h=SONUC[c]['sembol']['h'], ust=SONUC[c]['olcum']['sembol_ust'], alt=SONUC[c]['olcum']['sembol_alt'],
                            pay=SONUC[c]['olcum']['halka_pay'], sembol_hw=SONUC[c]['olcum']['sembol_hw'], beklenen_hw=SONUC[c]['olcum']['beklenen_hw'])
                 for c in ORNEK11}
    oranlar = [v['olcum']['render_nokta_orani'] for v in SONUC.values() if v['olcum']['render_nokta_orani'] is not None]
    R['render_nokta_orani_aralik'] = [min(oranlar), max(oranlar)] if oranlar else None
    (O / 'YERLESIM78_TEST.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str))
    (O / 'ISIM_OLCUM.json').write_text(json.dumps(dict(tarih=TARIH, isim=ISIM), indent=1, ensure_ascii=False, default=str))
    print('ref = SABIT', ref_sabit)
    print('78 cift', 78 - len(fail), 'PASS | FAIL', fail)
    print('bilinen FAIL', sum(x['gecti'] for x in BF), '/', len(BF), [(x['cift'], x['vaka'], x['fail']) for x in BF if not x['gecti']])
    print('render / nokta olcek orani aralik', R['render_nokta_orani_aralik'])
    print('en genis tarih', en_s, gen[en_s], 'px | sigar', tarih_sigar, '| N (W)', N_W)
    print('SSA esik', esik, 'px | erkek x kadin %', ISIM['ssa']['oran_erkek_kadin_yuzde'], '| tum %', ISIM['ssa']['oran_tum_ciftler_yuzde'],
          '| monoton', monoton, '| kucultme', json.dumps(kucultme, ensure_ascii=False))
    return 0 if (ref_sabit and not fail and bf_hepsi and tarih_sigar and monoton) else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                                                          # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.exit(2)
