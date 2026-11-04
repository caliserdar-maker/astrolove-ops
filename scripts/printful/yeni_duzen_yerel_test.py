#!/usr/bin/env python3
"""YENI DUZEN yerel geometri testi (Serdar 4 Kas aksam; asama 1 D). Motor girdisi yalniz Actions'ta: ana sembol yerine motor 6da763a
motor_gpt/girdi78/ana/<cift>_alfa.png (poster alfa maskesi; motorun okudugu <CIFT>_ana.png ile ayni sinir kutusu DOGRULANMADI: acik soru).
Kucuk isaretler: cancer / libra gercek kaynak (docs/ornament/kaynak), digerleri motorun hedef yuksekligiyle (h_oran x cap) dikdortgen benzetim.
Yazilar motorla ayni (o1.metin_alfa, Cinzel / EBGaramond-Italic TEK_DOKU 2a08a78; LOGO_1 6da763a). Halka: o5.halka_T (HALKA_BLUE 2a08a78).
Olcer: 78/78 yeni_duzen.kapilar + o4.kapi; 4 bilinen FAIL (yerlesimden SONRA sokulur); en genis tarih (12 ay x 31 gun x 2000-2035);
en uzun isim (W x N, iki isim esit) ve verilen isimler; KONTAK.jpg (11 cift RUBY benzetim).
Cikis: 0 78/78 PASS ve 4 bilinen FAIL beklenen kapidan, 1 degil, 2 cokus.
Kullanim: yeni_duzen_yerel_test.py --cikti DIR [--tarih_hizli]"""
import argparse
import importlib.util
import io
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
MERKEZ11 = dict(TAURUS_TAURUS=(308, 254, 302), CANCER_TAURUS=(274, 274, 287), AQUARIUS_CANCER=(346, 254, 301), LIBRA_LIBRA=(512, 246, 307),
                AQUARIUS_AQUARIUS=(474, 119, 402), ARIES_SCORPIO=(378, 250, 305), LEO_SAGITTARIUS=(280, 297, 269), CAPRICORN_CAPRICORN=(359, 211, 333),
                CANCER_LIBRA=(316, 297, 269), AQUARIUS_PISCES=(230, 297, 269), GEMINI_VIRGO=(297, 272, 288))
AYLAR = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER']


def git_bayt(rev, yol):
    return subprocess.run(['git', '-C', str(_k), 'show', f'{rev}:{yol}'], capture_output=True, check=True).stdout


def yukle(ad, dosya):
    s = importlib.util.spec_from_file_location(ad, _d / dosya); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--cikti', required=True); ap.add_argument('--tarih_hizli', action='store_true')
    a = ap.parse_args(); O = Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
    W = O / '_girdi'; W.mkdir(exist_ok=True)
    for ad, rev, yol in (('Cinzel.ttf', TEK_C, 'motor/font/Cinzel.ttf'), ('EBGaramond-Italic.ttf', TEK_C, 'motor/font/EBGaramond-Italic.ttf'),
                         ('HALKA_BLUE_16x20.png', TEK_C, 'motor/varlik/halka/HALKA_BLUE_16x20.png'), ('LOGO_1.png', MOTOR_C, 'motor_gpt/girdi/LOGO_1.png')):
        if not (W / ad).exists():
            (W / ad).write_bytes(git_bayt(rev, yol))
    al = yukle('altin', 'ornament_altin.py'); o1, o3, o4, o5, son = al.o1, al.o3, al.o4, al.o5, al.son
    mo = yukle('motor', 'ornament_motor.py'); yd = yukle('yd', 'yeni_duzen.py')
    o4.YASAK = o4.yasak_m(); o3.YASAK = o4.YASAK
    o4.GLOW_K = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * o4.GLOW_R + 1,) * 2)
    Pc, cap = o5.P, o4.CAP0
    lsrc = o4.logo_kaynak(W / 'LOGO_1.png')

    def logo():
        kk = cap * o4.LOGO_H / lsrc.shape[0]
        sz = (max(1, int(round(lsrc.shape[1] * kk))), max(1, int(round(cap * o4.LOGO_H))))
        return np.clip(cv2.resize(lsrc, sz, interpolation=cv2.INTER_AREA if kk <= 1 else cv2.INTER_CUBIC), 0, 1)
    tcap = Pc['tagline_T'] / Pc['cap'] * cap

    def T_(i1='EMILY', i2='JAMES', tarih=yd.TARIH_YENI):
        return dict(isim1=o1.metin_alfa(i1, W / 'Cinzel.ttf', cap, 500), isim2=o1.metin_alfa(i2, W / 'Cinzel.ttf', cap, 500),
                    tarih=o1.metin_alfa(tarih, W / 'EBGaramond-Italic.ttf', tcap, None, ref='T'), sonsuz=logo(), cap=cap)

    def h_oran(b):
        if b == 'CANCER':
            return Pc['kucuk_sol_h'] / Pc['cap']
        if b == 'LIBRA':
            return Pc['kucuk_sag_h'] / Pc['cap']
        return mo.SPRITE_H[b] * mo.SPRITE_C / Pc['cap']
    gercek = {}

    def kucuk(b):
        hb_ = h_oran(b) * cap
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

    def ana(c):
        f = W / f'{c.lower()}_alfa.png'
        if not f.exists():
            f.write_bytes(git_bayt(MOTOR_C, f'motor_gpt/girdi78/ana/{c.lower()}_alfa.png'))
        m = np.asarray(Image.open(f).convert('L'), np.float32) / 255.0
        g = np.dstack([np.full(m.shape + (3,), (212, 170, 90), np.float32), m])
        g = o1.kirp(g, g[..., 3], pad=2)
        if g.shape[1] > 1600:
            r_, a_ = o1.rgba_olcek(g, 1600 / g.shape[1]); g = np.dstack([r_, a_])
        g, _ = o5.delik_kapat(g)
        return g
    T0 = T_()
    SONUC, E11 = {}, {}
    t0 = time.time()
    for i, c in enumerate(CIFT78):
        b1, b2 = c.split('_')
        kc = {'sol': kucuk(b1), 'sag': kucuk(b2)}
        E, cizgi, d, g, olc = yd.yeni_yerlesim(o3.yazi_blogu, o1.rgba_olcek, T0, kc, ana(c), h_max)
        E2 = dict(E); E2['halka'] = (None, ha, 0, 0)
        _, yb, cak, ok = o4.kapi(E2)
        g['o4_kapi'] = bool(ok)
        SONUC[c] = dict(gecti=all(g.values()), kapi=g, olcum=olc, cizgi=cizgi, sembol=d, o4=dict(yasak=yb, cakisma=cak[:6]),
                        merkez_benzetim=MERKEZ11.get(c))
        if c in ORNEK11:
            E11[c] = E2
        if (i + 1) % 13 == 0:
            print(f'ETA {i + 1}/78 gecen {time.time() - t0:.0f} sn', flush=True)
    fail = sorted(c for c, v in SONUC.items() if not v['gecti'])
    # bilinen FAIL (yerlesimden SONRA)
    BF = []
    for c in ('CANCER_LIBRA', 'LEO_SAGITTARIUS'):
        b1, b2 = c.split('_'); kc = {'sol': kucuk(b1), 'sag': kucuk(b2)}; A = ana(c)
        E, cizgi, d, g, olc = yd.yeni_yerlesim(o3.yazi_blogu, o1.rgba_olcek, T0, kc, A, h_max)
        # 1 ust 229
        E1 = dict(E); s = yd.kutu_E(E1, 'sembol'); yd.kaydir(E1, ('sembol',), 229 - s[1])
        g1, _ = yd.kapilar(E1, cizgi, d)
        BF.append(dict(cift=c, vaka='sembol ustu 229', beklenen='ust_ge_230', fail=[k for k, v in g1.items() if not v], gecti=not g1['ust_ge_230']))
        # 2 olcek x 1,2 (ayni merkez)
        s0 = yd.kutu_E(E, 'sembol'); rgb_, a_ = o1.rgba_olcek(A, d['s'] * 1.2); bb = yd.kutu(a_)
        E3 = dict(E); E3['sembol'] = (rgb_, a_, int(round((s0[0] + s0[2]) / 2 - (bb[0] + bb[2]) / 2)), int(round((s0[1] + s0[3]) / 2 - (bb[1] + bb[3]) / 2)))
        d3 = dict(d, s=d['s'] * 1.2); g3, _ = yd.kapilar(E3, cizgi, d3)
        BF.append(dict(cift=c, vaka='olcek x 1,2', beklenen='halka_pay_ge_30 | ust_ge_230 | sembol_alt_le_sinir', fail=[k for k, v in g3.items() if not v],
                       gecti=not (g3['halka_pay_ge_30'] and g3['ust_ge_230'] and g3['sembol_alt_le_sinir'])))
        # 3 B3 0,90 (Y2 ile)
        sem9, d9 = yd.sembol_yerlestir(A, cizgi['sembol_alt_sinir'], o1.rgba_olcek, b3_kat=0.90)
        E4 = dict(E); E4['sembol'] = sem9; g4, _ = yd.kapilar(E4, cizgi, d9)
        BF.append(dict(cift=c, vaka='olcek x 0,90 (B3 0,85 yerine)', beklenen='b3_y2_oran', fail=[k for k, v in g4.items() if not v], gecti=not g4['b3_y2_oran']))
        # 4 tarih 5 px asagi
        E5 = dict(E); yd.kaydir(E5, ('tarih',), 5); g5, _ = yd.kapilar(E5, cizgi, d)
        BF.append(dict(cift=c, vaka='tarih 5 px asagi', beklenen='tarih_alt_795', fail=[k for k, v in g5.items() if not v], gecti=not g5['tarih_alt_795']))
    # en genis tarih
    gun = range(1, 32); yil = range(2000, 2036)
    adaylar = [f'{m} {dd}, {yy}' for m in AYLAR for dd in gun for yy in yil]
    if a.tarih_hizli:                                                      # genislik ay ve gun basamagi ile baskin; yillardan 2000-2035 hepsi korunur
        adaylar = [f'{m} {dd}, {yy}' for m in AYLAR for dd in (1, 11, 22, 28, 30, 31) for yy in yil]
    gen = {}
    for s_ in adaylar:
        al_ = o1.metin_alfa(s_, W / 'EBGaramond-Italic.ttf', tcap, None, ref='T')[0]; b = yd.kutu(al_); gen[s_] = b[2] - b[0]
    en_s = max(gen, key=gen.get)
    kc = {'sol': kucuk('CANCER'), 'sag': kucuk('LIBRA')}
    E, cizgi, d, g, olc = yd.yeni_yerlesim(o3.yazi_blogu, o1.rgba_olcek, T_(tarih=en_s), kc, ana('CANCER_LIBRA'), h_max)
    E2 = dict(E); E2['halka'] = (None, ha, 0, 0); _, yb, cak, ok = o4.kapi(E2)
    _, at, xt, yt = E['tarih']; rt = yd.halka_max_r(at, xt, yt)
    TARIH = dict(aday_sayisi=len(adaylar), tum_bilesim=not a.tarih_hizli, en_genis=en_s, genislik_px=int(gen[en_s]), genislik_mm=round(gen[en_s] / 11.8, 2),
                 ilk10=sorted(gen.items(), key=lambda kv: -kv[1])[:10], merkez_tahmini=dict(dizgi='SEPTEMBER 10, 2026', px=int(gen.get('SEPTEMBER 10, 2026', -1))),
                 ornek=dict(dizgi=yd.TARIH_YENI, px=int(gen.get(yd.TARIH_YENI, -1))),
                 sigar=dict(halka_ic_r_max=round(rt, 2), halka_ic_icinde=rt <= yd.HALKA_R, o4_kapi=bool(ok), yasak=yb, cakisma=cak[:4],
                            tum_kapi=g, gecti=bool(rt <= yd.HALKA_R and ok)))
    # en uzun isim
    def isim_dene(i1, i2):
        E, cizgi, d, g, olc = yd.yeni_yerlesim(o3.yazi_blogu, o1.rgba_olcek, T_(i1, i2), kc, ana('CANCER_LIBRA'), h_max)
        E2 = dict(E); E2['halka'] = (None, ha, 0, 0); _, yb, cak, ok = o4.kapi(E2)
        r = max(yd.halka_max_r(E[ad][1], E[ad][2], E[ad][3]) for ad in ('isim1', 'isim2', 'sonsuz', 'kucuk_sol', 'kucuk_sag'))
        b1, b2 = yd.kutu_E(E, 'isim1'), yd.kutu_E(E, 'isim2')
        return dict(isim1=i1, isim2=i2, halka_r_max=round(r, 2), o4_kapi=bool(ok), yasak=yb, cakisma=cak[:4], satir_x=[b1[0], b2[2]],
                    gecti=bool(r <= yd.HALKA_R and ok))
    ISIM = dict(W_testi=[], verilen=[], not_='harf sayisi tire / kesme isareti haric; sinir halka ic dairesi (r 336) + o4.kapi; W en genis buyuk harf (Cinzel)')
    N = None
    for n in range(4, 15):
        r = isim_dene('W' * n, 'W' * n); r['harf'] = n; ISIM['W_testi'].append(r)
        if r['gecti']:
            N = n
    for i1, i2 in (('MAXIMILIAN', 'CHRISTOPHER'), ('ALEXANDRIA', 'ANNA'), ('MARY-JANE', "O'NEIL"), ('EMILY', 'JAMES')):
        r = isim_dene(i1, i2); r['harf'] = [sum(ch.isalpha() for ch in i1), sum(ch.isalpha() for ch in i2)]; ISIM['verilen'].append(r)
    ISIM['N_W'] = N
    # kontak (benzetim)
    tiles = []
    fnt = ImageFont.load_default()
    for c in ORNEK11:
        E = E11[c]; im = np.zeros((954, 954, 3), np.float32)
        yy, xx = np.mgrid[0:954, 0:954]; im[np.hypot(xx - 476, yy - 477) <= 449] = (110, 18, 30)
        for ad, (_, a_, x, y) in E.items():
            m, _ = o3.maske_yaz(a_, x, y); im = im * (1 - m[..., None]) + np.array((212, 170, 90), np.float32) * m[..., None]
        t = Image.fromarray(np.clip(im, 0, 255).astype(np.uint8)); dr = ImageDraw.Draw(t)
        dr.ellipse((475.5 - 336, 504 - 336, 475.5 + 336, 504 + 336), outline=(120, 120, 120))
        dr.line((0, SONUC[c]['cizgi']['sembol_alt_sinir'], 954, SONUC[c]['cizgi']['sembol_alt_sinir']), fill=(90, 90, 90))
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
                           b3=yd.B3_KAT, y2=yd.Y2_UST_ORAN, h_max_12=round(h_max, 2), tarih=yd.TARIH_YENI),
             cift=SONUC, fail=fail, gecen=78 - len(fail), bilinen_fail=BF, bilinen_fail_hepsi=all(x['gecti'] for x in BF))
    R['ozet_11'] = {c: dict(w=SONUC[c]['sembol']['w'], h=SONUC[c]['sembol']['h'], ust=SONUC[c]['olcum']['sembol_ust'], merkez=MERKEZ11[c],
                            alt=SONUC[c]['olcum']['sembol_alt'], sinir=SONUC[c]['cizgi']['sembol_alt_sinir'], pay=SONUC[c]['olcum']['halka_pay']) for c in ORNEK11}
    (O / 'YERLESIM78_TEST.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str))
    (O / 'ISIM_OLCUM.json').write_text(json.dumps(dict(tarih=TARIH, isim=ISIM), indent=1, ensure_ascii=False, default=str))
    print('78 cift', 78 - len(fail), 'PASS | FAIL', fail)
    print('bilinen FAIL', [(x['cift'], x['vaka'], x['gecti'], x['fail']) for x in BF])
    print('en genis tarih', en_s, gen[en_s], 'px | sigar', TARIH['sigar']['gecti'], '| N (W)', N)
    print('11 cift', json.dumps(R['ozet_11']))
    return 0 if (not fail and R['bilinen_fail_hepsi']) else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                                                          # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.exit(2)
