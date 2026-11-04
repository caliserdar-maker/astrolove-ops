#!/usr/bin/env python3
"""Sikilastirma (Serdar 4 Kas) yerel MANTIK testleri: motor girdisi yalniz Actions'ta oldugu icin kapi mantigi sahte OLCUM / degerle denenir.
Her kapi bilinen PASS + bilinen FAIL (KALITE 3). Cikis: 0 tum vakalar beklendigi gibi, 1 en az biri degil, 2 cokus.
  1) kucult_sinir_oku (ornament_motor): bos -> 2 (sabit); '1' -> 1; '-1' -> -1; '2' -> 2; '3' -> ValueError (gevsetme yasak); 'x' -> ValueError
  2) kucultme_le_sinir motor icinde: gercek motor kosusuyla sinanir (burada yok)
  3) onarimsiz_neden (ornek78): tek neden leke -> PASS; cikis 2 / cikis 0 / baska neden / leke + baska FAIL / kosmadi / OLCUM yok / kaynak leke 0 -> FAIL
  4) dusuk_kontrast_liste (ornek78): kati alti / ortanca alti listede; ikisi de ustu listede degil; SADE ortanca kullanilmaz; CL ayri bilgi
  5) onayli_kiyas (ornek78): ayni PASS; 1 pikselde 5 seviye FAIL; 11 pikselde 1 seviye FAIL; eksik dosya FAIL
Kullanim: sikilastirma_mantik_testi.py --cikti DIR"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

_d = Path(__file__).resolve().parent


def yukle(ad, dosya):
    s = importlib.util.spec_from_file_location(ad, _d / dosya); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--cikti', required=True); a = ap.parse_args()
    O = Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
    mo = yukle('motor', 'ornament_motor.py'); o78 = yukle('o78', 'ornek78.py')
    V = []

    def vaka(ad, beklenen, f):
        try:
            sonuc = f()
        except Exception as e:                                                # noqa: BLE001
            sonuc = f'HATA {type(e).__name__}'
        V.append(dict(vaka=ad, beklenen=beklenen, sonuc=sonuc, gecti=sonuc == beklenen))

    # 1 sinir okuma
    vaka('sinir bos -> 2 sabit', [2, 'sabit'], lambda: list(mo.kucult_sinir_oku({})))
    vaka('sinir 1', 1, lambda: mo.kucult_sinir_oku({'ORN_KUCULT_SINIR_PX': '1'})[0])
    vaka('sinir -1 (yerel bilinen FAIL icin)', -1, lambda: mo.kucult_sinir_oku({'ORN_KUCULT_SINIR_PX': '-1'})[0])
    vaka('sinir 2', 2, lambda: mo.kucult_sinir_oku({'ORN_KUCULT_SINIR_PX': '2'})[0])
    vaka('sinir 3 reddedilir (bilinen FAIL)', 'HATA ValueError', lambda: mo.kucult_sinir_oku({'ORN_KUCULT_SINIR_PX': '3'}))
    vaka('sinir x reddedilir', 'HATA ValueError', lambda: mo.kucult_sinir_oku({'ORN_KUCULT_SINIR_PX': 'x'}))
    # 2 kapi ifadesi motor icinde (g['kucultme_le_sinir'] = KUCULT[0] <= SINIR_PX): mantik testinde sinanmaz (zayif olurdu); bilinen FAIL gercek
    #   motor kosusuyla: yerel sahte Kova ORN_KUCULT_SINIR_PX=-1 -> cikis 1, tek FAIL kucultme_le_sinir; Actions GV sinir 1 adimi.
    # 3 onarimsiz neden
    iyi = dict(kapi_sert=dict(leke_a_kaynak_0=False, leke_a_0=True), cikis=dict(kod=1, fail=['leke_a_kaynak_0']), kaynak_leke_onarim_sonrasi=dict(aquarius=445, pisces=0))
    vaka('neden leke PASS', True, lambda: o78.onarimsiz_neden(1, iyi, ['aquarius'])[0])
    vaka('cikis 2 FAIL', False, lambda: o78.onarimsiz_neden(2, iyi, ['aquarius'])[0])
    vaka('cikis 0 FAIL', False, lambda: o78.onarimsiz_neden(0, iyi, ['aquarius'])[0])
    vaka('kosmadi FAIL', False, lambda: o78.onarimsiz_neden(None, iyi, ['aquarius'])[0])
    vaka('OLCUM yok FAIL', False, lambda: o78.onarimsiz_neden(1, None, ['aquarius'])[0])
    baska = dict(kapi_sert=dict(leke_a_kaynak_0=True, ton=False), cikis=dict(kod=1, fail=['ton']), kaynak_leke_onarim_sonrasi=dict(aquarius=0))
    vaka('baska neden (ton) FAIL', False, lambda: o78.onarimsiz_neden(1, baska, ['aquarius'])[0])
    coklu = dict(kapi_sert=dict(leke_a_kaynak_0=False, ton=False), cikis=dict(kod=1, fail=['leke_a_kaynak_0', 'ton']), kaynak_leke_onarim_sonrasi=dict(aquarius=445))
    vaka('leke + baska sert FAIL (tek neden degil) FAIL', False, lambda: o78.onarimsiz_neden(1, coklu, ['aquarius'])[0])
    sifir = dict(kapi_sert=dict(leke_a_kaynak_0=False), cikis=dict(kod=1, fail=['leke_a_kaynak_0']), kaynak_leke_onarim_sonrasi=dict(aquarius=0, ana=3))
    vaka('onarilan kaynakta leke 0 FAIL', False, lambda: o78.onarimsiz_neden(1, sifir, ['aquarius'])[0])
    # 4 dusuk kontrast
    def d(k, o):
        return dict(kati=round(k, 2), ortanca=round(o, 2), kati_ham=k, ortanca_ham=o, en_kotu_oge='x')
    C = dict(CANCER_LIBRA=dict(SADE_ALTIN=d(1.5361, 2.0), FILDISI=d(1.3101, 2.4801)),
             A=dict(SADE_ALTIN=d(1.35, 9.0), FILDISI=d(1.20, 2.60)),          # SADE kati alti; FILDISI kati alti
             B=dict(SADE_ALTIN=d(1.60, 0.10), FILDISI=d(1.40, 2.40)),         # SADE ortanca dusuk ama SADE'de ortanca yok (liste disi); FILDISI ortanca alti
             C=dict(SADE_ALTIN=d(1.54, 1.0), FILDISI=d(1.31, 2.48)))          # tam duzeyde: liste disi
    L = o78.dusuk_kontrast_liste(C)
    ls = lambda s: sorted(x['cift'] for x in L['liste'][s])
    vaka('SADE listesi (kati alti; CL 1,5361 < 1,54 ham)', ['A', 'CANCER_LIBRA'], lambda: ls('SADE_ALTIN'))
    vaka('FILDISI listesi (kati alti A, ortanca alti B)', ['A', 'B'], lambda: ls('FILDISI'))
    vaka('CL ayri bilgi alani', True, lambda: 'SADE_ALTIN' in L['cancer_libra_bu_kosu_bilgi'] and 'FILDISI' in L['cancer_libra_bu_kosu_bilgi'])
    # 4b gercek r yapisi (ornek78 R['cift'] bicimi) -> dusuk_kontrast_girdi -> liste (deneme 1 KeyError 'kati' bu yoldaydi)
    rc = dict(A=dict(sade=dict(kati_kontrast=1.35, ortanca=2.0, kati_ham=1.3512, ortanca_ham=2.0, en_kotu_oge='kucuk_sol'),
                     fildisi=dict(kontrast_bilgi=dict(kati=1.15, ortanca=2.15, kati_ham=1.1503, ortanca_ham=2.1501, kati_en_kotu_oge='halka_govde'))),
              B=dict(eksik=['RUBY']))
    vaka('gercek r yapisi SADE + FILDISI listede', [['A'], ['A']],
         lambda: [sorted(x['cift'] for x in o78.dusuk_kontrast_liste(o78.dusuk_kontrast_girdi(rc))['liste'][s_]) for s_ in ('SADE_ALTIN', 'FILDISI')])
    # 5 onayli kiyas (ornek78.onayli_kiyas): ayni -> PASS; 1 pikselde 5 seviye -> FAIL; 11 pikselde 1 seviye -> FAIL; eksik -> FAIL
    import numpy as np
    from PIL import Image
    ka, kb_ = O / 'kiyas_a', O / 'kiyas_b'; ka.mkdir(exist_ok=True); kb_.mkdir(exist_ok=True)
    base = (np.random.default_rng(1).integers(0, 255, (60, 60, 3))).astype(np.uint8)
    Image.fromarray(base).save(ka / 'X_Y_RUBY_954.png'); Image.fromarray(base).save(kb_ / 'X_Y_RUBY_954.png')
    b2 = base.copy(); b2[5, 5] = np.clip(b2[5, 5].astype(int) + 5, 0, 255); Image.fromarray(b2).save(ka / 'X_Y_SAPPHIRE_954.png'); Image.fromarray(base).save(kb_ / 'X_Y_SAPPHIRE_954.png')
    b3 = base.copy(); b3[:11, 0, 0] = np.where(b3[:11, 0, 0] < 255, b3[:11, 0, 0] + 1, 254); Image.fromarray(b3).save(ka / 'X_Y_EMERALD_954.png'); Image.fromarray(base).save(kb_ / 'X_Y_EMERALD_954.png')
    K_ = o78.onayli_kiyas(ka, 'X_Y', kb_, ('RUBY', 'SAPPHIRE', 'EMERALD', 'SADE_ALTIN'))
    vaka('onayli kiyas ayni PASS', True, lambda: K_['RUBY']['tolerans_icinde'])
    vaka('onayli kiyas 5 seviye FAIL', False, lambda: K_['SAPPHIRE']['tolerans_icinde'])
    vaka('onayli kiyas 11 piksel FAIL', False, lambda: K_['EMERALD']['tolerans_icinde'])
    vaka('onayli kiyas eksik dosya FAIL', False, lambda: K_['SADE_ALTIN']['tolerans_icinde'])
    R = dict(vakalar=V, test_gecti=all(v['gecti'] for v in V), tur='mantik testi (sahte OLCUM / deger; motor girdisi yalniz Actions)')
    (O / 'MANTIK_TESTI.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str))
    for v in V:
        print('PASS' if v['gecti'] else 'FAIL', v['vaka'], '| beklenen', v['beklenen'], '| sonuc', v['sonuc'], flush=True)
    print('MANTIK TESTI', 'PASS' if R['test_gecti'] else 'FAIL', flush=True)
    return 0 if R['test_gecti'] else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                                                          # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.exit(2)
