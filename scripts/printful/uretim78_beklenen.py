#!/usr/bin/env python3
"""Ornament 78 ORNEK kosusu beklentileri (Serdar 4 Kas; 2. kisim kosusu icin; ornament-78-uretim.yml birlestirme isi): BEKLENEN_SONUC_ORNEK.json.
Her beklenti PASS/FAIL + kaynak:
  cl_kontrol_her_parca     her parcada CANCER_LIBRA kontrol_pass (BIRLESIK kontrol_parca)
  ornek_png_drive          ornek ciftlerinin her biri 5 PNG ile yuklendi (kok ya da FAIL/<CIFT>/) ve Drive sha karsilastirmasi PASS
  kova_tek_neden           AQUARIUS iceren ornek ciftlerinde kenar_onarimsiz_neden gecti (tek neden leke_a_kaynak_0)
  printful_dosya           yeni ciktilarda printful_dosya_<STIL> hepsi True
  dpi_piksel_ayni          dpi yazimi oncesi = sonrasi piksel sha (5 stil)
  o2_piksel                SADE_ALTIN piksel sha = SADE_1 piksel sha = FILDISI girdi piksel sha
  kenar_on_motor           kenar on olcumu = motor KENAR_ONARIM (cift x kaynak: n0, degisen piksel)
  aquarius_445_464         on olcum aquarius n0 445 / degisen 464 = KOVA_KAPI_TESTI (mod acik) (41839101824 degerleri)
  eta_satirlari            her parca logunda cift sayisi kadar ETA satiri
  katman_silindi           cift sonunda katman.pkl ve dump/ yok
  siparis_kaydi            hazirlik ve her parca siparis kontrol kaydi var
  onarimsiz_ek_fail_listesi BIRLESIK kenar_onarimsiz_ek_fail alani var (bilgi)
  birlesik_gecti           BIRLESIK gecti (eksik parca yok, cift FAIL yok, cokus yok, kontrol, Drive)
  --bolum yeni_duzen | yd67 (Serdar 4 Kas gece asama 2; 5 Kas PLAN67) ek beklentiler:
  yeni_duzen_modu          her ciftte kapi.sert yeni_duzen_kapilari_var True (motor yd_* kapilari var, 20/20/20 yok)
  yd_yerel_test            hazirlik YD_YERLESIM78_TEST.json: ref = SABIT, 78/78 PASS, bilinen FAIL hepsi beklenen kapidan
Cikis: 0 hepsi PASS, 1 en az biri FAIL, 2 cokus."""
import argparse
import json
import sys
from pathlib import Path

STIL = ('RUBY', 'SAPPHIRE', 'EMERALD', 'SADE_ALTIN', 'FILDISI')


def oku(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:                                                          # noqa: BLE001
        return None


def beklenti(B, kapi, kenar, siparis, parca_dir, ornek, bolum='ornek', yd_test=None):
    out = []

    def b(ad, gecti, olculen, kaynak):
        out.append(dict(beklenti=ad, gecti=bool(gecti), olculen=olculen, kaynak=kaynak))

    B = B or {}
    C = B.get('cift', {})
    kp = B.get('kontrol_parca', {})
    b('cl_kontrol_her_parca', bool(kp) and all(v.get('kontrol_pass') is True for v in kp.values()), {k: v.get('kontrol_pass') for k, v in kp.items()}, 'BIRLESIK kontrol_parca')
    yuk = {}
    for x in B.get('yukleme', []):
        yuk[x.get('cift')] = [y['yol'] for y in (x.get('yukleme') or {}).get('dosyalar', []) if y['yol'].endswith('_954.png')]
    png_ok = all(len(yuk.get(c, [])) == 5 for c in ornek)
    b('ornek_png_drive', png_ok and (B.get('drive') or {}).get('gecti') is True, dict(png={c: len(yuk.get(c, [])) for c in ornek}, drive=(B.get('drive') or {}).get('gecti')),
      'BIRLESIK yukleme + drive')
    kova = [c for c in ornek if 'AQUARIUS' in c.split('_')]
    kn = {c: ((C.get(c) or {}).get('kenar_onarimsiz_neden') or {}).get('gecti') for c in kova}
    b('kova_tek_neden', bool(kova) and all(v is True for v in kn.values()), kn, 'BIRLESIK cift.kenar_onarimsiz_neden')
    pf = {c: {s: ((C.get(c) or {}).get('kapi') or {}).get('sert', {}).get(f'printful_dosya_{s}') for s in STIL} for c in ornek}
    b('printful_dosya', all(all(v is True for v in d.values()) for d in pf.values()), pf, 'BIRLESIK cift.kapi.sert.printful_dosya_*')
    dp = {c: {s: v.get('piksel_ayni') for s, v in ((C.get(c) or {}).get('dpi_yazim') or {}).items()} for c in ornek}
    b('dpi_piksel_ayni', all(len(d) == 5 and all(v is True for v in d.values()) for d in dp.values()), dp, 'BIRLESIK cift.dpi_yazim')
    o2 = {}
    for c in ornek:
        sd = (C.get(c) or {}).get('sade') or {}; fd = (C.get(c) or {}).get('fildisi') or {}
        o2[c] = bool(sd.get('sade1_piksel_sha') and sd.get('sade1_piksel_sha') == sd.get('sade_altin_piksel_sha') == fd.get('girdi_piksel_sha'))
    b('o2_piksel', all(o2.values()) and bool(o2), o2, 'BIRLESIK cift.sade / fildisi piksel sha (ZAYIF: sade1 ve fildisi girdisi ayni dosya; anlamli kisim SADE_ALTIN dpi sonrasi = sade1)')
    km, kf = {}, []
    K = (kenar or {}).get('kaynak', {})
    for c in ornek:
        mk = (C.get(c) or {}).get('kaynak_kenar_onarim') or {}
        for kay, v in mk.items():
            on = K.get(f'{c}_ana' if kay == 'ana' else kay)
            ok_ = bool(on) and on['n0'] == v['n0'] and on['degisen_piksel'] == v['degisen_piksel']
            km[f'{c}/{kay}'] = ok_
            if not ok_:
                kf.append(dict(cift=c, kaynak=kay, motor=dict(n0=v['n0'], degisen=v['degisen_piksel']), on_olcum=on))
    b('kenar_on_motor', bool(km) and all(km.values()), dict(eslesen=sum(km.values()), toplam=len(km), farkli=kf), 'KENAR_ON_OLCUM + motor kaynak_kenar_onarim')
    aq = K.get('aquarius') or {}
    kt = None
    for t in (kapi or {}).get('kaynaklar', []):
        if t.get('kaynak', '').startswith('aquarius'):
            kt = t['mod_acik_bilgi']['kenar_onar']
    b('aquarius_445_464', aq.get('n0') == 445 and aq.get('degisen_piksel') == 464 and kt is not None and kt['n0'] == 445 and kt['degisen_piksel'] == 464,
      dict(on_olcum=[aq.get('n0'), aq.get('degisen_piksel')], kapi_testi=[kt and kt['n0'], kt and kt['degisen_piksel']]), 'KENAR_ON_OLCUM + KOVA_KAPI_TESTI (41839101824: 445/464)')
    eta = {}
    for d in sorted(Path(parca_dir).glob('PARCA_*')):
        lg = d / 'log_ornek78.txt'; R = oku(d / 'OLCUM.json') or {}
        n = len(R.get('cift_sonu', []))
        eta[d.name] = dict(eta=sum(1 for l in (lg.read_text().splitlines() if lg.exists() else []) if ' ETA ' in l), cift=n)
    b('eta_satirlari', bool(eta) and all(v['eta'] == v['cift'] and v['cift'] > 0 for v in eta.values()), eta, 'parca log_ornek78.txt')
    tm = {x.get('cift'): x.get('temizlik') for x in B.get('yukleme', [])}
    b('katman_silindi', bool(tm) and all(v and not v['katman_pkl_var'] and not v['dump_var'] for v in tm.values()), tm, 'BIRLESIK yukleme.temizlik')
    sp = {d.name: (d / 'SIPARIS.json').exists() for d in sorted(Path(parca_dir).glob('PARCA_*'))}
    b('siparis_kaydi', bool(siparis and siparis.get('akislar')) and bool(sp) and all(sp.values()), dict(hazirlik=len((siparis or {}).get('akislar', [])), parca=sp),
      'SIPARIS_HAZIRLIK.json + PARCA_*/SIPARIS.json')
    b('onarimsiz_ek_fail_listesi', 'kenar_onarimsiz_ek_fail' in B, B.get('kenar_onarimsiz_ek_fail'), 'BIRLESIK (bilgi)')
    b('birlesik_gecti', B.get('gecti') is True, dict(eksik_parca=B.get('eksik_parca'), fail=B.get('fail'), cokus=B.get('cokus')), 'BIRLESIK')
    if bolum in ('yeni_duzen', 'yd67'):                                     # yeni duzen bolumleri (uretim78.YD_BOLUMLER; Serdar 5 Kas PLAN67)
        ym = {c: ((C.get(c) or {}).get('kapi') or {}).get('sert', {}).get('yeni_duzen_kapilari_var') for c in ornek}
        b('yeni_duzen_modu', bool(ym) and all(v is True for v in ym.values()), ym, 'BIRLESIK cift.kapi.sert.yeni_duzen_kapilari_var')
        T = yd_test or {}
        b('yd_yerel_test', T.get('ref_sabit_esit') is True and T.get('gecen') == 78 and not T.get('fail') and T.get('bilinen_fail_hepsi') is True
          and T.get('bilinen_fail_sayi') == 45,                                      # K-1b-10: 3 cift x 15 vaka (yeni_duzen_yerel_test BF_VAKA)
          dict(ref_sabit=T.get('ref_sabit_esit'), gecen=T.get('gecen'), fail=T.get('fail'), bilinen_fail=[T.get('bilinen_fail_hepsi'), T.get('bilinen_fail_sayi')]),
          'hazirlik YD_YERLESIM78_TEST.json (yeni_duzen_yerel_test.py, is akisi Pillow 11.0.0)')
    return dict(beklentiler=out, hepsi_gecti=all(x['gecti'] for x in out))


def ornek_listesi(J, bolum):
    """bolumun uretim ciftleri (beklenen PNG listesi): parcalar + (cl_yeni_parca varsa) CL. yd67: 67 cift, CL yok (PLAN67)."""
    return [c for p in J[bolum]['parcalar'] for c in p] + (['CANCER_LIBRA'] if J[bolum].get('cl_yeni_parca') else [])


def main():
    ap = argparse.ArgumentParser()
    for k in ('birlesik', 'kapi', 'kenar_on', 'siparis', 'parca_dir', 'ciftler_json', 'cikti'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--bolum', default='ornek', choices=('ornek', 'yeni_duzen', 'yd67')); ap.add_argument('--yd_test')
    a = ap.parse_args()
    J = json.loads(Path(a.ciftler_json).read_text())
    ornek = ornek_listesi(J, a.bolum)
    R = beklenti(oku(a.birlesik), oku(a.kapi), oku(a.kenar_on), oku(a.siparis), a.parca_dir, ornek, a.bolum, oku(a.yd_test) if a.yd_test else None)
    Path(a.cikti).write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str))
    for x in R['beklentiler']:
        print('PASS' if x['gecti'] else 'FAIL', x['beklenti'], '|', json.dumps(x['olculen'], default=str)[:200], flush=True)
    print('BEKLENEN_' + a.bolum.upper(), 'PASS' if R['hepsi_gecti'] else 'FAIL', flush=True)
    return 0 if R['hepsi_gecti'] else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                                                          # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.exit(2)
