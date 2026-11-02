#!/usr/bin/env python3
"""ALTIN DUZELTME G1 / G2 (Merkez, Serdar 3 Kas): yalniz RUBY, SAPPHIRE, EMERALD. Etsy / Printful yazma yok. BEIGE / AGED_PAPYRUS'a dokunulmaz.
"Zemine butunlesik" = altinin RENGI DEGISMEZ; yapistirilmis gibi gorunmemesi YALNIZ isik ve golgeyle:
  1 notr koyu dis golge (kisa, yumusak; zemin rengi tasimaz: zemin yalniz carpimla koyulasir)
  2 parlaklik dususu: zeminin kenar koyulasmasiyla uyumlu, altin RGB'si tek carpanla (renk tonu sabit)
  3 kakma hissi: notr ince yumusak ic golge (sol ust ic kenar; RGB tek carpanla koyulasir)
  4 YASAK: altinin icine / kenarina zemin rengi (eski: golge tonuna %28 zemin rengi, zemin x 0.45 ic koyu kenar, zemin x 1.9 ic acik kenar) KALDIRILDI.
  Sicak isik tasmasi da kapali (listede yok).
G1: simdiki altin (tek doku modeli: sembol kaynak RGB, kucuk burc / yazi / halka model egrisi; kazanc 1.12) + zemin dokusu yalniz parlaklik carpani.
G2: posterin orijinal altini, renk islemi yok: sembol ve kucuk burclar kaynak RGB, yazi / logo / halka tek doku modeli (poster hatti), kazanc 1.0,
    zemin dokusu yok.
Yerlesim (A-T1, halka ax 341 tepe y 163, bosluk 20/20/20, sembol y 246) STIL3_SON (a5e3ea2) ile ayni (ornament_ornek5.yerlesim_V5).
Kapilar: ortanca kontrast >= 4.5 (kati bilgi), leke (hedef + kaynak) 0, delik / guvenli daire / y < 221 tasma 0, RENK SADAKATI (altin cekirdekte
ton sapmasi: isik / golge oncesi oge rengine gore; ortanca |dHue| < 1 derece, B >= R piksel %0).
Kullanim: ornament_altin.py --kaynak DIR --cikti DIR --son DIR(STIL3_SON pngleri)"""
import argparse
import colorsys
import importlib.util
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

_d = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('son', _d / 'ornament_son.py'); son = importlib.util.module_from_spec(_s); _s.loader.exec_module(son)
o5, o4, o3, o1 = son.o5, son.o4, son.o3, son.o1
N, MM, P, CX, CY = o5.N, o5.MM, o5.P, o5.CX, o5.CY
lum = o4.lum
RENKLER = (('RUBY', 'RUBY_1264.png'), ('SAPPHIRE', 'SAPPHIRE_1264.png'), ('EMERALD', 'EMERALD_1264.png'))
DIS_GOLGE = dict(kayma=1.5, sigma=1.2, opak=0.45)          # notr: zemin x (1 - opak x golge)
IC_GOLGE = dict(kayma=1.0, sigma=0.6, guc=0.35, ince=0.15)   # notr: altin x (1 - guc x ic kenar); ince ogelerde (yazi, logo, halka) 'ince'
DUSUS = dict(sigma=60.0, us=0.25, alt=0.92)                         # parlaklik carpani = clip((L_zemin_yerel / L_ref) ^ us, alt, 1)
DOKU_G1 = 0.05                                              # G1 zemin dokusu: parlaklik carpani 1 + DOKU_G1 x (yuksek gecirgen / std)
INCE = ('isim1', 'isim2', 'tarih', 'sonsuz', 'halka')


def oge_renk(Y, model, td, ad, varyant, kazanc):
    rgb, a, x, y = Y['E'][ad]
    if ad == 'sembol':
        col = rgb
    elif ad == 'halka':
        col = np.broadcast_to(td.renk(np.full((1, 1), model.Lmed, np.float32), model.egri), (N, N, 3)).astype(np.float32)
    elif ad.startswith('kucuk'):
        col = rgb if varyant == 'G2' else model.boya(lum(rgb), a)[0]
    else:
        col, _ = model.duz(a)
    cc = np.zeros((N, N, 3), np.float32)
    if ad == 'halka':
        cc = col.copy()
    else:
        h, w = a.shape
        xa, ya, xb, yb = max(0, x), max(0, y), min(N, x + w), min(N, y + h)
        cc[ya:yb, xa:xb] = col[ya - y:yb - y, xa - x:xb - x]
    return np.clip(cc * kazanc, 0, 255)


def boya_altin(Y, model, z, td, varyant, kazanc):
    """doner (rgb, renk_once): renk_once = isik / golge oncesi oge renkleri (renk sadakati olcumu icin)."""
    M = Y['M']
    zf = z.astype(np.float32)
    out = zf.copy()
    tum = np.maximum.reduce([M[k] for k in M])
    # 1 notr dis golge
    gm = cv2.GaussianBlur(tum, (0, 0), DIS_GOLGE['sigma'])
    gm = cv2.warpAffine(gm, np.float32([[1, 0, DIS_GOLGE['kayma']], [0, 1, DIS_GOLGE['kayma']]]), (N, N))
    out = out * (1 - DIS_GOLGE['opak'] * gm)[..., None]
    # 2 parlaklik dususu (zeminin kenar koyulasmasi)
    Lz = cv2.GaussianBlur(lum(zf), (0, 0), DUSUS['sigma'])
    yy, xx = np.mgrid[0:N, 0:N]
    Lref = float(np.median(Lz[np.hypot(xx + 0.5 - CX, yy + 0.5 - CY) < 150]))
    f_dus = np.clip((Lz / max(Lref, 1)) ** DUSUS['us'], DUSUS['alt'], 1.0)
    # G1 zemin dokusu (yalniz parlaklik)
    if varyant == 'G1':
        zL = lum(zf)
        dk = zL - cv2.GaussianBlur(zL, (0, 0), 6.0)
        f_doku = 1 + DOKU_G1 * dk / max(float(dk.std()), 1e-3)
    else:
        f_doku = np.ones((N, N), np.float32)
    once = {}
    sh = lambda a_, d: cv2.warpAffine(a_, np.float32([[1, 0, d], [0, 1, d]]), (N, N))
    for ad in Y['E']:
        cc = oge_renk(Y, model, td, ad, varyant, kazanc)
        once[ad] = cc.copy()
        m = M[ad]
        ic = cv2.GaussianBlur(np.clip(m - sh(m, IC_GOLGE['kayma']), 0, 1), (0, 0), IC_GOLGE['sigma']) * m
        g_ic = IC_GOLGE['ince'] if ad in INCE else IC_GOLGE['guc']
        carpan = f_dus * f_doku * (1 - g_ic * ic)                       # tek skaler carpan / piksel: RGB orani (ton) degismez
        cc = cc * carpan[..., None]
        sat = cc.max(2, keepdims=True)                                  # kirpma tonu bozmasin: en buyuk kanal 255'i asarsa orantili indir
        cc = np.where(sat > 255, cc * 255 / np.maximum(sat, 1e-3), cc)
        out = out * (1 - m[..., None]) + cc * m[..., None]
    return np.clip(np.round(out), 0, 255).astype(np.uint8), once


def renk_sadakati(rgb, once, M):
    """altin cekirdek (alfa >= 0.98) pikselleri: cikti tonu ile isik / golge oncesi oge tonu farki (derece); B >= R orani."""
    r = {}
    for ad, cc in once.items():
        ce = M[ad] >= 0.98
        if ce.sum() < 20:
            continue
        a_ = rgb[ce].astype(np.float32) / 255.0
        b_ = np.clip(cc[ce], 0, 255) / 255.0
        h1 = np.array([colorsys.rgb_to_hsv(*p)[0] for p in a_[::max(1, len(a_) // 4000)]])
        h0 = np.array([colorsys.rgb_to_hsv(*p)[0] for p in b_[::max(1, len(b_) // 4000)]])
        d = np.abs((h1 - h0 + 0.5) % 1.0 - 0.5) * 360
        r[ad] = dict(dhue_ortanca=round(float(np.median(d)), 2), dhue_p95=round(float(np.percentile(d, 95)), 2),
                     b_ge_r_yuzde=round(float((rgb[ce][:, 2] >= rgb[ce][:, 0]).mean() * 100), 2))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--cikti', required=True)
    ap.add_argument('--son', required=True)
    a = ap.parse_args()
    K, O, SON = Path(a.kaynak), Path(a.cikti), Path(a.son)
    O.mkdir(parents=True, exist_ok=True)
    for f, h in son.GERCEK.items():
        if not o1.sha(K / f).startswith(h):
            print('FAIL kaynak sha', f, flush=True); return 1
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
    ana5, _ = o5.delik_kapat(ana0)
    ic_, _ = o5.leke_ic_kaynak(ana5[..., 3]); o5.KAYNAK_SONRA['ana'] = int((ic_ & (ana5[..., 3] < 0.9)).sum())
    lsrc = o4.logo_kaynak(K / 'LOGO_1.png')
    cap = o4.CAP0
    G = int(math.ceil(o5.BOSLUK_ORAN * cap))

    def kucuk(burc, h_ratio):
        g = np.asarray(Image.open(K / f'{burc}_symbol_gold.png').convert('RGBA'), np.float32)
        g[..., 3] /= 255.0
        g = o1.kirp(g, g[..., 3], pad=2)
        g, _ = o5.delik_kapat(g)
        ic2, _ = o5.leke_ic_kaynak(g[..., 3]); o5.KAYNAK_SONRA[burc] = int((ic2 & (g[..., 3] < 0.9)).sum())
        gx0, gy0, gx1, gy1 = o1.bbox(g[..., 3], 0.5)
        rgb_, a_ = o1.rgba_olcek(g, h_ratio * cap / (gy1 - gy0))
        rgb_, a_, _ = o5.hedef_kapat(rgb_, a_)
        return rgb_, a_
    k_ = cap * o4.LOGO_H / lsrc.shape[0]
    la = np.clip(cv2.resize(lsrc, (max(1, int(round(lsrc.shape[1] * k_))), max(1, int(round(cap * o4.LOGO_H)))), interpolation=cv2.INTER_AREA), 0, 1)
    T = dict(isim1=o1.metin_alfa('EMILY', K / 'Cinzel.ttf', cap, 500), isim2=o1.metin_alfa('JAMES', K / 'Cinzel.ttf', cap, 500),
             tarih=o1.metin_alfa('14 JUNE 2025', K / 'EBGaramond-Italic.ttf', P['tagline_T'] / P['cap'] * cap, None, ref='T'), sonsuz=la, cap=cap)
    kc = {'sol': kucuk('cancer', P['kucuk_sol_h'] / P['cap']), 'sag': kucuk('libra', P['kucuk_sag_h'] / P['cap'])}
    ha, hb = o5.halka_T(pp, son.S0)
    Y, bilgi = o5.yerlesim_V5(pp, ana5, T, kc, ha, hb, G)
    if Y is None:
        print('FAIL yerlesim', flush=True); return 1
    model = son.model_kur(td, Y)
    um = o5.uc_maske(pp, son.S0)
    R = {'kaynak_sha256': {f.name: o1.sha(f) for f in sorted(K.iterdir()) if f.is_file()},
         'ayar': dict(dis_golge=DIS_GOLGE, ic_golge=IC_GOLGE, dusus=DUSUS, doku_G1=DOKU_G1,
                      kaldirilan='golge tonuna %28 zemin rengi; ic koyu kenar zemin x 0.45; ic acik kenar zemin x 1.9; sicak isik tasmasi'),
         'yerlesim': bilgi, 'sonuc': {}}
    font = ImageFont.truetype(str(K / 'EBGaramond-Italic.ttf'), 24)
    satirlar = {}
    for renk, zf in RENKLER:
        z = o1.zemin_canva(K / zf)
        satirlar[renk] = [np.asarray(Image.open(SON / f'CANCER_LIBRA_{renk}_954.png').convert('RGB'))]
        for var, kaz in (('G1', o5.ALTIN_SABIT), ('G2', 1.0)):
            rgb, once = boya_altin(Y, model, z, td, var, kaz)
            ok = {k: o5.kontrast_yeni(rgb, Y['M'][k], 'koyu') for k in ('isim1', 'isim2', 'tarih', 'kucuk_sol', 'kucuk_sag')}
            ok['halka_uclari'] = o5.kontrast_yeni(rgb, Y['M']['halka'] * um[0], 'koyu')
            ok['halka_uclari_2px_alti'] = o5.kontrast_yeni(rgb, Y['M']['halka'] * um[1], 'koyu', cekirdek=0.5)
            ok['sonsuz_bilgi'] = o5.kontrast_yeni(rgb, Y['M']['sonsuz'], 'koyu', cekirdek=0.5)
            kapi_k = [v['ortanca_bilgi'] for kk, v in ok.items() if kk not in ('halka_uclari_2px_alti', 'sonsuz_bilgi') and v.get('deger') is not None]
            kati_k = [v['deger'] for kk, v in ok.items() if kk not in ('halka_uclari_2px_alti', 'sonsuz_bilgi') and v.get('deger') is not None]
            gy, gb = o4.goruntu_yasak(rgb, z, Y['M'].get('halka'))
            lk = o5.leke_kapisi(Y['M'], rgb, None)
            rs = renk_sadakati(rgb, once, Y['M'])
            r = dict(kazanc=kaz, kontrast_ortanca_en_kotu=round(min(kapi_k), 2), kati_en_kotu_bilgi=round(min(kati_k), 2), kontrast=ok,
                     goruntu_yasak=gy, goruntu=gb, leke=lk, renk_sadakati=rs, bosluk_px=o5.bosluklar(Y['E']),
                     sembol_kutu=list(o5.kutu(Y['E'], 'sembol')))
            R['sonuc'].setdefault(renk, {})[var] = r
            (O / var).mkdir(exist_ok=True)
            o1.kaydet(rgb, O / var / f'CANCER_LIBRA_{renk}_954.png')
            satirlar[renk].append(rgb)
            la_ = sum(v['alfa_lt_09'] for k2, v in lk.items() if k2 in o5.LEKE_KAPI_OGE)
            print(renk, var, 'ortanca', r['kontrast_ortanca_en_kotu'], 'kati', r['kati_en_kotu_bilgi'], 'yasak', sum(gy.values()), 'leke a', la_,
                  'dhue max ortanca', max(v['dhue_ortanca'] for v in rs.values()), 'B>=R max %', max(v['b_ge_r_yuzde'] for v in rs.values()), flush=True)
    # onizleme 3 x 3 (SON | G1 | G2)
    bloklar = []
    for renk, _ in RENKLER:
        et = [f'{renk} SON (a5e3ea2)']
        for var in ('G1', 'G2'):
            r = R['sonuc'][renk][var]
            rs = r['renk_sadakati']
            et.append(f'{renk} {var}: ortanca {r["kontrast_ortanca_en_kotu"]} {"PASS" if r["kontrast_ortanca_en_kotu"] >= 4.5 else "FAIL"}, kati {r["kati_en_kotu_bilgi"]}\n'
                      f'ton sapmasi ortanca en cok {max(v["dhue_ortanca"] for v in rs.values())} derece, B>=R %{max(v["b_ge_r_yuzde"] for v in rs.values())}')
        bloklar.append(son.onizleme_etiketli(satirlar[renk], et, font, h_et=80))
    o = Image.new('RGB', (max(b.width for b in bloklar), sum(b.height for b in bloklar) + 24 * 2), 'white')
    yy_ = 0
    for b in bloklar:
        o.paste(b, (0, yy_)); yy_ += b.height + 24
    o.save(O / 'ONIZLEME_76mm_ALTIN.png', dpi=(300, 300))
    A = [R['sonuc'][r_][v] for r_ in R['sonuc'] for v in R['sonuc'][r_]]
    g = dict(kontrast_ortanca=all(r['kontrast_ortanca_en_kotu'] >= o4.HEDEF for r in A),
             goruntu_yasak_0=all(sum(r['goruntu_yasak'].values()) == 0 for r in A),
             leke_a_0=all(sum(v['alfa_lt_09'] for k2, v in r['leke'].items() if k2 in o5.LEKE_KAPI_OGE) == 0 for r in A),
             leke_a_kaynak_0=all(v == 0 for v in o5.KAYNAK_SONRA.values()),
             renk_sadakati=all(v['dhue_ortanca'] < 1.0 and v['b_ge_r_yuzde'] == 0 for r in A for v in r['renk_sadakati'].values()),
             yerlesim_ayni=all(r['bosluk_px'] == [20, 20, 20] and r['sembol_kutu'][1] == 246 for r in A))
    g = {k: bool(v) for k, v in g.items()}
    R['kapi'] = g
    R['kaynak_leke_onarim_sonrasi'] = dict(o5.KAYNAK_SONRA)
    (O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=float))
    print('KAPI', json.dumps(g), 'PASS' if all(g.values()) else 'FAIL', flush=True)
    return 0 if all(g.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
