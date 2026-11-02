#!/usr/bin/env python3
"""STIL3_V5 SON (Serdar kararlari 3 Kas): CANCER_LIBRA, EMILY / JAMES, 14 JUNE 2025. Yerel, gercek kaynaklar. Etsy / Printful yazma yok.
Duzen A-T1 (ornament_ornek5.py): halka kilitli (ax 341, tepe y 163), uc T1 (%30 kosinus), bosluklar 20/20/20, sembol V4 boyu.
5 renk: RUBY, SAPPHIRE, EMERALD (altin; kazanc V4 1.12, parlatma yok; kapi ORTANCA kontrast >= 4.5, kati bilgi; halka gomulu kenar %20,
yazilarda golge tonu yok) + BEIGE, AGED_PAPYRUS (bronz P1: yazi / kucuk burc dokusu yalniz koyulastirir, acik uc ana ton; kapi KATI >= 4.5).
Uzun isim B (yalniz RUBY): CAGLAYANGUL / MAXIMILIAN; yalniz isim olcegi kuculur (sembol, logo, tarih, kucuk burclar, bosluklar degismez).
Cikti: 5 x 954 px PNG (Printful dosyasi, kesim cizgisi yok), ONIZLEME_76mm_5RENK.png, UZUN_ISIM_B.png (+ 954 PNG), OLCUM.json.
Kullanim: ornament_son.py --kaynak DIR --cikti DIR"""
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
_s = importlib.util.spec_from_file_location('ornek5', _d / 'ornament_ornek5.py'); o5 = importlib.util.module_from_spec(_s); _s.loader.exec_module(o5)
o4, o3, o1 = o5.o4, o5.o3, o5.o1
N, MM, P, CX, CY = o5.N, o5.MM, o5.P, o5.CX, o5.CY
RENKLER = (('RUBY', 'RUBY_1264.png', 'koyu'), ('SAPPHIRE', 'SAPPHIRE_1264.png', 'koyu'), ('EMERALD', 'EMERALD_1264.png', 'koyu'),
           ('BEIGE', 'BEIGE_1264.png', 'acik'), ('AGED_PAPYRUS', 'AGED_PAPYRUS_1264.png', 'acik'))
GERCEK = {'CANCER_LIBRA_ana.png': 'e86c2629629305fd90bbb66494238faef9b4ad1acb815eb7b3ed55e7f44fc2d2',
          'cancer_symbol_gold.png': '2b5a32121ce8fa92ceef1a386f5ab1742a573681c30e742223be75005816cf28',
          'libra_symbol_gold.png': '6fe2d0355ee56f8468eb637d3ca6445fd517983b00e51bce76cac218864f6a4b',
          'RUBY_1264.png': '7c00922659872003', 'SAPPHIRE_1264.png': '29df83c0cf1d0df4', 'EMERALD_1264.png': 'f0d1483b42810dd0',
          'BEIGE_1264.png': 'a55e7703f65ca3bdaeba6ff5055517f0d4f2ecb2920ee3e5b04d021bbf58d29b',
          'AGED_PAPYRUS_1264.png': '0dfe2f2db5c1996bae7268c77d463b311d85c2b0f7f24d03dc4b2d13b2dd3988'}
S0 = o5.UC_T['T1']
UZUN = ('ÇAĞLAYANGÜL', 'MAXIMILIAN')


def model_kur(td, Y):
    sx = Y['E']['sembol']
    return o1.Model(td, sx[0], sx[1], 4800 * (o1.bbox(sx[1], 0.5)[2] - o1.bbox(sx[1], 0.5)[0]) / 2084)


def olc(Y, model, z, tur, td, pp, ad, rgb, b):
    o5.ayarla(tur, b['deger'])
    rgb0 = o4.boya(Y, model, z, b['kazanc'], td, 0.0, doku_kapali=True)
    rgbb = o4.boya(Y, model, z, b['kazanc'], td, b['dg'], butunlesme=False)
    tumm = np.maximum.reduce([Y['M'][k] for k in Y['M']])
    gy, gb = o4.goruntu_yasak(rgb, z, Y['M'].get('halka'))
    kut = o5.kutu(Y['E'], 'sembol')
    return dict(tur=tur, ton=('altin kazanci ' if tur == 'koyu' else 'bronz carpani ') + str(b['deger']),
                bronz_ana_rgb=[round(float(v), 1) for v in o5.BRONZ['ana'] * b['deger']] if tur == 'acik' else None,
                kapi_olcutu=b['kapi_olcutu'], en_kotu_kontrast=round(b['en'], 2), en_kotu_kati_bilgi=round(b['en_kati'], 2),
                hedef_tuttu=b['en'] >= o4.HEDEF, kontrast=b['ok'],
                bosluk_px=o5.bosluklar(Y['E']), sembol_kutu=list(kut), sembol_px=[kut[2] - kut[0], kut[3] - kut[1]],
                isim_guvenli_daireye_px=o5.isim_guvenli(Y['E']), yasak_piksel=Y['yasak'], cakisma=Y['cak'],
                goruntu_yasak=gy, goruntu=gb, doku_oge=o4.doku_oge(rgb, rgb0, Y['M']),
                isik=o4.glow_olc(rgb, rgbb, tumm) if tur == 'koyu' else 'kapali (acik zemin)',
                leke=o5.leke_kapisi(Y['M'], rgb, b['Lc']), halka_uc=o5.halka_uc_olc(Y['M']['halka'], Y['halka'], pp))


def onizleme_etiketli(rgbler, etiketler, font, ara=24, h_et=150):
    im = o4.onizleme(rgbler, ara=ara)
    tile = (im.width - ara * (len(rgbler) - 1)) // len(rgbler)
    b = Image.new('RGB', (im.width, im.height + h_et), 'white'); b.paste(im, (0, 0)); d = ImageDraw.Draw(b)
    for i, t in enumerate(etiketler):
        for j, line in enumerate(t.split('\n')):
            d.text((i * (tile + ara) + 6, im.height + 8 + j * 28), line, fill=(20, 20, 20), font=font)
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    K, O = Path(a.kaynak), Path(a.cikti)
    O.mkdir(parents=True, exist_ok=True)
    for f, h in GERCEK.items():
        if not o1.sha(K / f).startswith(h):
            print('FAIL kaynak sha', f, o1.sha(K / f)[:16], flush=True); return 1
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

    def metinler(ad1, ad2, isim_olcek=1.0):
        k = cap * o4.LOGO_H / lsrc.shape[0]
        la = np.clip(cv2.resize(lsrc, (max(1, int(round(lsrc.shape[1] * k))), max(1, int(round(cap * o4.LOGO_H)))), interpolation=cv2.INTER_AREA), 0, 1)
        return dict(isim1=o1.metin_alfa(ad1, K / 'Cinzel.ttf', cap * isim_olcek, 500), isim2=o1.metin_alfa(ad2, K / 'Cinzel.ttf', cap * isim_olcek, 500),
                    tarih=o1.metin_alfa('14 JUNE 2025', K / 'EBGaramond-Italic.ttf', P['tagline_T'] / P['cap'] * cap, None, ref='T'), sonsuz=la, cap=cap)
    kc = {'sol': kucuk('cancer', P['kucuk_sol_h'] / P['cap']), 'sag': kucuk('libra', P['kucuk_sag_h'] / P['cap'])}
    ha, hb = o5.halka_T(pp, S0)
    Y, bilgi = o5.yerlesim_V5(pp, ana5, metinler('EMILY', 'JAMES'), kc, ha, hb, G)
    if Y is None:
        print('FAIL yerlesim', bilgi, flush=True); return 1
    o4.YAZI_OGE = o4.YAZI_OGE + ('halka',) if 'halka' not in o4.YAZI_OGE else o4.YAZI_OGE
    o5.AKTIF.update(A=True, pvar='P1')
    model = model_kur(td, Y)
    R = {'kaynak_sha256': {f.name: o1.sha(f) for f in sorted(K.iterdir()) if f.is_file()}, 'kaynak_kontrol': 'GERCEK sha listesi tuttu',
         'karar': 'Serdar 3 Kas: acik zemin yazi P1, halka ucu T1, uzun isim B (yalniz isim olcegi), 5 renk',
         'yerlesim': bilgi, 'bosluk_hedef_px': G, 'sonuc': {}}
    rgbler, etiketler = [], []
    font = ImageFont.truetype(str(K / 'EBGaramond-Italic.ttf'), 24)
    for ad, zf, tur in RENKLER:
        z = o1.zemin_canva(K / zf)
        b = o5.boya_sec(Y, model, z, tur, td, pp, S0, sabit=o5.ALTIN_SABIT if tur == 'koyu' else None)
        rgb = b['rgb']
        r = olc(Y, model, z, tur, td, pp, ad, rgb, b)
        R['sonuc'][ad] = r
        o1.kaydet(rgb, O / f'CANCER_LIBRA_{ad}_954.png')
        rgbler.append(rgb)
        hu = r['halka_uc']
        u2 = r['kontrast'].get('halka_uclari_2px_alti', {})
        la = sum(v['alfa_lt_09'] for k_, v in r['leke'].items() if k_ in o5.LEKE_KAPI_OGE)
        lb = sum((v['acik_piksel'] or 0) for v in r['leke'].values())
        etiketler.append(f'{ad}: {r["ton"]}\n'
                         f'kontrast ({r["kapi_olcutu"]}) {r["en_kotu_kontrast"]} {"PASS" if r["hedef_tuttu"] else "FAIL"}, kati {r["en_kotu_kati_bilgi"]}\n'
                         f'bosluk {r["bosluk_px"][0]}/{r["bosluk_px"][1]}/{r["bosluk_px"][2]} px, sembol y {r["sembol_kutu"][1]}\n'
                         f'leke a {la} b {lb}; {"gomulu kenar yok" if tur == "acik" else "halka gomulu kenar %20"}\n'
                         f'uc < 0.17 mm {hu["sag"]["ince_2px_mm"]} / {hu["sol"]["ince_2px_mm"]} mm, kati {u2.get("deger")}')
        print(ad, r['ton'], 'kontrast', r['en_kotu_kontrast'], r['kapi_olcutu'], 'kati', r['en_kotu_kati_bilgi'], 'bosluk', r['bosluk_px'],
              'sembol', r['sembol_kutu'], 'yasak', sum(r['goruntu_yasak'].values()), 'cak', r['cakisma'], 'leke a', la, 'b', lb,
              'doku', min(r['doku_oge'].values()), max(r['doku_oge'].values()), flush=True)
    onizleme_etiketli(rgbler, etiketler, font).save(O / 'ONIZLEME_76mm_5RENK.png', dpi=(300, 300))
    # uzun isim B: yalniz isim olcegi; sembol yeri ve boyu, logo, tarih, kucuk burclar, bosluk ayni
    sem_A = Y['E']['sembol']
    alt_A = bilgi['alt']

    def uzun_yer(sc):
        E = o5.blok(metinler(*UZUN, isim_olcek=sc), kc, alt_A, G)
        E['halka'] = (None, ha, 0, 0)
        E['sembol'] = sem_A
        M_, yb, cak, ok = o4.kapi(E)
        return dict(E=E, M=M_, yasak=yb, cak=cak, halka=hb), ok
    def ara(fn):
        if fn(1.0)[1]:
            return 1.0
        lo, hi, en = 0.30, 1.0, None
        while hi - lo > 0.005:
            sc = (lo + hi) / 2
            if fn(sc)[1]:
                lo, en = sc, sc
            else:
                hi = sc
        return en

    def uzun_kayan(sc):                                                # V5 olcumuyle ayni: yazi blogu en asagi gecerli yerde, sembol yalniz yukari
        Yk, _ = o5.yerlesim_V5(pp, ana5, metinler(*UZUN, isim_olcek=sc), kc, ha, hb, G)
        return Yk, Yk is not None
    z = o1.zemin_canva(K / 'RUBY_1264.png')
    varyant = {}
    for vad, fn in (('B_blok_kayan', uzun_kayan), ('B_yer_sabit', uzun_yer)):
        en = ara(fn)
        YU, ok = fn(en)
        mU = model_kur(td, YU)
        bU = o5.boya_sec(YU, mU, z, 'koyu', td, pp, S0, sabit=o5.ALTIN_SABIT)
        rU = olc(YU, mU, z, 'koyu', td, pp, 'RUBY', bU['rgb'], bU)
        tasma = {}
        for k_, isim in (('isim1', UZUN[0]), ('isim2', UZUN[1])):
            A_, t_ = metinler(*UZUN, isim_olcek=en)[k_]
            bb = o1.bbox(A_, 0.5)
            tasma[isim] = dict(genislik_px=bb[2] - bb[0], ust_buyuk_harf_ustu_px=int(round((t_ - cap * en) - bb[1])), alt_taban_alti_px=int(round(bb[3] - t_)))
        varyant[vad] = dict(isim_olcegi=round(en, 3), buyuk_harf_px=round(cap * en, 1), buyuk_harf_mm=round(cap * en * MM, 2), aksan=tasma,
                            kapi_gecti=bool(ok), sembol_kutu=rU['sembol_kutu'], tarih_kutu=list(o5.kutu(YU['E'], 'tarih')), sonuc=rU, rgb=bU['rgb'])
        o1.kaydet(bU['rgb'], O / f'CANCER_LIBRA_RUBY_UZUN_ISIM_{vad}_954.png')
        print('UZUN', vad, 'olcek', round(en, 3), 'harf mm', round(cap * en * MM, 2), 'kontrast', rU['en_kotu_kontrast'], 'bosluk', rU['bosluk_px'],
              'sembol', rU['sembol_kutu'], 'kapi', ok, flush=True)
    R['uzun_isim_B'] = dict(isimler=list(UZUN), kural='B: yalniz isim olcegi kuculur; sembol / logo / tarih / kucuk burclar boyu ve bosluklar ayni',
                            not_=('B_blok_kayan: V5 raporundaki 0.557 olcumuyle ayni yontem (yazi blogu en asagi gecerli yerde, sembol yalniz yukari; '
                                  'yerler degisebilir). B_yer_sabit: tarih ve sembol A-T1 yerinde sabit; isim satiri dairenin dar alt kisminda kalir. '
                                  'Hangisi B: Serdar karari.'),
                            varyant={k: {kk: vv for kk, vv in v.items() if kk != 'rgb'} for k, v in varyant.items()})
    et = []
    for vad, v in varyant.items():
        rU = v['sonuc']
        et.append(f'{vad}: isim olcegi {v["isim_olcegi"]}, buyuk harf {v["buyuk_harf_mm"]} mm (11 harf)\n'
                  f'kontrast (ortanca) {rU["en_kotu_kontrast"]} {"PASS" if rU["hedef_tuttu"] else "FAIL"}, kati {rU["en_kotu_kati_bilgi"]}\n'
                  f'bosluk {rU["bosluk_px"][0]}/{rU["bosluk_px"][1]}/{rU["bosluk_px"][2]} px, sembol y {v["sembol_kutu"][1]}, tarih alt {v["tarih_kutu"][3]}\n'
                  f'aksan: ÇAĞLAYANGÜL ust {v["aksan"][UZUN[0]]["ust_buyuk_harf_ustu_px"]} px, alt {v["aksan"][UZUN[0]]["alt_taban_alti_px"]} px')
    onizleme_etiketli([v['rgb'] for v in varyant.values()], et, font, h_et=130).save(O / 'UZUN_ISIM_B.png', dpi=(300, 300))
    rU = varyant['B_blok_kayan']['sonuc']
    ok = varyant['B_blok_kayan']['kapi_gecti'] and varyant['B_yer_sabit']['kapi_gecti']
    A = list(R['sonuc'].values()) + [v['sonuc'] for v in varyant.values()]
    g = dict(yasak_0=all(sum(r['yasak_piksel'].values()) == 0 for r in A), cakisma_0=all(not r['cakisma'] for r in A),
             goruntu_yasak_0=all(sum(r['goruntu_yasak'].values()) == 0 for r in A), kontrast=all(r['hedef_tuttu'] for r in A),
             bosluk_ge_hedef=all(min(r['bosluk_px']) >= o5.BOSLUK_ORAN * cap for r in R['sonuc'].values()),
             leke_a_0=all(sum(v['alfa_lt_09'] for k_, v in r['leke'].items() if k_ in o5.LEKE_KAPI_OGE) == 0 for r in A),
             leke_a_kaynak_0=all(v == 0 for v in o5.KAYNAK_SONRA.values()),
             leke_b_0=all(sum((v['acik_piksel'] or 0) for v in r['leke'].values()) == 0 for r in A),
             doku_4_6=all(4.0 <= min(r['doku_oge'].values()) and max(r['doku_oge'].values()) <= 6.0 for r in A),
             isik_4_10_koyu=all(4 <= r['isik']['p95_px'] and r['isik']['uzanim_px'] <= 10 for r in A if r['tur'] == 'koyu'),
             uzun_isim_B=bool(ok))
    hm = Y['M']['halka']
    col = hm[130:200, int(CX)]
    g['halka_kilit'] = abs(float((np.arange(130, 200) * col).sum() / max(col.sum(), 1e-6)) + 0.5 - o4.DELIK[1]) < 0.6
    g = {k: bool(v) for k, v in g.items()}
    R['kapi'] = g
    R['kaynak_leke_onarim_sonrasi'] = dict(o5.KAYNAK_SONRA)
    (O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=float))
    print('KAPI', json.dumps(g), 'PASS' if all(g.values()) else 'FAIL', flush=True)
    return 0 if all(g.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
