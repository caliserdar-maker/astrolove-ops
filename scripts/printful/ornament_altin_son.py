#!/usr/bin/env python3
"""ALTIN SON (yalniz G2; Serdar 3 Kas): RUBY, SAPPHIRE, EMERALD. Etsy / Printful yazma yok. BEIGE / AGED_PAPYRUS'a dokunulmaz.
Tum altin ogeler (kucuk burclar, isimler, tarih, logo, HALKA) ana sembolun G2 dokusuyla (posterin orijinal altini):
  doku tuvali = ana sembolun HEDEF olcekteki cekirdek pikselleri (mesafe donusumu >= DT_MIN) icinden rastgele YAMA x YAMA yamalar,
  ADIM aralikla, yumusak agirlikli bindirme (sabit tohum). Tane boyu ana sembolle ayni (ayni olcek); renk yalniz ana sembolun kendi pikselleri.
  Ana sembol kendi RGB'si (degismez). Halka a114ddb'de duz tek renkti (td.renk(Lmed)): artik ayni doku (raporda).
Butunlesme a114ddb ile ayni (ornament_altin.boya_altin): notr dis golge, notr ic golge, parlaklik dususu (alt 0.92, us 0.25); zemin rengi YOK.
RUBY ortanca < 4.5 ise YALNIZ RUBY'nin kucuk ogelerinde (isimler, tarih, logo, kucuk burclar) tonu degistirmeden (tek carpan) esigi gecen EN AZ
parlaklik artisi (0.01 adim); miktar OLCUM'da.
Kullanim: ornament_altin_son.py --kaynak DIR --cikti DIR --son DIR(a5e3ea2 STIL3_SON)"""
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
_s = importlib.util.spec_from_file_location('altin', _d / 'ornament_altin.py'); al = importlib.util.module_from_spec(_s); _s.loader.exec_module(al)
son, o5, o4, o3, o1 = al.son, al.o5, al.o4, al.o3, al.o1
N, MM, P, CX, CY = o5.N, o5.MM, o5.P, o5.CX, o5.CY
lum = o4.lum
YAMA, ADIM, DT_MIN, TOHUM = 8, 6, 8.0, 7
YAMA_L_ARALIK = (40, 95)                      # deneme 2: yama ortalama lumasi cekirdek dagiliminin p40-p95 (cizgi kenari golge yamalari disarida)
KUCUK_OGE = ('isim1', 'isim2', 'tarih', 'sonsuz', 'kucuk_sol', 'kucuk_sag')
TEX = None
KAT = {}                                       # oge basina parlaklik carpani (yalniz RUBY kucuk ogeler, gerekirse)


def doku_tuvali(sem):
    """ana sembol (hedef olcek, yerlestirilmis) cekirdek yamalarindan N x N doku."""
    rgb, a, x, y = sem
    dt = cv2.distanceTransform(np.pad((a >= 0.999).astype(np.uint8), 1), cv2.DIST_L2, 5)[1:-1, 1:-1]
    h = YAMA // 2
    ys, xs = np.nonzero(dt >= DT_MIN)
    ok = (ys >= h) & (xs >= h) & (ys < a.shape[0] - h) & (xs < a.shape[1] - h)
    ys, xs = ys[ok], xs[ok]
    Lm = cv2.blur(lum(rgb.astype(np.float32)), (YAMA, YAMA))[ys, xs]
    lo_, hi_ = np.percentile(Lm, YAMA_L_ARALIK[0]), np.percentile(Lm, YAMA_L_ARALIK[1])
    sec = (Lm >= lo_) & (Lm <= hi_)
    ys, xs = ys[sec], xs[sec]
    rng = np.random.default_rng(TOHUM)
    acc = np.zeros((N + YAMA, N + YAMA, 3), np.float64)
    wsum = np.zeros((N + YAMA, N + YAMA), np.float64)
    w1 = np.hanning(YAMA + 2)[1:-1]
    w = np.outer(w1, w1) + 1e-3
    for yy in range(0, N + 1, ADIM):
        for xx in range(0, N + 1, ADIM):
            i = rng.integers(len(ys))
            p = rgb[ys[i] - h:ys[i] - h + YAMA, xs[i] - h:xs[i] - h + YAMA].astype(np.float64)
            acc[yy:yy + YAMA, xx:xx + YAMA] += p * w[..., None]
            wsum[yy:yy + YAMA, xx:xx + YAMA] += w
    t = (acc / np.maximum(wsum, 1e-9)[..., None])[:N, :N].astype(np.float32)
    cek = rgb[a >= 0.999].astype(np.float32)
    return t, dict(yama=YAMA, adim=ADIM, dt_min=DT_MIN, tohum=TOHUM, yama_L_yuzdelik=YAMA_L_ARALIK, kaynak_piksel=int(len(ys)),
                   sembol_cekirdek_L_ortanca=round(float(np.median(lum(cek))), 1), tuval_L_ortanca=round(float(np.median(lum(t))), 1),
                   sembol_cekirdek_L_std=round(float(lum(cek).std()), 1), tuval_L_std=round(float(lum(t).std()), 1))


def oge_renk_G2(Y, model, td, ad, varyant, kazanc):
    rgb, a, x, y = Y['E'][ad]
    if ad == 'sembol':
        cc = np.zeros((N, N, 3), np.float32)
        h, w = a.shape
        xa, ya, xb, yb = max(0, x), max(0, y), min(N, x + w), min(N, y + h)
        cc[ya:yb, xa:xb] = rgb[ya - y:yb - y, xa - x:xb - x]
    else:
        cc = TEX.copy()
    return np.clip(cc * kazanc * KAT.get(ad, 1.0), 0, 255)


def main():
    global TEX
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
    TEX, tex_bilgi = doku_tuvali(Y['E']['sembol'])
    al.oge_renk = oge_renk_G2
    um = o5.uc_maske(pp, son.S0)
    R = {'kaynak_sha256': {f.name: o1.sha(f) for f in sorted(K.iterdir()) if f.is_file()}, 'doku': tex_bilgi,
         'ayar': dict(dis_golge=al.DIS_GOLGE, ic_golge=al.IC_GOLGE, dusus=al.DUSUS, kazanc=1.0,
                      halka='a114ddb G2 halka duz tek renk (td.renk(Lmed)); burada ana sembol dokusu'),
         'yerlesim': bilgi, 'sonuc': {}}

    def olc(rgb, once, z):
        ok = {k: o5.kontrast_yeni(rgb, Y['M'][k], 'koyu') for k in ('isim1', 'isim2', 'tarih', 'kucuk_sol', 'kucuk_sag')}
        ok['halka_uclari'] = o5.kontrast_yeni(rgb, Y['M']['halka'] * um[0], 'koyu')
        ok['halka_uclari_2px_alti'] = o5.kontrast_yeni(rgb, Y['M']['halka'] * um[1], 'koyu', cekirdek=0.5)
        ok['sonsuz_bilgi'] = o5.kontrast_yeni(rgb, Y['M']['sonsuz'], 'koyu', cekirdek=0.5)
        kk = [v for k, v in ok.items() if k not in ('halka_uclari_2px_alti', 'sonsuz_bilgi') and v.get('deger') is not None]
        gy, gb = o4.goruntu_yasak(rgb, z, Y['M'].get('halka'))
        return dict(kontrast_ortanca_en_kotu=round(min(v['ortanca_bilgi'] for v in kk), 2), kati_en_kotu_bilgi=round(min(v['deger'] for v in kk), 2),
                    kontrast=ok, goruntu_yasak=gy, goruntu=gb, leke=o5.leke_kapisi(Y['M'], rgb, None),
                    renk_sadakati=al.renk_sadakati(rgb, once, Y['M']), bosluk_px=o5.bosluklar(Y['E']), sembol_kutu=list(o5.kutu(Y['E'], 'sembol')))
    rgbler = {}
    for renk, zf in al.RENKLER:
        z = o1.zemin_canva(K / zf)
        KAT.clear()
        rgb, once = al.boya_altin(Y, model, z, td, 'G2', 1.0)
        r = olc(rgb, once, z)
        artis = 1.0
        if renk == 'RUBY' and r['kontrast_ortanca_en_kotu'] < o4.HEDEF:
            for k100 in range(101, 161):                                # %1 adimla en az artis (yalniz kucuk ogeler, tek carpan: ton sabit)
                artis = k100 / 100
                KAT.clear(); KAT.update({k: artis for k in KUCUK_OGE})
                rgb, once = al.boya_altin(Y, model, z, td, 'G2', 1.0)
                r = olc(rgb, once, z)
                if r['kontrast_ortanca_en_kotu'] >= o4.HEDEF:
                    break
        r['kucuk_oge_parlaklik_artisi'] = round(artis, 2)
        R['sonuc'][renk] = r
        rgbler[renk] = rgb
        o1.kaydet(rgb, O / f'CANCER_LIBRA_{renk}_954.png')
        la_ = sum(v['alfa_lt_09'] for k2, v in r['leke'].items() if k2 in o5.LEKE_KAPI_OGE)
        print(renk, 'ortanca', r['kontrast_ortanca_en_kotu'], 'kati', r['kati_en_kotu_bilgi'], 'artis', artis, 'yasak', sum(r['goruntu_yasak'].values()),
              'leke', la_, 'dhue', max(v['dhue_ortanca'] for v in r['renk_sadakati'].values()),
              'B>=R', max(v['b_ge_r_yuzde'] for v in r['renk_sadakati'].values()), 'bosluk', r['bosluk_px'], flush=True)
    font = ImageFont.truetype(str(K / 'EBGaramond-Italic.ttf'), 24)
    # 5 renk onizleme (BEIGE / AGED_PAPYRUS a5e3ea2'den aynen)
    liste, et = [], []
    for renk in ('RUBY', 'SAPPHIRE', 'EMERALD', 'BEIGE', 'AGED_PAPYRUS'):
        if renk in rgbler:
            r = R['sonuc'][renk]
            liste.append(rgbler[renk])
            et.append(f'{renk}: G2 doku (tum ogeler)\nortanca {r["kontrast_ortanca_en_kotu"]} {"PASS" if r["kontrast_ortanca_en_kotu"] >= 4.5 else "FAIL"}, kati {r["kati_en_kotu_bilgi"]}\n'
                      f'kucuk oge parlaklik x{r["kucuk_oge_parlaklik_artisi"]}\nton sapmasi en cok {max(v["dhue_ortanca"] for v in r["renk_sadakati"].values())} derece')
        else:
            liste.append(np.asarray(Image.open(SON / f'CANCER_LIBRA_{renk}_954.png').convert('RGB')))
            et.append(f'{renk}: a5e3ea2 (onayli, aynen)')
    son.onizleme_etiketli(liste, et, font, h_et=130).save(O / 'ONIZLEME_76mm_5RENK.png', dpi=(300, 300))
    # yakin doku: ana sembol, kucuk burc, isim (3x)
    kut = {k: o5.kutu(Y['E'], k) for k in ('sembol', 'kucuk_sol', 'isim1')}
    s = kut['sembol']; ks = kut['kucuk_sol']; i1 = kut['isim1']
    kesit = {'ana sembol': (s[0] + 20, s[1] + 150, s[0] + 120, s[1] + 230), 'kucuk Yengec': (ks[0] - 4, ks[1] - 4, ks[2] + 4, ks[3] + 4),
             'isim EMILY': (i1[0] - 4, i1[1] - 4, i1[2] + 4, i1[3] + 4)}
    satir = []
    for renk in ('RUBY', 'SAPPHIRE', 'EMERALD'):
        parcalar = []
        for ad, bx in kesit.items():
            im = Image.fromarray(rgbler[renk]).crop(bx)
            im = im.resize((im.width * 3, im.height * 3), Image.NEAREST)
            c = Image.new('RGB', (im.width, im.height + 36), 'white'); c.paste(im, (0, 0))
            ImageDraw.Draw(c).text((4, im.height + 4), f'{renk} {ad} (3x)', fill=(20, 20, 20), font=font)
            parcalar.append(c)
        W = sum(c.width for c in parcalar) + 24 * 2; H = max(c.height for c in parcalar)
        sr = Image.new('RGB', (W, H), 'white'); x = 0
        for c in parcalar:
            sr.paste(c, (x, 0)); x += c.width + 24
        satir.append(sr)
    u = Image.new('RGB', (max(s_.width for s_ in satir), sum(s_.height for s_ in satir) + 24 * 2), 'white'); y = 0
    for s_ in satir:
        u.paste(s_, (0, y)); y += s_.height + 24
    u.save(O / 'YAKIN_DOKU.png')
    A = list(R['sonuc'].values())
    g = dict(kontrast_ortanca=all(r['kontrast_ortanca_en_kotu'] >= o4.HEDEF for r in A),
             goruntu_yasak_0=all(sum(r['goruntu_yasak'].values()) == 0 for r in A),
             leke_a_0=all(sum(v['alfa_lt_09'] for k2, v in r['leke'].items() if k2 in o5.LEKE_KAPI_OGE) == 0 for r in A),
             leke_a_kaynak_0=all(v == 0 for v in o5.KAYNAK_SONRA.values()),
             renk_sadakati=all(v['dhue_ortanca'] < 1.0 and v['b_ge_r_yuzde'] == 0 for r in A for v in r['renk_sadakati'].values()),
             yerlesim_ayni=all(r['bosluk_px'] == [20, 20, 20] and r['sembol_kutu'][1] == 246 for r in A),
             artis_yalniz_ruby=all(R['sonuc'][r]['kucuk_oge_parlaklik_artisi'] == 1.0 for r in ('SAPPHIRE', 'EMERALD')))
    g = {k: bool(v) for k, v in g.items()}
    R['kapi'] = g
    R['kaynak_leke_onarim_sonrasi'] = dict(o5.KAYNAK_SONRA)
    (O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=float))
    print('KAPI', json.dumps(g), 'PASS' if all(g.values()) else 'FAIL', flush=True)
    return 0 if all(g.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
